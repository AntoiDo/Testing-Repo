#!/bin/bash
# Docker CI Test - 完全模拟 GitHub Actions 的 Ubuntu 环境
# 使用方法: ./scripts/local-ci-docker.sh [分支名]

set -e

BRANCH=${1:-$(git branch --show-current)}
echo "🐳 Docker CI 模拟 - 测试分支: $BRANCH"

# 切换到目标分支
if [ "$BRANCH" != "$(git branch --show-current)" ]; then
    echo "📥 切换到分支: $BRANCH"
    git checkout "$BRANCH"
fi

# 使用 Docker 运行测试，完全模拟 GitHub Actions 环境
docker run --rm \
    -v "$(pwd):/workspace" \
    -w /workspace \
    ubuntu:latest \
    bash -c "
        apt-get update && \
        apt-get install -y python3 python3-pip ffmpeg && \
        pip3 install -r backend/requirements.txt && \
        pytest -v
    "

echo "✅ Docker CI 测试完成！"
