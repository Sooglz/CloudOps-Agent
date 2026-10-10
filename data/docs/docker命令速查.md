# Docker 常用命令速查手册

## 一、容器生命周期管理

### 启动与停止
- 运行一个容器：`docker run -d --name nginx nginx`
- 启动已停止的容器：`docker start <容器名>`
- 停止容器：`docker stop <容器名>`
- 强制停止：`docker kill <容器名>`
- 删除容器：`docker rm <容器名>`

### 查看容器
- 查看运行中的容器：`docker ps`
- 查看所有容器（含停止的）：`docker ps -a`
- 查看容器日志：`docker logs <容器名>`
- 实时跟踪日志：`docker logs -f <容器名>`

## 二、镜像管理

- 拉取镜像：`docker pull <镜像名>:<tag>`
- 查看本地镜像：`docker images`
- 删除镜像：`docker rmi <镜像名>`
- 构建镜像：`docker build -t <镜像名>:<tag> .`

## 三、进入容器与调试

- 进入运行中的容器：`docker exec -it <容器名> /bin/bash`
- 查看容器详情：`docker inspect <容器名>`
- 查看容器资源占用：`docker stats`

## 四、网络与数据卷

- 查看网络：`docker network ls`
- 创建数据卷：`docker volume create <卷名>`
- 挂载数据卷运行：`docker run -v <卷名>:/data <镜像名>`
- 查看数据卷：`docker volume ls`
