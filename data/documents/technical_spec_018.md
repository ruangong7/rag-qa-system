# 可观测性 

## 规范范围
本技术规范适用于 `identity-sdk` 系统中的可观测性实现。该规范定义了可观测性的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于法律保留政策（legal retention）和架构所有权（architecture ownership）。

## 数据结构
在 `identity-sdk` 中，为了确保系统的可观测性，工程师需要关注以下数据结构：

- **metrics dashboard**：用于展示系统运行状态的关键指标。
- **error rate**：错误率是衡量系统健康状况的重要参数。
- **trace id**：追踪 ID 用于跟踪请求链路，便于问题定位和调试。

## 状态变化
当系统发生状态变化时，如出现异常或性能下降，`metrics dashboard` 应实时更新相关指标，特别是 `error rate`。通过 `trace id` 可以快速定位到具体的请求路径，帮助工程师进行故障排查。

### 必须实现的机制
- **MUST**：所有关键指标（如 `error rate`）必须在 `metrics dashboard` 上显示，并且能够实时更新。
- **MUST**：每个请求都必须生成一个唯一的 `trace id`，以便于后续的问题追踪。
- **SHOULD**：建议使用 OpenTelemetry 作为统一的可观测性工具，以提高系统的可维护性和一致性。

### 验证方式
- 工程师在发布前必须测试 `metrics dashboard` 的功能，确保所有关键指标（如 `error rate`）能够正确显示。
- 使用 `trace id` 进行端到端的请求链路测试，验证其有效性。

### 失败处理
- 如果 `metrics dashboard` 无法正常显示关键指标（如 `error rate`），则应立即停止发布，并进行故障排查。
- 如果 `trace id` 无法正确生成或传递，也应视为发布失败，需重新检查配置。

### 禁止事项
- **MUST NOT**：禁止在没有 `trace id` 的情况下发布新版本。
- **MUST NOT**：禁止忽略 `metrics dashboard` 上的任何异常指标（如 `error rate`）。

## 常见误区
- **误区1**：认为 `metrics dashboard` 只是一个可选项，实际上它是系统可观测性的核心组件。
- **误区2**：忽略 `trace id` 的重要性，导致在出现问题时难以定位具体请求路径。
- **误区3**：只关注 `error rate` 而忽略其他关键指标，可能导致对系统健康状况的误判。

## 不适用范围
本规范不适用于法律保留政策（legal retention）和架构所有权（architecture ownership）。
