#!/usr/bin/env python3
"""
查询已有索引

用法:
    python query_index.py "查询内容"
    python query_index.py --chapter "第三章" "辛亥革命"
    python query_index.py --list-chapters
    python query_index.py --list-collections
    python query_index.py --direct "查询"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_cli_config
from vector_search import PDFVectorSearch, direct_query
from pdf_structure import get_chapter_tree


def main():
    def extra_args(parser):
        parser.add_argument("queries", nargs="*", help="查询列表")
        parser.add_argument("--list-collections", action="store_true", help="列出所有集合")
        parser.add_argument("--list-chapters", action="store_true", help="列出 PDF 章节结构")
        parser.add_argument("--direct", action="store_true", help="直接 ChromaDB 查询")
        parser.add_argument("--chapter", help="只搜索指定章节（模糊匹配）")
        parser.add_argument("--include-noise", action="store_true", help="包含噪声页（导言/目录等）")
        parser.add_argument("--pdf", help="PDF 文件路径（用于 --list-chapters）")

    cfg, args = load_cli_config(description="查询已有向量索引", extra_args_fn=extra_args)
    exclude_noise = not args.include_noise

    # 列出章节
    if args.list_chapters:
        searcher = PDFVectorSearch(cfg)
        chapters = searcher.list_chapters(args.pdf)
        if chapters:
            print(f"📖 文档结构 ({len(chapters)} 个章节):")
            print(get_chapter_tree(chapters))
        else:
            print("⚠  未检测到章节结构")
        return

    # 列出集合
    if args.list_collections:
        searcher = PDFVectorSearch(cfg)
        print("📂 集合列表:")
        for name in searcher.list_collections():
            info = searcher.collection_info(name)
            print(f"  - {name} ({info['count']} 条)")
        return

    if not args.queries:
        print("请提供查询，例如: python query_index.py '你的问题'")
        return

    sep = "=" * 60
    if args.direct:
        for query in args.queries:
            results = direct_query(cfg, query, n_results=5,
                                   chapter=args.chapter, exclude_noise=exclude_noise)
            print(f"\n{sep}\n查询: {query}\n{sep}")
            for i, item in enumerate(results, 1):
                ch_info = f" [{item['chapter']}]" if item['chapter'] else ""
                print(f"\n--- 结果 {i} (页码: {item['page']}{ch_info}, 距离: {item['distance']:.4f}) ---")
                print(item["text"][:500])
    else:
        searcher = PDFVectorSearch(cfg)
        searcher.load_index()
        for query in args.queries:
            nodes = searcher.retrieve(query, top_k=5,
                                      chapter=args.chapter, exclude_noise=exclude_noise)
            print(f"\n{sep}\n查询: {query}\n{sep}")
            for i, node in enumerate(nodes, 1):
                page = node.metadata.get("page", "?")
                ch = node.metadata.get("chapter", "")
                ch_info = f" [{ch}]" if ch else ""
                print(f"\n--- 结果 {i} (页码: {page}{ch_info}, 分数: {node.score:.4f}) ---")
                print(node.text[:500])


if __name__ == "__main__":
    main()
