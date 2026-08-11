# @love-reply/generated-api@1.0.0

A TypeScript SDK client for the localhost API.

## Usage

First, install the SDK from npm.

```bash
npm install @love-reply/generated-api --save
```

Next, try it out.


```ts
import {
  Configuration,
  ADMINAIApi,
} from '@love-reply/generated-api';
import type { CreateAdminAiEvaluationRunRequest } from '@love-reply/generated-api';

async function example() {
  console.log("🚀 Testing @love-reply/generated-api SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: adminBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ADMINAIApi(config);

  const body = {
    // string | Semantic application version used for compatibility enforcement.
    xClientVersion: xClientVersion_example,
    // 'ANDROID' | 'ADMIN_WEB'
    xPlatform: xPlatform_example,
    // string
    acceptLanguage: acceptLanguage_example,
    // string | Unique key scoped to authenticated actor, operation, and request fingerprint.
    idempotencyKey: idempotencyKey_example,
    // AiEvaluationRunRequest
    aiEvaluationRunRequest: ...,
    // string | Client correlation ID. The server returns the final accepted value. (optional)
    xRequestId: xRequestId_example,
  } satisfies CreateAdminAiEvaluationRunRequest;

  try {
    const data = await api.createAdminAiEvaluationRun(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```


## Documentation

### API Endpoints

All URIs are relative to *http://localhost:8000*

