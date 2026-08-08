package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.LedgerEntryType
import com.love_reply.generated.model.WalletLedgerResponse
import com.love_reply.generated.model.WalletResponse

interface WALLETApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetWallet(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/wallet
     * Get energy balance and active reservations
     *
     * Responses:
     *  - 200: Current wallet.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [WalletResponse]
     */
    @GET("v1/wallet")
    suspend fun getWallet(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetWallet, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<WalletResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListWalletLedger(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/wallet/ledger
     * List immutable wallet entries
     *
     * Responses:
     *  - 200: Immutable wallet ledger entries.
     *  - 400: Request syntax or fields are invalid.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @param cursor Opaque server-issued cursor. Clients must not parse it. (optional)
     * @param limit  (optional, default to 20)
     * @param entryType  (optional)
     * @return [WalletLedgerResponse]
     */
    @GET("v1/wallet/ledger")
    suspend fun listWalletLedger(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListWalletLedger, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null, @Query("cursor") cursor: kotlin.String? = null, @Query("limit") limit: kotlin.Int? = 20, @Query("entryType") entryType: LedgerEntryType? = null): Response<WalletLedgerResponse>

}
