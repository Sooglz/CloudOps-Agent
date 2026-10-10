# ============================================================
# CloudOps Agent —— Dockerfile
#
# 作用：把整个 Agent 项目打包成一个可运行的容器镜像
#
# 构建命令（在项目根目录 D:\Work\CloudOps-Agent 下执行）：
#   docker build -t cloudops-agent:latest .
#
# 运行命令：
#   docker run -it --rm \
#     --env-file .env \
#     cloudops-agent:latest
#
# 学习要点：
# 1. FROM 选基础镜像（Python 官方镜像自带 Python 环境）
# 2. WORKDIR 设定工作目录
# 3. COPY 把项目文件复制进镜像
# 4. RUN 在构建时执行命令（装依赖）
# 5. CMD 定义容器启动后默认运行的命令
# ============================================================

# 基础镜像：Python 3.12 的精简版（slim 更小，适合演示）
FROM python:3.12-slim

# 设置工作目录（容器内的路径）
WORKDIR /app

# 先复制依赖清单，再安装依赖
# 这样做的原因：Docker 会缓存每一层，依赖清单不变时，
# 重新构建就不用重复下载依赖，大幅加快构建速度
COPY requirements.txt .

# 安装依赖（用阿里云镜像加速；清华镜像有时同步滞后会找不到新版本）
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目源码和知识库文档
COPY src/ ./src/
COPY data/ ./data/

# 复制 .env.example 作为默认配置（真实 .env 通过 --env-file 或环境变量注入）
# 注意：真实 .env 含密钥，绝不能 COPY 进镜像（会被提交到镜像层里泄露）
COPY .env.example ./.env.example

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 容器启动后默认运行 Agent 交互式对话
CMD ["python", "src/app.py"]
