# 熔断器

## 规范范围
本技术规范适用于 `search-indexer` 和 `OpenTelemetry` 系统中的熔断器机制。该规范定义了熔断器的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于架构所有权（architecture ownership）和客户服务脚本（customer support scripts）。

## 必须实现的机制
- **必须**：所有外部调用（external calls）必须使用熔断器机制。
- **必须**：在 10 秒内发生 5 次失败（5 failures in 10 seconds）时，熔断器必须切换到打开状态（open state）。
- **必须**：工程师在发布前必须测试熔断器在 10 秒内发生 5 次失败的情况。

## 配置示例
以下是一个配置示例，展示了如何在 `search-indexer` 中启用熔断器：

```yaml
circuit_breaker:
  enabled: true
  failure_threshold: 5
  time_window: 10s
  open_state_duration: 30s
```

## 测试样例
为了确保熔断器正常工作，可以编写如下测试用例：

```python
import unittest
from search_indexer import SearchIndexer

class TestCircuitBreaker(unittest.TestCase):
    def test_circuit_breaker_open(self):
        indexer = SearchIndexer()
        for _ in range(5):
            with self.assertRaises(Exception):
                indexer.external_call()  # 假设 external_call 方法会抛出异常
        self.assertTrue(indexer.circuit_breaker.is_open())
        
if __name__ == '__main__':
    unittest.main()
```

## 性能/安全约束
- **应该**：建议将熔断器的打开状态持续时间设置为 30 秒，以避免频繁切换状态。
- **必须不**：不得在熔断器处于打开状态时继续尝试外部调用，以防止系统过载。

## 发布门禁
- **必须**：在每次发布前，必须通过自动化测试验证熔断器在 10 秒内发生 5 次失败的情况下能够正确切换到打开状态。
- **必须**：发布前必须检查日志中是否有熔断器相关的错误信息，并确保这些错误信息已被处理。

## 错误示例与反模式
- **反模式**：忽略熔断器的状态，在其处于打开状态时继续尝试外部调用。
- **反模式**：不进行熔断器的自动化测试，仅依赖手动测试或不进行测试。

通过遵循以上规范，可以有效预防因外部服务故障导致的系统级联故障，提高系统的稳定性和可靠性。
