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
  ADMINRBACApi,
} from '@love-reply/generated-api';
import type { GetCurrentAdminRequest } from '@love-reply/generated-api';

async function example() {
  console.log("🚀 Testing @love-reply/generated-api SDK...");
  const config = new Configuration({
    // Configure HTTP bearer authorization: adminBearerAuth
    accessToken: "YOUR BEARER TOKEN",
  });
  const api = new ADMINRBACApi(config);

  const body = {
    // string | Semantic application version used for compatibility enforcement.
    xClientVersion: xClientVersion_example,
    // 'ANDROID' | 'ADMIN_WEB'
    xPlatform: xPlatform_example,
    // string
    acceptLanguage: acceptLanguage_example,
    // string | Client correlation ID. The server returns the final accepted value. (optional)
    xRequestId: xRequestId_example,
  } satisfies GetCurrentAdminRequest;

  try {
    const data = await api.getCurrentAdmin(body);
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
*ADMINRBACApi* | [**getCurrentAdmin**](docs/ADMINRBACApi.md#getcurrentadmin) | **GET** /admin/v1/me | Read the current administrator and RBAC summary
*ADMINRBACApi* | [**loginAdmin**](docs/ADMINRBACApi.md#loginadmin) | **POST** /admin/v1/auth/login | Verify administrator credentials
*ADMINRBACApi* | [**logoutAdmin**](docs/ADMINRBACApi.md#logoutadmin) | **POST** /admin/v1/auth/logout | Revoke the current administrator session
*ADMINRBACApi* | [**refreshAdminAccessToken**](docs/ADMINRBACApi.md#refreshadminaccesstoken) | **POST** /admin/v1/auth/refresh | Rotate an administrator refresh token
*ADMINRBACApi* | [**verifyAdminMfa**](docs/ADMINRBACApi.md#verifyadminmfa) | **POST** /admin/v1/auth/mfa/verify | Verify an administrator MFA challenge
*APPCONFIGApi* | [**getHealth**](docs/APPCONFIGApi.md#gethealth) | **GET** /health | Read service health
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
*RISKApi* | [**appealRiskEvent**](docs/RISKApi.md#appealriskevent) | **POST** /v1/risk-events/{riskEventId}/appeals | Appeal a safety decision without bypassing it
*USERApi* | [**getCurrentUser**](docs/USERApi.md#getcurrentuser) | **GET** /v1/me | Get the current account
*USERApi* | [**listDevices**](docs/USERApi.md#listdevices) | **GET** /v1/me/devices | List authenticated devices
*USERApi* | [**revokeDevice**](docs/USERApi.md#revokedevice) | **DELETE** /v1/me/devices/{deviceId} | Revoke one authenticated device
*USERApi* | [**updateCurrentUser**](docs/USERApi.md#updatecurrentuser) | **PATCH** /v1/me | Update non-sensitive account profile fields
*WALLETApi* | [**getWallet**](docs/WALLETApi.md#getwallet) | **GET** /v1/wallet | Get energy balance and active reservations
*WALLETApi* | [**listWalletLedger**](docs/WALLETApi.md#listwalletledger) | **GET** /v1/wallet/ledger | List immutable wallet entries


### Models

- [AccountStatus](docs/AccountStatus.md)
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
- [AdminPermissionCode](docs/AdminPermissionCode.md)
- [AdminRefreshRequest](docs/AdminRefreshRequest.md)
- [AdminRoleSummary](docs/AdminRoleSummary.md)
- [AdminSessionSummary](docs/AdminSessionSummary.md)
- [AdminTokenData](docs/AdminTokenData.md)
- [AdminTokenPair](docs/AdminTokenPair.md)
- [AdminTokenResponse](docs/AdminTokenResponse.md)
- [Appeal](docs/Appeal.md)
- [AppealRequest](docs/AppealRequest.md)
- [AppealResponse](docs/AppealResponse.md)
- [AuthChallengeMode](docs/AuthChallengeMode.md)
- [AuthChannel](docs/AuthChannel.md)
- [AuthChannelAvailability](docs/AuthChannelAvailability.md)
- [AuthChannelPolicy](docs/AuthChannelPolicy.md)
- [AuthChannelPolicyResponse](docs/AuthChannelPolicyResponse.md)
- [BaseSuccessEnvelope](docs/BaseSuccessEnvelope.md)
- [BenefitBalances](docs/BenefitBalances.md)
- [Candidate](docs/Candidate.md)
- [CandidateAction](docs/CandidateAction.md)
- [CandidateActionRequest](docs/CandidateActionRequest.md)
- [CandidateActionResponse](docs/CandidateActionResponse.md)
- [CandidateActionType](docs/CandidateActionType.md)
- [ChargedFrom](docs/ChargedFrom.md)
- [CommunicationGoal](docs/CommunicationGoal.md)
- [ConsentListData](docs/ConsentListData.md)
- [ConsentListResponse](docs/ConsentListResponse.md)
- [ConsentRecord](docs/ConsentRecord.md)
- [ConsentResponse](docs/ConsentResponse.md)
- [ConsentType](docs/ConsentType.md)
- [CreateGenerationRequest](docs/CreateGenerationRequest.md)
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
- [EmailChallenge](docs/EmailChallenge.md)
- [EmailChallengeResponse](docs/EmailChallengeResponse.md)
- [EmailLoginRequest](docs/EmailLoginRequest.md)
- [EmailPurpose](docs/EmailPurpose.md)
- [EmailSendRequest](docs/EmailSendRequest.md)
- [EmptyResponse](docs/EmptyResponse.md)
- [Entitlement](docs/Entitlement.md)
- [EntitlementResponse](docs/EntitlementResponse.md)
- [ErrorDetail](docs/ErrorDetail.md)
- [ErrorResponse](docs/ErrorResponse.md)
- [FieldError](docs/FieldError.md)
- [GenerationAnalysis](docs/GenerationAnalysis.md)
- [GenerationContext](docs/GenerationContext.md)
- [GenerationInput](docs/GenerationInput.md)
- [GenerationQuote](docs/GenerationQuote.md)
- [GenerationQuoteRequest](docs/GenerationQuoteRequest.md)
- [GenerationQuoteResponse](docs/GenerationQuoteResponse.md)
- [GenerationResponse](docs/GenerationResponse.md)
- [GenerationSnapshot](docs/GenerationSnapshot.md)
- [GenerationSnapshotAnalysis](docs/GenerationSnapshotAnalysis.md)
- [GenerationSnapshotUsage](docs/GenerationSnapshotUsage.md)
- [GenerationStatus](docs/GenerationStatus.md)
- [GenerationUsage](docs/GenerationUsage.md)
- [HealthData](docs/HealthData.md)
- [HealthSuccessResponse](docs/HealthSuccessResponse.md)
- [LedgerEntryType](docs/LedgerEntryType.md)
- [LoginData](docs/LoginData.md)
- [LoginResponse](docs/LoginResponse.md)
- [ModelQuoteOption](docs/ModelQuoteOption.md)
- [PendingConsent](docs/PendingConsent.md)
- [RefineCandidateRequest](docs/RefineCandidateRequest.md)
- [RefreshRequest](docs/RefreshRequest.md)
- [RegenerateRequest](docs/RegenerateRequest.md)
- [RelationshipStage](docs/RelationshipStage.md)
- [ReplyStrategy](docs/ReplyStrategy.md)
- [SafetyStatus](docs/SafetyStatus.md)
- [SmsChallenge](docs/SmsChallenge.md)
- [SmsChallengeResponse](docs/SmsChallengeResponse.md)
- [SmsLoginRequest](docs/SmsLoginRequest.md)
- [SmsPurpose](docs/SmsPurpose.md)
- [SmsSendRequest](docs/SmsSendRequest.md)
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
