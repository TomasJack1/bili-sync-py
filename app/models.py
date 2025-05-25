from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlmodel import Field, SQLModel


class VideoStatus(str, Enum):
    VIDEO_DOWNLOAD_SUCCESS = "success"
    VIDEO_DOWNLOAD_PROCESSING = "processing"
    VIDEO_DOWNLOAD_ERROR = "error"


class Video(SQLModel, table=True):
    bvid: str = Field(primary_key=True)
    aid: int = 0
    title: str = "未指定名称"
    pic: str = "https://m.media-amazon.com/images/I/51i0m01RSxL.png"
    belong: str = ""
    created_at: str = datetime.now(tz=timezone(timedelta(hours=8))).strftime(
        "%Y年%m月%d日 %H:%M:%S",
    )
    finished_at: str = ""
    status: VideoStatus = Field(default=VideoStatus.VIDEO_DOWNLOAD_PROCESSING)
