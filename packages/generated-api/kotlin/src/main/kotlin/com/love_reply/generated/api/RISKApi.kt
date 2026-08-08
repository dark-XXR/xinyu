package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.AppealRequest
import com.love_reply.generated.model.AppealResponse
import com.love_reply.generated.model.ErrorResponse

interface RISKApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformAppealRiskEvent(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/risk-events/{riskEventId}/appeals
     * Appeal a safety decision without bypassing it
     *
     * Responses:
     *  - 202: Appeal submitted for review.
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
     * @param riskEventId
     * @param appealRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [AppealResponse]
     */
    @POST("v1/risk-events/{riskEventId}/appeals")
    suspend fun appealRiskEvent(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformAppealRiskEvent, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("riskEventId") riskEventId: kotlin.String, @Body appealRequest: AppealRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<AppealResponse>

}
