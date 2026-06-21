# 错误格式 

## 规范范围
本技术规范适用于 `billing-worker` 和 `RabbitMQ` 系统中的错误格式实现。该规范定义了标准错误对象（standard error object）的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于客户服务脚本（customer support scripts）和人力资源审批流程（HR approval）。

## 实现契约
为了确保系统在处理错误时的一致性和可追溯性，工程师必须遵循以下实现契约：

- **MUST**：所有错误响应必须包含一个标准错误对象（standard error object），其中至少应包括 `request_id` 和 `error code`。
- **SHOULD**：建议在标准错误对象中添加更多的上下文信息，如 `timestamp` 和 `message`，以便于问题定位和调试。

### 请求/响应字段
在 `billing-worker` 和 `RabbitMQ` 系统中，错误响应应包含以下字段：

- **request_id**：请求的唯一标识符，用于追踪特定请求的错误。
- **error_code**：错误代码，用于标识具体的错误类型。
- **timestamp**：错误发生的时间戳。
- **message**：对错误的简短描述。

### 示例
```json
{
  "request_id": "1234567890",
  "error_code": "E001",
  "timestamp": "2023-10-01T12:00:00Z",
  "message": "无效的请求参数"
}
```

## 日志指标
为了确保系统的可观测性，日志中必须记录以下指标：

- **request_id**：请求的唯一标识符。
- **error_code**：错误代码。
- **timestamp**：错误发生的时间戳。
- **message**：对错误的简短描述。

### 示例
```log
[ERROR] 2023-10-01T12:00:00Z - request_id: 1234567890, error_code: E001, message: 无效的请求参数
```

## CI 检查
在持续集成（CI）过程中，必须进行以下检查以确保错误格式的正确实现：

- **MUST**：验证所有错误响应是否包含 `request_id` 和 `error_code` 字段。
- **MUST**：验证 `request_id` 是否为有效的 UUID 格式。
- **MUST**：验证 `error_code` 是否符合预定义的错误代码列表。

### 配置示例
```yaml
checks:
  - name: error_format
    fields:
      - request_id
      - error_code
    validators:
      - type: uuid
        field: request_id
      - type: enum
        field: error_code
        values: [E001, E002, E003]
```

## 禁止事项
- **MUST NOT**：不允许在错误响应中返回敏感信息，如用户密码或内部系统路径。
- **MUST NOT**：不允许使用自定义错误代码，必须使用预定义的错误代码列表。

## 不适用范围
本规范不适用于客户服务脚本（customer support scripts）和人力资源审批流程（HR approval）。

