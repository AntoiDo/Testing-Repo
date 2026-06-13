#!/bin/bash
# 快速测试队友分支
# 使用方法: ./scripts/test-branch.sh <分支名>

if [ -z "$1" ]; then
    echo "❌ 请提供分支名"
    echo "使用方法: ./scripts/test-branch.sh <分支名>"
    echo "示例: ./scripts/test-branch.sh feature/new-feature"
    exit 1
fi

BRANCH=$1
echo "🚀 测试队友分支: $BRANCH"

# 拉取最新代码
echo "📥 拉取最新代码..."
git fetch --all

# 切换到目标分支
echo "🔀 切换到分支: $BRANCH"
git checkout "$BRANCH"

# 运行本地 CI
echo "🧪 运行 CI 测试..."
./scripts/local-ci.sh

# 切换回原来的分支
ORIGINAL_BRANCH=$(git branch --show-current)
echo "🔙 切换回分支: $ORIGINAL_BRANCH"
git checkout "$ORIGINAL_BRANCH"

echo "✅ 测试完成！"
