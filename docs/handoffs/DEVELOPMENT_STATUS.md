# Development status

Last updated: 2026-08-08

## Current checkpoint

- Active task: `CONTRACT-ADMIN-PROVIDERS-001`
- State: `in_progress`
- Contract version: `1.0.0`
- Current phase: Android P0 accepted; configurable provider, email auth, Epay, and commerce contracts are next

## Completed

- P0 backend, identity, privacy, entitlement, wallet, quote, generation, candidate,
  SSE, risk appeal, generated Kotlin client, and generated TypeScript client.
- Additive email-first authentication contract with public channel policy, email OTP challenge,
  email login, stable provider-unavailable errors, and SMS compatibility.
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

## Final acceptance

The P0 Android acceptance criteria are complete. OS-level capture confirms Antigravity has the
workspace and final source changes loaded. The `sky` activation/input methods still report
`node_repl exec context not found`, but this no longer blocks IDE source synchronization,
emulator verification, or screenshot review.

## Accepted provider and commerce direction

- Email OTP is the primary login method; SMS remains fallback, recovery, and step-up.
- AI, email, SMS, and payment integrations use encrypted, versioned provider adapters managed
  from the administration console.
- Payment includes an `EPAY_COMPAT` adapter and never grants benefits from a browser redirect.
- Free, VIP Standard, VIP Pro, and energy-pack defaults are catalog templates, not client constants.
- The complete decision and initial prices are in
  `docs/product/provider-and-subscription-spec.md` and ADR 0003.

## Next exact actions

1. Define unified admin provider contracts and finish product/order/subscription/refund contracts.
2. Implement email auth, encrypted provider registry, AI routes, Epay, and catalog versioning.
3. Build the administration console for provider, model, payment, product, and audit operations.
4. Change Android to email-first login only after generated contracts and backend tests pass.
