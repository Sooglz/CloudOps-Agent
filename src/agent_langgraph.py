"""
CloudOps Agent —— 阶段③进阶：LangGraph 版工具调用 Agent

用 LangGraph 的 StateGraph 重写 ReAct 循环，与手写版（agent.py）形成对比。

为什么单独做这一版：
- 手写版（agent.py）用 while 循环自己管理 ReAct，让你看清每一步
- LangGraph 版把「思考 → 调工具 → 观察」建模成一张「图」，节点+边清晰可见
- 面试加分点：能讲清楚「框架替你做了什么」——状态管理、循环控制、
  历史记忆、中断/恢复，这些手写时要自己维护，LangGraph 用 State + 图 自动搞定

关键概念对照：
  手写版 while 循环        LangGraph 版
  ─────────────────        ──────────────
  self.history 列表        State（TypedDict，含 messages 字段）
  for 循环迭代             graph 的「环」（agent → tools → agent）
  if 判断是否继续          条件边（conditional edge）
  _execute 逐个执行         tool 节点 + ToolNode 批量执行

用法：
    python agent_langgraph.py          # 交互式对话
    python agent_langgraph.py --demo   # 跑一段固定演示（适合截图）
"""

import os
import sys
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from tools import get_tool_list, execute_tool

# 1. 加载配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ============================================================
# 定义「状态」：LangGraph 的核心，图里的所有节点共享这个状态
# ============================================================

class AgentState(TypedDict):
    """
    图的状态。messages 是核心字段，用 add_messages 做「累加」而非覆盖，
    等价于手写版 self.history 的 append 操作——这就是 LangGraph 的「记忆」机制。
    """
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================
# 构建 LLM + 工具
# ============================================================

def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=0.3,
    )


# 把工具列表转成 LangChain 工具（能直接被 bind_tools / ToolNode 使用）
def _to_langchain_tools():
    from langchain_core.tools import StructuredTool
    lc_tools = []
    for t in get_tool_list():
        name = t["name"]
        desc = t["description"]

        def _make_fn(nm):
            # 闭包捕获工具名，避免循环变量延迟绑定
            def fn(**kwargs):
                return execute_tool(nm, **kwargs)
            return fn

        lc_tools.append(StructuredTool.from_function(
            func=_make_fn(name),
            name=name,
            description=desc,
        ))
    return lc_tools


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


# ============================================================
# 定义节点
# ============================================================

def agent_node(state: AgentState):
    """
    节点①：调用 LLM。LLM 决定是「直接回答」还是「请求调用工具」。
    返回的消息会通过 add_messages 追加进 state["messages"]。
    """
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# ============================================================
# 组装图
# ============================================================

def build_graph():
    """
    图结构：
        START → agent_node ──(无工具调用)──→ END
                        └──(有工具调用)──→ tools_node → agent_node（形成环）
    """
    builder = StateGraph(AgentState)

    # 两个节点
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))

    # 边：从 START 进入 agent 节点
    builder.add_edge(START, "agent")

    # 条件边：agent 节点之后，根据「是否有工具调用」决定去向
    # tools_condition 是 LangGraph 内置的判断器，等价于手写版里的
    #   if not response.tool_calls: 返回最终答案
    #   else: 去执行工具
    builder.add_conditional_edges(
        "agent",
        tools_condition,  # 返回 "tools" 或 END
        {"tools": "tools", END: END},
    )

    # tools 节点执行完，回到 agent 节点（这就是「循环」，等价于手写版的 for 循环）
    builder.add_edge("tools", "agent")

    return builder.compile()


# ============================================================
# 入口
# ============================================================

def _init_global():
    """初始化全局的 llm_with_tools 和 tools（模块级，供节点函数使用）。"""
    global llm_with_tools, tools
    llm = build_llm()
    tools = _to_langchain_tools()
    llm_with_tools = llm.bind_tools(tools)


def run_demo(graph):
    """固定演示：跑一个需要工具调用的问句，展示图的工作过程。"""
    print("=" * 56)
    print("LangGraph 版 Agent 演示（工具调用）")
    print("=" * 56)

    questions = [
        "集群里有哪些 Pod？",
    ]

    for q in questions:
        print(f"\n你 > {q}")
        print("-" * 56)
        # 初始状态：只有系统提示 + 用户问题
        initial_state = {
            "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=q)]
        }
        # stream 模式能看到每一步节点的流转（agent → tools → agent → END）
        for event in graph.stream(initial_state, stream_mode="values"):
            msgs = event["messages"]
            last = msgs[-1]
            # 打印工具调用节点，展示「Agent 决策调用了什么工具」
            if hasattr(last, "tool_calls") and last.tool_calls:
                for tc in last.tool_calls:
                    print(f"  [工具调用] {tc['name']}({tc.get('args', {})})")
            elif last.type == "tool":
                # 工具返回结果（截断显示）
                content = last.content[:120].replace("\n", " ")
                print(f"  [观察结果] {content}...")
        # 打印最终回答
        final = graph.invoke(initial_state)
        answer = final["messages"][-1].content
        print(f"\nAgent > {answer}")


def main():
    _init_global()
    graph = build_graph()

    if "--demo" in sys.argv:
        run_demo(graph)
        return

    print("=" * 56)
    print("CloudOps Agent 已启动（LangGraph 版）")
    print("可用工具：get_pods / get_nodes / get_container_logs / get_docker_containers / get_docker_images")
    print("输入 quit / exit / 退出 结束对话")
    print("=" * 56)

    # 多轮对话：持续把消息追加进同一个「线程」状态，这就是 LangGraph 的记忆
    # 这里用一个简单的列表保存历史消息，模拟多轮记忆（等价于手写版 self.history）
    thread_messages = [SystemMessage(content=SYSTEM_PROMPT)]

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

        thread_messages.append(HumanMessage(content=user_input))
        result = graph.invoke({"messages": thread_messages})
        # 用返回的完整消息更新历史，实现多轮记忆
        thread_messages = result["messages"]
        answer = result["messages"][-1].content

        print(f"\nAgent > {answer}")


if __name__ == "__main__":
    main()
