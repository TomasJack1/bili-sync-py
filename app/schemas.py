from pydantic import BaseModel, ConfigDict

from app.models import VideoStatus


class GetVideoInfoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bvid: str
    title: str
    pic: str
    status: VideoStatus
