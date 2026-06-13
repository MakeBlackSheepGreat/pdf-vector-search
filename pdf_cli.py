#!/usr/bin/env python3
"""
PDF 向量搜索 — Agent 专用 CLI

所有输出为 JSON，无交互，Agent 直接调用。

子命令:
    build    构建索引
    search   语义搜索
    chapters 列出章节结构
    read     读取指定页面文本
    collections 列出/删除集合
    check    环境检查

用法:
    python pdf_cli.py build --pdf book.pdf
    python pdf_cli.py search "查询内容" --chapter "第三章"
    python pdf_cli.py chapters --pdf book.pdf
    python pdf_cli.py read --pdf book.pdf --pages 1,2,10-15
    python pdf_cli.py collections
    python pdf_cli.py check
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _json_output(data):
    """输出 JSON 到 stdout"""
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    # 确保所有字符串都是 UTF-8 安全的
    output = json.dumps(data, ensure_ascii=False, indent=2)
    sys.stdout.buffer.write(output.encode('utf-8'))
    sys.stdout.buffer.write(b'\n')
    sys.stdout.buffer.flush()


def _error(msg, code=1):
    """输出错误并退出"""
    _json_output({"ok": False, "error": msg})
    sys.exit(code)


def _parse_pages(spec: str, total: int) -> list:
    """解析页码规格: '1,2,5-10' → [1,2,5,6,7,8,9,10]"""
    pages = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    return [p for p in pages if 1 <= p <= total]


# ── 子命令 ─────────────────────────────────────────────────

def cmd_build(args):
    """构建索引"""
    from config import get_config
    from vector_search import PDFVectorSearch

    cfg = get_config(
        pdf_path=args.pdf,
        collection_name=args.collection or "pdf_collection",
        chunk_size=args.chunk_size or 512,
        chunk_overlap=args.chunk_overlap or 50,
    )
    cfg.validate(require_pdf=True)

    searcher = PDFVectorSearch(cfg)
    searcher.ingest()

    info = searcher.collection_info()
    _json_output({
        "ok": True,
        "action": "build",
        "collection": info["name"],
        "vectors": info["count"],
        "db_path": cfg.db_path,
    })


def cmd_search(args):
    """语义搜索"""
    from config import get_config
    from vector_search import PDFVectorSearch, direct_query

    cfg = get_config(
        collection_name=args.collection or "pdf_collection",
        top_k=args.top_k or 5,
    )
    cfg.validate()

    if args.direct:
        results = direct_query(
            cfg, args.query,
            n_results=args.top_k or 5,
            chapter=args.chapter,
            exclude_noise=not args.include_noise,
        )
        _json_output({
            "ok": True,
            "action": "search",
            "mode": "direct",
            "query": args.query,
            "chapter_filter": args.chapter,
            "results": results,
        })
    else:
        # 抑制 LlamaIndex 的 print 输出
        import io
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = io.StringIO()

        searcher = PDFVectorSearch(cfg)
        searcher.load_index()

        nodes = searcher.retrieve(
            args.query,
            top_k=args.top_k or 5,
            chapter=args.chapter,
            exclude_noise=not args.include_noise,
        )

        sys.stdout, sys.stderr = old_stdout, old_stderr

        results = []
        for node in nodes:
            results.append({
                "text": node.text,
                "page": node.metadata.get("page", "?"),
                "chapter": node.metadata.get("chapter", ""),
                "section": node.metadata.get("section", ""),
                "score": round(node.score, 4),
            })

        _json_output({
            "ok": True,
            "action": "search",
            "mode": "llamaindex",
            "query": args.query,
            "chapter_filter": args.chapter,
            "results": results,
        })


def cmd_chapters(args):
    """列出章节结构"""
    from config import get_config
    from vector_search import PDFVectorSearch
    from pdf_structure import get_chapter_tree

    cfg = get_config(
        pdf_path=args.pdf,
        collection_name=args.collection or "pdf_collection",
    )
    cfg.validate()

    searcher = PDFVectorSearch(cfg)
    chapters = searcher.list_chapters(args.pdf)

    tree = get_chapter_tree(chapters) if chapters else ""

    _json_output({
        "ok": True,
        "action": "chapters",
        "pdf": args.pdf or cfg.pdf_path,
        "count": len(chapters),
        "chapters": chapters,
        "tree": tree,
    })


def cmd_read(args):
    """读取指定页面文本"""
    import fitz
    from config import get_config
    from pdf_structure import analyze_pdf_structure, detect_headers_footers, extract_page_text

    cfg = get_config(pdf_path=args.pdf)
    cfg.validate(require_pdf=True)

    pdf = fitz.open(cfg.pdf_path)
    total = pdf.page_count

    pages = _parse_pages(args.pages, total)
    headers, footers = detect_headers_footers(pdf)
    page_infos, _ = analyze_pdf_structure(cfg.pdf_path)

    results = []
    for p in pages:
        idx = p - 1
        text = extract_page_text(pdf, idx, remove_headers=headers, remove_footers=footers)
        info = page_infos[idx] if idx < len(page_infos) else None
        results.append({
            "page": p,
            "text": text,
            "chapter": info.chapter if info else "",
            "section": info.section if info else "",
            "is_noise": info.is_noise if info else False,
        })

    pdf.close()

    _json_output({
        "ok": True,
        "action": "read",
        "pdf": cfg.pdf_path,
        "total_pages": total,
        "requested": pages,
        "pages": results,
    })


def cmd_collections(args):
    """列出或删除集合"""
    from config import get_config
    from vector_search import PDFVectorSearch

    cfg = get_config(db_path=args.db_path or "./chroma_db")
    cfg.validate()

    searcher = PDFVectorSearch(cfg)

    if args.delete:
        searcher.delete_collection(args.delete)
        _json_output({"ok": True, "action": "delete_collection", "name": args.delete})
    else:
        cols = []
        for name in searcher.list_collections():
            info = searcher.collection_info(name)
            cols.append(info)
        _json_output({"ok": True, "action": "list_collections", "collections": cols})


def cmd_check(args):
    """环境检查"""
    results = {}

    # 依赖包
    deps = {}
    for mod, name in [
        ("llama_index", "LlamaIndex"),
        ("chromadb", "ChromaDB"),
        ("requests", "Requests"),
        ("fitz", "PyMuPDF"),
        ("dotenv", "python-dotenv"),
    ]:
        try:
            __import__(mod)
            deps[name] = True
        except ImportError:
            deps[name] = False
    results["dependencies"] = deps

    # 配置
    try:
        from config import get_config
        cfg = get_config()
        results["config"] = {
            "api_key_set": bool(cfg.api_key),
            "api_base": cfg.api_base,
            "embedding_model": cfg.embedding_model,
            "db_path": cfg.db_path,
        }
    except Exception as e:
        results["config"] = {"error": str(e)}

    # API 连通
    if results.get("config", {}).get("api_key_set"):
        try:
            import requests
            cfg = get_config()
            resp = requests.post(
                f"{cfg.api_base}/embeddings",
                headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
                json={"input": "test", "model": cfg.embedding_model},
                timeout=10,
            )
            results["api"] = {
                "reachable": resp.status_code == 200,
                "status_code": resp.status_code,
            }
        except Exception as e:
            results["api"] = {"reachable": False, "error": str(e)}
    else:
        results["api"] = {"reachable": False, "error": "API Key not set"}

    # ChromaDB
    try:
        import chromadb
        from config import get_config
        cfg = get_config()
        client = chromadb.PersistentClient(path=cfg.db_path)
        cols = client.list_collections()
        results["chromadb"] = {
            "accessible": True,
            "collections": [c.name for c in cols],
        }
    except Exception as e:
        results["chromadb"] = {"accessible": False, "error": str(e)}

    all_ok = (
        all(deps.values())
        and results.get("config", {}).get("api_key_set", False)
        and results.get("api", {}).get("reachable", False)
        and results.get("chromadb", {}).get("accessible", False)
    )

    _json_output({"ok": all_ok, "action": "check", "details": results})


# ── 主入口 ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PDF 向量搜索 — Agent 专用 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = sub.add_parser("build", help="构建索引")
    p_build.add_argument("--pdf", required=True, help="PDF 文件路径")
    p_build.add_argument("--collection", help="集合名称")
    p_build.add_argument("--chunk-size", type=int, help="分块大小")
    p_build.add_argument("--chunk-overlap", type=int, help="分块重叠")

    # search
    p_search = sub.add_parser("search", help="语义搜索")
    p_search.add_argument("query", help="查询文本")
    p_search.add_argument("--collection", help="集合名称")
    p_search.add_argument("--chapter", help="限定章节（模糊匹配）")
    p_search.add_argument("--top-k", type=int, help="返回结果数")
    p_search.add_argument("--direct", action="store_true", help="直接 ChromaDB 查询")
    p_search.add_argument("--include-noise", action="store_true", help="包含噪声页")

    # chapters
    p_chapters = sub.add_parser("chapters", help="列出章节结构")
    p_chapters.add_argument("--pdf", help="PDF 文件路径")
    p_chapters.add_argument("--collection", help="集合名称")

    # read
    p_read = sub.add_parser("read", help="读取指定页面文本")
    p_read.add_argument("--pdf", required=True, help="PDF 文件路径")
    p_read.add_argument("--pages", required=True, help="页码规格: 1,2,5-10")

    # collections
    p_cols = sub.add_parser("collections", help="列出/删除集合")
    p_cols.add_argument("--db-path", help="数据库路径")
    p_cols.add_argument("--delete", help="删除指定集合")

    # check
    sub.add_parser("check", help="环境检查")

    args = parser.parse_args()

    commands = {
        "build": cmd_build,
        "search": cmd_search,
        "chapters": cmd_chapters,
        "read": cmd_read,
        "collections": cmd_collections,
        "check": cmd_check,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        _error(str(e))


if __name__ == "__main__":
    main()
