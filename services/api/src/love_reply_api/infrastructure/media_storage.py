"""媒体文件存储适配器；当前使用本地磁盘，业务层不依赖具体存储厂商。"""

from pathlib import Path


class LocalMediaStorage:
    """以服务端生成的相对键读写文件，并阻断目录穿越。"""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def write(self, storage_key: str, content: bytes) -> Path:
        target = self._safe_path(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.tmp")
        temporary.write_bytes(content)
        temporary.replace(target)
        return target

    def resolve(self, storage_key: str) -> Path:
        target = self._safe_path(storage_key)
        if not target.is_file():
            raise FileNotFoundError(storage_key)
        return target

    def delete(self, storage_key: str) -> None:
        target = self._safe_path(storage_key)
        target.unlink(missing_ok=True)

    def _safe_path(self, storage_key: str) -> Path:
        target = (self._root / storage_key).resolve()
        try:
            target.relative_to(self._root)
        except ValueError as exc:
            raise ValueError("media storage key escapes the configured root") from exc
        return target
