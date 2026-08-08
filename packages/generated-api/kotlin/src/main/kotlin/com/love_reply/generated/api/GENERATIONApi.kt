package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.CreateGenerationRequest
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.GenerationQuoteRequest
import com.love_reply.generated.model.GenerationQuoteResponse
import com.love_reply.generated.model.GenerationResponse
import com.love_reply.generated.model.RegenerateRequest

interface GENERATIONApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCancelGeneration(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/generations/{generationId}/cancel
     * Cancel an unfinished task and release unsettled reservation
     *
     * Responses:
     *  - 200: Cancelled task snapshot.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param generationId
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [GenerationResponse]
     */
    @POST("v1/generations/{generationId}/cancel")
    suspend fun cancelGeneration(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCancelGeneration, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("generationId") generationId: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<GenerationResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCreateGeneration(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/generations
     * Create a generation and atomically reserve its quote
     *
     * Responses:
     *  - 202: Task created with status QUOTA_RESERVED.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 429: Rate limit exceeded.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param createGenerationRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [GenerationResponse]
     */
    @POST("v1/generations")
    suspend fun createGeneration(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCreateGeneration, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body createGenerationRequest: CreateGenerationRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<GenerationResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetGeneration(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/generations/{generationId}
     * Get an owned generation snapshot
     *
     * Responses:
     *  - 200: Current or final task snapshot.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param generationId
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [GenerationResponse]
     */
    @GET("v1/generations/{generationId}")
    suspend fun getGeneration(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetGeneration, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Path("generationId") generationId: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<GenerationResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformQuoteGeneration(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/generations/quote
     * Quote energy cost before creating a generation
     *
     * Responses:
     *  - 200: Short-lived quote bound to input, model, and entitlement version.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 429: Rate limit exceeded.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param generationQuoteRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [GenerationQuoteResponse]
     */
    @POST("v1/generations/quote")
    suspend fun quoteGeneration(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformQuoteGeneration, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body generationQuoteRequest: GenerationQuoteRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<GenerationQuoteResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRegenerateGeneration(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/generations/{generationId}/regenerate
     * Create a child generation using a new quote
     *
     * Responses:
     *  - 202: Child generation accepted.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param generationId
     * @param regenerateRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [GenerationResponse]
     */
    @POST("v1/generations/{generationId}/regenerate")
    suspend fun regenerateGeneration(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRegenerateGeneration, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("generationId") generationId: kotlin.String, @Body regenerateRequest: RegenerateRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<GenerationResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformStreamGenerationEvents(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/generations/{generationId}/events
     * Stream retained generation events
     *
     * Responses:
     *  - 200: SSE stream ordered by monotonically increasing sequence.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 410: The resource or retained stream is no longer available.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param generationId
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @param lastEventID Last fully processed SSE event ID used to resume a stream. (optional)
     * @return [kotlin.String]
     */
    @GET("v1/generations/{generationId}/events")
    suspend fun streamGenerationEvents(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformStreamGenerationEvents, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Path("generationId") generationId: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null, @Header("Last-Event-ID") lastEventID: kotlin.String? = null): Response<kotlin.String>

}
