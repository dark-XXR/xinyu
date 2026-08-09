package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.CreateOrderRequest
import com.love_reply.generated.model.CreatePaymentAttemptRequest
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.OrderResponse

interface ORDERApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCreateOrder(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/orders
     * Create an immutable order and initial payment attempt
     * Binds the current product, price, currency, region, renewal, and benefit facts before checkout. A checkout redirect is never proof of payment.
     * Responses:
     *  - 201: Order and initial payment attempt created.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *  - 503: A required external provider or dependency is temporarily unavailable.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param createOrderRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [OrderResponse]
     */
    @POST("v1/orders")
    suspend fun createOrder(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCreateOrder, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body createOrderRequest: CreateOrderRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<OrderResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCreatePaymentAttempt(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/orders/{orderId}/payment-attempts
     * Create another payment attempt for an unpaid order
     *
     * Responses:
     *  - 201: New payment attempt created without changing settlement state.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *  - 503: A required external provider or dependency is temporarily unavailable.
     *
     * @param orderId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param ifMatch Decimal resourceVersion expected by the caller.
     * @param createPaymentAttemptRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [OrderResponse]
     */
    @POST("v1/orders/{orderId}/payment-attempts")
    suspend fun createPaymentAttempt(@Path("orderId") orderId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCreatePaymentAttempt, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("If-Match") ifMatch: kotlin.String, @Body createPaymentAttemptRequest: CreatePaymentAttemptRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<OrderResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetOrder(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/orders/{orderId}
     * Read an owned order and its payment attempts
     *
     * Responses:
     *  - 200: Current server-authoritative order state.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param orderId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [OrderResponse]
     */
    @GET("v1/orders/{orderId}")
    suspend fun getOrder(@Path("orderId") orderId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetOrder, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<OrderResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformSyncOrderPayment(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/orders/{orderId}/sync-payment
     * Query the provider and reconcile an unpaid order
     * A verified provider query may settle an order only when merchant, order, amount, currency, and terminal status all match. The operation is bounded and rate limited; it cannot trust browser return parameters.
     * Responses:
     *  - 200: Reconciled order snapshot, whether changed or unchanged.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 429: Rate limit exceeded.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *  - 503: A required external provider or dependency is temporarily unavailable.
     *
     * @param orderId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param ifMatch Decimal resourceVersion expected by the caller.
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [OrderResponse]
     */
    @POST("v1/orders/{orderId}/sync-payment")
    suspend fun syncOrderPayment(@Path("orderId") orderId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformSyncOrderPayment, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("If-Match") ifMatch: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<OrderResponse>

}
