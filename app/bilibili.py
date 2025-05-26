import asyncio
import math
import os
from typing import AsyncGenerator, List, Optional

import httpx
from dm_pb2 import DmSegMobileReply

from app.wrappers import rate_limit


@rate_limit()
async def get_video_info(video_id: str) -> Optional[dict]:
    """获取视频基本信息

    Args:
        video_id (str): 视频bvid

    Returns:
        Optional[dict]: 视频基本信息
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.bilibili.com/x/web-interface/wbi/view",
            params={"bvid": video_id},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            },
        )

        if response.status_code != httpx.codes.OK:
            return None

        response = response.json()

        if response.get("code") != 0:
            return None

        return response.get("data")


@rate_limit()
async def get_video_page_info(video_id: str) -> Optional[dict]:
    """获取视频分P信息

    Args:
        video_id (str): 视频bvid

    Returns:
        dict: 视频分P信息
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.bilibili.com/x/player/pagelist",
            params={"bvid": video_id},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            },
        )

        if response.status_code != httpx.codes.OK:
            return None

        response = response.json()

        if response.get("code") != 0:
            return None

        return response.get("data")


@rate_limit()
async def get_season_info(mid: str, season_id: str) -> Optional[List[dict]]:
    """获取视频合集信息

    Args:
        mid (str): 合集mid
        season_id (str): 合集seasion_id

    Returns:
        Optional[List[dict]]: 合集基本信息
    """
    total_pages = 1
    page_num = 1
    page_size = 30
    result = None
    async with httpx.AsyncClient() as client:
        while page_num <= total_pages:
            response = await client.get(
                "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list",
                params={
                    "mid": mid,
                    "season_id": season_id,
                    "page_size": page_size,
                    "page_num": page_num,
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                },
            )

            if response.status_code != httpx.codes.OK:
                return None

            response = response.json()

            if response.get("code") != 0:
                return None

            if page_num == 1:
                total_pages = math.ceil(response["data"]["meta"]["total"] / page_size)

            if result is None:
                result = response["data"]
            else:
                result["archives"] += response["data"]["archives"]

            page_num += 1

    return result


@rate_limit()
async def get_series_info(mid: str, series_id: str) -> Optional[List[dict]]:
    """获取系列视频

    Args:
        mid (str): mid
        series_id (str): 系列id

    Returns:
        Optional[List[dict]]: 系列信息
    """
    total_pages = 1
    page_num = 1
    page_size = 30
    result = None
    async with httpx.AsyncClient() as client:
        while page_num <= total_pages:
            response = await client.get(
                "https://api.bilibili.com/x/series/archives",
                params={
                    "mid": mid,
                    "series_id": series_id,
                    "ps": page_size,
                    "pn": page_num,
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                },
            )

            if response.status_code != httpx.codes.OK:
                return None

            response = response.json()

            if response.get("code") != 0:
                return None

            if page_num == 1:
                total_pages = math.ceil(response["data"]["page"]["total"] / page_size)

            if result is None:
                result = response["data"]
            else:
                result["archives"] += response["data"]["archives"]

            page_num += 1

        response = await client.get(
            "https://api.bilibili.com/x/series/series",
            params={
                "series_id": series_id,
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            },
        )

        if response.status_code != httpx.codes.OK:
            return None

        response = response.json()

        if response.get("code") != 0:
            return None

        result["name"] = response["data"]["meta"]["name"]

    return result


@rate_limit()
async def get_video_playurl_info(video_id: str, video_cid: str) -> Optional[dict]:
    """获取视频流地址

    Args:
        video_id (str): 视频bvid
        video_cid (str): 视频cid
    Returns:
        Optional[dict]: 视频基本信息
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.bilibili.com/x/player/wbi/playurl",
            params={
                "bvid": video_id,
                "cid": video_cid,
                "fnval": 4048,
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            },
            cookies={
                "bili_jct": os.getenv("BILI_JCT"),
                "SESSDATA": os.getenv("SESSDATA"),
            },
        )

        if response.status_code != httpx.codes.OK:
            return None

        response = response.json()

        if response.get("code") != 0:
            return None

        return response.get("data")


async def download_video_page(video_page_download_url: str) -> AsyncGenerator:
    """下载视频

    Args:
        video_page_download_url (str): 视频分P下载链接

    Returns:
        AsyncGenerator: 异步生成器获取视频块chunk
    """
    async with httpx.AsyncClient() as client, client.stream(
        "GET",
        video_page_download_url,
        headers={
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        },
    ) as response:
        async for chunk in response.aiter_bytes():
            yield chunk


async def download_video_page_audio(video_page_audio_download_url: str) -> AsyncGenerator:
    """下载视频

    Args:
        video_page_audio_download_url (str): 视频分P的音频下载链接

    Returns:
        AsyncGenerator: 异步生成器获取音频块chunk
    """
    async with httpx.AsyncClient() as client, client.stream(
        "GET",
        video_page_audio_download_url,
        headers={
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        },
    ) as response:
        async for chunk in response.aiter_bytes():
            yield chunk


@rate_limit()
async def download_video_page_dm(video_page_cid: str, video_aid: int, video_page_duration: str) -> dict:
    dm_protobuf = b""

    async with httpx.AsyncClient() as client:
        for segment_index in range(math.ceil(video_page_duration / 360)):
            response = await client.get(
                "https://api.bilibili.com/x/v2/dm/web/seg.so",
                headers={
                    "Referer": "https://www.bilibili.com",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                },
                params={
                    "type": 1,
                    "oid": video_page_cid,
                    "aid": video_aid,
                    "segment_index": segment_index + 1,
                },
                cookies={
                    "bili_jct": os.getenv("BILI_JCT"),
                    "SESSDATA": os.getenv("SESSDATA"),
                },
            )

            # 组装不同段的弹幕数据
            dm_protobuf += await response.aread()

    # 解析弹幕protobuf数据
    dm_seg = DmSegMobileReply()
    dm_seg.ParseFromString(dm_protobuf)

    return dm_seg.elems


async def download_video_pic(video_pic_download_url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            video_pic_download_url,
            headers={
                "Referer": "https://www.bilibili.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            },
        )

        return await response.aread()


@rate_limit()
async def get_fav_info(media_id: str) -> dict:
    """获取收藏夹信息

    Args:
        media_id (str): 收藏夹id

    Returns:
        dict: 收藏夹信息
    """
    has_more = True
    page_num = 1
    result = None

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                "https://api.bilibili.com/x/v3/fav/resource/list",
                params={
                    "media_id": media_id,
                    "ps": 20,
                    "pn": page_num,
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                },
                cookies={
                    "bili_jct": os.getenv("BILI_JCT"),
                    "SESSDATA": os.getenv("SESSDATA"),
                },
            )

            if response.status_code != httpx.codes.OK:
                return None

            response = response.json()

            if response.get("code") != 0:
                return None

            if result is None:
                result = response["data"]
            else:
                result["medias"] += response["data"]["medias"]

            has_more = response["data"]["has_more"]

            if not has_more:
                break

            page_num += 1

        return result
