import asyncio
import os
import random
import re
import typing
from pathlib import Path

import aiofiles
from sqlmodel import select, update

from app import bilibili
from app.db import async_db_session
from app.dependencies import AsyncQueueManager
from app.logger import logger
from app.models import Video, VideoStatus
from app.wrappers import background_worker

if typing.TYPE_CHECKING:
    from app.models import Video


CURRENT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = CURRENT_DIR.parent / "download"


async def convert_dm_to_ass(danmaku_list) -> str:
    video_width = 1920
    video_height = 1080
    # ASS 文件基础结构
    ass_content = f"""[Script Info]
ScriptType: V4.00
PlayResX: {video_width}
PlayResY: {video_height}
Collisions: Normal
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,38,&H4cFFFFFF,&H00FFFFFF,&H4c000000,&H00000000,1, 0, 0, 0, 100, 100, 0.00, 0.00, 1, 0.8, 0, 7, 0, 0, 0, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect,Text
"""
    for danmaku in danmaku_list:
        progress = danmaku.progress
        mode = danmaku.mode
        text = danmaku.content

        start = ms_to_ass_time(progress)
        end = ms_to_ass_time(progress + 15000)

        if mode == 4:
            # 底部弹幕
            style_code = rf"{{\move(-100, {video_height}, {video_width}, {video_height})\fad(500,500)}}"
        elif mode == 5:
            # 顶部弹幕
            style_code = rf"{{\move(-100, 0, {video_width}, 0)\fad(500,500)}}"
        else:
            # 默认随机高度位置
            random_height = random.randint(0, int(video_height))
            style_code = rf"{{\move(-100, {random_height}, {video_width}, {random_height})\fad(500,500)}}"

        dialogue_line = f"Dialogue: 2,{start},{end},Default,,0,0,0,,{style_code}{text}"
        ass_content += dialogue_line + "\n"

    return ass_content


def ms_to_ass_time(ms):
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    cs = (ms % 1000) // 10
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"


def get_legal_filename(filename: str):
    return re.sub(r'[\\/:*?"<>|]', "_", filename.replace(":", "："))


def detect_available_decoder_encoder() -> tuple[str]:
    """获取系统可用的编解码器

    Returns:
        tuple[str]: 有两个元素的元组 第一个为解码器 第二个为编码器
    """
    if os.path.exists("/dev/nvidia0") or os.path.exists("/dev/nvidiactl"):
        return "h264_cuvid", "h264_nvenc"

    if os.path.exists("/dev/dri/renderD128"):
        return "h264_qsv", "h264_qsv"

    if os.path.exists("/dev/kfd"):
        return "h264_amf", "h264_amf"

    return "h264", "copy"


