# AI Coding Agent Harness

这是一个课程级 AI4SE Coding Agent Harness。项目重点是可审计、可恢复、可验证的
受治理代码变更机制，而不是 Web 产品或工业级安全执行平台。

## Implemented Capabilities

- 结构化 Agent Loop、Mock LLM、失败反馈和停止规则
- Policy、预算、审批、Acceptance Contract 和状态机
- Baseline、Task Workspace、ChangeSet 与冲突检测
- Apply Transaction、rollback、journal 和 startup recovery orchestration
- SQLite persistence、audit、DomainEvent、ProcessLock 与 ExecutionLease
- Python 3.12/Node.js 20 profile contract、preflight、doctor 和 Docker lifecycle adapter
- Trusted configuration、ProviderGateway 和课程级 Credential Provider

## Architecture Boundaries

事实、执行和恢复 authority 保持分离：Persistence 保存事实；ExecutionLease 管理执行
ownership；ApplyCoordinator 负责写回与 rollback；RecoveryCoordinator 负责恢复；
examples 只调用这些公开 contract，不成为新的 authority。

## Requirements

- Linux 或 WSL2
- Python 3.12
- Git
- pytest
- Docker CLI 仅在需要实际容器执行时使用；离线单元测试和 examples 不要求 daemon
- 不需要真实 API key

## Run the Test Suite

从仓库根目录执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q
```

Finalization contract：

```bash
python3 -m pytest tests/finalization -q
```

## Deterministic Demonstrations

一次运行全部演示验证：

```bash
python3 -m pytest tests/demos -q
```

也可直接运行 example。源码 checkout 模式需要让 Python 找到 `src/`：

```bash
PYTHONPATH=src python3 examples/governance_demo.py
PYTHONPATH=src python3 examples/feedback_demo.py
PYTHONPATH=src python3 examples/recovery_demo.py
```

三项输出分别证明：

1. Governance rejection：危险动作被永久拒绝，executor 调用数为 0。
2. Feedback loop：结构化失败进入下一轮 context，并使下一动作改变。
3. Recovery/rollback：通过公开 `ApplyJournal` contract 注入确定性的 PREPARE journal
   persistence failure；`ApplyCoordinator` 无 partial effect，并进入 `RECOVERY_REQUIRED`。
   内部 rollback 与 startup recovery 的更深故障注入由 transaction integration suite
   覆盖。

## CI

`.gitlab-ci.yml` 提供名称严格为 `unit-test` 的最小 job。依赖安装可以使用 package
index；安装完成后的测试执行不访问网络、不需要 API key，也不需要 Docker daemon 或
其他 external service。

## Recovery

Apply 失败时由 `ApplyCoordinator` 根据 durable journal 执行 rollback。无法确定或无法
完整恢复的副作用进入 `RECOVERY_REQUIRED`，并由既有 recovery authority 处理。
Finalization examples 不复制恢复逻辑。

## Threat Model

本课程实现防止不可信 repository、Issue、LLM response 或普通配置覆盖关键 authority，
并验证 bounded input、确定性 conflict、事务 rollback 和 secret non-leak contract。
它不防御同进程 Python reflection、memory dump、宿主机完全失陷或工业级供应链攻击。

## Deferred Scope

经人工批准，以下内容不属于本次课程提交闭环：

- WP-23 HTTP API
- WP-24 SSE
- WP-25 WebUI
- WP-27 Node.js 跨 profile runtime evidence
- 完整 encrypted credential store、credential CLI 和 Context Export
- 依赖 WebUI/serve 的 packaging、distribution 和 cold-start
- 工业级容器安全与真实 Docker security integration

这些项目仍保留冻结 Requirement ID 和原语义，不视为已实现或已验证。

## Cleanup and Uninstall

测试使用 pytest 临时目录，不应写入仓库。若使用源码 checkout，只需删除 checkout；
若自行创建虚拟环境，可删除对应 `.venv`。项目不会自动删除用户 repository。

## Final Verification Checklist

- `SPEC.md` 和 `PLAN.md` 保持冻结
- Finalization contract与三个 demo tests通过
- Full pytest通过
- `unit-test` job不需要API key、Docker daemon或external service
- `git diff --check`通过
- 无cache、bytecode、database或temporary artifact
- Deferred requirements没有被误报为完成
- `AGENT_LOG.md`和`SPEC_PROCESS.md`保存最终证据
