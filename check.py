#!/usr/bin/env python3
"""
环境检查脚本 — 合并 verify / test / quick-start 的功能

用法:
    python check.py          # 运行全部检查
    python check.py --api    # 只检查 API 连通
    python check.py --db     # 只检查 ChromaDB
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── 检查函数 ───────────────────────────────────────────────

def check_files():
    """检查必要的项目文件"""
    print("📁 项目文件...")
    required = ["vector_search.py", "config.py", "interactive_search.py",
                 "requirements.txt", ".env.example", ".api_key.example"]
    ok = True
    for f in required:
        exists = Path(f).exists()
        print(f"  {'✓' if exists else '✗'} {f}" + ("" if exists else " (缺失)"))
        ok &= exists
    return ok


def check_env():
    """检查 .api_key 和 .env 配置"""
    print("⚙️  配置...")
    key_path = Path(".api_key")
    env_path = Path(".env")
    has_key_file = key_path.exists()
    has_env_file = env_path.exists()

    if not has_key_file and not has_env_file:
        print("  ⚠  .api_key 和 .env 文件均不存在")
        print("     请复制 .api_key.example 为 .api_key 并填入 API Key")
        return False

    if has_key_file:
        print("  ✓ .api_key 存在")
    if has_env_file:
        print("  ✓ .env 存在")

    try:
        from config import get_config
        cfg = get_config()
        if cfg.api_key:
            masked = cfg.api_key[:4] + "****" + cfg.api_key[-4:] if len(cfg.api_key) > 8 else "****"
            print(f"  ✓ API Key: {masked}")
            return True
        print("  ⚠  API Key 未设置")
        return False
    except Exception as e:
        print(f"  ✗ 加载失败: {e}")
        return False


def check_packages():
    """检查 Python 依赖"""
    print("📦 依赖包...")
    ok = True
    for module, name in [
        ("llama_index", "LlamaIndex"),
        ("chromadb", "ChromaDB"),
        ("requests", "Requests"),
        ("fitz", "PyMuPDF"),
        ("dotenv", "python-dotenv"),
    ]:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} (未安装)")
            ok = False
    return ok


def check_api():
    """测试 API 连通"""
    print("🔗 API 连通...")
    try:
        import requests
        from config import get_config
        cfg = get_config()
        if not cfg.api_key:
            print("  ⚠  跳过（API Key 未设置）")
            return True
        resp = requests.post(
            f"{cfg.api_base}/embeddings",
            headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
            json={"input": "测试", "model": cfg.embedding_model},
            timeout=10,
        )
        if resp.status_code == 200:
            dim = len(resp.json()["data"][0]["embedding"])
            print(f"  ✓ 成功，向量维度: {dim}")
            return True
        print(f"  ✗ HTTP {resp.status_code}")
        return False
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def check_chromadb():
    """检查 ChromaDB 集合"""
    print("💾 ChromaDB...")
    try:
        import chromadb
        from config import get_config
        cfg = get_config()
        client = chromadb.PersistentClient(path=cfg.db_path)
        cols = client.list_collections()
        if cols:
            print(f"  ✓ {len(cols)} 个集合:")
            for c in cols:
                coll = client.get_collection(c.name)
                print(f"    - {c.name} ({coll.count()} 条)")
        else:
            print("  ⚠  无集合（需要先构建索引）")
        return True
    except Exception as e:
        print(f"  ✗ {e}")
        return False


# ── 主函数 ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PDF 向量搜索系统 — 环境检查")
    parser.add_argument("--api", action="store_true", help="只检查 API 连通")
    parser.add_argument("--db", action="store_true", help="只检查 ChromaDB")
    parser.add_argument("--deps", action="store_true", help="只检查依赖包")
    args = parser.parse_args()

    print("=" * 50)
    print("PDF 向量搜索系统 — 环境检查")
    print("=" * 50)

    if args.api:
        ok = check_api()
    elif args.db:
        ok = check_chromadb()
    elif args.deps:
        ok = check_packages()
    else:
        # 全部检查
        checks = [
            ("文件", check_files()),
            ("依赖", check_packages()),
            ("配置", check_env()),
            ("API", check_api()),
            ("ChromaDB", check_chromadb()),
        ]
        print(f"\n{'='*50}")
        print("结果:")
        print("=" * 50)
        for name, result in checks:
            print(f"  {name}: {'✓' if result else '✗'}")
        ok = all(r for _, r in checks)

    if ok:
        print("\n✅ 通过")
    else:
        print("\n❌ 有问题，请按提示修复")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
