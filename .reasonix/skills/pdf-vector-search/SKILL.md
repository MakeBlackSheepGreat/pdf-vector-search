---
name: pdf-vector-search
description: 通用 PDF 语义搜索引擎 — 支持任意 PDF 的向量化索引、语义查询、复习资料页码匹配
compatibility:
  - Codex
  - Claude Code
  - OpenClaw
  - opencode
  - Reasonix
allowed_tools:
  - read_file
  - write_file
  - bash
  - edit_file
  - glob
  - grep
---

# PDF Vector Search

通用 PDF 语义搜索引擎。基于 LlamaIndex + 硅基流动 Embedding，支持任意 PDF 文件。

兼容平台：Codex · Claude Code · OpenClaw · opencode · Reasonix

## 能力

- 对任意 PDF 构建 ChromaDB 向量索引
- 语义搜索（理解含义，非关键词匹配）
- 交互式 / 命令行 / 批量查询
- 复习资料自动页码匹配 + Word 文档生成
- 多索引管理（同时索引多本 PDF）

## 安装

```bash
./setup.sh          # Unix/macOS（交互式引导输入 API Key）
setup.bat           # Windows（交互式引导输入 API Key）
make setup          # Makefile
```

安装过程中会提示输入硅基流动 API Key，也可稍后编辑 `.api_key` 文件。

## 使用方式

### 构建索引

```bash
python build_index.py --pdf <pdf_path> [--collection <name>] [--chunk-size <n>]
```

### 搜索

```bash
# 交互式
python interactive_search.py --pdf <pdf_path>

# 限定章节搜索（消除跨章污染）
python interactive_search.py --pdf <pdf_path> --chapter "第三章"

# 查看 PDF 章节结构
python interactive_search.py --pdf <pdf_path> --list-chapters

# 单次查询
python interactive_search.py --pdf <pdf_path> "<query>"

# 批量
python interactive_search.py --pdf <pdf_path> --batch "Q1" "Q2"

# 详细模式（含页码和章节）
python interactive_search.py --pdf <pdf_path> --verbose
```

### 查询已有索引

```bash
python query_index.py "<query>"
python query_index.py --collection <name> "<query>"
python query_index.py --list-collections
python query_index.py --direct "<query>"
```

### 复习资料处理

```bash
python process_review.py -i <input.docx> -o <output.docx> --title "<title>"
```

## 配置

优先级：CLI 参数 > .api_key > .env > 环境变量 > 默认值

关键配置项：
- `SILICONFLOW_API_KEY` — API Key（必填，存储在 `.api_key` 文件中）
- `COLLECTION_NAME` — 集合名称
- `CHUNK_SIZE` — 分块大小（默认 512，大文件建议 1024）
- `TOP_K` — 返回结果数（默认 5）

## 环境检查

```bash
python check.py
```

## 注意事项

- **章节过滤**：使用 `--chapter "第三章"` 可消除跨章节污染，只返回指定章节的内容
- **噪声排除**：导言、目录、附录等页面自动检测并排除（`--include-noise` 可保留）
- **自动章节检测**：索引时自动识别中文章节标题（第X章/第X节），支持 OCR 错别字容错
- **PDF 加载**：使用 PyMuPDF 逐页提取，确保每页独立文档和正确页码
- API Key 存储在 `.api_key` 文件中（已被 .gitignore 保护，不会提交到版本控制）
- 首次构建索引需要调用嵌入 API，大 PDF 可能需要几分钟
- 索引缓存在 `./chroma_db/`，后续加载直接使用缓存
