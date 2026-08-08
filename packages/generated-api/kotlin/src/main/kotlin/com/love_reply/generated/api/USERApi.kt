package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.DeviceListResponse
import com.love_reply.generated.model.EmptyResponse
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.UpdateUserRequest
import com.love_reply.generated.model.UserResponse

interface USERApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetCurrentUser(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/me
     * Get the current account
     *
     * Responses:
     *  - 200: Current account.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [UserResponse]
     */
    @GET("v1/me")
    suspend fun getCurrentUser(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetCurrentUser, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<UserResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListDevices(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/me/devices
     * List authenticated devices
     *
     * Responses:
     *  - 200: Devices owned by the current user.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [DeviceListResponse]
     */
    @GET("v1/me/devices")
    suspend fun listDevices(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListDevices, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<DeviceListResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformRevokeDevice(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * DELETE v1/me/devices/{deviceId}
     * Revoke one authenticated device
     *
     * Responses:
     *  - 200: Device revoked.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: Request syntax or fields are invalid.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param deviceId
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [EmptyResponse]
     */
    @DELETE("v1/me/devices/{deviceId}")
    suspend fun revokeDevice(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformRevokeDevice, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Path("deviceId") deviceId: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<EmptyResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformUpdateCurrentUser(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * PATCH v1/me
     * Update non-sensitive account profile fields
     *
     * Responses:
     *  - 200: Updated account.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 409: Idempotency, version, or state-machine conflict.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param ifMatch Decimal resourceVersion expected by the caller.
     * @param idempotencyKey Unique key scoped to authenticated actor, operation, and request fingerprint.
     * @param updateUserRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [UserResponse]
     */
    @PATCH("v1/me")
    suspend fun updateCurrentUser(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformUpdateCurrentUser, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("If-Match") ifMatch: kotlin.String, @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body updateUserRequest: UpdateUserRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<UserResponse>

}
