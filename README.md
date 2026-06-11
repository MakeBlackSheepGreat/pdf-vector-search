# PDF Vector Search

> 基于 LlamaIndex + 硅基流动 Embedding 的通用 PDF 语义搜索引擎。支持任意 PDF 文件的向量化索引、语义查询、复习资料自动页码匹配。

**兼容平台：** Codex · Claude Code · OpenClaw · opencode · Reasonix

## 快速开始

```bash
# 1. 安装（二选一）
#    Unix/macOS
./setup.sh
#    Windows
setup.bat

# 2. 配置 API Key
#    编辑 .env，填入你的 SILICONFLOW_API_KEY

# 3. 构建索引 + 搜索
python build_index.py --pdf your-book.pdf
python interactive_search.py --pdf your-book.pdf
```

30 秒完成安装 → 1 分钟完成首次索引 → 即时语义搜索。

---

## 目录

- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [安装指南](#安装指南)
- [使用说明](#使用说明)
  - [构建索引](#构建索引)
  - [交互式搜索](#交互式搜索)
  - [查询已有索引](#查询已有索引)
  - [复习资料处理](#复习资料处理)
- [配置参考](#配置参考)
- [API 接口](#api-接口)
- [技术栈](#技术栈)
- [License](#license)

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 语义搜索 | 理解查询含义，非关键词匹配 |
| 任意 PDF | 不限学科、不限页数 |
| 持久化索引 | ChromaDB 本地存储，构建一次反复使用 |
| 多种查询模式 | 交互式 / 命令行 / 批量 / 直接 ChromaDB |
| 复习资料处理 | Word 文档 → 问答提取 → 页码匹配 → 格式化输出 |
| 配置灵活 | 命令行参数 / .env 文件 / 环境变量，三级优先级 |
| 中文优化 | 默认 Qwen3-VL-Embedding-8B 中文嵌入模型 |

---

## 项目结构

```
pdf-vector-search/
├── config.py              # 统一配置管理（.api_key + .env + CLI 参数）
├── embedder.py            # 嵌入模型封装（SiliconFlowEmbedding）
├── vector_search.py       # 核心引擎：PDFVectorSearch 类
├── pdf_structure.py       # PDF 结构分析（章节检测、噪声过滤、多栏布局）
├── build_index.py         # 构建向量索引
├── interactive_search.py  # 交互式/命令行搜索
├── query_index.py         # 查询已有索引
├── process_review.py      # 复习资料处理（Word → 页码 → 文档）
├── check.py               # 环境检查工具
├── requirements.txt       # Python 依赖
├── .api_key.example       # API Key 模板（复制为 .api_key）
├── .env.example           # 通用配置模板（复制为 .env）
├── .gitignore             # Git 忽略规则
├── Makefile               # 快捷命令（Unix）
├── setup.sh               # 安装脚本（Unix/macOS）
└── setup.bat              # 安装脚本（Windows）
```

---

## 安装指南

### 前置条件

- Python 3.9+
- 有效的硅基流动 API Key（[获取地址](https://siliconflow.cn/)）

### 方式一：自动安装（推荐）

**Unix / macOS：**
```bash
git clone <repo-url>
cd pdf-vector-search
chmod +x setup.sh
./setup.sh
```

**Windows：**
```cmd
git clone <repo-url>
cd pdf-vector-search
setup.bat
```

脚本会自动：创建虚拟环境 → 安装依赖 → 生成 `.env` 和 `.api_key` 配置文件 → 交互式引导输入 API Key。

### 方式二：手动安装

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
cp .api_key.example .api_key
# 编辑 .api_key，填入你的 SILICONFLOW_API_KEY
```

### 方式三：Makefile

```bash
make setup
```

### 验证安装

```bash
python check.py             # 全部检查
python check.py --deps      # 只检查依赖
python check.py --api       # 测试 API 连通
```

---

## 使用说明

### 构建索引

```bash
# 基本用法
python build_index.py --pdf book.pdf

# 指定集合名和分块参数
python build_index.py --pdf book.pdf --collection my_book --chunk-size 1024

# 管理多个索引
python build_index.py --pdf book1.pdf --collection book1
python build_index.py --pdf book2.pdf --collection book2
```

### 交互式搜索

```bash
# 标准模式（加载 PDF 构建索引后进入交互）
python interactive_search.py --pdf book.pdf

# 详细模式（显示页码和相关段落）
python interactive_search.py --pdf book.pdf --verbose

# 自动发现当前目录的 PDF
python interactive_search.py --auto

# 单次查询
python interactive_search.py --pdf book.pdf "机器学习的基本原理"

# 批量查询
python interactive_search.py --pdf book.pdf --batch "查询1" "查询2" "查询3"

# 加载已有索引（不指定 PDF）
python interactive_search.py
```

### 查询已有索引

```bash
# 基本查询
python query_index.py "你的问题"

# 多个查询
python query_index.py "查询1" "查询2" "查询3"

# 指定集合
python query_index.py --collection my_book "问题"

# 直接使用 ChromaDB（绕过 LlamaIndex）
python query_index.py --direct "问题"

# 列出所有集合
python query_index.py --list-collections
```

### 复习资料处理

从 Word 文档提取问答，自动搜索教材页码，生成格式化文档：

```bash
# 完整流程（提取 + 搜索页码 + 生成文档）
python process_review.py -i 复习资料.docx -o 整理版.docx

# 自定义标题
python process_review.py -i 复习资料.docx -o 整理版.docx --title "数据结构"

# 只整理格式，不搜索页码
python process_review.py -i 复习资料.docx -o 整理版.docx --no-search
```

### Makefile 快捷命令

```bash
make setup                  # 安装依赖
make check                  # 环境检查
make build PDF=book.pdf     # 构建索引
make search PDF=book.pdf    # 交互搜索
make query Q='你的问题'     # 快速查询
make review INPUT=题.docx   # 处理复习资料
make clean                  # 清理缓存和数据库
```

---

## 配置参考

### 三级配置优先级

```
命令行参数  >  .api_key / .env 文件  >  环境变量  >  默认值
```

### 配置文件说明

| 文件 | 用途 | 是否提交到 Git |
|------|------|---------------|
| `.api_key` | API Key 专用（从 `.api_key.example` 复制） | ❌ 已被 .gitignore 保护 |
| `.env` | 通用配置（从 `.env.example` 复制） | ❌ 已被 .gitignore 保护 |

### 配置项一览

| 配置项 | 命令行参数 | 环境变量 | 默认值 |
|--------|-----------|---------|--------|
| API Key | `--api-key` | `SILICONFLOW_API_KEY` | （必填） |
| API 地址 | `--api-base` | `SILICONFLOW_API_BASE` | `https://api.siliconflow.cn/v1` |
| 嵌入模型 | `--embedding-model` | `EMBEDDING_MODEL` | `Qwen/Qwen3-VL-Embedding-8B` |
| PDF 路径 | `--pdf` | `PDF_PATH` | — |
| 集合名称 | `--collection` | `COLLECTION_NAME` | `pdf_collection` |
| 数据库路径 | `--db-path` | `CHROMA_DB_PATH` | `./chroma_db` |
| 分块大小 | `--chunk-size` | `CHUNK_SIZE` | `512` |
| 分块重叠 | `--chunk-overlap` | `CHUNK_OVERLAP` | `50` |
| 返回结果数 | `--top-k` | `TOP_K` | `5` |

### 分块参数建议

| PDF 规模 | chunk_size | chunk_overlap | 说明 |
|----------|-----------|---------------|------|
| 小（<50页） | 256 | 30 | 更精确的匹配 |
| 中（50-200页） | 512 | 50 | 默认，均衡 |
| 大（200+页） | 1024 | 100 | 更完整的上下文 |

---

## API 接口

在 Python 代码中直接使用：

```python
from config import get_config
from vector_search import PDFVectorSearch, direct_query

# 方式 1：从 .env 加载配置，构建索引
cfg = get_config(pdf_path="book.pdf")
searcher = PDFVectorSearch(cfg)
searcher.ingest()

# 搜索
result = searcher.search("你的问题")

# 方式 2：加载已有索引（跳过构建）
searcher = PDFVectorSearch(get_config())
searcher.load_index()

# 获取带页码和分数的原始节点
nodes = searcher.retrieve("问题", top_k=5)
for node in nodes:
    print(f"页码: {node.metadata['page']}, 分数: {node.score:.4f}")

# 方式 3：直接 ChromaDB 查询（绕过 LlamaIndex）
cfg = get_config()
results = direct_query(cfg, "问题", n_results=3)
for r in results:
    print(f"页码: {r['page']}, 距离: {r['distance']:.4f}")
```

### PDFVectorSearch 核心方法

| 方法 | 说明 |
|------|------|
| `ingest(pdf_path=None)` | 加载 PDF + 构建索引（一步完成） |
| `load_index()` | 从已有 ChromaDB 加载索引 |
| `search(query, top_k=None, chapter=None, exclude_noise=True)` | 语义搜索，返回综合回答字符串 |
| `retrieve(query, top_k=None, chapter=None, exclude_noise=True)` | 相似度检索，返回原始节点列表 |
| `load_pdf(pdf_path=None)` | 只加载 PDF，不构建索引 |
| `build_index(documents)` | 从文档列表构建索引 |
| `add_pdf(pdf_path)` | 向已有索引添加新 PDF |
| `list_collections()` | 列出所有集合 |
| `collection_info(name=None)` | 获取集合信息（名称、文档数） |

---

## 技术栈

| 组件 | 用途 |
|------|------|
| [LlamaIndex](https://github.com/run-llama/llama_index) | RAG 框架 |
| [ChromaDB](https://github.com/chroma-core/chroma) | 向量数据库 |
| [硅基流动 API](https://siliconflow.cn/) | Qwen3-VL-Embedding-8B 嵌入模型 |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF 解析 |
| [python-docx](https://python-docx.readthedocs.io/) | Word 文档处理 |

---

## AI Agent 集成

本项目提供 `SKILL.md` 文件，可直接被以下 AI 编程 Agent 加载使用：

| 平台 | 加载方式 |
|------|---------|
| **Codex** | 将项目目录作为 workspace，Agent 自动识别 SKILL.md |
| **Claude Code** | 在项目目录下启动，Agent 可调用所有命令 |
| **OpenClaw** | 导入 SKILL.md 作为 skill 定义 |
| **opencode** | 将项目作为 tool provider 集成 |
| **Reasonix** | `.reasonix/skills/pdf-vector-search/SKILL.md` 自动注册 |

Agent 可通过以下命令操作本项目：

```
构建索引:  python build_index.py --pdf <path>
搜索:      python interactive_search.py --pdf <path> "<query>"
查询:      python query_index.py "<query>"
检查环境:  python check.py
```

---

## License

MIT License
