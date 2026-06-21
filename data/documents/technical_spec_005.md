# 日志字段 

## 规范范围
本技术规范适用于 `edge-api` 和 `platform-shared-lib` 系统中的日志记录机制。该规范定义了日志字段的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于人力资源审批流程（HR approval）和法律保留政策（legal retention）。

## RFC 条款
- **MUST**：所有日志条目必须包含 `request_id` 字段。
- **MUST**：所有日志条目必须包含 `latency_ms` 字段，用于记录请求处理的延迟时间（以毫秒为单位）。
- **SHOULD**：推荐使用 JSON 格式进行日志记录，以便于解析和分析。

### 配置示例
```json
{
  "request_id": "1234567890abcdef",
  "latency_ms": 123,
  "level": "INFO",
  "message": "Request processed successfully"
}
```

### 测试样例
以下是一个测试用例，用于验证日志记录是否符合规范：

```python
import logging
import json

def test_logging():
    logger = logging.getLogger('edge-api')
    request_id = '1234567890abcdef'
    latency_ms = 123
    
    # 模拟日志记录
    log_data = {
        'request_id': request_id,
        'latency_ms': latency_ms,
        'level': 'INFO',
        'message': 'Request processed successfully'
    }
    logger.info(json.dumps(log_data))
    
    # 读取日志文件并验证
    with open('log_file.log', 'r') as f:
        for line in f:
            log_entry = json.loads(line)
            assert 'request_id' in log_entry, "Missing request_id in log entry"
            assert 'latency_ms' in log_entry, "Missing latency_ms in log entry"
            assert log_entry['request_id'] == request_id, "Incorrect request_id in log entry"
            assert log_entry['latency_ms'] == latency_ms, "Incorrect latency_ms in log entry"

test_logging()
```

### 性能/安全约束
- **性能**：确保日志记录不会显著影响系统性能。建议在高负载情况下对日志记录进行性能测试。
- **安全**：敏感信息（如用户密码、API 密钥等）不得记录在日志中。应定期审查日志内容，确保没有泄露敏感信息。

### 发布门禁
- **验证方式**：在发布前，工程师必须测试 `request_id` 和 `latency_ms` 是否正确记录在日志中。可以使用上述测试样例进行验证。
- **失败处理**：如果日志记录不符合规范，应立即修复，并重新进行测试。未通过测试的日志记录代码不得发布到生产环境。

### 禁止事项
- **禁止**：在日志中记录任何敏感信息，如用户密码、API 密钥等。
- **禁止**：忽略或删除 `request_id` 和 `latency_ms` 字段。这两个字段是日志记录的关键部分，必须始终存在。

### 关键事实
- `request_id`
- `latency_ms`
- `JSON log`

以上规范旨在确保日志记录的一致性和可靠性，从而帮助故障排查和性能优化。

