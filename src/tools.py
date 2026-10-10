"""
CloudOps Agent —— 工具层（真实命令版）

定义 Agent 可以调用的工具。每个工具就是一个普通 Python 函数，
内部通过 subprocess 调用真实的 kubectl / docker 只读命令。

设计原则：
1. 只提供「只读」工具（查询类），危险操作（删除/重启）后续单独加安全确认
2. 工具层与 Agent 解耦：函数签名和 docstring 不变，Agent 代码无需改动
3. 「真实命令 + 自动降级」：当本机没有 kubectl/docker 环境时，
   自动降级为模拟数据，保证没有环境也能演示工具调用机制

学习要点：
- 这就是「工具调用」真正落地的样子：Agent 决策 → 程序执行真实命令 → 结果回传
"""

import shutil
import subprocess


# ============================================================
# 环境探测：判断本机是否有 kubectl / docker 命令
# ============================================================

def _has_cmd(cmd: str) -> bool:
    """检查某个命令是否在 PATH 中可用。"""
    return shutil.which(cmd) is not None


def _run(cmd_list, timeout: int = 10) -> str:
    """
    执行一条只读命令，返回 (是否成功, 输出文本)。
    统一用 subprocess 跑，捕获输出和错误。
    """
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"[命令执行失败] exit={result.returncode}: {result.stderr.strip()}"
    except FileNotFoundError:
        return "[命令不存在] 请确认已安装对应工具并加入 PATH"
    except subprocess.TimeoutExpired:
        return "[命令超时] 执行时间超过限制"


# ============================================================
# 真实工具（优先使用，需要 kubectl / docker 环境）
# ============================================================

def get_pods(namespace: str = "") -> str:
    """
    查询 Kubernetes 集群中指定命名空间下的 Pod 列表及状态。
    参数 namespace：命名空间名称，为空时查询所有命名空间（等价 kubectl get pods -A）。
    返回：Pod 名称和状态。
    """
    if _has_cmd("kubectl"):
        if namespace:
            out = _run(["kubectl", "get", "pods", "-n", namespace])
            label = f"命名空间 {namespace} 下的 Pod：\n"
        else:
            out = _run(["kubectl", "get", "pods", "-A"])
            label = "所有命名空间的 Pod：\n"
        if not out.startswith("["):
            return label + out
        # 命令执行失败（比如没连上集群），降级为模拟数据
    return _mock_get_pods(namespace)


def get_nodes() -> str:
    """
    查询 Kubernetes 集群的节点列表。
    返回：节点名称、状态、角色、版本等信息。
    """
    if _has_cmd("kubectl"):
        out = _run(["kubectl", "get", "nodes"])
        if not out.startswith("["):
            return f"集群节点：\n{out}"
    return _mock_get_nodes()


def get_container_logs(pod_name: str, namespace: str = "default", tail: int = 20) -> str:
    """
    查看指定 Pod 的容器日志，用于排查故障。
    参数 pod_name：Pod 名称（必填）。
    参数 namespace：命名空间，默认 default。
    参数 tail：返回最后多少行日志，默认 20。
    返回：日志内容。
    """
    if _has_cmd("kubectl"):
        out = _run(["kubectl", "logs", pod_name, "-n", namespace, f"--tail={tail}"])
        if not out.startswith("["):
            return f"Pod {pod_name} 的日志（最后 {tail} 行）：\n{out}"
    return _mock_get_container_logs(pod_name, tail)


def get_docker_containers() -> str:
    """
    查询本机 Docker 正在运行的容器列表。
    返回：容器 ID、镜像、状态、端口映射等。
    """
    if _has_cmd("docker"):
        out = _run(["docker", "ps"])
        if not out.startswith("["):
            return f"运行中的 Docker 容器：\n{out}"
    return _mock_get_docker_containers()


def get_docker_images() -> str:
    """
    查询本机 Docker 镜像列表。
    返回：镜像仓库、标签、大小等。
    """
    if _has_cmd("docker"):
        out = _run(["docker", "images"])
        if not out.startswith("["):
            return f"本机 Docker 镜像：\n{out}"
    return _mock_get_docker_images()


# ============================================================
# 模拟数据（降级用：没有真实环境时的 fallback）
# ============================================================

