"""站内图片签名识别与本地存储边界测试。"""

from pathlib import Path

import pytest
from love_reply_api.application.media import asset_id_from_path, sniff_image_content_type
from love_reply_api.infrastructure.media_storage import LocalMediaStorage


def test_image_signature_detection_rejects_svg_and_disguised_content() -> None:
    assert sniff_image_content_type(b"\x89PNG\r\n\x1a\ncontent") == "image/png"
    assert sniff_image_content_type(b"\xff\xd8\xffcontent") == "image/jpeg"
    assert sniff_image_content_type(b"RIFF\x08\x00\x00\x00WEBPcontent") == "image/webp"
    assert sniff_image_content_type(b"<svg><script>alert(1)</script></svg>") is None
    assert sniff_image_content_type(b"not-an-image.png") is None


def test_local_storage_generates_files_only_below_configured_root(tmp_path: Path) -> None:
    storage = LocalMediaStorage(tmp_path)
    written = storage.write("user_avatar/2026/08/image.png", b"image")
    assert written.read_bytes() == b"image"
    assert storage.resolve("user_avatar/2026/08/image.png") == written

    with pytest.raises(ValueError, match="escapes"):
        storage.write("../outside.png", b"bad")


def test_media_public_path_parser_only_accepts_generated_asset_ids() -> None:
    asset_id = "mda_" + "a" * 32
    assert asset_id_from_path(f"/media/{asset_id}") == asset_id
    assert asset_id_from_path("https://cdn.example.com/avatar.png") is None
    assert asset_id_from_path("/media/../../secret") is None
