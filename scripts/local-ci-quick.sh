#!/bin/bash
# 快速本地 CI 测试 - 只安装核心依赖
# 使用方法: ./scripts/local-ci-quick.sh [分支名]

set -e

BRANCH=${1:-$(git branch --show-current)}
echo "⚡ 快速 CI 测试 - 分支: $BRANCH"

# 切换到目标分支
if [ "$BRANCH" != "$(git branch --show-current)" ]; then
    echo "📥 切换到分支: $BRANCH"
    git checkout "$BRANCH"
fi

# 创建临时虚拟环境
VENV_DIR=".venv-ci-quick"
echo "🐍 创建 Python 虚拟环境..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 只安装测试必需的依赖
echo "📦 安装核心依赖..."
pip install --upgrade pip
pip install pytest pytest-asyncio

# 运行测试
echo "🧪 运行测试..."
pytest -v --tb=short

# 清理
deactivate
echo "🧹 清理虚拟环境..."
rm -rf "$VENV_DIR"

echo "✅ 快速 CI 测试完成！"
