# Contract test fixtures

`identity-manifest.json` indexes the synthetic AUTH, USER, CONSENT, and
DATA_GOVERNANCE fixtures. Each fixture is tied to an OpenAPI `operationId` and
either a request body or a documented response status.

Run validation from the repository root:

```text
python tools/contract-ci/validate_fixtures.py
python tools/contract-ci/validate_fixtures.py --manifest packages/contract-test-fixtures/admin-providers-manifest.json
python tools/contract-ci/validate_fixtures.py --manifest packages/contract-test-fixtures/commerce-manifest.json
```

The validator bundles and dereferences the OpenAPI document with the locally
installed Redocly CLI, validates every fixture value against its operation
schema, and enforces success, expected-error, and request-body coverage. Test
values use reserved domains, opaque fixture IDs, and non-credential tokens.
