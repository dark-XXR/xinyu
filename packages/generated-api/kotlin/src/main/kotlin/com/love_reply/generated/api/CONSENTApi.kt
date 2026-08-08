package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.ConsentListResponse
import com.love_reply.generated.model.ConsentResponse
import com.love_reply.generated.model.ConsentType
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.UpdateConsentRequest

interface CONSENTApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListMyConsents(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/me/consents
     * Read current consent records
     *
     * Responses:
     *  - 200: Consent records.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [ConsentListResponse]
     */
    @GET("v1/me/consents")
    suspend fun listMyConsents(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListMyConsents, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<ConsentListResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformUpdateConsent(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * PUT v1/me/consents/{consentType}
     * Grant or revoke an optional consent
     *
     * Responses:
     *  - 200: Updated consent.
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
     * @param consentType
     * @param updateConsentRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [ConsentResponse]
     */
    @PUT("v1/me/consents/{consentType}")
    suspend fun updateConsent(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformUpdateConsent, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("consentType") consentType: ConsentType, @Body updateConsentRequest: UpdateConsentRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<ConsentResponse>

}
