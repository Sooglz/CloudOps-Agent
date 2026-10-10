"""
CloudOps Agent —— 阶段③：工具调用 Agent（核心）

实现 Agent 的「思考 → 调用工具 → 观察结果 → 再思考」循环（ReAct）。

关键概念：
1. Function Call（工具调用）：大模型不是只能输出文字，还能输出"我要调用哪个工具、传什么参数"
2. 循环：大模型调用工具后，程序执行工具，把结果再喂回给大模型，让它基于结果继续思考或回答

用法：
    agent = ToolCallingAgent(llm, tools)
    answer = agent.run("集群里有几个 Pod？")
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage


class ToolCallingAgent:
    """
    一个极简的「工具调用 Agent」，手动实现 ReAct 循环。

    之所以不直接用 langchain 内置的 AgentExecutor，是为了让你
    看清楚工具调用的每一步是怎么发生的——这是理解 Agent 的关键。
    """

    def __init__(self, llm, tools, system_prompt: str, max_iterations: int = 5):
        self.llm = llm
        self.tools = tools  # 工具列表（每个工具是 dict，含 name/description）
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

        # 把工具绑定到 llm 上，让大模型"知道"有哪些工具可用
        self.llm_with_tools = llm.bind_tools(
            [self._make_tool_schema(t) for t in tools]
        )

    def _make_tool_schema(self, tool: dict) -> dict:
        """
        把工具的简单描述（name/description/parameters）转成 langchain 的 tool schema。
        这样大模型才知道工具的名字、用途和参数。
        """
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        }

    def run(self, user_input: str) -> str:
        """
        处理用户输入，返回最终回答。
        """
        # 初始消息：系统提示 + 用户问题
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_input),
        ]

        for _ in range(self.max_iterations):
            # 1. 思考：让大模型生成回复（可能是文字答案，也可能是工具调用请求）
            response = self.llm_with_tools.invoke(messages)

            # 2. 判断：大模型是否要求调用工具？
            if not response.tool_calls:
                # 没有工具调用，说明大模型已经能直接回答了
                return response.content

            # 3. 行动：大模型要求调用工具，逐个执行
            messages.append(response)  # 先把 AI 的（含工具调用）消息加进历史

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})

                # 执行工具
                result = self._execute(tool_name, tool_args)

                # 4. 观察：把工具执行结果作为 ToolMessage 加进历史
                messages.append(
                    ToolMessage(
                        content=result,
                        tool_call_id=tool_call["id"],
                    )
                )

            # 循环回到第 1 步，大模型会基于工具结果继续思考

        # 超过最大迭代次数仍未得到答案
        return "抱歉，处理超时了，请换个问法试试。"

    def _execute(self, tool_name: str, tool_args: dict) -> str:
        """执行工具（这里委托给 tools.py 的 execute_tool）。"""
        from tools import execute_tool
        return execute_tool(tool_name, **tool_args)
