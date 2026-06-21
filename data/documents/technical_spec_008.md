# 密钥管理 

## 规范范围
本技术规范适用于 `billing-worker` 和 `RabbitMQ` 系统中的密钥管理机制。该规范定义了使用批准的密钥管理器（approved secrets manager）的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于客户服务脚本（customer support scripts）和人力资源审批流程（HR approval）。

## 实现契约
- **MUST**：所有系统必须使用批准的密钥管理器来存储和检索敏感信息。
- **MUST**：密钥管理器必须支持自动轮换密钥，周期为 180 天。
- **SHOULD**：推荐使用 AWS Secrets Manager 或 HashiCorp Vault 作为批准的密钥管理器。
- **MUST NOT**：不得将密钥存储在源代码控制系统中（no source control）。

### 请求/响应字段
- **请求字段**：
  - `secret_name`：密钥名称（必填）
  - `version_id`：密钥版本（可选）
- **响应字段**：
  - `secret_value`：密钥值
  - `version_id`：当前密钥版本
  - `created_at`：创建时间
  - `updated_at`：更新时间

## 日志指标
- **MUST**：所有密钥操作（如获取、更新、删除）必须记录日志。
- **MUST**：日志条目必须包含以下字段：
  - `request_id`：请求唯一标识
  - `operation`：操作类型（如 GET, UPDATE, DELETE）
  - `secret_name`：密钥名称
  - `status`：操作状态（成功或失败）

## CI 检查
- **MUST**：持续集成（CI）过程中必须检查密钥管理器的配置是否正确。
- **MUST**：CI 流程必须确保密钥未被硬编码在源代码中。
- **MUST**：工程师在发布前必须测试批准的密钥管理器（approved secrets manager），确保其正常工作。

## 禁止事项
- **MUST NOT**：不得将密钥存储在源代码控制系统中（no source control）。
- **MUST NOT**：不得使用未经批准的密钥管理器。
- **MUST NOT**：不得手动管理密钥，所有密钥操作必须通过批准的密钥管理器进行。

## 验证方式
- **MUST**：定期审查密钥管理器的日志，确保没有异常操作。
- **MUST**：定期检查密钥轮换策略，确保密钥在 180 天内自动轮换。
- **MUST**：定期进行安全审计，确保密钥管理符合公司安全政策。

## 失败处理
- **MUST**：如果密钥管理器出现故障，系统应立即停止运行，并通知 SRE 团队。
- **MUST**：如果检测到密钥泄露，应立即撤销受影响的密钥，并启动应急响应流程。

通过以上规定，我们确保 `billing-worker` 和 `RabbitMQ` 系统中的密钥管理机制能够满足安全性和可靠性的要求。

