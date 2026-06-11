#!/usr/bin/env python3
"""
交互式 PDF 语义搜索

用法:
    python interactive_search.py --pdf book.pdf
    python interactive_search.py --pdf book.pdf --verbose
    python interactive_search.py --auto
    python interactive_search.py --chapter "第三章" --pdf book.pdf "辛亥革命"
    python interactive_search.py --pdf book.pdf --batch "Q1" "Q2"
    python interactive_search.py --pdf book.pdf --list-chapters
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_cli_config
from vector_search import PDFVectorSearch
from pdf_structure import get_chapter_tree


def _auto_find_pdf() -> str:
    """自动发现当前目录的 PDF 文件"""
    pdf_files = sorted(Path(".").glob("*.pdf"))
    if not pdf_files:
        return ""
    if len(pdf_files) == 1:
        print(f"📄 自动选择: {pdf_files[0]}")
        return str(pdf_files[0])
    print("📂 发现多个 PDF:")
    for i, f in enumerate(pdf_files, 1):
        print(f"   {i}. {f}")
    choice = input(f"\n请选择 (1-{len(pdf_files)}): ").strip()
    try:
        return str(pdf_files[int(choice) - 1])
    except (ValueError, IndexError):
        print("无效选择")
        return ""


def interactive_mode(searcher: PDFVectorSearch, verbose: bool = False,
                     chapter: str = None, exclude_noise: bool = True):
    """交互式搜索"""
    if chapter:
        print(f"  📖 限定章节: {chapter}")
    print("\n✓ 就绪！输入查询搜索，quit 退出\n")
    while True:
        try:
            query = input("🔍 查询: ").strip()
            if query.lower() in ["quit", "exit", "q", "退出"]:
                print("👋 再见！")
                break
            if not query:
                continue
            result = searcher.search(query, chapter=chapter, exclude_noise=exclude_noise)
            print(f"\n{'='*60}")
            print(result)
            if verbose:
                print("\n--- 详细节点 ---")
                for i, node in enumerate(searcher.retrieve(query, top_k=3,
                          chapter=chapter, exclude_noise=exclude_noise), 1):
                    page = node.metadata.get("page", "?")
                    ch = node.metadata.get("chapter", "")
                    print(f"  [{i}] 页码 {page} [{ch}] (分数: {node.score:.4f})")
                    print(f"  {node.text[:200]}...")
            print("=" * 60 + "\n")
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}\n")


def batch_mode(searcher: PDFVectorSearch, queries: list,
               chapter: str = None, exclude_noise: bool = True):
    """批量搜索"""
    for i, query in enumerate(queries, 1):
        result = searcher.search(query, chapter=chapter, exclude_noise=exclude_noise)
        print(f"\n[{i}/{len(queries)}] {query}")
        print(f"结果: {result[:300]}...")
        print("-" * 40)


def main():
    def extra_args(parser):
        parser.add_argument("--auto", action="store_true", help="自动发现当前目录的 PDF")
        parser.add_argument("query", nargs="?", help="直接搜索（不进入交互模式）")
        parser.add_argument("--batch", nargs="+", help="批量搜索")
        parser.add_argument("--verbose", "-v", action="store_true", help="详细模式（含页码和章节）")
        parser.add_argument("--chapter", help="只搜索指定章节（模糊匹配）")
        parser.add_argument("--include-noise", action="store_true", help="包含噪声页")
        parser.add_argument("--list-chapters", action="store_true", help="列出 PDF 章节结构")

    cfg, args = load_cli_config(description="PDF 语义搜索", extra_args_fn=extra_args)
    exclude_noise = not args.include_noise

    # --auto: 自动发现 PDF
    if args.auto and not cfg.pdf_path:
        pdf = _auto_find_pdf()
        if pdf:
            cfg.pdf_path = pdf
        else:
            print("⚠  未找到 PDF，将加载已有索引")

    # 初始化
    searcher = PDFVectorSearch(cfg)
    if cfg.pdf_path and os.path.exists(cfg.pdf_path):
        print("=" * 60)
        print("📚 PDF 向量搜索系统")
        print("=" * 60)
        searcher.ingest()
    else:
        print("📂 加载已有索引...")
        searcher.load_index()

    # 列出章节
    if args.list_chapters:
        chapters = searcher.list_chapters()
        if chapters:
            print(f"\n📖 文档结构 ({len(chapters)} 个章节):")
            print(get_chapter_tree(chapters))
        else:
            print("\n⚠  未检测到章节结构")
        return

    if args.batch:
        batch_mode(searcher, args.batch, chapter=args.chapter, exclude_noise=exclude_noise)
    elif args.query:
        print(searcher.search(args.query, chapter=args.chapter, exclude_noise=exclude_noise))
    else:
        interactive_mode(searcher, verbose=args.verbose,
                         chapter=args.chapter, exclude_noise=exclude_noise)


if __name__ == "__main__":
    main()
