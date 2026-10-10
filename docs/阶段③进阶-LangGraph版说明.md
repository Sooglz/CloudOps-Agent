# 阶段③进阶：LangGraph 版 Agent（对比手写 ReAct）

这一页讲清楚 LangGraph 版做了什么、和手写版有什么区别、以及面试怎么讲。

---

## 一、为什么要做 LangGraph 版

阶段③的手写版（`src/agent.py`）用 `while` 循环手动实现了 ReAct，目的是**看清每一步**。

LangGraph 版（`src/agent_langgraph.py`）用 **StateGraph 图** 重新编排同样的循环，目的是**理解框架**——这是很多 JD 明确要求的技能（LangGraph/AutoGen/CrewAI 等框架）。

两者功能等价，但实现方式不同，正好能回答面试官那个经典问题：
> 「为什么先手写，再用框架？」

答：**先手写理解原理，再上框架知道它替我做了什么。**

---

## 二、手写版 vs LangGraph 版对照

| 手写版（agent.py） | LangGraph 版（agent_langgraph.py） |
|---|---|
| `self.history` 列表存消息 | `AgentState`（TypedDict）+ `add_messages` |
| `for` 循环迭代 | 图的「环」：agent → tools → agent |
| `if not response.tool_calls` 判断结束 | `tools_condition` 条件边（内置） |
| `_execute()` 逐个执行工具 | `ToolNode` 批量执行 |
| 手动 `append` 维护历史 | 框架自动通过 State 累加（这就是「记忆」） |

核心：**LangGraph 的 `messages` 字段 + `add_messages` reducer，等价于手写版的 `history.append()`**。框架把「状态管理、循环控制、历史记忆」这些手写时要自己维护的东西，抽象成了「图 + 状态」。

---

## 三、图长什么样

```
         ┌─────────────────────────────┐
         │                             │
START ──▶│  agent 节点（调用 LLM）        │
         │                             │
         └───────┬──────────┬──────────┘
                 │          │
        有工具调用 │          │ 无工具调用
                 │          │
                 ▼          ▼
         ┌───────────┐    END（直接回答）
         │ tools 节点 │
         │(ToolNode)  │
         └─────┬─────┘
               │ 执行完回到 agent（形成循环）
               └──────────▶ agent
```

对应代码里：
- `builder.add_node("agent", agent_node)` —— 定义节点
- `builder.add_conditional_edges("agent", tools_condition, ...)` —— 条件边，判断继续还是结束
- `builder.add_edge("tools", "agent")` —— 工具执行完回到 agent，构成循环

---

## 四、怎么跑

```bash
cd D:\Work\CloudOps-Agent\src

# 交互式对话（和 app.py 一样）
..\.venv\Scripts\python.exe agent_langgraph.py

# 固定演示（跑一句需要工具调用的话，展示节点流转，适合截图）
..\.venv\Scripts\python.exe agent_langgraph.py --demo
```

`--demo` 模式会用 `stream` 逐节点打印，你能看到：
1. `[工具调用] get_pods({})` —— agent 节点决策调用了什么工具
2. `[观察结果] ...` —— tools 节点返回的数据
3. 最终回答

---

## 五、关键代码片段（面试可引用）

**定义状态（这就是「记忆」）：**
```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

**两个节点：**
```python
def agent_node(state):        # 节点①：调 LLM
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# 节点②：ToolNode(tools) 自动执行工具并回填结果
```

**组装图：**
```python
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
builder.add_edge("tools", "agent")
```

---

## 六、面试要点

1. **LangGraph 的核心抽象**：State（状态）+ Node（节点）+ Edge（边）。Agent 流程被建模成一张有向图。
2. **状态管理**：`add_messages` reducer 让消息自动累加，天然支持多轮记忆，不用手动维护 history。
3. **`tools_condition`**：LangGraph 内置的条件判断，检查上一条 AI 消息是否带 tool_calls，决定走工具分支还是结束。
4. **`ToolNode`**：自动把 tool_calls 转成实际的工具执行，并把结果写成 ToolMessage 回填。
5. **和手写的区别**：手写要自己管循环边界、历史、中断；LangGraph 还额外提供 checkpoint（持久化状态）、中断恢复、流式输出等，这些是手写要额外实现的能力。
6. **什么时候用框架、什么时候手写**：学习/教学手写；生产/复杂多 Agent 用 LangGraph，因为它有状态持久化、可视化、调试、并行控制等工程能力。
