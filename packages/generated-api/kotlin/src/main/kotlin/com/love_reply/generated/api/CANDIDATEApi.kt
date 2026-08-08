package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.CandidateActionRequest
import com.love_reply.generated.model.CandidateActionResponse
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.GenerationResponse
import com.love_reply.generated.model.RefineCandidateRequest

interface CANDIDATEApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRecordCandidateAction(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/candidates/{candidateId}/actions
     * Record an explicit candidate action
     *
     * Responses:
     *  - 200: Candidate action recorded exactly once.
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
     * @param candidateId
     * @param candidateActionRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [CandidateActionResponse]
     */
    @POST("v1/candidates/{candidateId}/actions")
    suspend fun recordCandidateAction(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRecordCandidateAction, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("candidateId") candidateId: kotlin.String, @Body candidateActionRequest: CandidateActionRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<CandidateActionResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRefineCandidate(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/candidates/{candidateId}/refine
     * Create a refined child generation for one candidate
     *
     * Responses:
     *  - 202: Refined generation accepted.
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
     * @param candidateId
     * @param refineCandidateRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [GenerationResponse]
     */
    @POST("v1/candidates/{candidateId}/refine")
    suspend fun refineCandidate(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRefineCandidate, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("candidateId") candidateId: kotlin.String, @Body refineCandidateRequest: RefineCandidateRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<GenerationResponse>

}
