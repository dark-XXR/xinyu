package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.AdRewardSessionResponse
import com.love_reply.generated.model.CreateAdRewardSessionRequest
import com.love_reply.generated.model.ErrorResponse

interface ADREWARDApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCreateAdRewardSession(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/ad-rewards/sessions
     * Create a short-lived server-bound advertising reward session
     * Reward amount and eligibility come from the active server configuration.
     * Responses:
     *  - 201: Reward session created; no reward has been granted yet.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 429: Rate limit exceeded.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *  - 503: A required external provider or dependency is temporarily unavailable.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param createAdRewardSessionRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [AdRewardSessionResponse]
     */
    @POST("v1/ad-rewards/sessions")
    suspend fun createAdRewardSession(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCreateAdRewardSession, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body createAdRewardSessionRequest: CreateAdRewardSessionRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<AdRewardSessionResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetAdRewardSession(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/ad-rewards/sessions/{rewardSessionId}
     * Read the verified advertising reward state
     *
     * Responses:
     *  - 200: Reward state after any verified provider callback.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param rewardSessionId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [AdRewardSessionResponse]
     */
    @GET("v1/ad-rewards/sessions/{rewardSessionId}")
    suspend fun getAdRewardSession(@Path("rewardSessionId") rewardSessionId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetAdRewardSession, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<AdRewardSessionResponse>

}
