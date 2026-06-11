#!/usr/bin/env python3
"""
构建 PDF 向量索引

用法:
    python build_index.py --pdf your-book.pdf
    python build_index.py --pdf your-book.pdf --collection my_book --chunk-size 1024
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_cli_config
from vector_search import PDFVectorSearch


def main():
    cfg, _ = load_cli_config(description="从 PDF 构建向量索引", require_pdf=True)

    searcher = PDFVectorSearch(cfg)
    searcher.ingest()

    info = searcher.collection_info()
    print(f"\n✅ 索引构建完成！集合 '{info['name']}' 包含 {info['count']} 条向量")
    print(f"   数据库路径: {cfg.db_path}")


if __name__ == "__main__":
    main()
