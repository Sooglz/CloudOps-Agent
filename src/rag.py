"""
CloudOps Agent —— 阶段②：RAG 检索增强生成

这个文件实现 RAG 的完整链路：
1. 文档加载与切分（Chunking）
2. 检索（Retriever）—— 目前用关键词检索，后续可无缝升级为向量检索
3. 增强生成（把检索到的内容拼进提示词，交给大模型）

关键设计：检索器被抽象成「可替换接口」。
- 现在的 KeywordRetriever 用关键词匹配，零额外依赖
- 以后拿到 Embedding Key，写一个 VectorRetriever 替换即可，其他代码不用动
"""

import os
import re
from typing import List


# ============================================================
# 一、文档加载与切分
# ============================================================

def load_docs(docs_dir: str) -> List[str]:
    """
    读取知识库目录下的所有 .md 文档，返回每个文档的文本。
    """
    docs = []
    for filename in os.listdir(docs_dir):
        if filename.endswith(".md"):
            path = os.path.join(docs_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                docs.append(f.read())
    return docs


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    把长文本切成小片段（chunk）。

    chunk_size：每个片段的最大字符数
    overlap：相邻片段重叠的字符数（避免切分切断语义）
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ============================================================
# 二、检索器（可替换接口）
# ============================================================

class Retriever:
    """检索器基类，定义统一接口。以后换成向量检索时继承它即可。"""

    def __init__(self, chunks: List[str]):
        self.chunks = chunks

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """根据问题返回最相关的 top_k 个片段。子类需实现。"""
        raise NotImplementedError


class KeywordRetriever(Retriever):
    """
    关键词检索器：把问题和片段都切词，按「命中关键词数量」打分排序。

    优点：零依赖、立即能用，能演示完整 RAG 链路。
    缺点：只能字面匹配，无法理解语义（比如问"容器崩了"匹配不到"CrashLoopBackOff"）。
    """

    def _tokenize(self, text: str) -> set:
        """简单分词：提取中英文单词和数字，忽略停用词。"""
        # 提取英文单词、中文词（按 2 字滑动）、数字
        tokens = set()
        # 英文单词和数字
        for m in re.findall(r"[a-zA-Z0-9]+", text):
            tokens.add(m.lower())
        # 中文：按连续汉字切块
        chinese = re.findall(r"[\u4e00-\u9fff]+", text)
        for phrase in chinese:
            for i in range(len(phrase) - 1):
                tokens.add(phrase[i:i + 2])
        return tokens

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for chunk in self.chunks:
            chunk_tokens = self._tokenize(chunk)
            # 命中关键词数量作为分数
            score = len(query_tokens & chunk_tokens)
            if score > 0:
                scored.append((score, chunk))

        # 按分数降序，取 top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]


# ============================================================
# 三、向量检索器（语义检索，需要 Embedding）
# ============================================================

class VectorRetriever(Retriever):
    """
    向量检索器：用 Chroma 向量数据库 + 智谱 Embedding 做语义检索。

    相比关键词检索的优势：
    - 能理解语义：问"容器崩了"也能匹配到"CrashLoopBackOff"
    - 检索更准确：按语义相似度排序，而不是字面命中数
    """

    def __init__(self, chunks: List[str], persist_dir: str = "./chroma_db"):
        import chromadb
        from embedding import get_zhipu_embedding

        self.chunks = chunks
        self._embed = get_zhipu_embedding

        # 创建 Chroma 客户端（持久化到磁盘，避免每次重新向量化）
        self.client = chromadb.PersistentClient(path=persist_dir)

        # 获取或创建集合（collection 相当于一个"表"）
        self.collection = self.client.get_or_create_collection(
            name="cloudops_docs",
            metadata={"hnsw:space": "cosine"},  # 用余弦相似度
        )

        # 判断是否已向量化过（集合里已有数据就不用重复计算）
        if self.collection.count() == 0:
            self._build_index()

    def _build_index(self):
        """把知识库片段向量化并写入 Chroma。"""
        ids = [f"chunk_{i}" for i in range(len(self.chunks))]
        embeddings = self._embed(self.chunks)

        self.collection.add(
            ids=ids,
            documents=self.chunks,
            embeddings=embeddings,
        )

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        # 把问题向量化，再在 Chroma 里做相似度检索
        query_embedding = self._embed([query])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        # results["documents"] 是 [[doc1, doc2, ...]] 这样的嵌套结构
        docs = results.get("documents", [[]])[0]
        return docs


# ============================================================
# 四、知识库封装
# ============================================================

class KnowledgeBase:
    """
    知识库：负责加载文档、切分、并提供检索入口。
    """

    def __init__(self, docs_dir: str, retriever_type: str = "keyword"):
        raw_docs = load_docs(docs_dir)
        self.chunks = []
        for doc in raw_docs:
            self.chunks.extend(chunk_text(doc))

        # 这里就是「可替换」的关键：根据类型选择检索器
        if retriever_type == "keyword":
            self.retriever = KeywordRetriever(self.chunks)
        elif retriever_type == "vector":
            self.retriever = VectorRetriever(self.chunks)
        else:
            raise ValueError(f"未知的检索器类型: {retriever_type}")

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """对外统一检索接口。"""
        return self.retriever.retrieve(query, top_k=top_k)

    def stats(self) -> str:
        """返回知识库的统计信息，便于调试。"""
        return f"知识库已加载 {len(self.chunks)} 个片段"
