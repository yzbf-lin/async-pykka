# FAQ / 常见问题

## 1) Why does cross-loop call fail? / 为什么跨 loop 调用会失败？

- EN: `async-pykka` binds each actor to the event loop where it is created.
- 中文：`async-pykka` 会把每个 Actor 绑定到其创建时的事件循环。

- EN: Calling `tell`/`ask`/`stop` from another loop raises `RuntimeError` intentionally.
- 中文：从其他 loop 调用 `tell`/`ask`/`stop` 会按设计抛 `RuntimeError`。

## 2) Should I use `tell` or `ask`? / 该用 `tell` 还是 `ask`？

- EN: Use `tell` when you do not need a return value.
- 中文：不需要返回值时用 `tell`。

- EN: Use `ask` when you need result, timeout, or error propagation.
- 中文：需要结果、超时控制或异常传播时用 `ask`。

## 3) How to mutate actor state safely? / 如何安全修改 Actor 状态？

- EN: Prefer actor methods or `await proxy.set(name, value)`.
- 中文：优先用 actor 方法或 `await proxy.set(name, value)`。

- EN: Avoid direct proxy attribute assignment (`proxy.x = y`).
- 中文：避免直接给 proxy 属性赋值（`proxy.x = y`）。

## 4) How to prevent test leakage? / 如何避免测试用例间 Actor 泄漏？

- EN: In fixture teardown, call `await ActorRegistry.stop_all(current_loop_only=True)`.
- 中文：在 fixture teardown 里调用 `await ActorRegistry.stop_all(current_loop_only=True)`。

- EN: Optionally clear registry if your test framework reuses loops aggressively.
- 中文：若测试框架强复用 loop，可额外清理 registry。

## 5) Why is `get_all` sequential? / 为什么 `get_all` 是串行收集？

- EN: It preserves deterministic result order and simple semantics.
- 中文：这是为了保证结果顺序确定和语义简单。

- EN: If you need parallel wait behavior, orchestrate tasks explicitly in your app layer.
- 中文：若需要并行等待语义，请在业务层显式编排并发任务。

## 6) How to benchmark correctly? / 如何正确做压测？

- EN: Use `examples/benchmark_ping.py` as baseline, then run matrix tests.
- 中文：先用 `examples/benchmark_ping.py` 建立基线，再按矩阵扩大测试。

- EN: Compare on same hardware/python/runtime settings.
- 中文：确保硬件、Python、运行参数一致后再做对比。
