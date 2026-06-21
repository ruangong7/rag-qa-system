# 特性开关 

## 规范范围
本技术规范适用于 `identity-sdk` 系统中的特性开关（feature flag）实现。该规范定义了特性开关的具体要求，包括必须实现的机制、参数以及验证信号。本规范不适用于法律保留政策（legal retention）和架构所有权（architecture ownership）。

## 实现契约
- **MUST**：所有特性开关必须明确指定拥有者（owner）和过期日期（expiry date）。
- **SHOULD**：特性开关应通过配置文件或环境变量进行管理，以确保在不同环境中的一致性。
- **MUST**：特性开关必须具备紧急关闭功能（kill switch），以便在必要时快速禁用某个特性。

## 请求/响应字段
### 请求
- **feature_flag_id** (string, required)：特性开关的唯一标识符。
- **owner** (string, required)：特性开关的拥有者。
- **expiry_date** (string, ISO 8601, required)：特性开关的过期日期。
- **enabled** (boolean, optional)：特性是否启用，默认为 `false`。

### 响应
- **status** (string, required)：请求状态，如 "success" 或 "failure"。
- **message** (string, optional)：附加信息，例如错误描述。
- **feature_flag** (object, optional)：包含更新后的特性开关信息。

## 日志指标
- **feature_flag_created**：记录创建新的特性开关事件。
- **feature_flag_updated**：记录更新特性开关事件。
- **feature_flag_deleted**：记录删除特性开关事件。
- **kill_switch_activated**：记录激活紧急关闭功能的事件。

## CI 检查
- **MUST**：CI Pipeline 必须检查每个特性开关是否指定了拥有者（owner）和过期日期（expiry date）。
- **MUST**：CI Pipeline 必须验证特性开关的过期日期格式是否符合 ISO 8601 标准。
- **SHOULD**：CI Pipeline 应该运行自动化测试，确保特性开关的紧急关闭功能（kill switch）能够正常工作。

## 禁止事项
- **MUST NOT**：不得在没有明确拥有者（owner）和过期日期（expiry date）的情况下启用特性开关。
- **MUST NOT**：不得绕过 CI Pipeline 的检查直接部署代码。
- **MUST NOT**：不得在生产环境中使用未经过充分测试的特性开关。

工程师在发布前必须测试特性开关（feature flag），确保其拥有者（owner and expiry date）和紧急关闭功能（kill switch）都能按预期工作。


