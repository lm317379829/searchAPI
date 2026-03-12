from fastapi import FastAPI, Query, HTTPException
from youtubesearchpython import VideosSearch, ChannelsSearch, PlaylistsSearch
import uvicorn
import time
import asyncio
# 创建 FastAPI 实例
app = FastAPI()

# 全局缓存和并发锁
searchCache = {}
cacheLock = asyncio.Lock()
CacheTTL = 3600  # 缓存时间(秒)：1小时



@app.get("/search")
async def search(
    keywords: str = Query(..., description="搜索关键词", min_length=1),
    page: int = Query(1, description="页码, 从1开始", ge=1)
):
    """
    搜索 YouTube 视频
    """
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
        if page == 1:
            # 初始搜索：并发实例化搜索对象，任务互不影响
            objs = await asyncio.gather(
                asyncio.to_thread(VideosSearch, keywords, language="zh", region="CN", limit=20, timeout=30),
                asyncio.to_thread(ChannelsSearch, keywords, language="zh", region="CN", limit=20, timeout=30),
                asyncio.to_thread(PlaylistsSearch, keywords, language="zh", region="CN", limit=20, timeout=30),
                return_exceptions=True
            )
            videoSearchOBJ = objs[0] if not isinstance(objs[0], Exception) else None
            channelSearchOBJ = objs[1] if not isinstance(objs[1], Exception) else None
            playlistSearchOBJ = objs[2] if not isinstance(objs[2], Exception) else None
        else:
            # 获取下一页：并发调用 .next()，任务互不影响
            tasks = []
            if videoSearchOBJ:
                tasks.append(asyncio.to_thread(videoSearchOBJ.next))
            if channelSearchOBJ:
                tasks.append(asyncio.to_thread(channelSearchOBJ.next))
            if playlistSearchOBJ:
                tasks.append(asyncio.to_thread(playlistSearchOBJ.next))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # 获取当前页结果
        videos = videoSearchOBJ.result() if videoSearchOBJ and hasattr(videoSearchOBJ, 'result') else {"result": []}
        channels = channelSearchOBJ.result() if channelSearchOBJ and hasattr(channelSearchOBJ, 'result') else {"result": []}
        playlists = playlistSearchOBJ.result() if playlistSearchOBJ and hasattr(playlistSearchOBJ, 'result') else {"result": []}

        vod = {"list": []}

        results = (videos.get("result", []) or []) + \
                  (channels.get("result", []) or []) + \
                  (playlists.get("result", []) or [])

        # 3. 将新的 searchOBJ 写入缓存
        async with cacheLock:
            # 当前时间戳 + 缓存生存时间，页码
            searchOBJs = {}
            if videos.get("result") and len(videos["result"]) == 20:
                searchOBJs["video"] = videoSearchOBJ
                vod["hasNext"] = True
            else:
                searchOBJs["video"] = None

            if channels.get("result") and len(channels["result"]) == 20:
                searchOBJs["channel"] = channelSearchOBJ
                vod["hasNext"] = True
            else:
                searchOBJs["channel"] = None
                
            if playlists.get("result") and len(playlists["result"]) == 20:
                searchOBJs["playlist"] = playlistSearchOBJ
                vod["hasNext"] = True
            else:
                searchOBJs["playlist"] = None
            searchCache[keywords] = (searchOBJs, int(time.time()+CacheTTL), page)

        for result in results:
            if result["id"] == "":
                continue

            cate = result["type"]
            if cate == "":
                cate = "video"
            vid = f'{{"cate":"{cate}","id":"{result["id"]}"}}'

            # 取最大的图片
            pic = ""
            maxSize = -1
            for thumbnail in result.get("thumbnails", []):
                # 计算面积 (宽 * 高)
                currentSize = thumbnail.get("width", 0) * thumbnail.get("width", 0)
                if currentSize > maxSize:
                    maxSize = currentSize
                    pic = thumbnail.get("url", "")
            
            if pic != "" and not pic.startswith("http"):
                pic = "https://" + pic.strip("/")

            if cate == "video":
                remarks = result.get('duration', "")
            else:
                remarks = result.get('videoCount', "")

            if not remarks:
                remarks = ""

            vod["list"].append({
                "vod_id": vid,
                "vod_pic": pic,
                "vod_name": result.get("title", "未知标题"),
                "vod_tag": "folder" if cate == "channel" else "",
                "vod_remarks": remarks.strip()
            })

            
        return vod
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"搜索时发生错误: {str(err)}")

if __name__ == "__main__":
    # 如果代码文件名为 main.py，则传入 "main:app"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
