# Provider configuration and subscription catalog specification

Status: Initial implementation specification
Version: 1.0
Date: 2026-08-08

This document defines implementation defaults. Prices and benefits are draft
catalog data, not hardcoded client behavior or a final commercial commitment.
Administrators may edit drafts and publish versioned replacements.

## 1. Administration principles

Every external provider uses a common lifecycle:

`DRAFT -> VALIDATING -> READY -> ACTIVE -> DISABLED`

An active version can be superseded or rolled back to a known version. The admin
console must support:

- provider name, adapter type, base URL, region, data retention statement, and
  enabled environments;
- write-only credential create and rotation, with only fingerprint and last
  rotation time readable;
- connection health check with redacted request and response summaries;
- timeouts, retry limits, circuit breaking, rate limits, and fallback priority;
- tenant/environment scope, gray percentage, effective time, and rollback;
- audit reason, operator identity, approval state, and immutable audit events.

Secrets must be envelope-encrypted with a deployment master key or KMS. They are
never included in list/detail responses, analytics, exception messages, or
provider health logs.

## 2. Authentication providers

### 2.1 User flow

Email OTP is the default login and registration method:

1. User enters an email address.
2. Server normalizes it, applies rate and risk checks, then creates a short-lived
   challenge without revealing whether the account already exists.
3. The selected email provider sends a six-digit OTP. The raw OTP is never stored.
4. A valid challenge creates or authenticates the account and issues rotating
   access and refresh tokens.
5. SMS can be selected as fallback, account recovery, or risk step-up.

Default policy values, all admin-configurable within server safety bounds:

| Setting | Default |
|---|---:|
| Email OTP lifetime | 10 minutes |
| SMS OTP lifetime | 5 minutes |
| Maximum verification attempts | 5 |
| Email resend delay | 60 seconds |
| SMS resend delay | 60 seconds |
| Per-address send limit | 5 per hour |
| Per-device send limit | 10 per hour |
| Primary channel | Email |
| Fallback channel | SMS |

Changing an email address or phone number requires verification of the new
channel and step-up verification on an existing trusted channel or device.

### 2.2 Email adapters

The first adapter is standards-based SMTP with TLS. Provider presets may add API
adapters for Amazon SES, SendGrid, Resend, Mailgun, or another service without
changing auth domain logic.

Required SMTP fields: host, port, TLS mode, username, write-only password, sender
address, sender name, reply-to address, template locale, and timeout. A health
check sends only to a configured administrator test address.

### 2.3 SMS adapters

SMS is optional and fail-closed when unconfigured. Presets should cover Alibaba
Cloud SMS and Tencent Cloud SMS first, while the adapter contract remains vendor
neutral. Required configuration includes region, application/signature ID,
template ID, write-only credentials, sender identity, and delivery callback.

## 3. AI model gateway

The initial adapter set is:

| Adapter | Purpose |
|---|---|
| `OPENAI_COMPAT` | Configurable base URL and OpenAI-compatible chat/responses APIs |
| `OPENAI` | Official OpenAI behavior and model metadata |
| `ANTHROPIC` | Claude message API mapping |
| `GEMINI` | Google Gemini content API mapping |

An administrator can add providers, models, and routes. Model records define a
logical model ID, provider model name, input/output modalities, context limit,
cost units, quality tier, data region, retention policy, and enabled state.
Routes define scenario, priority, timeout, retry, fallback chain, budget ceiling,
minimum safety policy, gray percentage, and effective version.

Provider credentials and raw provider model names are never returned to Android.
The app receives logical model IDs and server-calculated quotes only. No route may
be published until health, schema, safety, and bounded-cost checks pass.

## 4. Payment gateway and Epay compatibility

### 4.1 Unified payment behavior

Orders, payment attempts, provider events, refunds, subscriptions, entitlements,
and wallet ledger entries are separate records. All creation and callback writes
are idempotent. Amounts use integer minor units and an explicit ISO currency.

The client can open provider payment parameters, but only the backend can move an
order to `PAID` and grant benefits. It does so after a verified callback or a
verified provider query with matching merchant, order, amount, currency, and
terminal status.

### 4.2 `EPAY_COMPAT` adapter

Admin-configurable fields:

- gateway base URL and submit/query/refund paths;
- merchant/PID, write-only merchant key, and optional application ID;
- enabled payment types such as Alipay or WeChat Pay;
- signing preset, defaulting to canonical Epay MD5 for compatible gateways;
- notify URL, return URL, query timeout, callback time window, and ACK text;
- sandbox/production mode, IP allowlist option, and TLS certificate policy.

The canonical Epay signing preset sorts non-empty parameters by ASCII key,
excludes `sign` and `sign_type`, appends the merchant key according to the
selected preset, and verifies the returned signature using constant-time
comparison. Because Epay deployments vary, field aliases and signing behavior
are selected from reviewed adapter presets rather than arbitrary executable
scripts.

Callbacks must reject unknown merchants, stale timestamps when provided,
duplicate event conflicts, amount mismatches, order mismatches, and invalid
terminal states. Raw callbacks are encrypted for bounded audit retention.

## 5. Initial subscription catalog

All prices below are draft defaults for mainland China in CNY, tax-inclusive
where legally applicable. The database stores them in fen. A product version
specifies sales channel, region, currency, effective time, benefit policy, and
renewal type.

### 5.1 Membership plans

| Plan | Price | Benefit window | Text replies | Screenshot/OCR | Models and styles |
|---|---:|---:|---:|---:|---|
| Free | CNY 0 | Daily | 5/day | 0 | Basic model, one basic style |
| VIP Standard monthly | CNY 19.90 | 30 days | 300 | 30 | Quality model, all standard styles |
| VIP Standard quarterly | CNY 49.90 | 3 x 30 days | 300/window | 30/window | Same as Standard monthly |
| VIP Standard annual | CNY 159.00 | 12 x 30 days | 300/window | 30/window | Same as Standard monthly |
| VIP Pro monthly | CNY 39.90 | 30 days | 1,000 | 120 | Priority models, all styles, deep analysis |
| VIP Pro quarterly | CNY 99.00 | 3 x 30 days | 1,000/window | 120/window | Same as Pro monthly |
| VIP Pro annual | CNY 299.00 | 12 x 30 days | 1,000/window | 120/window | Same as Pro monthly |

Benefits reset at each 30-day window boundary and do not roll over. A plan may
grant additional logical model/style IDs, but the client never infers benefits
from a plan name. The server-returned entitlement is authoritative.

Epay products default to prepaid non-renewing terms because generic Epay gateways
do not provide a uniform recurring debit contract. An adapter may expose
auto-renew only when the provider supports explicit mandates, cancellation, and
signed renewal events. Auto-renew is never silently enabled.

### 5.2 Energy add-ons

| Product | Price | Energy | Default validity |
|---|---:|---:|---:|
| Small energy pack | CNY 6.90 | 10,000 | 365 days |
| Medium energy pack | CNY 19.90 | 40,000 | 365 days |
| Large energy pack | CNY 49.90 | 120,000 | 365 days |

Generation quotes show whether the charge comes from plan quota, wallet energy,
or both. Failed or cancelled generations release every unsettled reservation.

### 5.3 Product and refund rules

- Catalog changes create a new version and never mutate completed order facts.
- Existing prepaid terms retain their purchased benefits until expiration.
- Price, currency, amount, product version, and benefit grant are bound into the
  order before redirecting to a gateway.
- A refund request does not imply approval. Provider refund completion and
  entitlement recovery are tracked independently and reconciled.
- The initial operational policy permits automated full refund only when the
  product is eligible, no paid benefit has been consumed, and channel/legal rules
  allow it; every other request enters manual review.
- Final price, tax, renewal, refund, and consumer notice text require legal and
  payment-channel review before production publication.

## 6. Administration pages

The minimum configuration console includes:

1. Provider registry for AI, email, SMS, and payment.
2. Credential rotation and health checks.
3. AI model catalog, routes, fallback chains, and cost limits.
4. Email/SMS templates, channel priority, and rate policies.
5. Payment gateway configuration, callback diagnostics, and reconciliation.
6. Product catalog, price versions, benefit grants, regions, and publication.
7. Subscription, order, refund, entitlement, and wallet audit views.
8. Configuration versions, approvals, gray rollout, rollback, and audit log.

High-risk changes require an audit reason and a second confirmation. Production
secret rotation, payment activation, and product publication require a distinct
approval permission from ordinary editing.
