# 🚀 Bilibili视频自动下载工具 · FastAPI 驱动

**轻松下载B站视频，告别繁琐配置！**  
✨ **可视化操作 | 多类型支持 | 自动字幕 | 媒体库友好**  

![](https://img.shields.io/badge/Powered%20by-FastAPI-009688?logo=fastapi) 
![](https://img.shields.io/badge/Support-Bilibili-00A1D6?logo=bilibili) 
![](https://img.shields.io/badge/Media%20Server-Ready-important)

---

## 🌟 核心功能

- **🎥 操作简单**：无需配置文件！通过网页直接输入URL开箱即用。
- **📚 全场景支持**：单个视频、视频合集、视频列表、收藏夹统统拿下！
- **📥 智能抓取**：自动下载视频**弹幕**（支持多语言轨道）。
- **🔄 媒体库兼容**：完美适配 **Jellyfin/Plex**，文件名与元数据标准化。
![](https://github.com/TomasJack1/bili-sync-py/blob/main/images/main-menu.png?raw=true)
---

## 🛠️ 快速开始

### docker部署
```shell
docker run -e BILI_JCT={填你的BILI_JCT} -e SESSDATA={填你的SESSADATA} -d --name bili-sync-py -v {主机映射下载目录}:/bili-sync-py/download -p 4444:8080 ghcr.io/tomasjack1/bili-sync-py
```
