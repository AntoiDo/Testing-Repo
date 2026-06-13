# 本地 CI 测试指南

本指南帮助你在本地模拟 GitHub Actions 环境，测试队友的分支代码。

## 快速开始

### 方案一：快速测试（推荐）

```bash
# 快速测试指定分支（只安装核心依赖，速度快）
./scripts/local-ci-quick.sh [分支名]

# 或使用测试分支脚本
./scripts/test-branch.sh feature/branch-name
```

### 方案二：完整测试

```bash
# 完整测试（安装所有依赖，与 CI 环境一致）
./scripts/local-ci.sh [分支名]
```

### 方案三：Docker 完全模拟

```bash
# 使用 Docker 完全模拟 GitHub Actions 环境
./scripts/local-ci-docker.sh [分支名]
```

## 脚本说明

| 脚本 | 用途 | 速度 |
|------|------|------|
| `scripts/local-ci-quick.sh` | 快速测试（核心依赖） | ⚡ 快 |
| `scripts/local-ci.sh` | 完整测试（所有依赖） | 🐢 慢 |
| `scripts/local-ci-docker.sh` | Docker 容器完全模拟 | 🐢 慢 |
| `scripts/test-branch.sh` | 快速测试队友分支 | ⚡ 快 |

## 使用示例

### 测试队友的分支

```bash
# 1. 拉取最新代码
git fetch --all

# 2. 测试指定分支
./scripts/test-branch.sh teammate/feature-branch

# 3. 测试完成后会自动切回原分支
```

### 手动测试流程

```bash
# 1. 切换到目标分支
git checkout teammate/branch-name

# 2. 运行本地 CI
./scripts/local-ci.sh

# 3. 切换回原分支
git checkout master
```

## 环境要求

- Python 3.12+
- FFmpeg（可选，用于视频处理测试）
- Docker（可选，用于完全模拟）

## 与 GitHub Actions 的区别

| 特性 | 本地 CI | GitHub Actions |
|------|---------|----------------|
| 运行环境 | 本地机器 | GitHub 云端 |
| 运行速度 | 快 | 需要等待 |
| 测试分支 | 任意分支 | 仅 PR/Push |
| 依赖缓存 | 本地缓存 | 云端缓存 |

## 故障排除

### 问题：pytest 命令找不到

```bash
# 确保安装了 pytest
pip install pytest
```

### 问题：FFmpeg 相关测试失败

```bash
# 安装 FFmpeg
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 问题：Python 版本不匹配

```bash
# 检查 Python 版本
python3 --version

# 应该是 3.12 或更高
```
