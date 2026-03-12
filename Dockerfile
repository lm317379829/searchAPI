# 使用轻量级的 Python 3.11 镜像作为基础镜像
FROM python:3.14-slim

# 设置工作目录
WORKDIR /app

# 安装 git（因为 requirements.txt 中包含通过 git 安装的依赖）
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# 使用 --no-cache-dir 减少镜像体积
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源代码
COPY main.py .

# 暴露 FastAPI 运行的端口
EXPOSE 8000

# 运行应用
# 使用 uvicorn 启动，host 设置为 0.0.0.0 以便从容器外部访问
CMD ["python", "main.py"]
