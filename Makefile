# PDF Vector Search — Makefile
.PHONY: help setup check build search chapters read collections clean

help:
	@echo "PDF Vector Search"
	@echo "==========================================="
	@echo "  make setup       安装依赖"
	@echo "  make check       环境检查 (JSON)"
	@echo "  make build       构建索引   PDF=path"
	@echo "  make search      语义搜索   Q='问题'"
	@echo "  make chapters    章节结构   PDF=path"
	@echo "  make read        读取页面   PDF=path PAGES=1,2-5"
	@echo "  make collections 列出集合"
	@echo "  make clean       清理缓存"
	@echo "==========================================="

setup:
	python -m venv venv
	venv/bin/pip install -r requirements.txt 2>/dev/null || venv/Scripts/pip install -r requirements.txt
	@test -f .env || (cp .env.example .env && echo "✓ 已创建 .env")
	@test -f .api_key || (cp .api_key.example .api_key && echo "✓ 已创建 .api_key，请编辑填入 API Key")
	@echo "✅ 安装完成"

check:
	@python pdf_cli.py check

build:
ifndef PDF
	@echo "❌ 用法: make build PDF=your-book.pdf" && exit 1
endif
	@python pdf_cli.py build --pdf "$(PDF)"

search:
ifndef Q
	@echo "❌ 用法: make search Q='你的问题' [PDF=path]" && exit 1
endif
	@python pdf_cli.py search "$(Q)"

chapters:
ifndef PDF
	@echo "❌ 用法: make chapters PDF=your-book.pdf" && exit 1
endif
	@python pdf_cli.py chapters --pdf "$(PDF)"

read:
ifndef PDF
	@echo "❌ 用法: make read PDF=book.pdf PAGES=1,2-5" && exit 1
endif
ifndef PAGES
	@echo "❌ 请指定页码: make read PDF=book.pdf PAGES=1,2-5" && exit 1
endif
	@python pdf_cli.py read --pdf "$(PDF)" --pages "$(PAGES)"

collections:
	@python pdf_cli.py collections

clean:
	rm -rf chroma_db __pycache__ output
	@echo "✓ 清理完成"
