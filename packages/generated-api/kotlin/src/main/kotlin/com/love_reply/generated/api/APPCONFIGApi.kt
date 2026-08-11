package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import okhttp3.ResponseBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.AppBootstrapResponse
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.HealthSuccessResponse
import com.love_reply.generated.model.NoticeListResponse

interface APPCONFIGApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetAppBootstrap(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/app/bootstrap
     * Read the published application configuration
     * Returns the server-authoritative model and style catalog, generation policy, free entitlement template, and feature switches. Clients must not infer quotas, prices, or availability from local constants.
     * Responses:
     *  - 200: Current published application configuration.
     *  - 400: Request syntax or fields are invalid.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *  - 503: A required external provider or dependency is temporarily unavailable.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [AppBootstrapResponse]
     */
    @GET("v1/app/bootstrap")
    suspend fun getAppBootstrap(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetAppBootstrap, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<AppBootstrapResponse>

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

    /**
     * GET media/{assetId}
     * Read an immutable first-party image asset
     *
     * Responses:
     *  - 200: Image bytes.
     *  - 404: The resource does not exist or is not visible to the caller.
     *
     * @param assetId
     * @return [ResponseBody]
     */
    @GET("media/{assetId}")
    suspend fun getMediaAsset(@Path("assetId") assetId: kotlin.String): Response<ResponseBody>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListPublicNotices(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/app/notices
     * List announcements active for this client
     *
     * Responses:
     *  - 200: Active notices.
     *  - 400: Request syntax or fields are invalid.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [NoticeListResponse]
     */
    @GET("v1/app/notices")
    suspend fun listPublicNotices(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListPublicNotices, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<NoticeListResponse>

}
