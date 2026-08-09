# Development status

Last updated: 2026-08-09

## Current checkpoint

- Active task: `FRONTEND-ADMIN-CONSOLE-001`
- State: `in_progress`
- Contract version: `1.0.0`
- Current phase: administration console milestone 1 is accepted; AI and audit administration are next

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
- Published email providers now support authenticated SMTP, Amazon SES v2 with AWS Signature V4,
  SendGrid, Resend, and Mailgun. Published SMS providers support Aliyun RPC HMAC-SHA1 and Tencent
  Cloud TC3-HMAC-SHA256. Login-channel availability is derived from effective publications, health
  checks perform explicit administrator-addressed synthetic delivery, and transport failures never
  return provider bodies, credentials, or verification codes.
- EPAY-compatible providers now support administrator-configurable notification and browser-return
  URLs, callback freshness windows, canonical MD5 checkout signing, active payment query, refund,
  constant-time callback verification, and synthetic query health checks. CNY amounts are converted
  from integer minor units, unsupported currencies fail closed, and browser return values never
  represent settlement proof.
- Commerce persistence now covers product versions, immutable order facts, payment attempts, unique
  provider events, subscriptions, and refund requests. All contracted public commerce routes and the
  Epay webhook are registered. Callback/query settlement locks the order and entitlement accounts in
  one transaction; identical callbacks ACK without duplicate grants while conflicting callbacks fail.
- Administrator commerce now exposes 14 MFA permission-scoped operations for product drafts,
  maker-checker publication, published-only rollback, order/payment readback, refund review and
  execution, bounded reconciliation, and idempotent manual entitlement adjustment. Prices, quotas,
  benefits, effective windows and batch limits are administrator inputs rather than client constants.
- Successful refunds use the payment attempt's immutable provider facts. Full energy-pack refunds
  recover only available balance; plan benefits are restored only when the complete current
  entitlement still equals the recorded post-grant snapshot. Consumed or changed benefits enter
  explicit manual review instead of being guessed or forced negative.
- A Chinese file/page catalog and code-comment guide now map Android screens, UI parameters,
  backend routes, business services, data tables, contracts, and planned administration pages for
  non-developer maintenance.
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
- Referral runtime now resolves stable campaign rollout, creates opaque personal HTTPS codes,
  transaction-locks one permanent invitee binding, stores the bound campaign snapshot, and enforces
  self, same-device, verified-channel, shared-payment-identity and per-inviter-limit rules.
- Account verification, first successful generation and first verified purchase drive configured
  milestones from real backend transactions. Cooling-off rewards grant through wallet or entitlement
  ledgers exactly once; eligible reversals and failed reversal reviews both leave immutable audits.
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
- The administration console now runs as a React, TypeScript, Vite, React Router, and TanStack Query
  application created and edited through headless Antigravity CLI. Its repository layer switches
  between typed mock data and the generated administrator HTTP client without placing prices,
  quotas, benefit amounts, provider credentials, or resource versions in page components.
- Administration routes `/`, `/providers`, `/commerce/products`, and `/commerce/orders` now cover
  operational metrics, provider drafts and filters, write-only credential rotation, provider health
  checks, provider publication/rollback, versioned products and benefits, immutable order readback,
  refund review, and refund execution. Destructive and publication actions require confirmation.
- The first administration UI milestone passed strict TypeScript, oxlint, production build, and real
  browser acceptance at `1440x900` and `390x844`. Mobile data tables become labeled card rows,
  all checked pages have zero horizontal overflow, menus and dialogs close with Escape, and the
  checked browser console has zero warnings or errors.

## Verification commands

```powershell
cd apps/android
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
.\gradlew.bat :app:connectedDebugAndroidTest
```

Last results: 5 unit tests, 6 default-size device UI tests, 6 compact-size UI tests,
Android Lint, and Debug APK assembly all passed.

Administration web results: TypeScript project references, oxlint (0 warnings/errors), and Vite
production build pass. The production bundle is 270.21 kB JavaScript (80.59 kB gzip) and 6.63 kB
CSS (1.88 kB gzip). Playwright accepted all four routes at desktop size and the three tabular routes
at 390px with `scrollWidth === innerWidth`.

Identity contract validation now covers 46 fixtures across 19 tagged operations. Generated
Kotlin and TypeScript clients both compile with the new email/channel models and operations.

Backend verification now covers 59 PostgreSQL integration and transport tests. The email/auth,
administrator authentication, provider-registry, and AI-gateway migrations passed
upgrade, downgrade, and re-upgrade. The commerce administration migration also passed its own
downgrade/upgrade loop. Referral tables also passed downgrade/upgrade. Ruff, strict MyPy across
62 source files, OpenAPI lint/bundle, referral fixture validation, generated
TypeScript build, generated Kotlin build, Android unit tests, Android Lint, and Debug APK assembly pass.

## External inputs

- Real email/SMTP/API credentials and verified sender domain are not configured.
- Real Aliyun/Tencent SMS credentials, signatures, templates, and sender registration are not configured;
  SMS remains the fallback channel.
- Real AI provider credentials and production model mapping are not configured.
- Epay gateway URL, merchant ID/key, enabled payment types, and callback domain are not configured.

## UI acceptance

The P0 Android flow acceptance criteria are complete, but the product owner has rejected the
current visual direction as final UI. A full redesign remains tracked after the administration
console. The administration UI milestone uses a restrained neutral/coral operational design and
has been accepted from actual browser output. All frontend implementation continues through
Antigravity CLI only; the IDE is not launched or controlled.

## Accepted provider and commerce direction

- Email OTP is the primary login method; SMS remains fallback, recovery, and step-up.
- AI, email, SMS, and payment integrations use encrypted, versioned provider adapters managed
  from the administration console.
- Payment includes an `EPAY_COMPAT` adapter and never grants benefits from a browser redirect.
- Free, VIP Standard, VIP Pro, and energy-pack defaults are catalog templates, not client constants.
- The complete decision and initial prices are in
  `docs/product/provider-and-subscription-spec.md` and ADR 0003.

## Next exact actions

1. Continue the administration console through Antigravity CLI with AI model mappings, routes,
   prompts, evaluations, risk policies, publication, and rollback.
2. Add provider disable and dedicated provider/payment audit readback to finish the administration
   console acceptance criteria.
3. Redesign the Android UI through Antigravity CLI and verify it on emulator viewports.
4. Add invite sharing, progress and reward history to the redesigned Android experience.
