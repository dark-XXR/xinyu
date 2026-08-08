from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


class FixtureValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FixtureValidationError(f"cannot read JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FixtureValidationError(f"expected a JSON object in {path}")
    return value


def bundle_openapi(repo: Path, source: Path, output: Path) -> dict[str, Any]:
    cli = repo / "node_modules" / "@redocly" / "cli" / "bin" / "cli.js"
    if not cli.is_file():
        raise FixtureValidationError("Redocly CLI is missing; run npm install before validation")
    command = [
        "node",
        str(cli),
        "bundle",
        str(source),
        "--dereferenced",
        "--ext",
        "json",
        "-o",
        str(output),
    ]
    completed = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        details = (completed.stdout + completed.stderr).strip()
        raise FixtureValidationError(f"OpenAPI bundling failed:\n{details}")
    return load_json(output)


def type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_format(value: str, format_name: str, path: str, errors: list[str]) -> None:
    if format_name == "date-time":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path}: expected RFC 3339 date-time")
    elif format_name == "uri":
        parsed = urlparse(value)
        if not parsed.scheme or (parsed.scheme in {"http", "https"} and not parsed.netloc):
            errors.append(f"{path}: expected an absolute URI")


def declared_properties(schema: Any) -> set[str]:
    if not isinstance(schema, dict):
        return set()
    names = set(schema.get("properties", {}))
    for member in schema.get("allOf", []):
        names.update(declared_properties(member))
    return names


def validate_value(value: Any, schema: Any, path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return
    for index, member in enumerate(schema.get("allOf", [])):
        validate_value(value, member, f"{path}.allOf[{index}]", errors)
    if "anyOf" in schema:
        alternatives: list[list[str]] = []
        for member in schema["anyOf"]:
            member_errors: list[str] = []
            validate_value(value, member, path, member_errors)
            alternatives.append(member_errors)
        if all(alternatives):
            errors.append(f"{path}: value does not match any allowed schema")
            return
    if "oneOf" in schema:
        matches = 0
        for member in schema["oneOf"]:
            member_errors = []
            validate_value(value, member, path, member_errors)
            matches += not member_errors
        if matches != 1:
            errors.append(f"{path}: expected exactly one matching schema, got {matches}")
            return

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(type_matches(value, item) for item in allowed):
            errors.append(f"{path}: expected type {allowed}, got {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum {schema['enum']!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                errors.append(f"{path}: missing required property {name!r}")
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: has fewer than {schema['minProperties']} properties")
        properties = schema.get("properties", {})
        evaluated = declared_properties(schema)
        for name, child in value.items():
            if name in properties:
                validate_value(child, properties[name], f"{path}.{name}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: additional property {name!r} is not allowed")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate_value(child, schema["additionalProperties"], f"{path}.{name}", errors)
            elif schema.get("unevaluatedProperties") is False and name not in evaluated:
                errors.append(f"{path}: unevaluated property {name!r} is not allowed")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: has fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: has more than {schema['maxItems']} items")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate_value(item, item_schema, f"{path}[{index}]", errors)
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string is longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: value does not match pattern {schema['pattern']!r}")
        if "format" in schema:
            validate_format(value, schema["format"], path, errors)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value is above maximum {schema['maximum']}")


def operation_index(openapi: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for path, path_item in openapi.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if not operation_id:
                continue
            if operation_id in indexed:
                raise FixtureValidationError(f"duplicate operationId {operation_id}")
            indexed[operation_id] = {"path": path, "method": method, "operation": operation}
    return indexed


def fixture_schema(fixture: dict[str, Any], operation: dict[str, Any]) -> Any:
    kind = fixture.get("kind")
    media_type = fixture.get("mediaType", "application/json")
    if kind == "request":
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            raise FixtureValidationError(f"operation has no request body for {fixture['id']}")
        media = request_body.get("content", {}).get(media_type)
    elif kind == "response":
        status_code = str(fixture.get("statusCode", ""))
        response = operation.get("responses", {}).get(status_code)
        if not isinstance(response, dict):
            raise FixtureValidationError(
                f"operation does not document response {status_code} for {fixture['id']}"
            )
        media = response.get("content", {}).get(media_type)
    else:
        raise FixtureValidationError(f"fixture {fixture.get('id')} has invalid kind {kind!r}")
    if not isinstance(media, dict) or "schema" not in media:
        raise FixtureValidationError(
            f"operation has no {media_type} schema for fixture {fixture['id']}"
        )
    return media["schema"]


def validate_manifest(repo: Path, manifest_path: Path, openapi: dict[str, Any]) -> int:
    manifest = load_json(manifest_path)
    indexed = operation_index(openapi)
    fixtures: list[dict[str, Any]] = []
    for relative in manifest.get("fixtureFiles", []):
        document = load_json(repo / relative)
        module_fixtures = document.get("fixtures")
        if not isinstance(module_fixtures, list):
            raise FixtureValidationError(f"fixtureFiles entry {relative} has no fixtures array")
        fixtures.extend(module_fixtures)

    fixture_ids: set[str] = set()
    errors: list[str] = []
    coverage: dict[str, dict[str, bool]] = {}
    target_tags = set(manifest.get("targetTags", []))
    for operation_id, item in indexed.items():
        if target_tags.intersection(item["operation"].get("tags", [])):
            coverage[operation_id] = {"success": False, "error": False, "request": False}

    for fixture in fixtures:
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str) or not fixture_id:
            errors.append("fixture is missing a non-empty id")
            continue
        if fixture_id in fixture_ids:
            errors.append(f"duplicate fixture id {fixture_id}")
            continue
        fixture_ids.add(fixture_id)
        operation_id = fixture.get("operationId")
        item = indexed.get(operation_id)
        if item is None:
            errors.append(f"{fixture_id}: unknown operationId {operation_id!r}")
            continue
        try:
            schema = fixture_schema(fixture, item["operation"])
        except FixtureValidationError as exc:
            errors.append(str(exc))
            continue
        validate_value(fixture.get("value"), schema, f"{fixture_id}.value", errors)
        if operation_id in coverage:
            if fixture.get("kind") == "request":
                coverage[operation_id]["request"] = True
            else:
                status = int(str(fixture["statusCode"]))
                coverage[operation_id]["success" if status < 400 else "error"] = True

    requirements = manifest.get("coverage", {})
    for operation_id, state in coverage.items():
        operation = indexed[operation_id]["operation"]
        if requirements.get("requireSuccessResponsePerOperation") and not state["success"]:
            errors.append(f"{operation_id}: missing success response fixture")
        if requirements.get("requireErrorResponsePerOperation") and not state["error"]:
            errors.append(f"{operation_id}: missing expected error response fixture")
        if (
            requirements.get("requireRequestFixtureForRequestBody")
            and "requestBody" in operation
            and not state["request"]
        ):
            errors.append(f"{operation_id}: missing request fixture")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Validated {len(fixtures)} fixtures across {len(coverage)} tagged operations "
        "with complete success/error/request coverage."
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate contract fixtures against OpenAPI")
    parser.add_argument(
        "--manifest",
        default="packages/contract-test-fixtures/identity-manifest.json",
        help="manifest path relative to the repository root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(__file__).resolve().parents[2]
    manifest_path = repo / args.manifest
    try:
        manifest = load_json(manifest_path)
        source = repo / manifest["openapi"]
        with tempfile.TemporaryDirectory(prefix="contract-fixtures-") as temp_dir:
            openapi = bundle_openapi(repo, source, Path(temp_dir) / "openapi.json")
            return validate_manifest(repo, manifest_path, openapi)
    except (FixtureValidationError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
