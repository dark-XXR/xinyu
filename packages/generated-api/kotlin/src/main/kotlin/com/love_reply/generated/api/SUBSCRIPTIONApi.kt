package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.CancelSubscriptionRequest
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.SubscriptionListResponse
import com.love_reply.generated.model.SubscriptionResponse

interface SUBSCRIPTIONApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCancelSubscription(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/subscriptions/{subscriptionId}/cancel
     * Cancel renewal or schedule cancellation at period end
     * Prepaid non-renewing terms remain active until their purchased expiry.
     * Responses:
     *  - 200: Updated subscription term.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param subscriptionId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param ifMatch Decimal resourceVersion expected by the caller.
     * @param cancelSubscriptionRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [SubscriptionResponse]
     */
    @POST("v1/subscriptions/{subscriptionId}/cancel")
    suspend fun cancelSubscription(@Path("subscriptionId") subscriptionId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCancelSubscription, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("If-Match") ifMatch: kotlin.String, @Body cancelSubscriptionRequest: CancelSubscriptionRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<SubscriptionResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListSubscriptions(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/subscriptions
     * List owned prepaid terms and recurring mandates
     *
     * Responses:
     *  - 200: Current and historical subscription terms.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [SubscriptionListResponse]
     */
    @GET("v1/subscriptions")
    suspend fun listSubscriptions(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListSubscriptions, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<SubscriptionListResponse>

}
