# ADR 0001: Repository and backend architecture

- Status: Accepted
- Date: 2026-08-07
- Task: ARCH-001

## Context

The product requires Android and admin clients, 198 documented HTTP operations,
streaming generation, transactional billing, asynchronous jobs, and multiple
external providers. The contract must remain the single cross-language source of
truth while development is distributed across independent work items.

## Decision

Use the documented monorepo layout and a contract-first workflow. Implement the
initial backend as a modular FastAPI monolith with explicit application, domain,
infrastructure, and transport boundaries. Use PostgreSQL as the source of truth,
Redis for bounded ephemeral state, and S3-compatible object storage for uploads
and generated artifacts. Run AI and long-running jobs in separate worker
processes while reusing domain contracts.

Generate Android, TypeScript, and backend transport types from OpenAPI 3.1.
Public JSON fields use lowerCamelCase; Python internals use snake_case. Database
migrations are append-only. Cross-boundary side effects use a transactional
outbox, and financial ledgers and audit records are immutable.

## Consequences

- Deployment starts simple without merging domain ownership boundaries.
- A later service split can follow the module registry without changing public
  API contracts.
- Contract linting and generated-code drift checks are release gates.
- Provider SDKs remain behind adapters and cannot enter the domain layer.