| Class | Method | HTTP request | Description
| ----- | ------ | ------------ | -------------
*ADMINAIApi* | [**createAdminAiEvaluationRun**](docs/ADMINAIApi.md#createadminaievaluationrun) | **POST** /admin/v1/ai/evaluation-runs | Start a bounded-cost prompt and route evaluation
*ADMINAIApi* | [**createAdminAiModelMapping**](docs/ADMINAIApi.md#createadminaimodelmapping) | **POST** /admin/v1/ai/model-mappings | Create an AI model mapping draft
*ADMINAIApi* | [**createAdminAiPrompt**](docs/ADMINAIApi.md#createadminaiprompt) | **POST** /admin/v1/ai/prompts | Create a prompt template draft
*ADMINAIApi* | [**createAdminAiRiskPolicy**](docs/ADMINAIApi.md#createadminairiskpolicy) | **POST** /admin/v1/ai/risk-policies | Create an AI risk policy draft
*ADMINAIApi* | [**createAdminAiRoute**](docs/ADMINAIApi.md#createadminairoute) | **POST** /admin/v1/ai/routes | Create an AI scenario route draft
*ADMINAIApi* | [**getAdminAiEvaluationRun**](docs/ADMINAIApi.md#getadminaievaluationrun) | **GET** /admin/v1/ai/evaluation-runs/{evaluationRunId} | Read evaluation progress and gate result
*ADMINAIApi* | [**getAdminAiModelMapping**](docs/ADMINAIApi.md#getadminaimodelmapping) | **GET** /admin/v1/ai/model-mappings/{modelMappingId} | Read one AI model mapping
*ADMINAIApi* | [**getAdminAiPrompt**](docs/ADMINAIApi.md#getadminaiprompt) | **GET** /admin/v1/ai/prompts/{promptId} | Read one prompt template version
*ADMINAIApi* | [**getAdminAiRiskPolicy**](docs/ADMINAIApi.md#getadminairiskpolicy) | **GET** /admin/v1/ai/risk-policies/{riskPolicyId} | Read one AI risk policy version
*ADMINAIApi* | [**getAdminAiRoute**](docs/ADMINAIApi.md#getadminairoute) | **GET** /admin/v1/ai/routes/{routeId} | Read one AI route version
*ADMINAIApi* | [**listAdminAiModelMappings**](docs/ADMINAIApi.md#listadminaimodelmappings) | **GET** /admin/v1/ai/model-mappings | List administrator-only logical to provider model mappings
*ADMINAIApi* | [**listAdminAiPrompts**](docs/ADMINAIApi.md#listadminaiprompts) | **GET** /admin/v1/ai/prompts | List versioned AI prompt templates
*ADMINAIApi* | [**listAdminAiRiskPolicies**](docs/ADMINAIApi.md#listadminairiskpolicies) | **GET** /admin/v1/ai/risk-policies | List versioned AI risk policies
*ADMINAIApi* | [**listAdminAiRoutes**](docs/ADMINAIApi.md#listadminairoutes) | **GET** /admin/v1/ai/routes | List versioned AI scenario routes
*ADMINAIApi* | [**publishAdminAiPrompt**](docs/ADMINAIApi.md#publishadminaiprompt) | **POST** /admin/v1/ai/prompts/{promptId}/publish | Publish a prompt version after a successful evaluation gate
*ADMINAIApi* | [**publishAdminAiRiskPolicy**](docs/ADMINAIApi.md#publishadminairiskpolicy) | **POST** /admin/v1/ai/risk-policies/{riskPolicyId}/publish | Publish an evaluated AI risk policy
*ADMINAIApi* | [**publishAdminAiRoute**](docs/ADMINAIApi.md#publishadminairoute) | **POST** /admin/v1/ai/routes/{routeId}/publish | Publish an evaluated bounded-cost AI route
*ADMINAIApi* | [**rollbackAdminAiPrompt**](docs/ADMINAIApi.md#rollbackadminaiprompt) | **POST** /admin/v1/ai/prompts/{promptId}/rollback | Restore a previously published prompt version
*ADMINAIApi* | [**rollbackAdminAiRiskPolicy**](docs/ADMINAIApi.md#rollbackadminairiskpolicy) | **POST** /admin/v1/ai/risk-policies/{riskPolicyId}/rollback | Restore a previously published AI risk policy version
*ADMINAIApi* | [**rollbackAdminAiRoute**](docs/ADMINAIApi.md#rollbackadminairoute) | **POST** /admin/v1/ai/routes/{routeId}/rollback | Restore a previously published AI route version
*ADMINAIApi* | [**updateAdminAiModelMapping**](docs/ADMINAIApi.md#updateadminaimodelmapping) | **PATCH** /admin/v1/ai/model-mappings/{modelMappingId} | Replace an AI model mapping draft
*ADMINAIApi* | [**updateAdminAiPrompt**](docs/ADMINAIApi.md#updateadminaiprompt) | **PATCH** /admin/v1/ai/prompts/{promptId} | Replace a prompt template draft
*ADMINAIApi* | [**updateAdminAiRiskPolicy**](docs/ADMINAIApi.md#updateadminairiskpolicy) | **PATCH** /admin/v1/ai/risk-policies/{riskPolicyId} | Replace an AI risk policy draft
*ADMINAIApi* | [**updateAdminAiRoute**](docs/ADMINAIApi.md#updateadminairoute) | **PATCH** /admin/v1/ai/routes/{routeId} | Replace an AI route draft configuration
*ADMINCOMMERCEApi* | [**createAdminEntitlementAdjustment**](docs/ADMINCOMMERCEApi.md#createadminentitlementadjustment) | **POST** /admin/v1/entitlement-adjustments | Apply one idempotent and audited manual benefit adjustment
*ADMINCOMMERCEApi* | [**createAdminProduct**](docs/ADMINCOMMERCEApi.md#createadminproduct) | **POST** /admin/v1/products | Create a new immutable product draft version
*ADMINCOMMERCEApi* | [**decideAdminRefund**](docs/ADMINCOMMERCEApi.md#decideadminrefund) | **POST** /admin/v1/refunds/{refundId}/decision | Approve or reject a refund request
*ADMINCOMMERCEApi* | [**executeAdminRefund**](docs/ADMINCOMMERCEApi.md#executeadminrefund) | **POST** /admin/v1/refunds/{refundId}/execute | Execute an approved provider refund and recover eligible benefits
*ADMINCOMMERCEApi* | [**getAdminOrder**](docs/ADMINCOMMERCEApi.md#getadminorder) | **GET** /admin/v1/orders/{orderId} | Read one order and all payment attempts
*ADMINCOMMERCEApi* | [**getAdminProduct**](docs/ADMINCOMMERCEApi.md#getadminproduct) | **GET** /admin/v1/products/{productVersionId} | Read one product version
*ADMINCOMMERCEApi* | [**getAdminRefund**](docs/ADMINCOMMERCEApi.md#getadminrefund) | **GET** /admin/v1/refunds/{refundId} | Read one refund request
*ADMINCOMMERCEApi* | [**listAdminOrders**](docs/ADMINCOMMERCEApi.md#listadminorders) | **GET** /admin/v1/orders | List immutable order and payment facts
*ADMINCOMMERCEApi* | [**listAdminProducts**](docs/ADMINCOMMERCEApi.md#listadminproducts) | **GET** /admin/v1/products | List all product drafts and published versions
*ADMINCOMMERCEApi* | [**listAdminRefunds**](docs/ADMINCOMMERCEApi.md#listadminrefunds) | **GET** /admin/v1/refunds | List refund requests and recovery status
*ADMINCOMMERCEApi* | [**publishAdminProduct**](docs/ADMINCOMMERCEApi.md#publishadminproduct) | **POST** /admin/v1/products/{productVersionId}/publish | Publish a product version with maker-checker approval
*ADMINCOMMERCEApi* | [**rollbackAdminProduct**](docs/ADMINCOMMERCEApi.md#rollbackadminproduct) | **POST** /admin/v1/products/{productCode}/rollback | Re-publish a previously published immutable version
*ADMINCOMMERCEApi* | [**runAdminPaymentReconciliation**](docs/ADMINCOMMERCEApi.md#runadminpaymentreconciliation) | **POST** /admin/v1/payment-reconciliations | Reconcile stale payment attempts and recover interrupted grants
*ADMINCOMMERCEApi* | [**updateAdminProduct**](docs/ADMINCOMMERCEApi.md#updateadminproduct) | **PATCH** /admin/v1/products/{productVersionId} | Replace a draft with a new immutable product version
*ADMINPLATFORMApi* | [**changeAdminUserStatus**](docs/ADMINPLATFORMApi.md#changeadminuserstatus) | **PATCH** /admin/v1/users/{userId}/status | Suspend or restore a user and revoke active sessions
*ADMINPLATFORMApi* | [**createAdminNotice**](docs/ADMINPLATFORMApi.md#createadminnotice) | **POST** /admin/v1/notices | Create an announcement draft
*ADMINPLATFORMApi* | [**getAdminSystemConfig**](docs/ADMINPLATFORMApi.md#getadminsystemconfig) | **GET** /admin/v1/system-config | Read latest website configuration draft or published version
*ADMINPLATFORMApi* | [**getAdminUser**](docs/ADMINPLATFORMApi.md#getadminuser) | **GET** /admin/v1/users/{userId} | Read one user with devices and consents
*ADMINPLATFORMApi* | [**getAdminUserEntitlements**](docs/ADMINPLATFORMApi.md#getadminuserentitlements) | **GET** /admin/v1/users/{userId}/entitlements | Read user entitlement and wallet facts
*ADMINPLATFORMApi* | [**grantAdminUserPlan**](docs/ADMINPLATFORMApi.md#grantadminuserplan) | **POST** /admin/v1/users/{userId}/plan-grants | Grant benefits from an active published plan version
*ADMINPLATFORMApi* | [**listAdminNotices**](docs/ADMINPLATFORMApi.md#listadminnotices) | **GET** /admin/v1/notices | List latest announcement versions
*ADMINPLATFORMApi* | [**listAdminUserLedger**](docs/ADMINPLATFORMApi.md#listadminuserledger) | **GET** /admin/v1/users/{userId}/ledger | List immutable user wallet ledger entries
*ADMINPLATFORMApi* | [**listAdminUsers**](docs/ADMINPLATFORMApi.md#listadminusers) | **GET** /admin/v1/users | List and search masked user accounts
*ADMINPLATFORMApi* | [**publishAdminNotice**](docs/ADMINPLATFORMApi.md#publishadminnotice) | **POST** /admin/v1/notices/{noticeId}/publish | Publish an announcement draft
*ADMINPLATFORMApi* | [**publishAdminSystemConfig**](docs/ADMINPLATFORMApi.md#publishadminsystemconfig) | **POST** /admin/v1/system-config/publish | Publish the current website configuration draft
*ADMINPLATFORMApi* | [**resetAdminUserLoginState**](docs/ADMINPLATFORMApi.md#resetadminuserloginstate) | **POST** /admin/v1/users/{userId}/security/reset | Revoke all sessions and invalidate pending login challenges
*ADMINPLATFORMApi* | [**revokeAdminNotice**](docs/ADMINPLATFORMApi.md#revokeadminnotice) | **POST** /admin/v1/notices/{noticeId}/revoke | Revoke a published announcement immediately
*ADMINPLATFORMApi* | [**revokeAdminUserDevice**](docs/ADMINPLATFORMApi.md#revokeadminuserdevice) | **POST** /admin/v1/users/{userId}/devices/{deviceId}/revoke | Revoke a user device and its active sessions
*ADMINPLATFORMApi* | [**updateAdminNotice**](docs/ADMINPLATFORMApi.md#updateadminnotice) | **PATCH** /admin/v1/notices/{noticeId} | Save an announcement draft
*ADMINPLATFORMApi* | [**updateAdminSystemConfig**](docs/ADMINPLATFORMApi.md#updateadminsystemconfig) | **PATCH** /admin/v1/system-config | Save a website configuration draft
*ADMINPLATFORMApi* | [**updateAdminUserProfile**](docs/ADMINPLATFORMApi.md#updateadminuserprofile) | **PATCH** /admin/v1/users/{userId}/profile | Update non-credential user profile fields
*ADMINPROVIDERApi* | [**checkAdminProviderHealth**](docs/ADMINPROVIDERApi.md#checkadminproviderhealth) | **POST** /admin/v1/providers/{providerId}/health-checks | Execute an audited redacted provider health check
*ADMINPROVIDERApi* | [**createAdminProvider**](docs/ADMINPROVIDERApi.md#createadminprovider) | **POST** /admin/v1/providers | Create a provider draft
*ADMINPROVIDERApi* | [**disableAdminProvider**](docs/ADMINPROVIDERApi.md#disableadminprovider) | **POST** /admin/v1/providers/{providerId}/disable | Immediately remove a published provider from runtime selection
*ADMINPROVIDERApi* | [**getAdminProvider**](docs/ADMINPROVIDERApi.md#getadminprovider) | **GET** /admin/v1/providers/{providerId} | Read one redacted provider configuration
*ADMINPROVIDERApi* | [**listAdminProviders**](docs/ADMINPROVIDERApi.md#listadminproviders) | **GET** /admin/v1/providers | List configured external providers
*ADMINPROVIDERApi* | [**publishAdminProvider**](docs/ADMINPROVIDERApi.md#publishadminprovider) | **POST** /admin/v1/providers/{providerId}/publish | Publish a validated provider with bounded rollout
*ADMINPROVIDERApi* | [**rollbackAdminProvider**](docs/ADMINPROVIDERApi.md#rollbackadminprovider) | **POST** /admin/v1/providers/{providerId}/rollback | Atomically restore a previously published provider version
*ADMINPROVIDERApi* | [**rotateAdminProviderCredentials**](docs/ADMINPROVIDERApi.md#rotateadminprovidercredentials) | **POST** /admin/v1/providers/{providerId}/credentials | Create a write-only encrypted credential version
*ADMINPROVIDERApi* | [**updateAdminProvider**](docs/ADMINPROVIDERApi.md#updateadminprovider) | **PATCH** /admin/v1/providers/{providerId} | Update a provider draft configuration
*ADMINRBACApi* | [**changeAdminAuditLegalHold**](docs/ADMINRBACApi.md#changeadminauditlegalhold) | **POST** /admin/v1/audit-events/{eventId}/legal-hold | Enable or release legal hold for one audit event
*ADMINRBACApi* | [**createAdminAuditExport**](docs/ADMINRBACApi.md#createadminauditexport) | **POST** /admin/v1/audit-events/exports | Create a short-lived encrypted regulatory audit bundle
*ADMINRBACApi* | [**getCurrentAdmin**](docs/ADMINRBACApi.md#getcurrentadmin) | **GET** /admin/v1/me | Read the current administrator and RBAC summary
*ADMINRBACApi* | [**listAdminAuditEvents**](docs/ADMINRBACApi.md#listadminauditevents) | **GET** /admin/v1/audit-events | Search the tamper-evident compliance audit ledger
*ADMINRBACApi* | [**loginAdmin**](docs/ADMINRBACApi.md#loginadmin) | **POST** /admin/v1/auth/login | Verify administrator credentials
*ADMINRBACApi* | [**logoutAdmin**](docs/ADMINRBACApi.md#logoutadmin) | **POST** /admin/v1/auth/logout | Revoke the current administrator session
*ADMINRBACApi* | [**readAdminAuditExport**](docs/ADMINRBACApi.md#readadminauditexport) | **POST** /admin/v1/audit-events/exports/{exportId}/content | Read a non-expired regulatory audit bundle
*ADMINRBACApi* | [**readAdminAuditSensitiveContent**](docs/ADMINRBACApi.md#readadminauditsensitivecontent) | **POST** /admin/v1/audit-events/{eventId}/sensitive-content | Read encrypted user content with mandatory purpose logging
*ADMINRBACApi* | [**refreshAdminAccessToken**](docs/ADMINRBACApi.md#refreshadminaccesstoken) | **POST** /admin/v1/auth/refresh | Rotate an administrator refresh token
*ADMINRBACApi* | [**verifyAdminAuditIntegrity**](docs/ADMINRBACApi.md#verifyadminauditintegrity) | **GET** /admin/v1/audit-events/integrity | Verify audit hash-chain and encrypted payload digests
*ADMINRBACApi* | [**verifyAdminMfa**](docs/ADMINRBACApi.md#verifyadminmfa) | **POST** /admin/v1/auth/mfa/verify | Verify an administrator MFA challenge
*ADMINREFERRALApi* | [**createAdminReferralCampaign**](docs/ADMINREFERRALApi.md#createadminreferralcampaign) | **POST** /admin/v1/referral-campaigns | Create a referral campaign draft
*ADMINREFERRALApi* | [**getAdminReferralCampaign**](docs/ADMINREFERRALApi.md#getadminreferralcampaign) | **GET** /admin/v1/referral-campaigns/{campaignId} | Read one referral campaign version
*ADMINREFERRALApi* | [**listAdminReferralCampaignVersions**](docs/ADMINREFERRALApi.md#listadminreferralcampaignversions) | **GET** /admin/v1/referral-campaigns/{campaignId}/versions | List immutable referral campaign versions
*ADMINREFERRALApi* | [**listAdminReferralCampaigns**](docs/ADMINREFERRALApi.md#listadminreferralcampaigns) | **GET** /admin/v1/referral-campaigns | List referral campaign versions
*ADMINREFERRALApi* | [**publishAdminReferralCampaign**](docs/ADMINREFERRALApi.md#publishadminreferralcampaign) | **POST** /admin/v1/referral-campaigns/{campaignId}/publish | Publish a referral campaign with bounded rollout
*ADMINREFERRALApi* | [**rollbackAdminReferralCampaign**](docs/ADMINREFERRALApi.md#rollbackadminreferralcampaign) | **POST** /admin/v1/referral-campaigns/{campaignId}/rollback | Restore a previously published campaign version for new bindings
*ADMINREFERRALApi* | [**updateAdminReferralCampaign**](docs/ADMINREFERRALApi.md#updateadminreferralcampaign) | **PATCH** /admin/v1/referral-campaigns/{campaignId} | Replace a referral campaign draft configuration
*ADMINSUPPORTApi* | [**getAdminSupportTicket**](docs/ADMINSUPPORTApi.md#getadminsupportticket) | **GET** /admin/v1/support/tickets/{ticketId} | Read ticket conversation including internal notes
*ADMINSUPPORTApi* | [**listAdminSupportTickets**](docs/ADMINSUPPORTApi.md#listadminsupporttickets) | **GET** /admin/v1/support/tickets | List support queue
*ADMINSUPPORTApi* | [**updateAdminSupportTicket**](docs/ADMINSUPPORTApi.md#updateadminsupportticket) | **PATCH** /admin/v1/support/tickets/{ticketId} | Reply, add internal note, assign, prioritize, or resolve a ticket
*ADREWARDApi* | [**createAdRewardSession**](docs/ADREWARDApi.md#createadrewardsessionoperation) | **POST** /v1/ad-rewards/sessions | Create a short-lived server-bound advertising reward session
*ADREWARDApi* | [**getAdRewardSession**](docs/ADREWARDApi.md#getadrewardsession) | **GET** /v1/ad-rewards/sessions/{rewardSessionId} | Read the verified advertising reward state
*ADWEBHOOKApi* | [**receiveAdRewardCallback**](docs/ADWEBHOOKApi.md#receiveadrewardcallback) | **POST** /webhooks/v1/ads/{providerId} | Verify a server-to-server advertising completion callback
*APPCONFIGApi* | [**getAppBootstrap**](docs/APPCONFIGApi.md#getappbootstrap) | **GET** /v1/app/bootstrap | Read the published application configuration
*APPCONFIGApi* | [**getHealth**](docs/APPCONFIGApi.md#gethealth) | **GET** /health | Read service health
*APPCONFIGApi* | [**listPublicNotices**](docs/APPCONFIGApi.md#listpublicnotices) | **GET** /v1/app/notices | List announcements active for this client
*AUTHApi* | [**getAuthChannels**](docs/AUTHApi.md#getauthchannels) | **GET** /v1/auth/channels | Read the public authentication channel policy
*AUTHApi* | [**loginWithEmail**](docs/AUTHApi.md#loginwithemail) | **POST** /v1/auth/email/login | Login or register with a verified email challenge
*AUTHApi* | [**loginWithSms**](docs/AUTHApi.md#loginwithsms) | **POST** /v1/auth/sms/login | Login or register with a verified SMS challenge
*AUTHApi* | [**logoutAllDevices**](docs/AUTHApi.md#logoutalldevices) | **POST** /v1/auth/logout-all | Revoke all sessions for the current user
*AUTHApi* | [**logoutCurrentDevice**](docs/AUTHApi.md#logoutcurrentdevice) | **POST** /v1/auth/logout | Revoke the current device session
*AUTHApi* | [**refreshAccessToken**](docs/AUTHApi.md#refreshaccesstoken) | **POST** /v1/auth/refresh | Rotate a refresh token
*AUTHApi* | [**sendEmailChallenge**](docs/AUTHApi.md#sendemailchallenge) | **POST** /v1/auth/email/send | Send a passwordless email login code
*AUTHApi* | [**sendSmsChallenge**](docs/AUTHApi.md#sendsmschallenge) | **POST** /v1/auth/sms/send | Send a login verification code
*CANDIDATEApi* | [**recordCandidateAction**](docs/CANDIDATEApi.md#recordcandidateaction) | **POST** /v1/candidates/{candidateId}/actions | Record an explicit candidate action
*CANDIDATEApi* | [**refineCandidate**](docs/CANDIDATEApi.md#refinecandidateoperation) | **POST** /v1/candidates/{candidateId}/refine | Create a refined child generation for one candidate
*CONSENTApi* | [**listMyConsents**](docs/CONSENTApi.md#listmyconsents) | **GET** /v1/me/consents | Read current consent records
*CONSENTApi* | [**updateConsent**](docs/CONSENTApi.md#updateconsentoperation) | **PUT** /v1/me/consents/{consentType} | Grant or revoke an optional consent
*DATAGOVERNANCEApi* | [**cancelAccountDeletion**](docs/DATAGOVERNANCEApi.md#cancelaccountdeletion) | **DELETE** /v1/me/deletion | Cancel deletion during the cooling-off period
*DATAGOVERNANCEApi* | [**getDataRequest**](docs/DATAGOVERNANCEApi.md#getdatarequest) | **GET** /v1/me/data-requests/{requestId} | Read a personal data request
*DATAGOVERNANCEApi* | [**getDeletionStatus**](docs/DATAGOVERNANCEApi.md#getdeletionstatus) | **GET** /v1/me/deletion | Read account deletion status
*DATAGOVERNANCEApi* | [**requestAccountDeletion**](docs/DATAGOVERNANCEApi.md#requestaccountdeletion) | **POST** /v1/me/deletion | Request account deletion with a cooling-off period
*DATAGOVERNANCEApi* | [**requestDataExport**](docs/DATAGOVERNANCEApi.md#requestdataexport) | **POST** /v1/me/data-export | Request an asynchronous personal data export
*ENTITLEMENTApi* | [**getEntitlements**](docs/ENTITLEMENTApi.md#getentitlements) | **GET** /v1/entitlements | Get server-authoritative user entitlements
*GENERATIONApi* | [**cancelGeneration**](docs/GENERATIONApi.md#cancelgeneration) | **POST** /v1/generations/{generationId}/cancel | Cancel an unfinished task and release unsettled reservation
*GENERATIONApi* | [**createGeneration**](docs/GENERATIONApi.md#creategenerationoperation) | **POST** /v1/generations | Create a generation and atomically reserve its quote
*GENERATIONApi* | [**getGeneration**](docs/GENERATIONApi.md#getgeneration) | **GET** /v1/generations/{generationId} | Get an owned generation snapshot
*GENERATIONApi* | [**quoteGeneration**](docs/GENERATIONApi.md#quotegeneration) | **POST** /v1/generations/quote | Quote energy cost before creating a generation
*GENERATIONApi* | [**regenerateGeneration**](docs/GENERATIONApi.md#regenerategeneration) | **POST** /v1/generations/{generationId}/regenerate | Create a child generation using a new quote
*GENERATIONApi* | [**streamGenerationEvents**](docs/GENERATIONApi.md#streamgenerationevents) | **GET** /v1/generations/{generationId}/events | Stream retained generation events
*ORDERApi* | [**createOrder**](docs/ORDERApi.md#createorderoperation) | **POST** /v1/orders | Create an immutable order and initial payment attempt
*ORDERApi* | [**createPaymentAttempt**](docs/ORDERApi.md#createpaymentattemptoperation) | **POST** /v1/orders/{orderId}/payment-attempts | Create another payment attempt for an unpaid order
*ORDERApi* | [**getOrder**](docs/ORDERApi.md#getorder) | **GET** /v1/orders/{orderId} | Read an owned order and its payment attempts
*ORDERApi* | [**syncOrderPayment**](docs/ORDERApi.md#syncorderpayment) | **POST** /v1/orders/{orderId}/sync-payment | Query the provider and reconcile an unpaid order
*PAYMENTWEBHOOKApi* | [**receiveEpayCallback**](docs/PAYMENTWEBHOOKApi.md#receiveepaycallback) | **POST** /webhooks/v1/payments/epay/{providerId} | Receive and verify an Epay-compatible server callback
*PRODUCTApi* | [**getProduct**](docs/PRODUCTApi.md#getproduct) | **GET** /v1/products/{productVersionId} | Read one currently purchasable product version
*PRODUCTApi* | [**listProducts**](docs/PRODUCTApi.md#listproducts) | **GET** /v1/products | List the active server-published product catalog
*REFERRALApi* | [**bindReferralInvite**](docs/REFERRALApi.md#bindreferralinvite) | **POST** /v1/referrals/bind | Bind the authenticated account to one inviter
*REFERRALApi* | [**getReferralProgram**](docs/REFERRALApi.md#getreferralprogram) | **GET** /v1/referrals/program | Read the active referral campaign and personal invite link
*REFERRALApi* | [**listReferralInvites**](docs/REFERRALApi.md#listreferralinvites) | **GET** /v1/referrals/invites | List masked invitation progress
*REFERRALApi* | [**listReferralRewards**](docs/REFERRALApi.md#listreferralrewards) | **GET** /v1/referrals/rewards | List referral reward and reversal entries
*REFUNDApi* | [**createRefund**](docs/REFUNDApi.md#createrefundoperation) | **POST** /v1/refunds | Request a full or partial refund
*REFUNDApi* | [**getRefund**](docs/REFUNDApi.md#getrefund) | **GET** /v1/refunds/{refundId} | Read an owned refund and entitlement recovery state
*RISKApi* | [**appealRiskEvent**](docs/RISKApi.md#appealriskevent) | **POST** /v1/risk-events/{riskEventId}/appeals | Appeal a safety decision without bypassing it
*SUBSCRIPTIONApi* | [**cancelSubscription**](docs/SUBSCRIPTIONApi.md#cancelsubscriptionoperation) | **POST** /v1/subscriptions/{subscriptionId}/cancel | Cancel renewal or schedule cancellation at period end
*SUBSCRIPTIONApi* | [**listSubscriptions**](docs/SUBSCRIPTIONApi.md#listsubscriptions) | **GET** /v1/subscriptions | List owned prepaid terms and recurring mandates
*SUPPORTApi* | [**addMySupportMessage**](docs/SUPPORTApi.md#addmysupportmessage) | **POST** /v1/support/tickets/{ticketId}/messages | Reply to an owned support ticket
*SUPPORTApi* | [**createSupportTicket**](docs/SUPPORTApi.md#createsupportticketoperation) | **POST** /v1/support/tickets | Create a support ticket
*SUPPORTApi* | [**getMySupportTicket**](docs/SUPPORTApi.md#getmysupportticket) | **GET** /v1/support/tickets/{ticketId} | Read one owned support ticket
*SUPPORTApi* | [**listMySupportTickets**](docs/SUPPORTApi.md#listmysupporttickets) | **GET** /v1/support/tickets | List current user\&#39;s support tickets
*USERApi* | [**getCurrentUser**](docs/USERApi.md#getcurrentuser) | **GET** /v1/me | Get the current account
*USERApi* | [**listDevices**](docs/USERApi.md#listdevices) | **GET** /v1/me/devices | List authenticated devices
*USERApi* | [**revokeDevice**](docs/USERApi.md#revokedevice) | **DELETE** /v1/me/devices/{deviceId} | Revoke one authenticated device
*USERApi* | [**updateCurrentUser**](docs/USERApi.md#updatecurrentuser) | **PATCH** /v1/me | Update non-sensitive account profile fields
*WALLETApi* | [**getWallet**](docs/WALLETApi.md#getwallet) | **GET** /v1/wallet | Get energy balance and active reservations
*WALLETApi* | [**listWalletLedger**](docs/WALLETApi.md#listwalletledger) | **GET** /v1/wallet/ledger | List immutable wallet entries


### Models

- [AccountStatus](docs/AccountStatus.md)
- [AdRewardCallbackRequest](docs/AdRewardCallbackRequest.md)
- [AdRewardSession](docs/AdRewardSession.md)
- [AdRewardSessionResponse](docs/AdRewardSessionResponse.md)
- [AdRewardStatus](docs/AdRewardStatus.md)
- [AddSupportMessageRequest](docs/AddSupportMessageRequest.md)
- [AdminAccountStatus](docs/AdminAccountStatus.md)
- [AdminAuthErrorCode](docs/AdminAuthErrorCode.md)
- [AdminAuthErrorResponse](docs/AdminAuthErrorResponse.md)
- [AdminAuthenticationData](docs/AdminAuthenticationData.md)
- [AdminAuthenticationResponse](docs/AdminAuthenticationResponse.md)
- [AdminEmptyResponse](docs/AdminEmptyResponse.md)
- [AdminIdentitySummary](docs/AdminIdentitySummary.md)
- [AdminLoginData](docs/AdminLoginData.md)
- [AdminLoginRequest](docs/AdminLoginRequest.md)
- [AdminLoginResponse](docs/AdminLoginResponse.md)
- [AdminMeData](docs/AdminMeData.md)
- [AdminMeResponse](docs/AdminMeResponse.md)
- [AdminMfaChallenge](docs/AdminMfaChallenge.md)
- [AdminMfaMethod](docs/AdminMfaMethod.md)
- [AdminMfaStatus](docs/AdminMfaStatus.md)
- [AdminMfaVerifyRequest](docs/AdminMfaVerifyRequest.md)
- [AdminOrder](docs/AdminOrder.md)
- [AdminOrderListData](docs/AdminOrderListData.md)
- [AdminOrderListResponse](docs/AdminOrderListResponse.md)
- [AdminOrderResponse](docs/AdminOrderResponse.md)
- [AdminPermissionCode](docs/AdminPermissionCode.md)
- [AdminProductListData](docs/AdminProductListData.md)
- [AdminProductListResponse](docs/AdminProductListResponse.md)
- [AdminProductPublishRequest](docs/AdminProductPublishRequest.md)
- [AdminProductResponse](docs/AdminProductResponse.md)
- [AdminProductRollbackRequest](docs/AdminProductRollbackRequest.md)
- [AdminProductVersion](docs/AdminProductVersion.md)
- [AdminProductWriteRequest](docs/AdminProductWriteRequest.md)
- [AdminRefreshRequest](docs/AdminRefreshRequest.md)
- [AdminRefund](docs/AdminRefund.md)
- [AdminRefundDecisionRequest](docs/AdminRefundDecisionRequest.md)
- [AdminRefundExecuteRequest](docs/AdminRefundExecuteRequest.md)
- [AdminRefundListData](docs/AdminRefundListData.md)
- [AdminRefundListResponse](docs/AdminRefundListResponse.md)
- [AdminRefundResponse](docs/AdminRefundResponse.md)
- [AdminRoleSummary](docs/AdminRoleSummary.md)
- [AdminSessionSummary](docs/AdminSessionSummary.md)
- [AdminTokenData](docs/AdminTokenData.md)
- [AdminTokenPair](docs/AdminTokenPair.md)
- [AdminTokenResponse](docs/AdminTokenResponse.md)
- [AdminUpdateSupportTicketRequest](docs/AdminUpdateSupportTicketRequest.md)
- [AdminUserDetail](docs/AdminUserDetail.md)
- [AdminUserDetailResponse](docs/AdminUserDetailResponse.md)
- [AdminUserDeviceRevokeRequest](docs/AdminUserDeviceRevokeRequest.md)
- [AdminUserEntitlementResponse](docs/AdminUserEntitlementResponse.md)
- [AdminUserListData](docs/AdminUserListData.md)
- [AdminUserListResponse](docs/AdminUserListResponse.md)
- [AdminUserPlanGrantRequest](docs/AdminUserPlanGrantRequest.md)
- [AdminUserProfileRequest](docs/AdminUserProfileRequest.md)
- [AdminUserResponse](docs/AdminUserResponse.md)
- [AdminUserSecurityAction](docs/AdminUserSecurityAction.md)
- [AdminUserSecurityActionResponse](docs/AdminUserSecurityActionResponse.md)
- [AdminUserSecurityResetRequest](docs/AdminUserSecurityResetRequest.md)
- [AdminUserStatusRequest](docs/AdminUserStatusRequest.md)
- [AdminUserSummary](docs/AdminUserSummary.md)
- [AdminWalletLedgerListResponse](docs/AdminWalletLedgerListResponse.md)
- [AiEvaluationRun](docs/AiEvaluationRun.md)
- [AiEvaluationRunRequest](docs/AiEvaluationRunRequest.md)
- [AiEvaluationRunResponse](docs/AiEvaluationRunResponse.md)
- [AiModality](docs/AiModality.md)
- [AiModelMapping](docs/AiModelMapping.md)
- [AiModelMappingListData](docs/AiModelMappingListData.md)
- [AiModelMappingListResponse](docs/AiModelMappingListResponse.md)
- [AiModelMappingResponse](docs/AiModelMappingResponse.md)
- [AiModelMappingWriteRequest](docs/AiModelMappingWriteRequest.md)
- [AiPromptListData](docs/AiPromptListData.md)
- [AiPromptListResponse](docs/AiPromptListResponse.md)
- [AiPromptResponse](docs/AiPromptResponse.md)
- [AiPromptTemplate](docs/AiPromptTemplate.md)
- [AiPromptWriteRequest](docs/AiPromptWriteRequest.md)
- [AiPublishRequest](docs/AiPublishRequest.md)
- [AiResourceStatus](docs/AiResourceStatus.md)
- [AiRiskPolicy](docs/AiRiskPolicy.md)
- [AiRiskPolicyListData](docs/AiRiskPolicyListData.md)
- [AiRiskPolicyListResponse](docs/AiRiskPolicyListResponse.md)
- [AiRiskPolicyResponse](docs/AiRiskPolicyResponse.md)
- [AiRiskPolicyWriteRequest](docs/AiRiskPolicyWriteRequest.md)
- [AiRollbackRequest](docs/AiRollbackRequest.md)
- [AiRoute](docs/AiRoute.md)
- [AiRouteListData](docs/AiRouteListData.md)
- [AiRouteListResponse](docs/AiRouteListResponse.md)
- [AiRouteResponse](docs/AiRouteResponse.md)
- [AiRouteTarget](docs/AiRouteTarget.md)
- [AiRouteWriteRequest](docs/AiRouteWriteRequest.md)
- [AiScenario](docs/AiScenario.md)
- [AppBootstrap](docs/AppBootstrap.md)
- [AppBootstrapResponse](docs/AppBootstrapResponse.md)
- [Appeal](docs/Appeal.md)
- [AppealRequest](docs/AppealRequest.md)
- [AppealResponse](docs/AppealResponse.md)
- [AuditEvent](docs/AuditEvent.md)
- [AuditEventListData](docs/AuditEventListData.md)
- [AuditEventListResponse](docs/AuditEventListResponse.md)
- [AuditEventResponse](docs/AuditEventResponse.md)
- [AuditExportContentData](docs/AuditExportContentData.md)
- [AuditExportContentResponse](docs/AuditExportContentResponse.md)
- [AuditExportData](docs/AuditExportData.md)
- [AuditExportReadRequest](docs/AuditExportReadRequest.md)
- [AuditExportRequest](docs/AuditExportRequest.md)
- [AuditExportResponse](docs/AuditExportResponse.md)
- [AuditIntegrityData](docs/AuditIntegrityData.md)
- [AuditIntegrityResponse](docs/AuditIntegrityResponse.md)
- [AuditReasonRequest](docs/AuditReasonRequest.md)
- [AuthChallengeMode](docs/AuthChallengeMode.md)
- [AuthChannel](docs/AuthChannel.md)
- [AuthChannelAvailability](docs/AuthChannelAvailability.md)
- [AuthChannelPolicy](docs/AuthChannelPolicy.md)
- [AuthChannelPolicyResponse](docs/AuthChannelPolicyResponse.md)
- [BaseSuccessEnvelope](docs/BaseSuccessEnvelope.md)
- [BenefitBalances](docs/BenefitBalances.md)
- [BenefitGrant](docs/BenefitGrant.md)
- [BindReferralRequest](docs/BindReferralRequest.md)
- [CancelSubscriptionRequest](docs/CancelSubscriptionRequest.md)
- [Candidate](docs/Candidate.md)
- [CandidateAction](docs/CandidateAction.md)
- [CandidateActionRequest](docs/CandidateActionRequest.md)
- [CandidateActionResponse](docs/CandidateActionResponse.md)
- [CandidateActionType](docs/CandidateActionType.md)
- [ChargedFrom](docs/ChargedFrom.md)
- [CheckoutAction](docs/CheckoutAction.md)
- [CheckoutActionType](docs/CheckoutActionType.md)
- [CommunicationGoal](docs/CommunicationGoal.md)
- [ConsentListData](docs/ConsentListData.md)
- [ConsentListResponse](docs/ConsentListResponse.md)
- [ConsentRecord](docs/ConsentRecord.md)
- [ConsentResponse](docs/ConsentResponse.md)
- [ConsentType](docs/ConsentType.md)
- [CreateAdRewardSessionRequest](docs/CreateAdRewardSessionRequest.md)
- [CreateGenerationRequest](docs/CreateGenerationRequest.md)
- [CreateOrderRequest](docs/CreateOrderRequest.md)
- [CreatePaymentAttemptRequest](docs/CreatePaymentAttemptRequest.md)
- [CreateRefundRequest](docs/CreateRefundRequest.md)
- [CreateSupportTicketRequest](docs/CreateSupportTicketRequest.md)
- [CredentialName](docs/CredentialName.md)
- [CredentialRotation](docs/CredentialRotation.md)
- [CredentialRotationResponse](docs/CredentialRotationResponse.md)
- [CredentialSecretInput](docs/CredentialSecretInput.md)
- [DataRequestBase](docs/DataRequestBase.md)
- [DataRequestResponse](docs/DataRequestResponse.md)
- [DataRequestStatus](docs/DataRequestStatus.md)
- [DataRequestType](docs/DataRequestType.md)
- [DeletionRequest](docs/DeletionRequest.md)
- [DeletionStatus](docs/DeletionStatus.md)
- [DeletionStatusResponse](docs/DeletionStatusResponse.md)
- [Device](docs/Device.md)
- [DeviceListData](docs/DeviceListData.md)
- [DeviceListResponse](docs/DeviceListResponse.md)
- [DisableProviderRequest](docs/DisableProviderRequest.md)
- [EmailApiConfiguration](docs/EmailApiConfiguration.md)
- [EmailChallenge](docs/EmailChallenge.md)
- [EmailChallengeResponse](docs/EmailChallengeResponse.md)
- [EmailLoginRequest](docs/EmailLoginRequest.md)
- [EmailPurpose](docs/EmailPurpose.md)
- [EmailSendRequest](docs/EmailSendRequest.md)
- [EmptyResponse](docs/EmptyResponse.md)
- [Entitlement](docs/Entitlement.md)
- [EntitlementAdjustment](docs/EntitlementAdjustment.md)
- [EntitlementAdjustmentRequest](docs/EntitlementAdjustmentRequest.md)
- [EntitlementAdjustmentResponse](docs/EntitlementAdjustmentResponse.md)
- [EntitlementResponse](docs/EntitlementResponse.md)
- [EpayConfiguration](docs/EpayConfiguration.md)
- [ErrorDetail](docs/ErrorDetail.md)
- [ErrorResponse](docs/ErrorResponse.md)
- [FieldError](docs/FieldError.md)
- [FreeEntitlementTemplate](docs/FreeEntitlementTemplate.md)
- [GenerationAnalysis](docs/GenerationAnalysis.md)
- [GenerationContext](docs/GenerationContext.md)
- [GenerationInput](docs/GenerationInput.md)
- [GenerationPolicy](docs/GenerationPolicy.md)
- [GenerationQuote](docs/GenerationQuote.md)
- [GenerationQuoteRequest](docs/GenerationQuoteRequest.md)
- [GenerationQuoteResponse](docs/GenerationQuoteResponse.md)
- [GenerationResponse](docs/GenerationResponse.md)
- [GenerationSnapshot](docs/GenerationSnapshot.md)
- [GenerationSnapshotAnalysis](docs/GenerationSnapshotAnalysis.md)
- [GenerationSnapshotUsage](docs/GenerationSnapshotUsage.md)
- [GenerationStatus](docs/GenerationStatus.md)
- [GenerationUsage](docs/GenerationUsage.md)
- [HealthCheckRequest](docs/HealthCheckRequest.md)
- [HealthData](docs/HealthData.md)
- [HealthSuccessResponse](docs/HealthSuccessResponse.md)
- [LedgerEntryType](docs/LedgerEntryType.md)
- [LegalHoldRequest](docs/LegalHoldRequest.md)
- [LogicalModel](docs/LogicalModel.md)
- [LoginData](docs/LoginData.md)
- [LoginResponse](docs/LoginResponse.md)
- [ModelQuoteOption](docs/ModelQuoteOption.md)
- [NativeAiConfiguration](docs/NativeAiConfiguration.md)
- [NoticeListResponse](docs/NoticeListResponse.md)
- [NoticeListResponseAllOfData](docs/NoticeListResponseAllOfData.md)
- [NoticeResponse](docs/NoticeResponse.md)
- [NoticeVersion](docs/NoticeVersion.md)
- [NoticeWriteRequest](docs/NoticeWriteRequest.md)
- [OpenAiCompatibleConfiguration](docs/OpenAiCompatibleConfiguration.md)
- [Order](docs/Order.md)
- [OrderResponse](docs/OrderResponse.md)
- [OrderStatus](docs/OrderStatus.md)
- [PaymentAttempt](docs/PaymentAttempt.md)
- [PaymentAttemptStatus](docs/PaymentAttemptStatus.md)
- [PaymentMethod](docs/PaymentMethod.md)
- [PaymentReconciliation](docs/PaymentReconciliation.md)
- [PaymentReconciliationRequest](docs/PaymentReconciliationRequest.md)
- [PaymentReconciliationResponse](docs/PaymentReconciliationResponse.md)
- [PendingConsent](docs/PendingConsent.md)
- [ProductListData](docs/ProductListData.md)
- [ProductListResponse](docs/ProductListResponse.md)
- [ProductOrderSnapshot](docs/ProductOrderSnapshot.md)
- [ProductPublicationStatus](docs/ProductPublicationStatus.md)
- [ProductResponse](docs/ProductResponse.md)
- [ProductType](docs/ProductType.md)
- [ProductVersion](docs/ProductVersion.md)
- [Provider](docs/Provider.md)
- [ProviderConfiguration](docs/ProviderConfiguration.md)
- [ProviderHealthCheck](docs/ProviderHealthCheck.md)
- [ProviderHealthCheckResponse](docs/ProviderHealthCheckResponse.md)
- [ProviderKind](docs/ProviderKind.md)
- [ProviderListData](docs/ProviderListData.md)
- [ProviderListResponse](docs/ProviderListResponse.md)
- [ProviderResponse](docs/ProviderResponse.md)
- [ProviderStatus](docs/ProviderStatus.md)
- [ProviderWriteRequest](docs/ProviderWriteRequest.md)
- [PublishProviderRequest](docs/PublishProviderRequest.md)
- [PublishReferralCampaignRequest](docs/PublishReferralCampaignRequest.md)
- [ReferralAntiAbusePolicy](docs/ReferralAntiAbusePolicy.md)
- [ReferralBeneficiary](docs/ReferralBeneficiary.md)
- [ReferralCampaign](docs/ReferralCampaign.md)
- [ReferralCampaignListData](docs/ReferralCampaignListData.md)
- [ReferralCampaignListResponse](docs/ReferralCampaignListResponse.md)
- [ReferralCampaignResponse](docs/ReferralCampaignResponse.md)
- [ReferralCampaignStatus](docs/ReferralCampaignStatus.md)
- [ReferralCampaignVersion](docs/ReferralCampaignVersion.md)
- [ReferralCampaignVersionListData](docs/ReferralCampaignVersionListData.md)
- [ReferralCampaignVersionListResponse](docs/ReferralCampaignVersionListResponse.md)
- [ReferralCampaignWriteRequest](docs/ReferralCampaignWriteRequest.md)
- [ReferralInvite](docs/ReferralInvite.md)
- [ReferralInviteListData](docs/ReferralInviteListData.md)
- [ReferralInviteListResponse](docs/ReferralInviteListResponse.md)
- [ReferralInviteResponse](docs/ReferralInviteResponse.md)
- [ReferralInviteStatus](docs/ReferralInviteStatus.md)
- [ReferralMilestoneCode](docs/ReferralMilestoneCode.md)
- [ReferralProgram](docs/ReferralProgram.md)
- [ReferralProgramResponse](docs/ReferralProgramResponse.md)
- [ReferralReward](docs/ReferralReward.md)
- [ReferralRewardListData](docs/ReferralRewardListData.md)
- [ReferralRewardListResponse](docs/ReferralRewardListResponse.md)
- [ReferralRewardRule](docs/ReferralRewardRule.md)
- [ReferralRewardStatus](docs/ReferralRewardStatus.md)
- [RefineCandidateRequest](docs/RefineCandidateRequest.md)
- [RefreshRequest](docs/RefreshRequest.md)
- [Refund](docs/Refund.md)
- [RefundResponse](docs/RefundResponse.md)
- [RefundStatus](docs/RefundStatus.md)
- [RegenerateRequest](docs/RegenerateRequest.md)
- [RelationshipStage](docs/RelationshipStage.md)
- [RenewalType](docs/RenewalType.md)
- [ReplyStrategy](docs/ReplyStrategy.md)
- [ReplyStyle](docs/ReplyStyle.md)
- [RewardUnit](docs/RewardUnit.md)
- [RollbackProviderRequest](docs/RollbackProviderRequest.md)
- [RollbackReferralCampaignRequest](docs/RollbackReferralCampaignRequest.md)
- [RotateCredentialsRequest](docs/RotateCredentialsRequest.md)
- [SafetyStatus](docs/SafetyStatus.md)
- [SalesChannel](docs/SalesChannel.md)
- [SensitiveContentData](docs/SensitiveContentData.md)
- [SensitiveContentReadRequest](docs/SensitiveContentReadRequest.md)
- [SensitiveContentResponse](docs/SensitiveContentResponse.md)
- [SmsChallenge](docs/SmsChallenge.md)
- [SmsChallengeResponse](docs/SmsChallengeResponse.md)
- [SmsConfiguration](docs/SmsConfiguration.md)
- [SmsLoginRequest](docs/SmsLoginRequest.md)
- [SmsPurpose](docs/SmsPurpose.md)
- [SmsSendRequest](docs/SmsSendRequest.md)
- [SmtpConfiguration](docs/SmtpConfiguration.md)
- [Subscription](docs/Subscription.md)
- [SubscriptionListData](docs/SubscriptionListData.md)
- [SubscriptionListResponse](docs/SubscriptionListResponse.md)
- [SubscriptionResponse](docs/SubscriptionResponse.md)
- [SubscriptionStatus](docs/SubscriptionStatus.md)
- [SupportMessage](docs/SupportMessage.md)
- [SupportTicket](docs/SupportTicket.md)
- [SupportTicketDetailResponse](docs/SupportTicketDetailResponse.md)
- [SupportTicketDetailResponseAllOfData](docs/SupportTicketDetailResponseAllOfData.md)
- [SupportTicketListResponse](docs/SupportTicketListResponse.md)
- [SupportTicketListResponseAllOfData](docs/SupportTicketListResponseAllOfData.md)
- [SupportTicketResponse](docs/SupportTicketResponse.md)
- [SystemConfigResponse](docs/SystemConfigResponse.md)
- [SystemConfigVersion](docs/SystemConfigVersion.md)
- [SystemConfigWriteRequest](docs/SystemConfigWriteRequest.md)
- [SystemIdentityConfig](docs/SystemIdentityConfig.md)
- [TlsMode](docs/TlsMode.md)
- [TokenPair](docs/TokenPair.md)
- [TokenResponse](docs/TokenResponse.md)
- [UpdateConsentRequest](docs/UpdateConsentRequest.md)
- [UpdateUserRequest](docs/UpdateUserRequest.md)
- [User](docs/User.md)
- [UserResponse](docs/UserResponse.md)
- [Wallet](docs/Wallet.md)
- [WalletLedgerData](docs/WalletLedgerData.md)
- [WalletLedgerEntry](docs/WalletLedgerEntry.md)
- [WalletLedgerResponse](docs/WalletLedgerResponse.md)
- [WalletResponse](docs/WalletResponse.md)
- [WalletSummary](docs/WalletSummary.md)

### Authorization


Authentication schemes defined for the API:
<a id="bearerAuth"></a>
#### bearerAuth


- **Type**: HTTP Bearer Token authentication (JWT)
<a id="adminBearerAuth"></a>
#### adminBearerAuth


- **Type**: HTTP Bearer Token authentication (JWT)

## About

This TypeScript SDK client supports the [Fetch API](https://fetch.spec.whatwg.org/)
and is automatically generated by the
[OpenAPI Generator](https://openapi-generator.tech) project:

- API version: `1.0.0`
- Package version: `1.0.0`
- Generator version: `7.24.0`
- Build package: `org.openapitools.codegen.languages.TypeScriptFetchClientCodegen`

The generated npm module supports the following:

- Environments
  * Node.js
  * Webpack
  * Browserify
- Language levels
  * ES5 - you must have a Promises/A+ library installed
  * ES6
- Module systems
  * CommonJS
  * ES6 module system


## Development

### Building

To build the TypeScript source code, you need to have Node.js and npm installed.
After cloning the repository, navigate to the project directory and run:

```bash
npm install
npm run build
```

### Publishing

Once you've built the package, you can publish it to npm:

```bash
npm publish
```

## License

[Proprietary]()
