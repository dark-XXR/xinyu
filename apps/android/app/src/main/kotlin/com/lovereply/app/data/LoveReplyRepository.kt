package com.lovereply.app.data

import com.love_reply.generated.api.AUTHApi
import com.love_reply.generated.api.ENTITLEMENTApi
import com.love_reply.generated.api.GENERATIONApi
import com.love_reply.generated.infrastructure.ApiClient
import com.love_reply.generated.infrastructure.Serializer
import com.love_reply.generated.model.CommunicationGoal
import com.love_reply.generated.model.CreateGenerationRequest
import com.love_reply.generated.model.GenerationContext
import com.love_reply.generated.model.GenerationInput
import com.love_reply.generated.model.GenerationQuoteRequest
import com.love_reply.generated.model.GenerationSnapshot
import com.love_reply.generated.model.GenerationStatus
import com.love_reply.generated.model.RefreshRequest
import com.love_reply.generated.model.RelationshipStage
import com.love_reply.generated.model.SmsLoginRequest
import com.love_reply.generated.model.SmsPurpose
import com.love_reply.generated.model.SmsSendRequest
import com.lovereply.app.domain.ApiFailure
import com.lovereply.app.domain.ComposerDraft
import com.lovereply.app.domain.EntitlementSummary
import com.lovereply.app.domain.GenerationPhase
import com.lovereply.app.domain.GenerationQuoteSummary
import com.lovereply.app.domain.GenerationResult
import com.lovereply.app.domain.ReplyAnalysis
import com.lovereply.app.domain.ReplyCandidate
import com.lovereply.app.domain.SmsChallenge
import java.io.IOException
import java.util.UUID
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import retrofit2.Response

interface LoveReplyRepository {
    fun hasSession(): Boolean
    suspend fun sendSms(countryCode: String, phoneNumber: String): SmsChallenge
    suspend fun login(challengeId: String, code: String)
    suspend fun getEntitlements(): EntitlementSummary
    suspend fun quote(draft: ComposerDraft): GenerationQuoteSummary
    suspend fun create(draft: ComposerDraft, quote: GenerationQuoteSummary): GenerationResult
    suspend fun getGeneration(generationId: String): GenerationResult
    fun clearSession()
}