def _mock_get_pods(namespace: str = "default") -> str:
    mock_pods = [
        ("nginx-deployment-6d4b7c9f8-abc12", "Running"),
        ("nginx-deployment-6d4b7c9f8-def34", "Running"),
        ("redis-7f8c9d6e5-ghi56", "Running"),
        ("mysql-0", "Pending"),
        ("flask-app-5c6d7e8f9-jkl78", "CrashLoopBackOff"),
    ]
    lines = [f"命名空间 {namespace} 下的 Pod（模拟数据）："]
    for name, status in mock_pods:
        lines.append(f"  - {name}: {status}")
    return "\n".join(lines)


def _mock_get_nodes() -> str:
    mock_nodes = [
        ("node-1", "CPU 45%", "内存 62%"),
        ("node-2", "CPU 38%", "内存 51%"),
        ("node-3", "CPU 72%", "内存 78%"),
    ]
    lines = ["集群节点（模拟数据）："]
    for name, cpu, mem in mock_nodes:
        lines.append(f"  - {name}: {cpu}, {mem}")
    return "\n".join(lines)


def _mock_get_container_logs(pod_name: str, tail: int = 20) -> str:
    mock_logs = [
        f"[INFO] 2026-10-10 10:00:01 {pod_name} 启动完成",
        f"[INFO] 2026-10-10 10:00:02 监听端口 8080",
        f"[WARN] 2026-10-10 10:05:11 数据库连接超时",
        f"[ERROR] 2026-10-10 10:05:12 连接数据库失败: timeout after 30s",
        f"[ERROR] 2026-10-10 10:05:13 进程退出，退出码 1",
    ]
    shown = mock_logs[-tail:]
    return f"Pod {pod_name} 的日志（模拟数据，最后 {len(shown)} 行）：\n" + "\n".join(shown)


def _mock_get_docker_containers() -> str:
    return (
        "运行中的 Docker 容器（模拟数据）：\n"
        "CONTAINER ID   IMAGE          STATUS         PORTS\n"
        "a1b2c3d4e5f6   nginx:latest   Up 2 hours     0.0.0.0:80->80/tcp\n"
        "b2c3d4e5f6a7   redis:7        Up 2 hours     0.0.0.0:6379->6379/tcp"
    )


def _mock_get_docker_images() -> str:
    return (
        "本机 Docker 镜像（模拟数据）：\n"
        "REPOSITORY   TAG       SIZE\n"
        "nginx        latest    187MB\n"
        "redis        7         117MB"
    )


# ============================================================
# 工具注册表：把工具集中管理，方便 Agent 使用
# ============================================================

def get_tool_list():
    """
    返回所有可用工具及其描述，供 Agent 判断该调用哪个。
    每个工具是一个 dict，包含 name、description 和 parameters（JSON Schema）。
    """
    return [
        {
            "name": "get_pods",
            "description": "查询 Kubernetes 集群的 Pod 列表及状态。不传 namespace 时查询所有命名空间。",
            "parameters": {
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "命名空间名称。留空则查询所有命名空间（推荐，可一次看到全部 Pod）",
                    }
                },
            },
        },
        {
            "name": "get_nodes",
            "description": "查询 Kubernetes 集群的节点列表。",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_container_logs",
            "description": "查看指定 Pod 的容器日志，用于排查故障。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pod_name": {
                        "type": "string",
                        "description": "Pod 名称（必填）",
                    },
                    "namespace": {
                        "type": "string",
                        "description": "命名空间，默认 default",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "返回最后多少行日志，默认 20",
                    },
                },
                "required": ["pod_name"],
            },
        },
        {
            "name": "get_docker_containers",
            "description": "查询本机 Docker 正在运行的容器列表。",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "get_docker_images",
            "description": "查询本机 Docker 镜像列表。",
            "parameters": {"type": "object", "properties": {}},
        },
    ]


def execute_tool(name: str, **kwargs) -> str:
    """
    根据工具名执行对应工具，返回结果字符串。
    这是工具调用的统一入口。
    """
    tools = {
        "get_pods": get_pods,
        "get_nodes": get_nodes,
        "get_container_logs": get_container_logs,
        "get_docker_containers": get_docker_containers,
        "get_docker_images": get_docker_images,
    }
    if name not in tools:
        return f"错误：未知工具 {name}"
    try:
        return tools[name](**kwargs)
    except TypeError as e:
        return f"错误：工具 {name} 参数不正确 - {e}"
