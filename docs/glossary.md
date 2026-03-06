# Glossary / 术语表

## Actor

- EN: A concurrency unit that processes messages from its mailbox sequentially.
- 中文：并发执行单元，从邮箱中按顺序处理消息。

## Mailbox

- EN: Queue that stores messages sent to an actor.
- 中文：Actor 接收消息的队列。

## ActorRef

- EN: Safe reference used to communicate with an actor (`tell`, `ask`, `stop`, `proxy`).
- 中文：与 Actor 通信的安全引用（`tell`、`ask`、`stop`、`proxy`）。

## ActorProxy

- EN: Proxy facade that lets you call actor methods as async operations.
- 中文：代理门面，把 Actor 方法调用封装成异步操作。

## Future

- EN: Result placeholder representing value/exception available now or later.
- 中文：异步结果占位符，可在现在或未来获取值/异常。

## Event Loop

- EN: Async scheduler executing tasks, callbacks, and I/O events.
- 中文：执行任务、回调与 I/O 事件的异步调度器。

## Cross-loop call

- EN: Calling actor APIs from a different event loop than actor's bound loop.
- 中文：在非 Actor 所属 loop 中调用其 API。

## Backpressure

- EN: Mechanism to prevent producer from overwhelming consumer.
- 中文：防止生产者压垮消费者的流量控制机制。

## Graceful shutdown

- EN: Controlled stop process that releases resources and drains pending work safely.
- 中文：可控停机流程，安全释放资源并处理在途任务。
