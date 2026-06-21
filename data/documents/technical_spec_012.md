# 消息队列 

## 规范范围
本技术规范适用于 `billing-worker` 和 `RabbitMQ` 系统中的消息队列机制。该规范定义了使用 RabbitMQ 主题交换（RabbitMQ topic exchange）的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于客户服务脚本（customer support scripts）和人力资源审批流程（HR approval）。

## 数据结构与状态变化
- **MUST**：所有消息队列必须配置主题交换（topic exchange），以确保消息能够根据路由键（routing key）正确分发。
- **MUST**：在消息处理失败时，系统必须将消息发送到死信队列（dead letter queue）。
- **SHOULD**：推荐使用重试策略（retry policy）来处理临时性错误，例如网络中断或服务暂时不可用。

### 重试/幂等要求
- **MUST**：重试策略应包含最大重试次数（maximum retry attempts）和重试间隔时间（retry interval）。
- **MUST**：系统必须确保消息处理的幂等性（idempotence），即多次处理同一消息不会导致不同的结果。
- **SHOULD**：建议在重试策略中加入指数退避算法（exponential backoff）以减少对系统的冲击。

### 观测字段
- **MUST**：系统必须记录每条消息的处理状态，包括成功、失败、重试次数等。
- **MUST**：日志中应包含请求 ID（request_id）、消息 ID（message_id）和处理时间戳（timestamp）。
- **SHOULD**：推荐使用 OpenTelemetry 来收集和分析消息队列的性能指标，如延迟、吞吐量等。

### 反例
- **MUST NOT**：不要在没有配置死信队列的情况下直接丢弃失败的消息。
- **MUST NOT**：不要忽略重试策略的重要性，否则可能导致消息丢失或重复处理。
- **MUST NOT**：不要在未测试重试逻辑的情况下发布代码，这可能会导致生产环境中的不稳定。

## 验证方式
- **MUST**：工程师在发布前必须测试 RabbitMQ 主题交换（RabbitMQ topic exchange）的功能，确保消息能够正确地被路由到目标队列。
- **MUST**：验证死信队列（dead letter queue）是否按预期工作，确保失败的消息能够被正确处理。
- **MUST**：通过模拟故障场景来测试重试策略（retry policy），确保系统能够在不同情况下正常运行。

## 不适用范围
- 客户服务脚本（customer support scripts）
- 人力资源审批流程（HR approval）

## 常见误区
- **误区1**：认为消息队列只需要简单的发布/订阅模式即可，忽略了主题交换（topic exchange）的重要性。
- **误区2**：忽视了死信队列（dead letter queue）的作用，导致失败的消息无法被有效处理。
- **误区3**：没有充分测试重试策略（retry policy），导致生产环境中出现消息丢失或重复处理的问题。

通过遵循以上规范，可以确保 `billing-worker` 和 `RabbitMQ` 系统中的消息队列机制稳定可靠。

