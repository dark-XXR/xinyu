package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.CreateRefundRequest
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.RefundResponse

interface REFUNDApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCreateRefund(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/refunds
     * Request a full or partial refund
     *
     * Responses:
     *  - 202: Refund request accepted for automatic checks or manual review.
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
     * @param createRefundRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [RefundResponse]
     */
    @POST("v1/refunds")
    suspend fun createRefund(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCreateRefund, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body createRefundRequest: CreateRefundRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<RefundResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetRefund(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/refunds/{refundId}
     * Read an owned refund and entitlement recovery state
     *
     * Responses:
     *  - 200: Current refund and benefit-recovery state.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param refundId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [RefundResponse]
     */
    @GET("v1/refunds/{refundId}")
    suspend fun getRefund(@Path("refundId") refundId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetRefund, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<RefundResponse>

}
