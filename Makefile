# PDF Vector Search — Makefile
.PHONY: help setup check build search query review clean

help:
	@echo "PDF Vector Search"
	@echo "==========================================="
	@echo "  make setup       安装依赖（创建 venv）"
	@echo "  make check       环境检查"
	@echo "  make build       构建索引   PDF=path"
	@echo "  make search      交互搜索   PDF=path"
	@echo "  make query       查询索引   Q='问题'"
	@echo "  make review      处理资料   INPUT=path"
	@echo "  make clean       清理缓存"
	@echo "==========================================="
	@echo
	@echo "示例:"
	@echo "  make build PDF=your-book.pdf"
	@echo "  make search PDF=your-book.pdf"
	@echo "  make query Q='什么是机器学习'"

setup:
	@echo "📦 安装依赖..."
	python -m venv venv
	venv/bin/pip install -r requirements.txt 2>/dev/null || venv/Scripts/pip install -r requirements.txt
	@test -f .env || (cp .env.example .env && echo "✓ 已创建 .env")
	@test -f .api_key || (cp .api_key.example .api_key && echo "✓ 已创建 .api_key，请编辑填入 API Key")
	@echo "✅ 安装完成"

check:
	@python check.py

build:
ifndef PDF
	@echo "❌ 请指定 PDF: make build PDF=your-book.pdf" && exit 1
endif
	@python build_index.py --pdf "$(PDF)"

search:
ifndef PDF
	@python interactive_search.py
else
	@python interactive_search.py --pdf "$(PDF)"
endif

query:
ifndef Q
	@echo "❌ 请指定查询: make query Q='你的问题'" && exit 1
endif
	@python query_index.py "$(Q)"

review:
ifndef INPUT
	@echo "❌ 请指定输入: make review INPUT=复习资料.docx" && exit 1
endif
	@python process_review.py -i "$(INPUT)" -o "$(or $(OUTPUT),output/整理版.docx)"

clean:
	rm -rf chroma_db __pycache__ output
	@echo "✓ 清理完成"
