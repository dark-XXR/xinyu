package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.DataRequestResponse
import com.love_reply.generated.model.DeletionRequest
import com.love_reply.generated.model.DeletionStatusResponse
import com.love_reply.generated.model.EmptyResponse
import com.love_reply.generated.model.ErrorResponse

interface DATAGOVERNANCEApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCancelAccountDeletion(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * DELETE v1/me/deletion
     * Cancel deletion during the cooling-off period
     *
     * Responses:
     *  - 200: Deletion cancelled.
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
    @DELETE("v1/me/deletion")
    suspend fun cancelAccountDeletion(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCancelAccountDeletion, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<EmptyResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetDataRequest(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/me/data-requests/{requestId}
     * Read a personal data request
     *
     * Responses:
     *  - 200: Data request state.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: Request syntax or fields are invalid.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param requestId
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [DataRequestResponse]
     */
    @GET("v1/me/data-requests/{requestId}")
    suspend fun getDataRequest(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetDataRequest, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Path("requestId") requestId: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<DataRequestResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetDeletionStatus(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/me/deletion
     * Read account deletion status
     *
     * Responses:
     *  - 200: Deletion status or an empty active state.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [DeletionStatusResponse]
     */
    @GET("v1/me/deletion")
    suspend fun getDeletionStatus(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetDeletionStatus, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<DeletionStatusResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRequestAccountDeletion(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/me/deletion
     * Request account deletion with a cooling-off period
     *
     * Responses:
     *  - 202: Deletion request accepted.
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
     * @param deletionRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [DeletionStatusResponse]
     */
    @POST("v1/me/deletion")
    suspend fun requestAccountDeletion(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRequestAccountDeletion, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body deletionRequest: DeletionRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<DeletionStatusResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRequestDataExport(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/me/data-export
     * Request an asynchronous personal data export
     *
     * Responses:
     *  - 202: Export request accepted.
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
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [DataRequestResponse]
     */
    @POST("v1/me/data-export")
    suspend fun requestDataExport(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRequestDataExport, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<DataRequestResponse>

}
