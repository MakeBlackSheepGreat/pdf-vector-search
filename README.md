# PDF Vector Search

> 通用 PDF 语义搜索引擎 — 为 AI Agent 设计的 Skill 工具

**兼容平台：** Codex · Claude Code · OpenClaw · opencode · Reasonix

## 快速开始

```bash
# 1. 安装
./setup.sh          # Unix/macOS
setup.bat           # Windows

# 2. 配置 API Key
# 编辑 .api_key，填入 SILICONFLOW_API_KEY

# 3. 使用
python pdf_cli.py check                           # 检查环境
python pdf_cli.py build --pdf your-book.pdf       # 构建索引
python pdf_cli.py search "你的问题"               # 搜索
python pdf_cli.py chapters --pdf your-book.pdf    # 查看章节
python pdf_cli.py read --pdf your-book.pdf --pages 1-5  # 读取页面
```

所有命令输出 JSON，Agent 可直接解析。

---

## 功能

| 命令 | 说明 |
|------|------|
| `check` | 环境检查（依赖/API/ChromaDB） |
| `build` | 构建 PDF 向量索引 |
| `search` | 语义搜索（支持章节过滤） |
| `chapters` | 提取章节结构树 |
| `read` | 读取指定页面完整文本 |
| `collections` | 列出/删除索引集合 |

### 搜索特性

- **多语言章节检测** — 自动识别中/英/日文章节结构
- **噪声过滤** — 自动排除目录、索引、参考文献等
- **多栏布局** — 自动检测双栏排版，正确合并文本
- **页眉页脚去除** — 模式匹配检测并自动去除
- **章节过滤** — `--chapter "第三章"` 精准定位

---

## 项目结构

```
├── pdf_cli.py             # Agent 专用 CLI（统一入口，JSON 输出）
├── config.py              # 统一配置管理
├── embedder.py            # 嵌入模型封装
├── vector_search.py       # 核心搜索引擎
├── pdf_structure.py       # PDF 结构分析（章节/噪声/多栏）
├── check.py               # 环境检查（人类可读输出）
├── .reasonix/skills/pdf-vector-search/SKILL.md  # Agent Skill 定义
├── .api_key.example       # API Key 模板
├── .env.example           # 通用配置模板
├── setup.sh / setup.bat   # 安装脚本
└── Makefile               # 快捷命令
```

---

## 配置

API Key 存储在 `.api_key` 文件（从 `.api_key.example` 复制）。

| 配置项 | 环境变量 | 默认值 |
|--------|---------|--------|
| API Key | `SILICONFLOW_API_KEY` | （必填） |
| 集合名称 | `COLLECTION_NAME` | `pdf_collection` |
| 分块大小 | `CHUNK_SIZE` | `512` |
| 返回结果数 | `TOP_K` | `5` |

---

## 技术栈

| 组件 | 用途 |
|------|------|
| [LlamaIndex](https://github.com/run-llama/llama_index) | RAG 框架 |
| [ChromaDB](https://github.com/chroma-core/chroma) | 向量数据库 |
| [硅基流动 API](https://siliconflow.cn/) | Qwen3-VL-Embedding-8B |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF 解析 |

---

## License

MIT License
