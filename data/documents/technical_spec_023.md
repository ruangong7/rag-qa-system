# 批处理规范 

## 规范范围
本技术规范适用于 `search-indexer` 系统中的批处理作业实现。该规范定义了批处理作业的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于架构所有权（architecture ownership）和客户服务脚本（customer support scripts）。

## 工程检查清单
为了确保批处理作业的可靠性和可恢复性，工程师必须遵循以下检查清单：

- **MUST**：所有批处理作业必须实现检查点（checkpoint）机制，以支持可重启的作业（restartable job）。
- **MUST**：在发布前，工程师必须测试检查点机制，确保其正常工作。
- **SHOULD**：建议在批处理作业中使用 OpenTelemetry 进行日志记录和监控，以便更好地跟踪作业状态和性能。
- **MUST NOT**：禁止在没有检查点机制的情况下部署批处理作业，以防止因故障导致的数据丢失或重复处理。

### 配置示例
```yaml
batch_job:
  checkpoint_enabled: true
  max_retries: 3
  retry_interval: 60s
  telemetry:
    enabled: true
    provider: OpenTelemetry
```

### 测试样例
以下是一个简单的测试用例，用于验证检查点机制是否正常工作：

```python
def test_checkpoint_recovery():
    # 模拟批处理作业失败
    job = BatchJob()
    job.run()
    assert job.checkpoint_saved() == True

    # 重新启动作业
    job.restart_from_checkpoint()
    assert job.completed_successfully() == True
```

### 性能/安全约束
- **性能**：批处理作业应尽量减少检查点的频率，以避免对性能产生过大影响。建议每处理一定数量的数据后保存一次检查点。
- **安全性**：检查点数据应加密存储，并且只能由授权的服务访问。此外，应定期清理不再需要的检查点数据，以减少存储成本和潜在的安全风险。

### 发布门禁
- **MUST**：在发布新的批处理作业之前，必须通过自动化测试验证检查点机制的有效性。
- **MUST**：如果批处理作业在测试过程中出现故障警报（failure alert），则不得发布，直到问题被解决并重新测试通过。


