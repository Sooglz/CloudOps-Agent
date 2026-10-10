"""
CloudOps Agent —— 向量检索验证脚本

用途：验证智谱 Embedding + Chroma 向量检索是否正常工作。
填好 .env 里的 ZHIPU_API_KEY 后，运行：
    python test_vector.py

如果一切正常，你会看到：
1. 智谱 Embedding 接口调用成功（返回 1024 维向量）
2. 知识库向量化成功
3. 语义检索能命中正确内容（重点看"语义匹配"效果）
"""

import os

from dotenv import load_dotenv

from rag import KnowledgeBase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DOCS_DIR = os.path.join(BASE_DIR, "..", "data", "docs")


def main() -> None:
    print("=" * 55)
    print("向量检索验证")
    print("=" * 55)

    # 1. 验证智谱 Key 已配置
    if not os.getenv("ZHIPU_API_KEY"):
        print("\n❌ 未检测到 ZHIPU_API_KEY")
        print("   请在 .env 文件中添加：")
        print("   ZHIPU_API_KEY=你的智谱key")
        return

    print("\n[1/3] 测试智谱 Embedding 接口...")
    try:
        from embedding import embed_one
        vec = embed_one("测试文本")
        print(f"      ✅ 成功，向量维度：{len(vec)}")
    except Exception as e:
        print(f"      ❌ 失败：{e}")
        print("      请检查 Key 是否正确、网络是否可达")
        return

    # 2. 构建向量知识库
    print("\n[2/3] 构建向量知识库（向量化所有文档片段）...")
    try:
        kb = KnowledgeBase(DOCS_DIR, retriever_type="vector")
        print(f"      ✅ {kb.stats()}")
    except Exception as e:
        print(f"      ❌ 失败：{e}")
        return

    # 3. 语义检索测试
    print("\n[3/3] 语义检索测试...")
    test_cases = [
        ("Pod 一直 CrashLoopBackOff 怎么办", "应该命中 K8s 故障排查"),
        ("容器崩了怎么查", "应该命中 K8s CrashLoopBackOff（语义匹配）"),
        ("怎么查看 docker 日志", "应该命中 Docker 命令"),
        ("linux 查看内存占用", "应该命中 Linux 命令"),
    ]
    for query, expect in test_cases:
        refs = kb.search(query, top_k=1)
        if refs:
            snippet = refs[0][:60].replace("\n", " ")
            print(f"      Q: {query}")
            print(f"         → {snippet}...")
        else:
            print(f"      Q: {query} → 未命中")

    print("\n验证完成！如果上面的检索结果合理，说明向量检索升级成功 ✅")


if __name__ == "__main__":
    main()
