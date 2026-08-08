package com.lovereply.app

import com.lovereply.app.data.LoveReplyRepository
import com.lovereply.app.domain.ComposerDraft
import com.lovereply.app.domain.EntitlementSummary
import com.lovereply.app.domain.GenerationPhase
import com.lovereply.app.domain.GenerationQuoteSummary
import com.lovereply.app.domain.GenerationResult
import com.lovereply.app.domain.ReplyAnalysis
import com.lovereply.app.domain.ReplyCandidate
import com.lovereply.app.domain.SmsChallenge
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class MainViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun loginMovesToComposerAndLoadsEntitlement() = runTest(mainDispatcherRule.dispatcher) {
        val repository = FakeRepository(hasSession = false)
        val viewModel = MainViewModel(repository)

        viewModel.updateCountryCode("+86")
        viewModel.updatePhone("13800138000")
        viewModel.sendSms()
        advanceUntilIdle()
        viewModel.updateVerificationCode("123456")
        viewModel.login()
        advanceUntilIdle()

        assertEquals(AppScreen.COMPOSER, viewModel.state.value.screen)
        assertEquals(8, viewModel.state.value.entitlement?.textRemaining)
        assertEquals(1, repository.loginCalls)
    }

    @Test
    fun successfulGenerationContainsAllThreeStrategies() = runTest(mainDispatcherRule.dispatcher) {
        val repository = FakeRepository(hasSession = true)
        val viewModel = MainViewModel(repository)
        advanceUntilIdle()

        viewModel.updateMessage("对方：周末有空吗？")
        viewModel.requestQuote()
        advanceUntilIdle()
        viewModel.confirmGeneration()
        advanceUntilIdle()

        val result = viewModel.state.value.generation
        assertEquals(AppScreen.RESULT, viewModel.state.value.screen)
        assertEquals(GenerationPhase.SUCCEEDED, result?.phase)
        assertEquals(setOf("SAFE", "PUSH_PULL", "DIRECT"), result?.candidates?.map { it.strategy }?.toSet())
    }

    @Test
    fun failedGenerationRetryKeepsDraftAndRequestsFreshQuote() = runTest(mainDispatcherRule.dispatcher) {
        val repository = FakeRepository(hasSession = true, failGeneration = true)
        val viewModel = MainViewModel(repository)
        advanceUntilIdle()

        val original = "对方：我最近有点忙"
        viewModel.updateMessage(original)
        viewModel.requestQuote()
        advanceUntilIdle()
        viewModel.confirmGeneration()
        advanceUntilIdle()

        assertEquals(GenerationPhase.FAILED, viewModel.state.value.generation?.phase)
        assertEquals(original, viewModel.state.value.draft.message)

        viewModel.retryGeneration()
        advanceUntilIdle()

        assertEquals(AppScreen.COMPOSER, viewModel.state.value.screen)
        assertEquals(original, viewModel.state.value.draft.message)
        assertNotNull(viewModel.state.value.quote)
        assertEquals(2, repository.quoteCalls)
    }
}

private class FakeRepository(
    private val hasSession: Boolean,
    private val failGeneration: Boolean = false,
) : LoveReplyRepository {
    var loginCalls = 0
    var quoteCalls = 0
    private var pollCalls = 0

    override fun hasSession(): Boolean = hasSession

    override suspend fun sendSms(countryCode: String, phoneNumber: String) =
        SmsChallenge(id = "sms_test", resendAfterSeconds = 1)

    override suspend fun login(challengeId: String, code: String) {
        loginCalls += 1
    }

    override suspend fun getEntitlements() = EntitlementSummary(
        textRemaining = 8,
        energyAvailable = 1_200,
        allowedModelIds = setOf("model_quality"),
        allowedStyleIds = setOf("warm", "humorous", "steady"),
    )

    override suspend fun quote(draft: ComposerDraft): GenerationQuoteSummary {
        quoteCalls += 1
        return GenerationQuoteSummary(
            id = "quote_$quoteCalls",
            selectedModelId = "model_quality",
            estimatedEnergy = 120,
            expiresAtLabel = "12:30:00",
        )
    }

    override suspend fun create(
        draft: ComposerDraft,
        quote: GenerationQuoteSummary,
    ): GenerationResult = if (failGeneration) {
        GenerationResult(
            id = "gen_failed",
            phase = GenerationPhase.FAILED,
            statusLabel = "FAILED",
            failureCode = "MODEL_PROVIDER_UNAVAILABLE",
        )
    } else {
        GenerationResult(
            id = "gen_working",
            phase = GenerationPhase.WORKING,
            statusLabel = "ANALYZING",
        )
    }

    override suspend fun getGeneration(generationId: String): GenerationResult {
        pollCalls += 1
        return successfulResult()
    }

    override fun clearSession() = Unit
}

private fun successfulResult() = GenerationResult(
    id = "gen_success",
    phase = GenerationPhase.SUCCEEDED,
    statusLabel = "SUCCEEDED",
    analysis = ReplyAnalysis(
        possibleIntent = "对方可能在确认见面意愿",
        emotion = "期待",
        uncertaintyNote = "仅依据当前上下文推测",
        riskTips = listOf("避免替对方下结论"),
    ),
    candidates = listOf(
        ReplyCandidate("can_safe", "SAFE", "warm", "有呀，你想怎么安排？"),
        ReplyCandidate("can_push", "PUSH_PULL", "humorous", "有一点，要看你的计划够不够吸引我。"),
        ReplyCandidate("can_direct", "DIRECT", "steady", "有空，我们周六见面吧。"),
    ),
    chargedEnergy = 104,
)
