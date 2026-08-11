package com.love_reply.generated.api

import com.love_reply.generated.infrastructure.CollectionFormats.*
import retrofit2.http.*
import retrofit2.Response
import okhttp3.RequestBody
import com.squareup.moshi.Json

import com.love_reply.generated.model.AddSupportMessageRequest
import com.love_reply.generated.model.CreateSupportTicketRequest
import com.love_reply.generated.model.ErrorResponse
import com.love_reply.generated.model.SupportTicketDetailResponse
import com.love_reply.generated.model.SupportTicketListResponse
import com.love_reply.generated.model.SupportTicketResponse

interface SUPPORTApi {

    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformAddMySupportMessage(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/support/tickets/{ticketId}/messages
     * Reply to an owned support ticket
     *
     * Responses:
     *  - 200: Updated ticket.
     *  - 409: Idempotency, version, or state-machine conflict.
     *
     * @param ticketId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param addSupportMessageRequest
     * @return [SupportTicketResponse]
     */
    @POST("v1/support/tickets/{ticketId}/messages")
    suspend fun addMySupportMessage(@Path("ticketId") ticketId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformAddMySupportMessage, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Body addSupportMessageRequest: AddSupportMessageRequest): Response<SupportTicketResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformCreateSupportTicket(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * POST v1/support/tickets
     * Create a support ticket
     *
     * Responses:
     *  - 201: Created ticket.
     *  - 400: Request syntax or fields are invalid.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @param createSupportTicketRequest
     * @return [SupportTicketResponse]
     */
    @POST("v1/support/tickets")
    suspend fun createSupportTicket(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformCreateSupportTicket, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN", @Body createSupportTicketRequest: CreateSupportTicketRequest): Response<SupportTicketResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformGetMySupportTicket(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/support/tickets/{ticketId}
     * Read one owned support ticket
     *
     * Responses:
     *  - 200: Ticket conversation.
     *  - 404: The resource does not exist or is not visible to the caller.
     *
     * @param ticketId
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @return [SupportTicketDetailResponse]
     */
    @GET("v1/support/tickets/{ticketId}")
    suspend fun getMySupportTicket(@Path("ticketId") ticketId: kotlin.String, @Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformGetMySupportTicket, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN"): Response<SupportTicketDetailResponse>


    /**
    * enum for parameter xPlatform
    */
    enum class XPlatformListMySupportTickets(val value: kotlin.String) {
        @Json(name = "ANDROID") ANDROID("ANDROID"),
        @Json(name = "ADMIN_WEB") ADMIN_WEB("ADMIN_WEB")
    }

    /**
     * GET v1/support/tickets
     * List current user&#39;s support tickets
     *
     * Responses:
     *  - 200: Tickets.
     *  - 401: Access token is missing, expired, or revoked.
     *
     * @param xClientVersion Semantic application version used for compatibility enforcement.
     * @param xPlatform
     * @param xDeviceId Opaque installation ID. It is not an authentication credential.
     * @param acceptLanguage  (default to "zh-CN")
     * @return [SupportTicketListResponse]
     */
    @GET("v1/support/tickets")
    suspend fun listMySupportTickets(@Header("X-Client-Version") xClientVersion: kotlin.String, @Header("X-Platform") xPlatform: XPlatformListMySupportTickets, @Header("X-Device-Id") xDeviceId: kotlin.String, @Header("Accept-Language") acceptLanguage: kotlin.String = "zh-CN"): Response<SupportTicketListResponse>

}
