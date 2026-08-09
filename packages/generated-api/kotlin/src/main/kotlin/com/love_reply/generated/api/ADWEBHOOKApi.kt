package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.AdRewardCallbackRequest
import com.love_reply.generated.model.AdRewardSessionResponse
import com.love_reply.generated.model.ErrorResponse

interface ADWEBHOOKApi {
    /**
     * POST webhooks/v1/ads/{providerId}
     * Verify a server-to-server advertising completion callback
     * The selected reviewed adapter verifies signature, timestamp, provider event identity, reward session binding, placement, and completion. An identical replay ACKs without issuing another reward; a conflicting replay is rejected and audited.
     * Responses:
     *  - 200: Callback accepted or an identical event replay acknowledged.
     *  - 400: Request syntax or fields are invalid.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param providerId
     * @param adRewardCallbackRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [AdRewardSessionResponse]
     */
    @POST("webhooks/v1/ads/{providerId}")
    suspend fun receiveAdRewardCallback(@Path("providerId") providerId: kotlin.String, @Body adRewardCallbackRequest: AdRewardCallbackRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<AdRewardSessionResponse>

}
