# SearchAPI - YouTube 搜索 API

一个基于 FastAPI 的 YouTube 搜索服务，提供视频、频道、播放列表搜索功能。

## 功能特性

- 🔍 YouTube 视频、频道、播放列表搜索
- 📄 支持分页查询
- 🎯 丰富的搜索筛选选项
- ⚡ 并发搜索加速
- 💾 智能缓存机制
- 🌐 支持中文搜索和多区域查询

## API 端点

### GET /search
搜索 YouTube 内容

**参数:**
- `keywords` (必需): 搜索关键词
- `filter` (可选): 筛选条件
  - `videos`: 视频
  - `channels`: 频道
  - `playlists`: 播放列表
  - `livestreams`: 直播
  - `relevance`: 相关性排序
  - `uploadDate`: 上传时间排序
  - `viewCount`: 播放量排序
  - `rating`: 评分排序
  - `lastHour/today/thisWeek/thisMonth/thisYear`: 时间过滤
  - `short/long`: 视频长度过滤
- `page` (可选): 页码，默认为 1

**示例:**
```
GET /search?keywords=python&filter=videos&page=1
```

### GET /video
获取视频详情

**参数:**
- `id` (必需): 视频 ID

### GET /playlist
获取播放列表详情

**参数:**
- `id` (必需): 播放列表 ID

## 本地运行

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动服务
```bash
python main.py
```

服务将运行在 `http://localhost:8000`

### 访问 Web 界面
打开浏览器访问 `http://localhost:8000/`

## Vercel 部署

### 部署步骤

1. **准备仓库**
   - 确保所有文件已推送到 GitHub

2. **连接 Vercel**
   - 访问 https://vercel.com
   - 点击 "New Project"
   - 选择你的 GitHub 仓库

3. **配置部署**
   - 项目名称：自动填充为仓库名
   - Framework Preset：选择 "Other"
   - Build Command：`pip install -r requirements.txt`
   - Output Directory：保持默认
   - Environment Variables：如需要可添加

4. **完成部署**
   - 点击 "Deploy"
   - 等待部署完成，Vercel 会提供你的项目 URL

### 部署注意事项

- ⏱️ **冷启动时间**: 首次请求可能需要 10-20 秒，这是 Serverless 的正常行为
- 🔌 **外部依赖**: 该项目依赖外部 YouTube 服务，确保网络连接正常
- ⏲️ **超时限制**: 默认超时时间为 10 秒（Vercel 标准版限制）
- 💾 **缓存限制**: Serverless 环境中的缓存是临时的，不会跨请求保留

### 环境变量配置

如果需要添加自定义配置，可在 Vercel 项目设置中添加：
```
PORT=3000
```

## 项目结构

```
searchAPI/
├── main.py              # FastAPI 应用主文件
├── requirements.txt     # Python 依赖
├── index.html          # Web 界面
├── favicon.ico         # 网站图标
├── vercel.json         # Vercel 配置
├── build.sh            # 构建脚本
├── Dockerfile          # Docker 配置
└── README.md           # 本文件
```

## 技术栈

- **Framework**: FastAPI
- **Server**: Uvicorn
- **Search**: youtube-search-python
- **Async**: asyncio
- **Deployment**: Docker / Vercel

## 常见问题

### Q: 部署后无法访问？
A: 请检查：
1. GitHub 仓库是否公开或 Vercel 有访问权限
2. 部署是否成功完成
3. 网络连接是否正常

### Q: 搜索速度慢？
A: 这可能是因为：
1. YouTube API 响应缓慢
2. Serverless 冷启动
3. 并发请求过多

### Q: 缓存不工作？
A: Serverless 环境中缓存是临时的，每次函数启动时会重置。考虑使用外部���存服务如 Redis。

## 许可证

MIT

## 更新日志

### v1.0.0
- ✅ 初始版本发布
- ✅ 支持 Vercel 部署
- ✅ 完整搜索功能
