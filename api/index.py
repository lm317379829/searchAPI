from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

from youtubesearchpython import CustomSearch, VideosSearch, ChannelsSearch, PlaylistsSearch, Video, Playlist
import time
import asyncio

# 创建 FastAPI 实例
app = FastAPI(title="SearchAPI", version="1.0.0")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局缓存和并发锁
searchCache = {}
cacheLock = asyncio.Lock()
CacheTTL = 3600  # 缓存时间(秒)：1小时


def handlePic(sources):
    pic = ""
    maxSize = -1
    for thumbnail in sources:
        # 计算面积 (宽 * 高)
        currentSize = thumbnail.get("width", 0) * thumbnail.get("width", 0)
        if currentSize > maxSize:
            maxSize = currentSize
            pic = thumbnail.get("url", "")

    if pic != "" and not pic.startswith("http"):
        pic = "https://" + pic.strip("/")

    return pic


def get_file_path(filename: str):
    """获取文件路径，兼容本地和 Serverless 环境"""
    # 尝试从当前目录获取
    if os.path.exists(filename):
        return filename
    
    # 尝试从项目根目录获取
    root_path = Path(__file__).parent.parent
    file_path = root_path / filename
    if file_path.exists():
        return str(file_path)
    
    # 返回默认路径
    return filename


@app.get("/")
async def read_index():
    try:
        return FileResponse(get_file_path("index.html"))
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "message": "SearchAPI 运行中 - 访问 /docs 查看 API 文档",
                "endpoints": {
                    "search": "/search?keywords=python",
                    "video": "/video?id=VIDEO_ID",
                    "playlist": "/playlist?id=PLAYLIST_ID"
                }
            }
        )


@app.get("/favicon.ico")
async def favicon():
    try:
        return FileResponse(get_file_path("favicon.ico"))
    except Exception:
        return JSONResponse(status_code=204)


@app.get("/video")
async def video(id: str = Query(..., description="视频ID")):
    try:
        result = Video.get(id, timeout=30)
        channel = result.get("channel", {})
        duartion = result["duration"] if 'duration' in result else {}
        vod = {
            "name": result.get("title", ""),
            "pic": handlePic(result.get("thumbnails", [])),
            "duration": duartion.get("text", ""),
            "channel": {
                "id": channel.get("id", ""),
                "name": channel.get("name", ""),
            }
        }
        return vod
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"获取视频信息错误: {str(err)}")


@app.get("/playlist")
async def playlist(id: str = Query(..., description="播放列表ID")):
    try:
        result = Playlist.get(id, timeout=30).get("info", {})
        channel = result.get("channel", {})
        vod = {
            "name": result.get("title", ""),
            "pic": handlePic(result.get("thumbnails", [])),
            "channel": {
                "id": channel.get("id", ""),
                "name": channel.get("name", ""),
            }
        }
        return vod
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"获取播放列表信息错误: {str(err)}")


