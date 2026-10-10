"""
CloudOps Agent —— 阶段③：工具调用 + RAG 完整版

在阶段②的基础上，新增了「工具调用」能力：
- Agent 不再只是"查资料回答"，而是能真正"动手"执行运维操作（当前为模拟工具）
- 采用 ReAct 循环：思考 → 调用工具 → 观察结果 → 再思考 → 回答

相比阶段②，这里多了核心概念：
1. Function Call（工具调用）—— 大模型输出"要调用哪个工具、传什么参数"
2. ReAct 循环 —— 大模型和工具之间多轮交互，直到得出答案

运行方式：
    python app.py

输入 quit / exit / 退出 可结束对话。
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent import ToolCallingAgent
from rag import KnowledgeBase
from tools import get_tool_list

# 1. 加载配置（明确指定项目根目录的 .env，避免工作目录不同导致找不到）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DOCS_DIR = os.path.join(BASE_DIR, "..", "data", "docs")


def build_llm() -> ChatOpenAI:
    """初始化 DeepSeek 大模型。"""
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0.3,  # 工具调用场景降低温度，让决策更稳定
    )


# 2. 系统提示词：告诉 Agent 它的能力和工具使用规则
SYSTEM_PROMPT = """你是一个云原生运维助手，精通 Linux、Docker、Kubernetes。

你有一组工具可以调用：
- get_pods：查询 Kubernetes 集群的 Pod 列表
- get_nodes：查询 Kubernetes 集群的节点
- get_container_logs：查看指定 Pod 的容器日志
- get_docker_containers：查询本机 Docker 运行中的容器
- get_docker_images：查询本机 Docker 镜像

使用规则：
- 当用户询问集群状态、Pod、节点、日志、Docker 容器/镜像等需要"查询实际环境"的问题时，先调用对应工具获取真实数据，再基于数据回答
- 不要编造数据，如果工具返回了结果，就基于结果回答
- 如果用户的问题不需要工具（比如纯知识问答），直接回答即可
- 回答用简洁、专业的中文"""


def main() -> None:
    llm = build_llm()

    # 3. 准备工具列表
    tools = get_tool_list()

    # 4. 创建带工具调用能力的 Agent
    agent = ToolCallingAgent(llm, tools, system_prompt=SYSTEM_PROMPT)

    print("=" * 50)
    print("CloudOps Agent 已启动（阶段③ 工具调用版）")
    print("可用工具：get_pods / get_nodes / get_container_logs / get_docker_containers / get_docker_images")
    print("输入 quit / exit / 退出 结束对话")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "退出", "q"):
            print("再见！")
            break

        # 5. 交给 Agent 处理（内部会走 思考→工具调用→观察 循环）
        answer = agent.run(user_input)

        print(f"\nAgent > {answer}")


if __name__ == "__main__":
    main()
