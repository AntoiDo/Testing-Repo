#!/bin/bash
# Local CI Test Script - 模拟 GitHub Actions 环境
# 使用方法: ./scripts/local-ci.sh [分支名]

set -e

BRANCH=${1:-$(git branch --show-current)}
echo "🔍 Testing branch: $BRANCH"

# 检查是否在正确的目录
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ 请在项目根目录运行此脚本"
    exit 1
fi

# 切换到目标分支
if [ "$BRANCH" != "$(git branch --show-current)" ]; then
    echo "📥 切换到分支: $BRANCH"
    git checkout "$BRANCH"
fi

# 创建临时虚拟环境
VENV_DIR=".venv-ci"
echo "🐍 创建 Python 虚拟环境..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 检查 FFmpeg
echo "🎬 检查 FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg 未安装，跳过依赖 FFmpeg 的测试"
    FFMPEG_FLAG="--ignore-glob='*ffmpeg*'"
else
    echo "✅ FFmpeg 已安装"
    FFMPEG_FLAG=""
fi

# 运行测试
echo "🧪 运行测试..."
pytest -v $FFMPEG_FLAG

# 清理
deactivate
echo "🧹 清理虚拟环境..."
rm -rf "$VENV_DIR"

echo "✅ CI 测试完成！"