@background_worker
async def scan_video():
    """后台任务，循环从下载队列中获取视频，并下载视频"""
    download_queue = AsyncQueueManager.get_queue()

    logger.warning("后台视频下载队列启动......")

    # 首先完成上次未完成的任务
    async with async_db_session() as session:
        stmt = select(Video)
        videos = await session.exec(stmt)
        videos = videos.all()

        for video in videos:
            if video.status == VideoStatus.VIDEO_DOWNLOAD_PROCESSING:
                await download_queue.put(video)

    while True:
        video: Video = await download_queue.get()

        # 获取视频分P信息
        video_bvid = video.bvid
        video_tile = video.title
        video_aid = video.aid
        video_page_info = await bilibili.get_video_page_info(video_bvid)

        # 视频保存目录
        video_page_save_dir = DOWNLOAD_DIR / video_tile

        # 创建视频文件夹
        os.makedirs(video_page_save_dir, exist_ok=True)

        # 依次下载视频的分P
        for video_page in video_page_info:
            video_page_cid = video_page.get("cid")
            video_page_title = video_page.get("part")
            video_page_title = video_page_title.replace(":", "：")

            # 定义各文件保存位置
            # 视频保存位置
            video_page_save_path = video_page_save_dir / get_legal_filename(video_page_title + ".mp4")
            # 音频保存位置
            video_page_audio_save_path = video_page_save_dir / get_legal_filename(video_page_title + ".m4a")
            # 创建ffmpeg视频合成临时输出文件
            video_page_temp_save_path = video_page_save_dir / (video_page_title + "-temp.mp4")
            # 弹幕保存位置
            video_page_dm_save_path = video_page_save_dir / get_legal_filename(video_page_title + ".ass")
            # 封面保存位置
            video_pic_save_path = video_page_save_dir / get_legal_filename(video_page_title + ".jpg")

            if not os.path.exists(video_page_save_path) or not os.path.exists(video_page_audio_save_path):
                # 获取视频分P的下载地址
                video_playurl_info = await bilibili.get_video_playurl_info(video_bvid, video_page_cid)

            if not os.path.exists(video_page_save_path):
                # 视频地址
                video_page_download_url = video_playurl_info.get("dash").get("video")
                video_page_download_url = video_page_download_url[0]
                video_page_download_url = video_page_download_url.get("baseUrl")

                # 下载视频
                logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-视频开始下载")
                async with aiofiles.open(video_page_save_path, "wb") as f:
                    async for chunk in bilibili.download_video_page(video_page_download_url):
                        await f.write(chunk)

                logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-视频下载完成")

            if not os.path.exists(video_page_audio_save_path):
                # 音频地址
                video_page_audio_download_url = video_playurl_info.get("dash").get("audio")
                video_page_audio_download_url = video_page_audio_download_url[0]
                video_page_audio_download_url = video_page_audio_download_url.get("baseUrl")

                # 下载音频
                logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-音频开始下载")
                async with aiofiles.open(video_page_audio_save_path, "wb") as f:
                    async for chunk in bilibili.download_video_page_audio(video_page_audio_download_url):
                        await f.write(chunk)

                logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-音频下载完成")

            decoder, encoder = detect_available_decoder_encoder()

            # 合成视频和音频
            logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-视频和音频合成开始")
            cmd = f'ffmpeg  -i "{video_page_save_path}" -i "{video_page_audio_save_path}" -c copy -y "{video_page_temp_save_path}"'

            logger.warning(f"视频音频合成命令：{cmd}")
            proc = await asyncio.create_subprocess_shell(cmd, cwd=video_page_save_dir)
            await proc.wait()

            # 替换视频为合成后有音频的视频
            os.remove(video_page_save_path)
            os.rename(video_page_temp_save_path, video_page_save_path)

            logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-视频和音频合成成功")

            if not os.path.exists(video_page_dm_save_path):
                # 下载弹幕
                logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-弹幕下载开始")

                # 视频时长用来计算弹幕有几段（每6分钟为一段）
                video_page_duration = video_page.get("duration")
                video_page_dm = await bilibili.download_video_page_dm(video_page_cid, video_aid, video_page_duration)

                logger.warning(f"{video_bvid}-{video_tile}-{video_page_title}-弹幕下载完成")

                # 将弹幕转化为ASS格式字符串
                ass_content = await convert_dm_to_ass(video_page_dm)

                async with aiofiles.open(video_page_dm_save_path, "w", encoding="utf8") as f:
                    await f.write(ass_content)

            if not os.path.exists(video_pic_save_path):
                logger.warning(f"{video_bvid}-{video_tile}-封面下载开始")

                # 下载封面
                pic = await bilibili.download_video_pic(video.pic)

                async with aiofiles.open(video_pic_save_path, "wb") as f:
                    await f.write(pic)

                logger.warning(f"{video_bvid}-{video_tile}-封面下载完成")

        # 更新视频数据库状态为成功
        async with async_db_session() as session:
            stmt = update(Video).where(Video.bvid == video_bvid).values(status=VideoStatus.VIDEO_DOWNLOAD_SUCCESS)
            await session.exec(stmt)
            await session.commit()
