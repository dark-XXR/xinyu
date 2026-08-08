package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.EmptyResponse
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.LoginResponse
import com.love_reply.generated.model.RefreshRequest
import com.love_reply.generated.model.SmsChallengeResponse
import com.love_reply.generated.model.SmsLoginRequest
import com.love_reply.generated.model.SmsSendRequest
import com.love_reply.generated.model.TokenResponse

interface AUTHApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformLoginWithSms(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/auth/sms/login
     * Login or register with a verified SMS challenge
     *
     * Responses:
     *  - 200: Access and refresh tokens issued.
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
     * @param smsLoginRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [LoginResponse]
     */
    @POST("v1/auth/sms/login")
    suspend fun loginWithSms(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformLoginWithSms, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body smsLoginRequest: SmsLoginRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<LoginResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformLogoutAllDevices(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/auth/logout-all
     * Revoke all sessions for the current user
     *
     * Responses:
     *  - 200: All sessions revoked.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [EmptyResponse]
     */
    @POST("v1/auth/logout-all")
    suspend fun logoutAllDevices(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformLogoutAllDevices, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<EmptyResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformLogoutCurrentDevice(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/auth/logout
     * Revoke the current device session
     *
     * Responses:
     *  - 200: Session revoked.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [EmptyResponse]
     */
    @POST("v1/auth/logout")
    suspend fun logoutCurrentDevice(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformLogoutCurrentDevice, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<EmptyResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRefreshAccessToken(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/auth/refresh
     * Rotate a refresh token
     *
     * Responses:
     *  - 200: Rotated access and refresh tokens.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param refreshRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [TokenResponse]
     */
    @POST("v1/auth/refresh")
    suspend fun refreshAccessToken(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRefreshAccessToken, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body refreshRequest: RefreshRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<TokenResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformSendSmsChallenge(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/auth/sms/send
     * Send a login verification code
     *
     * Responses:
     *  - 200: Verification challenge created.
     *  - 400: Request syntax or fields are invalid.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 429: Rate limit exceeded.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param smsSendRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [SmsChallengeResponse]
     */
    @POST("v1/auth/sms/send")
    suspend fun sendSmsChallenge(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformSendSmsChallenge, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body smsSendRequest: SmsSendRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<SmsChallengeResponse>

}
