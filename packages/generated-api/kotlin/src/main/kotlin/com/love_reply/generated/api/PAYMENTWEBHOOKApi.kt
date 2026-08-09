package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.ErrorResponse

interface PAYMENTWEBHOOKApi {

    /**
    * enum for parameter type
    */
    enum class TypeReceiveEpayCallback(val value: kotlin.String) {
        @Json(name = "alipay") alipay("alipay"),
        @Json(name = "wxpay") wxpay("wxpay")
    }


    /**
    * enum for parameter tradeStatus
    */
    enum class TradeStatusReceiveEpayCallback(val value: kotlin.String) {
        @Json(name = "TRADE_SUCCESS") TRADE_SUCCESS("TRADE_SUCCESS")
    }


    /**
    * enum for parameter signType
    */
    enum class SignTypeReceiveEpayCallback(val value: kotlin.String) {
        @Json(name = "MD5") MD5("MD5")
    }

    /**
     * POST webhooks/v1/payments/epay/{providerId}
     * Receive and verify an Epay-compatible server callback
     * The backend verifies the configured provider, signature, merchant, order, amount, currency, callback freshness when available, and terminal state. Duplicate identical events ACK without granting benefits twice; conflicting duplicates are rejected and audited. Browser return parameters never call this operation and never grant entitlements.
     * Responses:
     *  - 200: Provider-specific configured ACK text as plain text.
     *  - 400: Request syntax or fields are invalid.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param providerId
     * @param pid
     * @param tradeNo
     * @param outTradeNo
     * @param type
     * @param name
     * @param money Decimal provider amount parsed exactly and compared to order minor units.
     * @param tradeStatus
     * @param sign
     * @param signType
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @param timestamp Provider timestamp when supported by the configured reviewed preset. (optional)
     * @return [kotlin.String]
     */
    @FormUrlEncoded
    @POST("webhooks/v1/payments/epay/{providerId}")
    suspend fun receiveEpayCallback(@Path("providerId") providerId: kotlin.String, @Field("pid") pid: kotlin.String, @Field("trade_no") tradeNo: kotlin.String, @Field("out_trade_no") outTradeNo: kotlin.String, @Field("type") type: kotlin.String, @Field("name") name: kotlin.String, @Field("money") money: kotlin.String, @Field("trade_status") tradeStatus: kotlin.String, @Field("sign") sign: kotlin.String, @Field("sign_type") signType: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null, @Field("timestamp") timestamp: kotlin.String? = null): Response<kotlin.String>

}
