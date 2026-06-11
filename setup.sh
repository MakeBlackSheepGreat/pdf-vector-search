#!/usr/bin/env bash
# PDF Vector Search — 安装脚本 (Unix/macOS)
set -e

echo "=========================================="
echo "  PDF Vector Search — 安装"
echo "=========================================="
echo

# 检查 Python 版本
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ 需要 Python 3.9+，请先安装 Python"
    exit 1
fi
echo "✓ Python: $PYTHON ($($PYTHON --version 2>&1))"

# 创建虚拟环境
echo
echo "[1/4] 创建虚拟环境..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "  ✓ 创建完成"
else
    echo "  ✓ 已存在"
fi

# 激活并安装依赖
echo "[2/4] 安装依赖..."
source venv/bin/activate
pip install --quiet -r requirements.txt
echo "  ✓ 依赖安装完成"

# 配置 .env
echo "[3/4] 通用配置..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✓ 已创建 .env"
else
    echo "  ✓ .env 已存在"
fi

# 配置 API Key
echo "[4/4] API Key 配置..."
if [ ! -f .api_key ]; then
    cp .api_key.example .api_key
    echo "  请输入你的硅基流动 API Key"
    echo "  获取地址: https://siliconflow.cn/"
    echo -n "  API Key (直接回车跳过，稍后手动编辑 .api_key): "
    read -r USER_KEY
    if [ -n "$USER_KEY" ]; then
        echo "SILICONFLOW_API_KEY=$USER_KEY" > .api_key
        echo "  ✓ API Key 已保存到 .api_key"
    else
        echo "  ⚠  已跳过，请稍后编辑 .api_key 填入 Key"
    fi
else
    echo "  ✓ .api_key 已存在"
fi

echo
echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo
echo "下一步:"
echo "  1. 如未填入 Key，请编辑 .api_key"
echo "  2. 构建索引:  python build_index.py --pdf your-book.pdf"
echo "  3. 开始搜索:  python interactive_search.py --pdf your-book.pdf"
echo
echo "或运行 make help 查看所有命令"
echo
