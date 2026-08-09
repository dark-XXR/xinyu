package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.BindReferralRequest
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.ReferralInviteListResponse
import com.love_reply.generated.model.ReferralInviteResponse
import com.love_reply.generated.model.ReferralProgramResponse
import com.love_reply.generated.model.ReferralRewardListResponse

interface REFERRALApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformBindReferralInvite(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/referrals/bind
     * Bind the authenticated account to one inviter
     * Binding is permanent for the campaign, rejects self-referral, and never returns inviter contact information. The client stores a deep-link code until authentication, then submits it once.
     * Responses:
     *  - 200: Existing identical binding returned idempotently.
     *  - 201: Referral binding created pending milestone and risk checks.
     *  - 400: Request syntax or fields are invalid.
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
     * @param bindReferralRequest
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [ReferralInviteResponse]
     */
    @POST("v1/referrals/bind")
    suspend fun bindReferralInvite(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformBindReferralInvite, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("Idempotency-Key") idempotencyKey: kotlin.String, @Body bindReferralRequest: BindReferralRequest, @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<ReferralInviteResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetReferralProgram(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/referrals/program
     * Read the active referral campaign and personal invite link
     *
     * Responses:
     *  - 200: Active campaign presentation, personal invite code, and aggregate progress.
     *  - 401: Access token is missing, expired, or revoked.
     *  - 404: The resource does not exist or is not visible to the caller.
     *  - 500: Unexpected internal failure with no sensitive implementation detail.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param xRequestId Client correlation ID. The server returns the final accepted value. (optional)
     * @return [ReferralProgramResponse]
     */
    @GET("v1/referrals/program")
    suspend fun getReferralProgram(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetReferralProgram, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null): Response<ReferralProgramResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListReferralInvites(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/referrals/invites
     * List masked invitation progress
     *
     * Responses:
     *  - 200: Owned invitations with irreversible invitee display hints.
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
     * @return [ReferralInviteListResponse]
     */
    @GET("v1/referrals/invites")
    suspend fun listReferralInvites(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListReferralInvites, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null, @Query("cursor") cursor: kotlin.String? = null, @Query("limit") limit: kotlin.Int? = 20): Response<ReferralInviteListResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListReferralRewards(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/referrals/rewards
     * List referral reward and reversal entries
     *
     * Responses:
     *  - 200: Immutable reward grants and reversals for the current user.
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
     * @return [ReferralRewardListResponse]
     */
    @GET("v1/referrals/rewards")
    suspend fun listReferralRewards(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListReferralRewards, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Header("X-Request-Id") xRequestId: kotlin.String? = null, @Query("cursor") cursor: kotlin.String? = null, @Query("limit") limit: kotlin.Int? = 20): Response<ReferralRewardListResponse>

}