@app.get("/search")
async def search(
        keywords: str = Query(..., description="搜索关键词", min_length=1),
        filter: str = Query("", description="筛选条件", min_length=0),
        page: int = Query(1, description="页码, 从1开始", ge=1)
):
    # 筛选列表
    searchModes = {
        'videos': 'EgIQAQ%3D%3D',
        'channels': 'EgIQAg%3D%3D',
        'playlists': 'EgIQAw%3D%3D',
        'livestreams': 'EgJAAQ%3D%3D'
    }

    sortFilters = {
        'relevance': 'CAASAhAB',
        'uploadDate': 'CAISAhAB',
        'viewCount': 'CAMSAhAB',
        'rating': 'CAESAhAB',
        'lastHour': 'EgQIARAB',
        'today': 'EgQIAhAB',
        'thisWeek': 'EgQIAxAB',
        'thisMonth': 'EgQIBBAB',
        'thisYear': 'EgQIBRAB',
        'short': 'EgQQARgB',
        'long': 'EgQQARgC'
    }

    try:
        # 1. 尝试从缓存中读取，使用锁保证并发读写安全
        videoSearchOBJ = None
        channelSearchOBJ = None
        playlistSearchOBJ = None

        async with cacheLock:
            if keywords in searchCache:
                cache, expireTime, cachePage = searchCache[keywords]
                # 检查是否过期，并且请求的是下一页
                if int(time.time()) < expireTime and page > cachePage:
                    videoSearchOBJ = cache.get("video")
                    channelSearchOBJ = cache.get("channel")
                    playlistSearchOBJ = cache.get("playlist")
                else:
                    # 缓存已过期或请求的是第一页（需要重置），从字典中删除
                    del searchCache[keywords]

        # 2. 执行搜索（并发处理）
        tasks = []
        taskDict = {}  # 用于存储 Task 对象和对应的变量名

        if page == 1:
            # 初始搜索：并发实例化搜索对象，任务互不影响
            if filter in searchModes.keys():
                task = asyncio.create_task(
                    asyncio.to_thread(CustomSearch, keywords, searchModes[filter], language="zh", region="CN", limit=20,
                                      timeout=30),
                    name=filter
                )
                tasks.append(task)
                match filter:
                    case "videos" | "livestreams":
                        taskDict["videoSearchOBJ"] = task
                    case "channels":
                        taskDict["channelSearchOBJ"] = task
                    case "playlists":
                        taskDict["playlistSearchOBJ"] = task
            elif filter in sortFilters.keys():
                task = asyncio.create_task(
                    asyncio.to_thread(CustomSearch, keywords, sortFilters[filter], language="zh", region="CN", limit=20,
                                      timeout=30),
                    name="videos"
                )
                tasks.append(task)
                taskDict["videoSearchOBJ"] = task
            else:
                videos = asyncio.create_task(
                    asyncio.to_thread(VideosSearch, keywords, language="zh", region="CN", limit=20, timeout=30),
                    name="videos")
                channels = asyncio.create_task(
                    asyncio.to_thread(ChannelsSearch, keywords, language="zh", region="CN", limit=20, timeout=30),
                    name="channels")
                playlists = asyncio.create_task(
                    asyncio.to_thread(PlaylistsSearch, keywords, language="zh", region="CN", limit=20, timeout=30),
                    name="playlists")

                tasks.extend([videos, channels, playlists])
                taskDict["videoSearchOBJ"] = videos
                taskDict["channelSearchOBJ"] = channels
                taskDict["playlistSearchOBJ"] = playlists
        else:
            # 获取下一页：并发调用 .next()，任务互不影响
            if videoSearchOBJ:
                tasks.append(asyncio.create_task(asyncio.to_thread(videoSearchOBJ.next), name="videos"))
            if channelSearchOBJ:
                tasks.append(asyncio.create_task(asyncio.to_thread(channelSearchOBJ.next), name="channels"))
            if playlistSearchOBJ:
                tasks.append(asyncio.create_task(asyncio.to_thread(playlistSearchOBJ.next), name="playlists"))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # 关键点：从 Task 中获取真正的 Search 对象实例 (仅在 page 1 时需要转换)
        if page == 1:
            if "videoSearchOBJ" in taskDict:
                task = taskDict["videoSearchOBJ"]
                videoSearchOBJ = task.result() if not isinstance(task.exception(), Exception) else None
            if "channelSearchOBJ" in taskDict:
                task = taskDict["channelSearchOBJ"]
                channelSearchOBJ = task.result() if not isinstance(task.exception(), Exception) else None
            if "playlistSearchOBJ" in taskDict:
                task = taskDict["playlistSearchOBJ"]
                playlistSearchOBJ = task.result() if not isinstance(task.exception(), Exception) else None

        # 获取当前页结果 (此时 videoSearchOBJ 已经是真正的搜索对象实例)
        videos = videoSearchOBJ.result() if videoSearchOBJ and hasattr(videoSearchOBJ, 'result') else {"result": []}
        channels = channelSearchOBJ.result() if channelSearchOBJ and hasattr(channelSearchOBJ, 'result') else {
            "result": []}
        playlists = playlistSearchOBJ.result() if playlistSearchOBJ and hasattr(playlistSearchOBJ, 'result') else {
            "result": []}

        vods = {"list": [], "hasNext": False}

        results = (videos.get("result", []) or []) + \
                  (channels.get("result", []) or []) + \
                  (playlists.get("result", []) or [])

        # 3. 将新的 searchOBJ 写入缓存
        async with cacheLock:
            # 当前时间戳 + 缓存生存时间，页码
            searchOBJs = {}
            if videos.get("result") and len(videos["result"]) == 20:
                searchOBJs["video"] = videoSearchOBJ
                vods["hasNext"] = True
            else:
                searchOBJs["video"] = None

            if channels.get("result") and len(channels["result"]) == 20:
                searchOBJs["channel"] = channelSearchOBJ
                vods["hasNext"] = True
            else:
                searchOBJs["channel"] = None

            if playlists.get("result") and len(playlists["result"]) == 20:
                searchOBJs["playlist"] = playlistSearchOBJ
                vods["hasNext"] = True
            else:
                searchOBJs["playlist"] = None
            searchCache[keywords] = (searchOBJs, int(time.time() + CacheTTL), page)

        for result in results:
            if result["id"] == "":
                continue

            cate = result["type"]
            if cate == "":
                cate = "video"

            pic = handlePic(result.get("thumbnails", []))

            if cate == "video":
                remarks = result.get('duration', "")
            else:
                remarks = result.get('videoCount', "")

            if not remarks:
                remarks = ""

            vod = {
                "id": result["id"],
                "pic": pic,
                "cate": cate,
                "name": result.get("title", "未知"),
                "remarks": remarks.strip()
            }

            vods["list"].append(vod)

        return vods
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"搜索错误: {str(err)}")


if __name__ == "__main__":
    import uvicorn
    # 如果代码文件名为 main.py，则传入 "main:app"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
