import asyncio
import re
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.dialects.sqlite import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app import bilibili
from app.dependencies import AsyncQueueManager, PageDepends, get_db
from app.logger import logger
from app.models import Video
from app.pagination import _Page, paging_data
from app.schemas import GetVideoInfoSchema

router = APIRouter(prefix="/api")


@router.get("/video", dependencies=[PageDepends])
async def get_video_list(
    session: AsyncSession = Depends(get_db),
) -> _Page[GetVideoInfoSchema]:
    statement = select(Video)

    result = await paging_data(session, statement, GetVideoInfoSchema)

    return result


@router.post("/video")
async def add_video(
    video_id_or_url: str = Body(embed=True),
    session: AsyncSession = Depends(get_db),
    download_queue: asyncio.Queue = Depends(AsyncQueueManager),
) -> Video:
    # video_id_or_url为BV111111或https://www.bilibili.com/video/BV11a411h7pL/或者非法
    search_result = re.search(r"BV[\dA-Za-z]{10}", video_id_or_url)

    # 没有搜索到BV号
    if search_result is None:
        logger.error(f"{video_id_or_url}不是一个有效的编号或URL")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="传入的视频编号或URL无效",
        )

    video_id = search_result.group(0)

    # 获取视频详细信息（封面等）同时验证BV号是否有效
    video_info = await bilibili.get_video_info(video_id)

    if video_info is None:
        logger.error(f"{video_id}不是一个有效的BV号")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="传入的视频编号或URL无效",
        )

    video = Video(
        bvid=video_info.get("bvid"),
        pic=video_info.get("pic"),
        title=video_info.get("title"),
        aid=video_info.get("aid"),
    )

    # 添加video
    try:
        session.add(video)
        await session.commit()
    except Exception:
        logger.error(f"{video.bvid}添加失败")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"{video.bvid}添加失败",
        )
    else:
        await download_queue.put(video)
        logger.warning(f"{video.bvid}成功添加到下载队列")

    return video


@router.post("/season", response_model=List[Video])
async def add_season(
    season_url: str = Body(embed=True),
    session: AsyncSession = Depends(get_db),
    download_queue: asyncio.Queue = Depends(AsyncQueueManager),
) -> List[Video]:
    search_result = re.findall(r"[0-9]+", season_url)

    if len(search_result) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="传入的season链接无效")

    mid = search_result[0]
    season_id = search_result[1]

    season_info = await bilibili.get_season_info(mid, season_id)
    video_list_info = season_info["archives"]
    season_name = season_info["meta"]["name"]

    if video_list_info is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="传入的season链接无效")

    video_list = [
        Video(
            bvid=video.get("bvid"),
            pic=video.get("pic"),
            title=video.get("title"),
            aid=video.get("aid"),
            belong=season_name,
        )
        for video in video_list_info
    ]

    stmt = insert(Video).values([video.model_dump() for video in video_list]).on_conflict_do_nothing(index_elements=["bvid"])

    await session.exec(stmt)
    await session.commit()

    for video in video_list:
        await download_queue.put(video)

    return video_list


@router.post("/series")
async def add_series(
    series_url: str = Body(embed=True),
    session: AsyncSession = Depends(get_db),
    download_queue: asyncio.Queue = Depends(AsyncQueueManager),
) -> List[Video]:
    search_result = re.findall(r"[0-9]+", series_url)

    if len(search_result) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="series")

    mid = search_result[0]
    series_id = search_result[1]

    series_info = await bilibili.get_series_info(mid, series_id)
    video_list_info = series_info["archives"]
    series_name = series_info["name"]

    if video_list_info is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="传入的season链接无效")

    video_list = [
        Video(
            bvid=video.get("bvid"),
            pic=video.get("pic"),
            title=video.get("title"),
            aid=video.get("aid"),
            belong=series_name,
        )
        for video in video_list_info
    ]

    stmt = insert(Video).values([video.model_dump() for video in video_list]).on_conflict_do_nothing(index_elements=["bvid"])

    await session.exec(stmt)
    await session.commit()

    for video in video_list:
        await download_queue.put(video)

    return video_list


@router.post("/fav")
async def add_fav(
    fav_url: str = Body(embed=True),
    session: AsyncSession = Depends(get_db),
    download_queue: asyncio.Queue = Depends(AsyncQueueManager),
):
    search_result = re.findall(r"fid=([0-9]+)", fav_url)

    if len(search_result) < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="series")

    media_id = search_result[0]

    fav_info = await bilibili.get_fav_info(media_id=media_id)
    video_list_info = fav_info["medias"]
    fav_name = fav_info["info"]["title"]

    video_list = [
        Video(
            bvid=video.get("bvid"),
            pic=video.get("cover"),
            title=video.get("title"),
            aid=video.get("id"),
            belong=fav_name,
        )
        for video in video_list_info
    ]

    stmt = insert(Video).values([video.model_dump() for video in video_list]).on_conflict_do_nothing(index_elements=["bvid"])

    await session.exec(stmt)
    await session.commit()

    for video in video_list:
        await download_queue.put(video)

    return video_list
