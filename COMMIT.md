
# 提交规范说明

本文档用于说明上传仓库时的分支使用规范与 commit message 规范，便于多人协作、代码审查与持续集成。

## 一、分支使用约定
- `master`：主分支，存放已发布的最终版本。禁止直接向 `master` 提交代码，所有更改须通过 Pull Request 合并。
- `unit-test`：单元测试分支，用于提交单元测试相关变更或临时测试。
- `selenium-test`：Selenium 测试分支，自动化 UI 测试相关提交请推到此分支。
- `performance-test`：性能测试分支，用于 JMeter 等性能测试脚本与配置。
- `integration-test`：集成测试分支，集成环境调试与测试提交。
- `ci-config`：CI/CD 配置分支，存放 GitHub Actions 或其他 CI 配置变更。

> 注意：例如自动化测试完成后，应使用 `git push origin selenium-test` 将变更推送到 `selenium-test` 分支，避免直接提交到 `master`。完成验证后通过 PR 合并到 `master`。

## 二、Commit Message 规范
推荐使用类似 Conventional Commits 的格式：`<type>: <scope?> <description>`，简洁明了。

常用的 `type`：
- `feat:`     新功能
- `fix:`      Bug 修复
- `docs:`     文档变更（报告、说明文档等）
- `test:`     测试相关（单元测试、Selenium、JMeter 等）
- `ci:`       CI/CD 配置变更（GitHub Actions 等）
- `chore:`    构建/工程配置等杂项

示例表：

| 工作内容        | 提交格式示例           |
| -------------- | ---------------------- |
| 单元测试        | `test: add user service tests` |
| Selenium 测试   | `test: add login selenium test` |
| 集成测试        | `test: update integration test for api` |
| JMeter 脚本     | `test: add jmeter script for load` |
| GitHub Actions  | `ci: add workflow for build-and-test` |
| 报告/文档       | `docs: update CONTRIBUTING.md` |
| Bug 修复        | `fix: correct null pointer in parser` |

高级用法：可添加可选 `scope` 来说明改动影响的模块，例如 `fix(api): handle empty body`。

## 三、PR 与合并流程建议
- 提交到对应功能/测试分支后，创建 Pull Request 指向 `master` 或目标分支。
- PR 描述应包含变更摘要、关联 issue（若有）以及如何验证的步骤。
- 重要变更建议至少一个同事复审并通过 CI 后再合并。

## 四、其他注意事项
- 合并前请确保本地通过对应测试（单元、集成或 UI 测试）。
- 对于紧急修复，使用 `fix:` 并在 PR 中说明紧急原因与影响范围。
- 保持 Commit 信息简洁、可追溯，避免使用无意义的信息如 `update`、`misc` 等。

---

如果你希望我基于现有提交历史生成更具体的提交模板（如 Git hook 或提交消息模板），我可以继续帮你添加样例与工具集成步骤。

