# Development status

Last updated: 2026-08-09

## Current checkpoint

- Active task: `BACKEND-PROVIDER-REGISTRY-001`
- State: `in_progress`
- Contract version: `1.0.0`
- Current phase: AI runtime and administrator publication APIs are complete; provider adapters are next

## Completed

- P0 backend, identity, privacy, entitlement, wallet, quote, generation, candidate,
  SSE, risk appeal, generated Kotlin client, and generated TypeScript client.
- Additive email-first authentication contract with public channel policy, email OTP challenge,
  email login, stable provider-unavailable errors, and SMS compatibility.
- Email OTP is now implemented end to end through an injected delivery adapter. The database stores
  only HMAC challenge digests, supports email-only users, enforces published TTL, resend, attempt,
  enable/disable policies, and reuses SMS token rotation, device, wallet, and entitlement behavior.
- Administrator authentication is now isolated from ordinary user authentication. Deployment-time
  bootstrap values create the first owner; passwords use Argon2id, TOTP seeds are encrypted, MFA
  counters reject replay, admin JWT signing is distinct, and reused refresh tokens revoke the whole
  administrator token family. Active MFA-backed sessions expose permission context for provider APIs.
- Published runtime configuration now owns free benefits, logical models, reply styles, feature
  switches, and quote lifetime. Android reads its style catalog from server bootstrap and
  intersects it with the authenticated entitlement.
- Unified administrator provider contract now covers AI, SMTP/API email, Aliyun/Tencent SMS,
  and EPAY-compatible payment configuration, write-only credential rotation, redacted health
  checks, bounded publication, and rollback. Twenty-two provider fixtures validate 8 operations.
- AI administration contracts now define administrator-only upstream model mappings, bounded
  scenario routes, prompt versions, evaluation gates, risk policies, gray rollout, and rollback.
  Timeouts, retries, token limits, costs, budgets, and fallback order are published data rather
  than application constants. Generated Kotlin and TypeScript models compile successfully.
- The provider registry now persists validated drafts, encrypted immutable credential versions,
  redacted health checks, immutable configuration snapshots, publication pointers, gray rollout,
  atomic rollback, and audit events. Editing a published provider cannot change its online snapshot.
  Keyed credential fingerprints resist offline guessing and secrets are never returned by the API.
- Published providers are now resolved from immutable snapshots by effective time, priority, adapter,
  and a server-keyed stable rollout bucket. SMTP uses authenticated TLS, database-published localized
  templates, encrypted credentials, and a real synthetic-delivery health check. The auth channel
  endpoint automatically reflects whether an effective SMTP publication exists.
- The AI runtime now maps logical models to encrypted published OpenAI-compatible, OpenAI,
  Anthropic, and Gemini providers. Database routes enforce deterministic rollout, prompt versions,
  per-target timeouts and retries, total attempts, input/output token limits, and request cost
  ceilings before cross-provider failover. Strict structured output validation and redacted attempt
  records prevent provider payloads or credentials from leaking into client errors.
- All 22 administrator AI operations are implemented behind dedicated MFA-backed permissions.
  Model mappings, routes, prompts, evaluation runs, and risk policies support optimistic
  concurrency. Publication requires an exact successful evaluation version, validates published
  providers and logical-model references, proves the worst-case retry cost fits the configured
  budget, and freezes mappings, upstream model names, costs, prompts, and safety policies in an
  immutable runtime snapshot. Draft edits cannot change the online version, and rollback accepts
  only a previously published immutable version.
- Versioned products and prices, immutable order benefit snapshots, payment attempts, active
  provider-query reconciliation, subscription cancellation, refunds, entitlement recovery, and
  signed Epay-compatible callbacks are now defined. Twenty-seven commerce fixtures validate
  11 operations; browser returns cannot grant benefits.
- Advertising reward sessions and signed server callbacks complete the billing contract. The
  client cannot claim completion, and identical callback replays cannot grant twice.
- Single-level referral campaigns now cover personal codes and links, authenticated immutable
  binding, masked invite progress, milestone and risk qualification, cooling-off, reward and
  reversal ledgers, plus administrator publication and rollback. Twenty-five fixtures validate
  10 operations; reward amounts and limits are not client constants.
- Android Compose project with an app module and a read-only generated API module.
- Encrypted access/refresh token persistence, atomic refresh retry, and installation ID.
- Email-first login with server-policy-controlled SMS fallback, shared encrypted sessions and refresh,
  server-authoritative entitlement display, composer draft, relationship/goal/style controls, quote
  confirmation, create, and polling flow.
- Result analysis and `SAFE`, `PUSH_PULL`, and `DIRECT` candidate cards with copy actions.
- Failed and cancelled generation states preserve the draft and request a fresh quote on retry.
- P1 OCR, profile, payment, history, and knowledge entry points remain hidden.
- Five ViewModel tests and six Android 35 Compose UI tests pass.
- Debug APK assembles successfully with compile SDK 35 and Java 17.
- Real emulator-to-local-API SMS login, entitlement, quote, generation failure, and quota release
  flow verified. The default unavailable AI provider still fails closed without fake replies.
- Antigravity CLI `1.107.0` is installed. All future frontend implementation will use its CLI
  agent/edit modes only; the IDE will not be launched or controlled. Browser and emulator
  screenshots plus automated viewport tests remain the visual acceptance path.
- Login, composer, quote, success, and failure states were exported and inspected at `1080x2400`
  and a compact `360x640dp` equivalent; no clipping, overlap, or unsafe-inset issues remain.

## Verification commands

```powershell
cd apps/android
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
.\gradlew.bat :app:connectedDebugAndroidTest
```

Last results: 5 unit tests, 6 default-size device UI tests, 6 compact-size UI tests,
Android Lint, and Debug APK assembly all passed.

Identity contract validation now covers 46 fixtures across 19 tagged operations. Generated
Kotlin and TypeScript clients both compile with the new email/channel models and operations.

Backend verification now covers 34 PostgreSQL integration and transport tests. The email/auth,
administrator authentication, provider-registry, and AI-gateway migrations passed
upgrade, downgrade, and re-upgrade; Ruff, strict MyPy, TypeScript, Android unit tests, Android Lint,
and Debug APK assembly also pass.

## External inputs

- Real email/SMTP credentials and verified sender domain are not configured.
- Real SMS credentials and sender registration are not configured; SMS is now the fallback channel.
- Real AI provider credentials and production model mapping are not configured.
- Epay gateway URL, merchant ID/key, enabled payment types, and callback domain are not configured.

## UI acceptance

The P0 Android flow acceptance criteria are complete, but the product owner has rejected the
current visual direction as final UI. A full redesign remains tracked after backend provider and
commerce work. It will be implemented through Antigravity CLI only and verified from actual
browser/emulator output rather than IDE automation.

## Accepted provider and commerce direction

- Email OTP is the primary login method; SMS remains fallback, recovery, and step-up.
- AI, email, SMS, and payment integrations use encrypted, versioned provider adapters managed
  from the administration console.
- Payment includes an `EPAY_COMPAT` adapter and never grants benefits from a browser redirect.
- Free, VIP Standard, VIP Pro, and energy-pack defaults are catalog templates, not client constants.
- The complete decision and initial prices are in
  `docs/product/provider-and-subscription-spec.md` and ADR 0003.

## Next exact actions

1. Implement configurable email API and Aliyun/Tencent SMS runtime adapters.
2. Implement Epay runtime integration and catalog persistence, then referral rewards.
3. Build the administration console through Antigravity CLI only.
4. Redesign the Android UI through Antigravity CLI and verify it on emulator viewports.
