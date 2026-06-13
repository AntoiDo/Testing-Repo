# 测试基础设施修复：数据库引擎懒加载 + 跨模块隔离

## 问题描述

`pytest -v` 一次性运行全部 111 个测试时，出现两类跨模块污染导致 8 个测试失败：

1. **数据库连接失败**：`app/db/engine.py` 在模块 import 时创建 engine 单例，三个集成测试文件设置不同 `DATABASE_URL` 时，后加载的模块覆盖环境变量，导致 engine 指向错误的临时数据库或已被清理的数据库
2. **GPT stub 泄漏**：单元测试文件在模块级向 `sys.modules` 注入空壳 `GPT`/`GPTSource`，污染集成测试的 import 命名空间
3. **FastAPI stub 泄漏**：数据库/流水线测试文件在模块级用空壳覆盖 `fastapi`，导致 API 异常处理器找不到 `Request`

## 解决方案

### 1. 数据库引擎懒加载 + URL 变更检测 (`backend/app/db/engine.py`)

- engine 不再在模块 import 时创建，改为首次调用 `get_engine()` 时懒加载
- `get_engine()` 检测 `DATABASE_URL` 环境变量变化，自动 dispose 旧连接并以新 URL 重建
- 新增 `reset_engine()` 函数供测试 teardown 使用

### 2. 测试隔离层 (`backend/tests/conftest.py`)

- 自动将 `backend/` 加入 `sys.path`
- 每个测试模块运行前通过 `sys.modules` 直接操作 engine 全局变量重置

### 3. Stub 生命周期管理

- `test_universal_gpt_checkpoint.py`：stub 注入从模块级移至 `setUpClass`/`tearDownClass`
- `test_universal_gpt_content_format.py`：stub 注入从模块级移至 `setUpModule`/`tearDownModule`
- `test_integration_database.py` / `test_integration_pipeline.py`：移除 `fastapi` 模块 stub（真实 fastapi 已在环境安装）

### 4. DATABASE_URL 恢复

三个集成测试文件各自添加 `setUpModule`，在测试运行前恢复自身的 `DATABASE_URL`，防止字母序加载覆盖。

### 5. CI 配置 (`ci.yml`)

- 添加 `working-directory: backend`，确保 pytest 在正确目录运行

## 修改文件

| 文件 | 改动 |
|------|------|
| `backend/app/db/engine.py` | 懒加载引擎 + URL 变更检测 + `reset_engine()` |
| `backend/tests/conftest.py` | 新增：sys.path 管理 + 模块级 engine 重置 |
| `.github/workflows/ci.yml` | 添加 `working-directory: backend` |
| `backend/tests/test_integration_api.py` | 添加 `setUpModule`，修复 `test_invalid_url_format` 断言 |
| `backend/tests/test_integration_database.py` | 添加 `setUpModule` URL 恢复，移除 fastapi stub，修复 `test_database_file_exists` |
| `backend/tests/test_integration_pipeline.py` | 添加 `setUpModule`，移除 fastapi stub |
| `backend/tests/test_universal_gpt_checkpoint.py` | stub 注入移至 `setUpClass`/`tearDownClass` |
| `backend/tests/test_universal_gpt_content_format.py` | stub 注入移至 `setUpModule`/`tearDownModule` |

## 测试结果

**111 passed, 0 failed, 6 subtests passed** — 全部测试在单次 `pytest -v` 中通过。
