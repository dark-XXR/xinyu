from pathlib import Path
from typing import Any

import yaml
from love_reply_api.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def _operations(document: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (path, method, operation["operationId"])
        for path, path_item in document["paths"].items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    }


def test_fastapi_provider_operations_match_bundled_contract() -> None:
    repository_root = Path(__file__).parents[3]
    bundled_contract = repository_root / "contracts/openapi/dist/openapi.yaml"
    contract = yaml.safe_load(bundled_contract.read_text(encoding="utf-8"))

    assert _operations(app.openapi()) == _operations(contract)
