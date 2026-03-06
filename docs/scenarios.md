# Scenarios / 场景说明

This page maps common real-world usage to concrete async-pykka patterns.

本页把常见业务需求映射为可直接落地的 async-pykka 模式。

## Scenario 1: Player workflow orchestration / 场景 1：玩家流程编排

### Problem / 问题

- EN: One user needs isolated mutable state and ordered action execution.
- 中文：单个用户需要隔离状态，并保证动作顺序执行。

### Pattern / 模式

- EN: One `PlayerActor` per user.
- 中文：每个用户一个 `PlayerActor`。

- EN: External callers use `ActorProxy` only.
- 中文：外部统一通过 `ActorProxy` 调用。

- EN: Keep mutable state inside actor.
- 中文：可变状态仅保存在 actor 内部。

### Why this works / 为什么有效

- EN: Single mailbox processing avoids state races while keeping async I/O.
- 中文：单邮箱串行处理避免状态竞争，同时保留异步 I/O 并发能力。

## Scenario 2: Net I/O actor + notify worker / 场景 2：网络 Actor + 通知处理 Actor

### Problem / 问题

- EN: TCP response traffic and notify push traffic are mixed; notify may burst.
- 中文：TCP 响应流与 notify 推送流混合，推送可能突发。

### Pattern / 模式

- EN: Net actor handles socket read/write and response correlation.
- 中文：网络 Actor 专注收发包与响应关联。

- EN: Notify events are queued and batch-consumed by business actor.
- 中文：notify 先入队，再由业务 Actor 批量消费。

### Reference / 参考

- `examples/notify_batch.py`

## Scenario 3: Timeout fallback / 场景 3：超时兜底

### Problem / 问题

- EN: Some protocol calls may exceed SLO or hang.
- 中文：部分协议请求可能超时或卡住。

### Pattern / 模式

- EN: Always use `future.get(timeout=...)` for latency-sensitive calls.
- 中文：时延敏感请求统一使用 `future.get(timeout=...)`。

- EN: Convert timeout into deterministic fallback behavior.
- 中文：将超时统一转换成可预期的兜底逻辑。

### Reference / 参考

- `examples/timeout_request.py`

## Scenario 4: CI/test teardown safety / 场景 4：测试与 CI 的收尾安全

### Problem / 问题

- EN: Leaked actors can make tests flaky.
- 中文：Actor 泄漏会导致测试不稳定。

### Pattern / 模式

- EN: In fixture teardown, call `ActorRegistry.stop_all(current_loop_only=True)`.
- 中文：在 fixture teardown 中调用 `ActorRegistry.stop_all(current_loop_only=True)`。

- EN: Optionally clear registry in heavily reused loop environments.
- 中文：在重用 loop 场景可额外清理 registry。

### Reference / 参考

- `tests/conftest.py`
