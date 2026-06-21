# 依赖扫描 

## 规范范围
本技术规范适用于 `search-indexer` 和 `OpenTelemetry` 系统中的依赖扫描机制。该规范定义了依赖扫描的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于架构所有权（architecture ownership）和客户服务脚本（customer support scripts）。

## 工程检查清单
### 必须实现的机制
- **MUST**：所有依赖项必须进行定期扫描以检测关键漏洞（critical vulnerability）。
- **MUST**：在发现关键漏洞后，工程师必须在48小时内修复或缓解该漏洞（48 hours）。
- **SHOULD**：建议使用自动化工具进行依赖扫描，以提高效率和准确性。

### 边界条件
- 如果在发布前48小时内发现关键漏洞且无法及时修复，则应推迟发布。
- 在非工作时间发现的关键漏洞，应在下一个工作日开始后的48小时内处理。

### 错误码
- **ERR_DEPENDENCY_SCAN_FAILED**：依赖扫描失败，未能完成扫描任务。
- **ERR_CRITICAL_VULNERABILITY_FOUND**：发现关键漏洞，需要立即处理。
- **ERR_FIX_DELAYED**：修复延迟，超过48小时未处理关键漏洞。

### 回滚要求
- **MUST**：如果在发布后发现关键漏洞且无法在48小时内修复，必须回滚到上一个稳定版本。
- **MUST**：回滚操作必须记录详细的变更日志，并通知相关团队。

### 验收标准
- **MUST**：每周至少进行一次依赖扫描（weekly scan），并记录扫描结果。
- **MUST**：扫描结果必须包含所有已知漏洞及其严重性等级。
- **MUST**：扫描报告必须存档并可追溯，以便审计和合规检查。

## 不适用范围
- 架构所有权（architecture ownership）
- 客户服务脚本（customer support scripts）

通过上述机制、参数和验证信号，确保 `search-indexer` 和 `OpenTelemetry` 系统中的依赖扫描能够有效检测和处理关键漏洞，保障系统的安全性和稳定性。

