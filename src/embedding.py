"""
CloudOps Agent —— 智谱 Embedding 封装

用智谱的 OpenAI 兼容接口做文本向量化。
接口地址：https://open.bigmodel.cn/api/paas/v4
模型：embedding-2（向量维度 1024）
"""

import os

from openai import OpenAI


def get_zhipu_embedding(texts):
    """
    调用智谱 Embedding 接口，把文本列表转成向量列表。

    参数：
        texts: 字符串列表

    返回：
        向量列表（每个向量是 1024 维的 float 列表）
    """
    client = OpenAI(
        api_key=os.getenv("ZHIPU_API_KEY"),
        base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
    )

    # 智谱 embedding 接口支持批量输入，但为了简单稳定，这里逐个处理
    # （embedding-2 支持单条或数组输入）
    model = os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-2")

    if isinstance(texts, str):
        texts = [texts]

    vectors = []
    for text in texts:
        resp = client.embeddings.create(model=model, input=text)
        vectors.append(resp.data[0].embedding)

    return vectors


def embed_one(text: str):
    """向量化单个文本，返回一个向量。"""
    return get_zhipu_embedding([text])[0]
