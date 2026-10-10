"""
CloudOps Agent —— 知识库构建脚本

用途：把 data/docs 目录下的文档加载、切分、构建成知识库，
并打印统计信息和检索测试结果，方便你验证知识库是否正常工作。

运行方式：
    python build_kb.py

这个脚本独立于 app.py，方便你单独调试知识库。
"""

import os

from dotenv import load_dotenv

from rag import KnowledgeBase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DOCS_DIR = os.path.join(BASE_DIR, "..", "data", "docs")


def main() -> None:
    print("=" * 50)
    print("CloudOps Agent 知识库构建")
    print("=" * 50)

    # 构建知识库（retriever_type 可选 "keyword" 或 "vector"）
    kb = KnowledgeBase(DOCS_DIR, retriever_type="vector")
    print(kb.stats())
    print()

    # 交互式检索测试
    print("输入问题测试检索效果（输入 quit 退出）：")
    while True:
        try:
            query = input("\n检索 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "退出", "q"):
            print("退出")
            break

        refs = kb.search(query, top_k=3)
        if not refs:
            print("未检索到相关内容")
            continue

        print(f"检索到 {len(refs)} 段相关内容：\n")
        for i, ref in enumerate(refs):
            print(f"--- 片段 {i + 1} ---")
            print(ref[:200].replace("\n", " "))
            print()


if __name__ == "__main__":
    main()
