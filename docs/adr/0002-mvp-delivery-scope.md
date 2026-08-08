# ADR 0002: MVP delivery scope

- Status: Accepted
- Date: 2026-08-07
- Task: ARCH-001

## Context

The product architecture includes screenshot correction in its MVP checklist,
while the validation report recommends releasing text generation first and OCR
in the second phase. Implementing both as mandatory first-release behavior would
increase privacy, upload-security, device-compatibility, and model-quality risk.

## Decision

Define P0 as text generation, three candidates, history and feedback, account
privacy, entitlement reservation and settlement, the Android text share target,
and minimum administration. Define screenshot upload/OCR, target profiles,
payment subscriptions, and general support as P1. Preserve their documented API
space and protect incomplete client entry points with server-delivered feature
flags.

## Consequences

- P0 can be tested without pretending OCR accuracy and ROM compatibility are
  already proven.
- No documented P1 capability is removed from the final scope.
- The bootstrap contract must expose capability flags and compatibility data.

