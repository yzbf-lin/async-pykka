# Scenarios

This page maps common real-world usage to concrete async-pykka patterns.

## Scenario 1: Player workflow orchestration

### Problem

You need one actor to own per-user state and dispatch business actions in sequence.

### Pattern

- One `PlayerActor` per user.
- External code only interacts through `ActorProxy`.
- Keep mutable state inside actor.

### Why this works

Single mailbox processing prevents race conditions on user state while preserving async I/O concurrency.

## Scenario 2: Net I/O actor + notify worker actor

### Problem

TCP responses and push-notify traffic are mixed; push traffic may burst.

### Pattern

- Net actor focuses on socket read/write and response correlation.
- Notify events are queued and consumed in batches by business actor.

### Reference

- Runnable demo: `examples/notify_batch.py`

### Benefits

- Isolates network concerns from domain logic.
- Queue-based batching smooths traffic spikes.

## Scenario 3: Request-response with timeout fallback

### Problem

A subset of protocol calls can hang or exceed SLO.

### Pattern

- Always await with timeout (`future.get(timeout=...)`).
- Convert timeout into deterministic business fallback.

### Reference

- Runnable demo: `examples/timeout_request.py`

## Scenario 4: Batch shutdown in test/CI

### Problem

Actors leak between tests, causing flaky behavior.

### Pattern

- In fixture teardown, call `ActorRegistry.stop_all(current_loop_only=True)`.
- Then clear registry if your framework reuses event loops heavily.

### Reference

- `tests/conftest.py`
