# Development status

Last updated: 2026-08-08

## Current checkpoint

- Active task: `CONTRACT-BILLING-001`
- State: `in_progress`
- Contract version: `1.0.0`
- Current phase: runtime configuration and provider contracts complete; commerce and real adapters are next

## Completed

- P0 backend, identity, privacy, entitlement, wallet, quote, generation, candidate,
  SSE, risk appeal, generated Kotlin client, and generated TypeScript client.
- Additive email-first authentication contract with public channel policy, email OTP challenge,
  email login, stable provider-unavailable errors, and SMS compatibility.
- Published runtime configuration now owns free benefits, logical models, reply styles, feature
  switches, and quote lifetime. Android reads its style catalog from server bootstrap and
  intersects it with the authenticated entitlement.
- Unified administrator provider contract now covers AI, SMTP/API email, Aliyun/Tencent SMS,
  and EPAY-compatible payment configuration, write-only credential rotation, redacted health
  checks, bounded publication, and rollback. Twenty-two provider fixtures validate 8 operations.
- Versioned products and prices, immutable order benefit snapshots, payment attempts, active
  provider-query reconciliation, subscription cancellation, refunds, entitlement recovery, and
  signed Epay-compatible callbacks are now defined. Twenty-seven commerce fixtures validate
  11 operations; browser returns cannot grant benefits.
- Android Compose project with an app module and a read-only generated API module.
- Encrypted access/refresh token persistence, atomic refresh retry, and installation ID.
- SMS login, server-authoritative entitlement display, composer draft, relationship/goal/style
  controls, quote confirmation, create and polling flow.
- Result analysis and `SAFE`, `PUSH_PULL`, and `DIRECT` candidate cards with copy actions.
- Failed and cancelled generation states preserve the draft and request a fresh quote on retry.
- P1 OCR, profile, payment, history, and knowledge entry points remain hidden.
- Three ViewModel tests and five Android 35 Compose UI tests pass.
- Debug APK assembles successfully with compile SDK 35 and Java 17.
- Real emulator-to-local-API SMS login, entitlement, quote, generation failure, and quota release
  flow verified. The default unavailable AI provider still fails closed without fake replies.
- Antigravity loaded and displayed the final Android test changes after the desktop reconfiguration.
- Login, composer, quote, success, and failure states were exported and inspected at `1080x2400`
  and a compact `360x640dp` equivalent; no clipping, overlap, or unsafe-inset issues remain.

## Verification commands

```powershell
cd apps/android
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
.\gradlew.bat :app:connectedDebugAndroidTest
```

Last results: 3 unit tests, 5 default-size device UI tests, 5 compact-size UI tests,
Android Lint, and Debug APK assembly all passed.

Identity contract validation now covers 46 fixtures across 19 tagged operations. Generated
Kotlin and TypeScript clients both compile with the new email/channel models and operations.

## External inputs

- Real email/SMTP credentials and verified sender domain are not configured.
- Real SMS credentials and sender registration are not configured; SMS is now the fallback channel.
- Real AI provider credentials and production model mapping are not configured.
- Epay gateway URL, merchant ID/key, enabled payment types, and callback domain are not configured.

## UI acceptance

The P0 Android flow acceptance criteria are complete, but the product owner has rejected the
current visual direction as final UI. A full redesign is tracked separately after email-first
auth and bootstrap integration. Antigravity detects the workspace window, while activation and
input still report `node_repl exec context not found`; source synchronization works, but this is
not being represented as a completed interactive Antigravity design workflow.

## Accepted provider and commerce direction

- Email OTP is the primary login method; SMS remains fallback, recovery, and step-up.
- AI, email, SMS, and payment integrations use encrypted, versioned provider adapters managed
  from the administration console.
- Payment includes an `EPAY_COMPAT` adapter and never grants benefits from a browser redirect.
- Free, VIP Standard, VIP Pro, and energy-pack defaults are catalog templates, not client constants.
- The complete decision and initial prices are in
  `docs/product/provider-and-subscription-spec.md` and ADR 0003.

## Next exact actions

1. Finish ad reward and administrator finance contracts, then freeze the billing contract.
2. Implement email auth, encrypted provider registry, AI routes, Epay, and catalog versioning.
3. Build the administration console for provider, model, payment, product, and audit operations.
4. Change Android to email-first login, then perform the full Antigravity UI redesign.