class NetworkLoveReplyRepository(
    private val baseUrl: String,
    private val sessionStore: SessionStore,
    private val deviceIdStore: DeviceIdStore,
) : LoveReplyRepository {
    private val refreshMutex = Mutex()
    private val errorAdapter = Serializer.moshiBuilder.build().adapter(ApiErrorEnvelope::class.java)

    override fun hasSession(): Boolean = sessionStore.read() != null

    override suspend fun sendSms(countryCode: String, phoneNumber: String): SmsChallenge {
        val api = anonymousClient().createService(AUTHApi::class.java)
        val response = networkCall {
            api.sendSmsChallenge(
                xClientVersion = CLIENT_VERSION,
                xPlatform = AUTHApi.XPlatformSendSmsChallenge.ANDROID,
                xDeviceId = deviceIdStore.value,
                idempotencyKey = idempotencyKey(),
                smsSendRequest = SmsSendRequest(
                    countryCode = countryCode,
                    phoneNumber = phoneNumber,
                    purpose = SmsPurpose.LOGIN,
                ),
            )
        }
        val challenge = response.data
        return SmsChallenge(challenge.challengeId, challenge.resendAfterSeconds)
    }

    override suspend fun login(challengeId: String, code: String) {
        val api = anonymousClient().createService(AUTHApi::class.java)
        val response = networkCall {
            api.loginWithSms(
                xClientVersion = CLIENT_VERSION,
                xPlatform = AUTHApi.XPlatformLoginWithSms.ANDROID,
                xDeviceId = deviceIdStore.value,
                idempotencyKey = idempotencyKey(),
                smsLoginRequest = SmsLoginRequest(challengeId, code),
            )
        }
        sessionStore.write(
            SessionTokens(
                accessToken = response.data.tokens.accessToken,
                refreshToken = response.data.tokens.refreshToken,
            ),
        )
    }

    override suspend fun getEntitlements(): EntitlementSummary = authorized { client ->
        val api = client.createService(ENTITLEMENTApi::class.java)
        val response = api.getEntitlements(
            xClientVersion = CLIENT_VERSION,
            xPlatform = ENTITLEMENTApi.XPlatformGetEntitlements.ANDROID,
            xDeviceId = deviceIdStore.value,
        )
        response.mapBody { envelope ->
            val entitlement = envelope.data
            EntitlementSummary(
                textRemaining = entitlement.benefits.textRemaining,
                energyAvailable = entitlement.wallet.energyAvailable,
                allowedModelIds = entitlement.benefits.allowedModelIds,
                allowedStyleIds = entitlement.benefits.allowedStyleIds,
            )
        }
    }

    override suspend fun quote(draft: ComposerDraft): GenerationQuoteSummary = authorized { client ->
        val api = client.createService(GENERATIONApi::class.java)
        val response = api.quoteGeneration(
            xClientVersion = CLIENT_VERSION,
            xPlatform = GENERATIONApi.XPlatformQuoteGeneration.ANDROID,
            xDeviceId = deviceIdStore.value,
            idempotencyKey = idempotencyKey(),
            generationQuoteRequest = GenerationQuoteRequest(
                input = draft.toGenerationInput(),
                context = draft.toGenerationContext(),
                saveToHistory = true,
            ),
        )
        response.mapBody { envelope ->
            val quote = envelope.data
            GenerationQuoteSummary(
                id = quote.quoteId,
                selectedModelId = quote.selectedModelId,
                estimatedEnergy = quote.estimatedEnergyAmount,
                expiresAtLabel = quote.expiresAt.toLocalTime().withNano(0).toString(),
            )
        }
    }

    override suspend fun create(
        draft: ComposerDraft,
        quote: GenerationQuoteSummary,
    ): GenerationResult = authorized { client ->
        val api = client.createService(GENERATIONApi::class.java)
        val response = api.createGeneration(
            xClientVersion = CLIENT_VERSION,
            xPlatform = GENERATIONApi.XPlatformCreateGeneration.ANDROID,
            xDeviceId = deviceIdStore.value,
            idempotencyKey = idempotencyKey(),
            createGenerationRequest = CreateGenerationRequest(
                clientRequestId = UUID.randomUUID().toString(),
                input = draft.toGenerationInput(),
                context = draft.toGenerationContext(),
                modelId = quote.selectedModelId,
                saveToHistory = true,
                quoteId = quote.id,
            ),
        )
        response.mapBody { it.data.toDomain() }
    }

    override suspend fun getGeneration(generationId: String): GenerationResult = authorized { client ->
        val api = client.createService(GENERATIONApi::class.java)
        val response = api.getGeneration(
            xClientVersion = CLIENT_VERSION,
            xPlatform = GENERATIONApi.XPlatformGetGeneration.ANDROID,
            xDeviceId = deviceIdStore.value,
            generationId = generationId,
        )
        response.mapBody { it.data.toDomain() }
    }

    override fun clearSession() = sessionStore.clear()

    private suspend fun <T> authorized(block: suspend (ApiClient) -> Response<T>): T {
        val initial = sessionStore.read() ?: throw ApiFailure(
            code = "SESSION_REQUIRED",
            message = "登录状态已失效，请重新登录",
            retryable = false,
        )
        val first = callResponse { block(authenticatedClient(initial.accessToken)) }
        if (first.code() != 401) return first.bodyOrThrow()

        val refreshed = refreshMutex.withLock {
            val current = sessionStore.read() ?: throw sessionExpired()
            if (current.accessToken != initial.accessToken) current else refresh(current)
        }
        return callResponse { block(authenticatedClient(refreshed.accessToken)) }.bodyOrThrow()
    }

    private suspend fun refresh(tokens: SessionTokens): SessionTokens {
        val api = anonymousClient().createService(AUTHApi::class.java)
        val response = callResponse {
            api.refreshAccessToken(
                xClientVersion = CLIENT_VERSION,
                xPlatform = AUTHApi.XPlatformRefreshAccessToken.ANDROID,
                xDeviceId = deviceIdStore.value,
                idempotencyKey = idempotencyKey(),
                refreshRequest = RefreshRequest(tokens.refreshToken),
            )
        }
        if (!response.isSuccessful) {
            sessionStore.clear()
            throw response.toFailure().let { failure ->
                ApiFailure(failure.code, "登录状态已失效，请重新登录", false)
            }
        }
        val pair = response.body()?.data ?: throw sessionExpired()
        return SessionTokens(pair.accessToken, pair.refreshToken).also(sessionStore::write)
    }

    private fun anonymousClient(): ApiClient = ApiClient(baseUrl = baseUrl)

    private fun authenticatedClient(accessToken: String): ApiClient = ApiClient(
        baseUrl = baseUrl,
        authName = "bearerAuth",
        bearerToken = accessToken,
    )

    private suspend fun <T> networkCall(block: suspend () -> Response<T>): T =
        callResponse(block).bodyOrThrow()

    private suspend fun <T> callResponse(block: suspend () -> Response<T>): Response<T> = try {
        block()
    } catch (error: IOException) {
        throw ApiFailure("NETWORK_UNAVAILABLE", "网络不可用，请检查连接后重试", true)
    }

    private fun <T> Response<T>.bodyOrThrow(): T {
        if (!isSuccessful) throw toFailure()
        return body() ?: throw ApiFailure("EMPTY_RESPONSE", "服务返回了空结果", true)
    }

    private fun <T, R> Response<T>.mapBody(transform: (T) -> R): Response<R> {
        if (!isSuccessful) {
            @Suppress("UNCHECKED_CAST")
            return this as Response<R>
        }
        val value = body() ?: throw ApiFailure("EMPTY_RESPONSE", "服务返回了空结果", true)
        return Response.success(code(), transform(value))
    }

    private fun Response<*>.toFailure(): ApiFailure {
        val parsed = errorBody()?.string()?.let { raw ->
            runCatching { errorAdapter.fromJson(raw) }.getOrNull()
        }
        return ApiFailure(
            code = parsed?.code ?: "HTTP_${code()}",
            message = parsed?.message?.takeIf(String::isNotBlank) ?: userMessageFor(code()),
            retryable = parsed?.error?.retryable ?: (code() >= 500 || code() == 429),
        )
    }

    private fun userMessageFor(status: Int): String = when (status) {
        400 -> "请检查输入内容"
        401 -> "登录状态已失效，请重新登录"
        409 -> "请求状态已变化，请重新报价"
        429 -> "请求较多，请稍后再试"
        in 500..599 -> "服务暂时不可用，请稍后重试"
        else -> "请求失败，请稍后重试"
    }

    private fun sessionExpired() = ApiFailure(
        code = "SESSION_EXPIRED",
        message = "登录状态已失效，请重新登录",
        retryable = false,
    )

    private fun idempotencyKey(): String = UUID.randomUUID().toString()

    private data class ApiErrorEnvelope(
        val code: String? = null,
        val message: String? = null,
        val error: ApiErrorDetail? = null,
    )

    private data class ApiErrorDetail(
        val retryable: Boolean = false,
    )

    private companion object {
        const val CLIENT_VERSION = "0.1.0"
    }
}

