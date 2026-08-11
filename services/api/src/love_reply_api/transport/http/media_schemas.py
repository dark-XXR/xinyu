"""站内媒体上传接口模型。"""

from datetime import datetime
from typing import Literal

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class MediaAssetData(ApiModel):
    asset_id: str
    purpose: Literal["USER_AVATAR", "WEBSITE_BRAND", "CONTENT_IMAGE"]
    content_type: str
    size_bytes: int
    width_pixels: int
    height_pixels: int
    public_url: str
    created_at: datetime


MediaAssetResponse = SuccessEnvelope[MediaAssetData]
