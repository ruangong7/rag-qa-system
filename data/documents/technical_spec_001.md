# API认证 

## 规范范围
本技术规范适用于 `edge-api` 和 `platform-shared-lib` 系统中的 API 认证机制。该规范定义了使用 OAuth 2.0 进行 API 认证的具体要求，包括必须使用的参数和验证信号。本规范不适用于人力资源审批流程（HR approval）和法律保留政策（legal retention）。

## MUST 要求
- **OAuth 2.0**：所有对外提供的 API 必须支持 OAuth 2.0 认证机制。
- **Bearer token**：API 请求中必须包含 Bearer token 作为认证凭据。
- **Token 有效期**：Bearer token 的有效期应设置为 3600 秒（即 1 小时）。

## 配置项
- **授权服务器配置**：在 `platform-shared-lib` 中配置 OAuth 2.0 授权服务器的 URL 和相关参数。
- **客户端 ID 和密钥**：在 `edge-api` 中配置 OAuth 2.0 客户端的 ID 和密钥。
- **Token 存储**：确保 Bearer token 在客户端安全存储，并在每次请求时正确传递。

## 接口行为
- **认证头**：每个 API 请求必须在 HTTP 头中包含 `Authorization: Bearer <token>`。
- **无效 Token 处理**：如果接收到的 Bearer token 无效或已过期，API 应返回 401 Unauthorized 状态码，并附带相应的错误信息。
- **Token 刷新**：客户端应在 Bearer token 过期前通过刷新令牌机制获取新的 Bearer token。

## 测试要求
- **功能测试**：工程师必须在发布前对 OAuth 2.0 认证机制进行全面的功能测试，确保所有 API 请求都能正确处理 Bearer token。
- **性能测试**：测试 Bearer token 的生成、验证和刷新过程的性能，确保在高并发情况下仍能正常工作。
- **安全性测试**：进行安全性测试，确保 Bearer token 不会被泄露或篡改。

## 失败处理
- **认证失败**：如果认证失败，API 应立即停止处理请求，并返回 401 Unauthorized 状态码。
- **Token 过期**：如果 Bearer token 已过期，API 应返回 401 Unauthorized 状态码，并提示客户端需要重新获取 Bearer token。
- **日志记录**：所有认证失败的情况都应在系统日志中记录详细信息，以便后续分析和审计。

### 关键事实
- OAuth 2.0
- Bearer token
- 3600 seconds

---

本规范由平台工程团队负责维护，如有任何疑问或建议，请联系平台工程团队。

