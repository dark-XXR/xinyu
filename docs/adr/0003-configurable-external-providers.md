# ADR 0003: Configurable external providers and primary email authentication

- Status: Accepted
- Date: 2026-08-08
- Task: ARCH-PROVIDERS-001

## Context

The product must connect to AI, email, SMS, and payment services without tying
domain code or client releases to one vendor. Operators need to add credentials,
test connectivity, publish configuration, and roll back from the administration
console after deployment. The first payment integration must support common
Epay-compatible gateways. Email is the primary user authentication channel and
SMS is a fallback.

## Decision

Introduce a versioned provider registry with adapters for `AI`, `EMAIL`, `SMS`,
and `PAYMENT`. Provider records contain non-secret routing and compliance
metadata; credentials are encrypted at rest, write-only through the admin API,
and never returned to clients or logs. Configuration changes follow draft,
validation, health check, publish, gray rollout, and rollback states. Every
publish, secret rotation, rollback, and emergency disable is audited. Editable
draft state and immutable online publication state are separate, so editing a
published provider does not silently replace or remove the online snapshot.

Emergency disable is an immediate runtime circuit breaker with an independent
permission and optimistic concurrency check. It sets online rollout to zero while
retaining encrypted credentials, the last published version pointer, effective
time, and immutable audit/version history. A disabled provider can return to
runtime selection only after a new successful validation and publication or an
explicit rollback to a previously published version.

Use passwordless email OTP as the default login method. Email links may be added
as a second email challenge mode. SMS remains available for account recovery,
step-up verification, and users who cannot receive email. Auth channel priority
and availability are delivered by bootstrap configuration, but clients retain a
safe email-first fallback.

Implement an `EPAY_COMPAT` payment adapter behind the unified payment gateway.
The adapter maps Epay merchant, signing, submit, query, refund, callback, and ACK
semantics into internal order events. Browser redirects never grant benefits;
only a verified server callback or verified active query can settle an order.

Products, prices, benefit grants, renewal behavior, regions, currencies, and
sales channels are versioned server data. The initial catalog is a draft template
defined in the product specification and can be changed before publication.

## Consequences

- A new vendor normally requires an adapter and admin schema preset, not domain
  or Android changes.
- The first administrator still needs a deployment-time bootstrap credential and
  encryption master key; provider secrets then move to managed encrypted records.
- Production enablement requires provider terms, callback reachability, sandbox
  verification, and legal review even when the software integration is complete.
- Existing SMS P0 operations remain compatible while email operations are added.
- Operators can distinguish editable configuration state from real online traffic
  through the published version, rollout percentage, and effective-time fields.
- A mistaken disable does not destroy recovery material, but restoration remains
  explicit, permission-scoped, and audited.