private fun ComposerDraft.toGenerationInput() = GenerationInput(
    text = message.trim(),
    attachmentIds = emptyList(),
)

private fun ComposerDraft.toGenerationContext() = GenerationContext(
    relationshipStage = relationshipStage,
    communicationGoal = communicationGoal,
    styleIds = styleIds,
    additionalContext = additionalContext.trim().ifBlank { null },
)

private fun GenerationSnapshot.toDomain(): GenerationResult {
    val phase = when (status) {
        GenerationStatus.SUCCEEDED -> GenerationPhase.SUCCEEDED
        GenerationStatus.FAILED -> GenerationPhase.FAILED
        GenerationStatus.CANCELLED -> GenerationPhase.CANCELLED
        else -> GenerationPhase.WORKING
    }
    return GenerationResult(
        id = generationId,
        phase = phase,
        statusLabel = status.value,
        analysis = analysis?.let {
            ReplyAnalysis(
                possibleIntent = it.possibleIntent,
                emotion = it.emotion,
                uncertaintyNote = it.uncertaintyNote,
                riskTips = it.riskTips,
            )
        },
        candidates = candidates.map {
            ReplyCandidate(
                id = it.candidateId,
                strategy = it.strategy.value,
                styleId = it.styleId,
                text = it.text,
            )
        },
        chargedEnergy = usage?.chargedEnergy,
        failureCode = failureCode,
    )
}
