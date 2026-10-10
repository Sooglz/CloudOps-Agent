# 阶段② 说明：接入 RAG 检索增强生成

这一页讲清楚阶段②做了什么、怎么跑、以及设计思路。

---

## 一、RAG 是什么

RAG（Retrieval-Augmented Generation，检索增强生成）= **先查资料，再回答**。

普通的对话 Agent 只会用大模型「记住」的知识回答，遇到私有知识（比如你公司的运维手册）就无能为力，还可能瞎编（幻觉）。

RAG 的做法是：回答问题前，先从「知识库」里检索相关内容，把这些内容作为参考资料喂给大模型，让它基于真实资料回答。这样既准确、又能接入私有知识。

## 二、阶段②做了什么

1. **准备知识库文档**：`data/docs/` 下放了 3 篇运维文档
   - `k8s故障排查.md`
   - `docker命令速查.md`
   - `linux运维命令.md`
2. **实现 RAG 链路**：`src/rag.py`
   - 文档加载 → 切分（chunk）→ 检索（retrieve）
   - 检索器做成「可替换接口」，现在是关键词检索，以后可换向量检索
3. **升级对话 Agent**：`src/app.py`
   - 回答前先检索知识库，把结果拼进提示词

## 三、怎么跑

```bash
cd D:\Work\CloudOps-Agent\src
..\.venv\Scripts\python.exe app.py
```

也可以先单独测知识库（不调大模型，快速验证检索效果）：

```bash
..\.venv\Scripts\python.exe build_kb.py
```

## 四、验证 RAG 是否生效

问一个只有知识库里有的问题，看它能否答对：

```
你 > Pod 一直 CrashLoopBackOff 怎么办？
Agent > （应该能答出知识库里的排查步骤，而不是泛泛而谈）
```

对比：如果你用阶段①（不带知识库）问同样的问题，它只能靠大模型自己的知识泛泛回答；现在它能引用你知识库里的**具体排查步骤**，这就是 RAG 的价值。

## 五、关键设计：检索器可替换

这是阶段②最重要的设计，也是面试能讲清楚的亮点：

```python
class Retriever:        # 基类，定义统一接口
    def retrieve(self, query, top_k): ...

class KeywordRetriever(Retriever):   # 关键词检索（先跑通用）
    ...

class VectorRetriever(Retriever):    # 向量检索（已实现，Chroma + 智谱 Embedding）
    ...
```

为什么这么设计：

- **关键词检索**：零依赖、立即能用，先把 RAG 流程跑通、理解透
- **向量检索**：语义匹配更准（问"容器崩了"能匹配到"CrashLoopBackOff"），但需要 Embedding API Key

**已完成的升级**（拿到智谱 Embedding Key 后）：

1. ✅ 装 `chromadb`
2. ✅ 写 `VectorRetriever` 类（`src/rag.py`）
3. ✅ 写智谱 Embedding 封装（`src/embedding.py`）
4. ✅ `KnowledgeBase` 加 `vector` 分支
5. ✅ 默认检索器切换为 `vector`

**其他代码一行都不用改**——这就是"可替换接口"的威力。

### 向量检索的实现细节

- **向量库**：Chroma（本地持久化，存 `chroma_db/` 目录，避免每次重新向量化）
- **Embedding**：智谱 `embedding-2`（1024 维），接口 `https://open.bigmodel.cn/api/paas/v4`
- **相似度**：余弦相似度（cosine）
- **持久化**：首次运行会向量化所有片段并存盘，之后直接加载，不重复调用 Embedding API（省钱）

### 配置智谱 Key

在 `.env` 里加：

```
ZHIPU_API_KEY=你的智谱key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

验证升级是否成功：

```bash
python src/test_vector.py
```

## 六、面试可能被问的点

1. **关键词检索 vs 向量检索的区别**：关键词是字面匹配，向量是语义匹配。
2. **为什么要切分（chunk）**：太长会稀释相关性，太短会切断语义，所以要控制长度+重叠。
3. **top_k 是什么**：检索时返回最相关的几个片段，k 就是数量。
4. **为什么检索结果要"增强"进提示词**：给大模型提供事实依据，减少幻觉。
5. **为什么要持久化向量库**：避免每次启动都重新调用 Embedding API（慢+费钱），存盘后直接加载。
6. **余弦相似度是什么**：衡量两个向量方向的夹角，越接近 1 越相似，与向量长度无关。

