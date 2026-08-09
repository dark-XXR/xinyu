package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.ProductListResponse
import com.love_reply.generated.model.ProductResponse

interface PRODUCTApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetProduct(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/products/{productVersionId}
     * Read one currently purchasable product version
     *
     * Responses:
     *  - 200: Published product version.
     *  - 400: Request syntax or fields are invalid.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param productVersionId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [ProductResponse]
     */
    @GET("v1/products/{productVersionId}")
    suspend fun getProduct(@Path("productVersionId") productVersionId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetProduct, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<ProductResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListProducts(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/products
     * List the active server-published product catalog
     *
     * Responses:
     *  - 200: Active product versions for the requested region and channel.
     *  - 400: Request syntax or fields are invalid.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param region
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [ProductListResponse]
     */
    @GET("v1/products")
    suspend fun listProducts(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListProducts, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Query("region") region: kotlin.String, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<ProductListResponse>

}
