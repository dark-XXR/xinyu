package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.HealthSuccessResponse

interface APPCONFIGApi {
    /**
     * GET health
     * Read service health
     *
     * Responses:
     *  - 200: Service is accepting requests.
     *  - 400: Request syntax or fields are invalid.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [HealthSuccessResponse]
     */
    @GET("health")
    suspend fun getHealth(@Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<HealthSuccessResponse>

}
