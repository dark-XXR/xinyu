# Development status

Last updated: 2026-08-09

## Current checkpoint

- Active task: `BACKEND-PROVIDER-REGISTRY-001`
- State: `ready`
- Contract version: `1.0.0`
- Current phase: encrypted provider registry and administration are implemented; real adapters and runtime routing are next

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
- The provider registry now persists validated drafts, encrypted immutable credential versions,
  redacted health checks, immutable configuration snapshots, publication pointers, gray rollout,
  atomic rollback, and audit events. Editing a published provider cannot change its online snapshot.
  Keyed credential fingerprints resist offline guessing and secrets are never returned by the API.
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

Backend verification now covers 17 PostgreSQL integration tests. The email/auth, administrator
authentication, and provider-registry migrations passed
upgrade, downgrade, and re-upgrade; Ruff, strict MyPy, TypeScript, Android unit tests, Android Lint,
and Debug APK assembly also pass.

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

1. Resolve effective published providers by kind, priority, rollout, and effective time.
2. Connect the SMTP email sender and real SMTP health check to encrypted provider credentials.
3. Change Android to email-first login and expose SMS only when the channel policy allows it.
4. Add real AI provider routing, then implement Epay and catalog persistence.
5. Build the administration console, followed by the full Antigravity Android UI redesign.
