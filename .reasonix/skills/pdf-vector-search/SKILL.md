---
name: pdf-vector-search
description: PDF 语义搜索引擎 — 对任意 PDF 构建向量索引，支持语义搜索、章节结构提取、指定页面读取
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

对任意 PDF 文件构建语义索引，支持按语义搜索内容、提取章节结构、读取指定页面。

## 何时使用

- 用户要求读取/分析/总结 PDF 文件内容
- 用户要求在 PDF 中搜索特定信息
- 用户要求提取 PDF 的目录/章节结构
- 用户要求对比 PDF 中不同章节的内容

## 入口

所有操作通过一个 CLI 入口：`python pdf_cli.py <command>`

所有输出为 JSON，字段 `"ok": true/false` 表示成功/失败。

## 命令

### 环境检查

```bash
python pdf_cli.py check
```

返回 `{ok, details: {dependencies, config, api, chromadb}}`。

首次使用前必须确保 `ok: true`。如果 `api_key_set: false`，提示用户编辑 `.api_key` 文件。

### 构建索引

```bash
python pdf_cli.py build --pdf <path> [--collection <name>] [--chunk-size <n>]
```

首次对 PDF 使用时必须先构建。大 PDF 可能需要几分钟。

返回 `{ok, collection, vectors, db_path}`。

已有同名集合时会覆盖。

### 搜索

```bash
python pdf_cli.py search "<query>" [--chapter "第三章"] [--top-k 5] [--direct]
```

返回 `{ok, results: [{text, page, chapter, section, score}]}`。

- `--chapter`：限定章节范围，模糊匹配 chapter/section/subsection 字段
- `--top-k`：返回结果数（默认 5）
- `--direct`：绕过 LlamaIndex，直接 ChromaDB 查询（更快，返回 distance 而非 score）
- `--include-noise`：包含噪声页（目录/索引/参考文献）

### 章节结构

```bash
python pdf_cli.py chapters --pdf <path>
```

返回 `{ok, count, chapters: [{title, page, level}], tree}`。

`tree` 是缩进格式的章节树文本，可直接展示给用户。

### 读取指定页面

```bash
python pdf_cli.py read --pdf <path> --pages 1,2,10-15
```

返回 `{ok, total_pages, requested, pages: [{page, text, chapter, section, is_noise}]}`。

用于需要精确获取某几页完整文本的场景。

### 集合管理

```bash
python pdf_cli.py collections                    # 列出所有集合
python pdf_cli.py collections --delete <name>    # 删除集合
```

## 典型工作流

### 用户要求"读一下这本书"

```
1. check         → 确认环境正常
2. build --pdf   → 构建索引（如果还没有）
3. chapters --pdf → 获取章节结构，展示给用户
4. search "..."  → 根据用户问题搜索
```

### 用户要求"总结第3章"

```
1. search "第三章" --chapter "第三章" --top-k 10
2. 将返回的文本段落综合为回答
```

### 用户要求"读第12-15页"

```
1. read --pdf book.pdf --pages 12-15
2. 将返回的文本展示给用户
```

### 用户要求"对比A书和B书的某个主题"

```
1. build --pdf a.pdf --collection book_a
2. build --pdf b.pdf --collection book_b
3. search "主题" --collection book_a
4. search "主题" --collection book_b
5. 综合对比两组结果
```

## 配置

API Key 存储在 `.api_key` 文件（一行：`SILICONFLOW_API_KEY=sk-xxx`）。

其他配置在 `.env` 文件。优先级：CLI 参数 > .api_key > .env > 默认值。

关键配置项：
- `SILICONFLOW_API_KEY` — 必填
- `COLLECTION_NAME` — 集合名（默认 pdf_collection）
- `CHUNK_SIZE` — 分块大小（默认 512，大文件建议 1024）
- `TOP_K` — 默认返回结果数（默认 5）

## 注意事项

- 索引缓存在 `./chroma_db/`，同一 PDF 不需要重复构建
- 章节检测支持中/英/日文，自动识别 PDF 书签或字号
- 噪声页（目录/索引/参考文献/附录）默认排除
- 多栏 PDF 自动检测并正确合并文本
- `search` 的 `--chapter` 在 chapter/section/subsection 三个字段中模糊匹配
- 不要在代码中硬编码 API Key
