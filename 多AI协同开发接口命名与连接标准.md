# 《高情商恋爱回复助手》多 AI 协同开发接口命名与连接标准

> 规范版本：1.0.0  
> 适用范围：Android、管理后台、业务 API、AI Worker、异步任务、数据库、第三方集成和测试  
> 目标：让不同 AI 编程工具在没有隐含上下文的情况下，使用同一模块边界、名称、数据契约和验收标准并行开发

## 1. 规范权威层级

不同文档分别对不同问题负责，不允许用低层文档覆盖高层语义：

| 优先级 | 文档/文件 | 权威范围 |
|---:|---|---|
| 1 | 安全、隐私、支付渠道和法律强制规则 | 任何冲突均采用更严格规则 |
| 2 | `contracts/openapi/openapi.yaml`（生成后） | HTTP path、method、参数、Schema、响应和错误 |
| 3 | `ai-collaboration-manifest.yaml` | 模块编码、依赖、代码包名、表名和公共枚举 |
| 4 | 本文档 | 命名、分层、连接方式、变更流程和协作门禁 |
| 5 | 《Android 页面与前后台 API 联动规范》 | 页面行为、业务流程、状态机和接口清单 |
| 6 | 《产品功能架构与系统设计文档》 | 产品目标、范围、优先级和可行性边界 |
| 7 | 《文档可行性与接口联动验证报告》 | 某一版本的静态验证结论 |

当前尚未生成 OpenAPI 文件，因此开发前的 wire contract 暂以《Android 页面与前后台 API 联动规范》为准。进入编码阶段的第一个契约任务是生成并评审 `contracts/openapi/openapi.yaml`；生成后，任何手写 DTO 都不能与它冲突。

`WORK_ITEMS.yaml` 不是业务契约，而是协作调度入口，记录任务责任人、允许修改路径、依赖和验收测试。新接入工具应按顺序读取 manifest、本文档、自己的工作包和所依赖的契约文件。

## 2. 建议仓库结构

```text
/
├─ apps/
│  ├─ android/                 # Android 客户端
│  └─ admin-web/               # 管理后台
├─ services/
│  ├─ api/                     # 用户与管理 HTTP API
│  ├─ ai-worker/               # OCR、模型编排、安全检查
│  └─ async-worker/            # 导出、分享图、对账等异步任务
├─ packages/
│  ├─ generated-api/           # OpenAPI 生成代码，禁止手改
│  ├─ contract-test-fixtures/  # 跨语言契约样例
│  └─ observability/           # requestId、trace、metrics 公共封装
├─ contracts/
│  ├─ openapi/openapi.yaml     # HTTP 单一事实来源
│  ├─ events/                  # SSE/领域事件 JSON Schema
│  ├─ webhooks/                # 外部回调样例与验签说明
│  └─ examples/                # 成功与失败固定样例
├─ database/
│  ├─ migrations/              # 只追加迁移，禁止改已发布迁移
│  └─ seeds/                   # 非生产测试数据
├─ docs/
│  ├─ adr/                     # 架构决策记录
│  └─ runbooks/                # 故障与运维手册
├─ ai-collaboration-manifest.yaml
└─ WORK_ITEMS.yaml             # 多工具任务分配与依赖，进入开发时创建
```

目录尚未创建时，各工具不得自行选择另一套同义结构；应先提交结构 ADR 或更新本文档。

## 3. 全局模块编码与边界

模块编码使用 `UPPER_SNAKE_CASE`，作为任务、日志、权限、事件和文档引用的稳定标识。

| 模块编码 | 中文名称 | 用户端 API 前缀 | 前端 Client | 后端边界/服务 | 主要数据表 |
|---|---|---|---|---|---|
| `APP_CONFIG` | 启动配置 | `/app` | `appConfigApi` | `app_config` | `app_config_versions` |
| `AUTH` | 认证会话 | `/auth` | `authApi` | `identity` | `auth_sessions`, `sms_challenges` |
| `USER` | 用户账户 | `/me` | `userApi` | `identity` | `users`, `user_profiles` |
| `DEVICE` | 登录设备/推送 | `/me/devices` | `deviceApi` | `identity` | `user_devices`, `push_tokens` |
| `CONSENT` | 协议与授权 | `/me/consents` | `consentApi` | `privacy` | `consent_records`, `legal_documents` |
| `TARGET_PROFILE` | 对象档案 | `/target-profiles` | `targetProfileApi` | `persona` | `target_profiles` |
| `MEMORY` | 长期记忆 | `/memories` | `memoryApi` | `persona` | `profile_memories` |
| `ATTACHMENT` | 安全上传 | `/attachments` | `attachmentApi` | `media` | `attachments` |
| `OCR` | 截图解析校正 | `/attachments/{attachmentId}/ocr` | `ocrApi` | `media` | `ocr_results`, `ocr_turns` |
| `GENERATION` | 生成任务 | `/generations` | `generationApi` | `generation` | `generation_tasks`, `generation_usage` |
| `CANDIDATE` | 候选回复 | `/candidates` | `candidateApi` | `generation` | `reply_candidates`, `candidate_actions` |
| `CONVERSATION` | 历史会话 | `/conversations` | `conversationApi` | `history` | `conversations`, `conversation_items` |
| `FAVORITE` | 收藏 | `/favorites` | `favoriteApi` | `history` | `favorites` |
| `KNOWLEDGE` | 锦囊内容 | `/knowledge` | `knowledgeApi` | `content` | `content_categories`, `content_cards`, `content_versions` |
| `SHARE_CARD` | 脱敏分享图 | `/share-cards` | `shareCardApi` | `content` | `share_cards`, `share_card_templates` |
| `ENTITLEMENT` | 会员权益 | `/entitlements` | `entitlementApi` | `billing` | `user_entitlements`, `benefit_balances` |
| `WALLET` | 算力钱包 | `/wallet` | `walletApi` | `billing` | `wallet_accounts`, `wallet_ledger` |
| `PRODUCT` | 商品目录 | `/products` | `productApi` | `billing` | `products`, `product_prices` |
| `ORDER` | 支付订单 | `/orders` | `orderApi` | `billing` | `orders`, `payment_attempts`, `payment_events` |
| `SUBSCRIPTION` | 订阅 | `/subscriptions` | `subscriptionApi` | `billing` | `subscriptions` |
| `REFUND` | 退款申请 | `/refund-requests` | `refundApi` | `billing` | `refund_requests`, `refund_events` |
| `AD_REWARD` | 广告奖励 | `/ad-rewards` | `adRewardApi` | `billing` | `ad_reward_sessions` |
| `NOTICE` | 公告 | `/notices` | `noticeApi` | `operations` | `notices`, `notice_deliveries` |
| `INBOX` | 站内消息 | `/inbox` | `inboxApi` | `notification` | `inbox_messages` |
| `SUPPORT` | 客服工单 | `/support-tickets` | `supportApi` | `support` | `support_tickets`, `support_messages` |
| `JOB` | 异步任务 | `/jobs` | `jobApi` | `async_job` | `async_jobs` |
| `TELEMETRY` | 最小化埋点 | `/telemetry` | `telemetryApi` | `analytics` | `telemetry_events` 或合规分析存储 |
| `AI_GATEWAY` | 模型供应商和路由 | `/admin/v1/model-*` | `modelAdminApi` | `ai_gateway` | `model_providers`, `ai_models`, `model_routes` |
| `PROMPT` | Prompt 版本 | `/admin/v1/prompts` | `promptAdminApi` | `ai_gateway` | `prompts`, `prompt_versions` |
| `EVALUATION` | 模型评测 | `/admin/v1/evaluation-*` | `evaluationAdminApi` | `evaluation` | `evaluation_suites`, `evaluation_runs` |
| `RISK` | 风控与申诉 | `/risk-events`, `/admin/v1/risk-*` | `riskApi`/`riskAdminApi` | `risk` | `risk_events`, `risk_policies`, `appeals` |
| `FEATURE_FLAG` | 功能开关/实验 | `/admin/v1/feature-flags` | `featureFlagAdminApi` | `operations` | `feature_flags`, `experiments`, `experiment_assignments` |
| `RELEASE` | App 发布 | `/app/releases`, `/admin/v1/app-releases` | `releaseApi` | `operations` | `app_releases` |
| `DATA_GOVERNANCE` | 导出删除与数据集 | `/me/data-*`, `/admin/v1/data-*` | `dataGovernanceApi` | `privacy` | `data_requests`, `datasets`, `dataset_items`, `export_jobs` |
| `ADMIN_RBAC` | 管理员与角色 | `/admin/v1/roles`, `/admin/v1/admin-users` | `adminRbacApi` | `admin_identity` | `admin_users`, `roles`, `role_permissions` |
| `AUDIT` | 审计 | `/admin/v1/audit-logs` | `auditAdminApi` | `audit` | `audit_logs` |
| `INTEGRATION` | 第三方集成 | `/admin/v1/integrations` | `integrationAdminApi` | `integration` | `integrations`, `webhook_events` |

禁止创建 `common`, `misc`, `helper`, `other`, `manager` 等无边界模块。公共代码必须说明它解决的横切问题，例如 `observability`, `security`, `serialization`。

## 4. 名称规则

### 4.1 各层命名

| 对象 | 规则 | 示例 |
|---|---|---|
| URL 资源 | 小写复数 kebab-case | `/target-profiles`, `/refund-requests` |
| URL path 参数 | lowerCamelCase | `{generationId}` |
| Query/JSON 字段 | lowerCamelCase | `relationshipStage`, `nextCursor` |
| HTTP Header | 标准或 Title-Case | `Authorization`, `Idempotency-Key`, `X-Request-Id` |
| TypeScript/Kotlin 类型 | PascalCase | `GenerationCreateRequest` |
| TypeScript 变量/函数 | lowerCamelCase | `createGeneration`, `candidateId` |
| Kotlin 属性/函数 | lowerCamelCase | `createGeneration`, `candidateId` |
| Python 函数/局部变量 | snake_case | `create_generation`, `candidate_id` |
| Python DTO JSON 别名 | lowerCamelCase | 内部 `candidate_id` 映射 wire `candidateId` |
| Java/Kotlin 包 | 全小写 | `com.example.generation` |
| Python 模块 | snake_case | `generation_service.py` |
| 数据表/列 | 复数 snake_case / snake_case | `generation_tasks`, `created_at` |
| 枚举值 | UPPER_SNAKE_CASE | `PENDING_PAYMENT` |
| 模块编码 | UPPER_SNAKE_CASE | `DATA_GOVERNANCE` |
| SSE 事件 | lower.dot.past-tense | `candidate.completed` |
| 领域事件 | lower.dot.past-tense.vN | `billing.order.paid.v1` |
| 队列/Topic | lower.dot.purpose.vN | `generation.task.execute.v1` |
| 环境变量 | UPPER_SNAKE_CASE | `MODEL_GATEWAY_BASE_URL` |
| 指标名 | snake_case，项目统一前缀 | `love_reply_generation_duration_seconds` |

线上 JSON 字段是跨语言权威名称。各语言内部可遵循语言惯例，但序列化/反序列化必须显式映射，不得改变 wire 名称。

### 4.2 缩写规则

缩写按普通单词处理：JSON 使用 `ocrStatus`, `aiModelId`, `apiVersion`, `imageUrl`, `ipAddress`；类型使用 `OcrResult`, `AiModel`, `ApiError`, `ImageUrl`。禁止同时出现 `OCRStatus`、`ocr_status` 和 `ocrState` 表达同一线上字段。

### 4.3 字段后缀

| 语义 | 后缀/前缀 | 示例 |
|---|---|---|
| 主键/外键 | `Id` | `userId`, `generationId` |
| 时间点 | `At` | `createdAt`, `expiresAt` |
| 日历日期 | `Date` | `birthdayDate` |
| 时长 | `DurationMs`/`TtlSeconds` | `requestDurationMs`, `streamTtlSeconds` |
| 布尔 | `is`, `has`, `can`, `should` | `isActive`, `hasMore`, `canRetry` |
| 数量 | `Count` | `retryCount`, `unreadCount` |
| 游标 | `Cursor` | `nextCursor` |
| 版本 | `Version` | `schemaVersion`, `resourceVersion` |
| 金额最小单位 | `AmountMinor` | `priceAmountMinor` |
| 币种 | `Currency` | `priceCurrency: CNY` |
| 百分比/比例 | `Rate`，范围另行声明 | `successRate` |
| URL | `Url` | `downloadUrl` |
| 列表 | 使用复数名词 | `styleIds`, `riskTips` |

禁止 `data1`, `value`, `obj`, `info`, `list`, `flag`, `type`, `status` 等脱离资源语境的变量。使用 `generationStatus`, `actionType`, `isTrainingAllowed` 等完整名称。

### 4.4 Null、缺省与空集合

* 字段未出现：调用方没有提供，更新接口保持原值。  
* 字段为 `null`：调用方明确清空，只有 Schema 标记 nullable 时允许。  
* 空字符串：真实值为空，仅允许自由文本字段；ID、枚举和时间禁止空字符串。  
* 空数组：明确设置为空集合。列表响应必须返回 `[]`，不能返回 `null`。  
* 数字 `0` 和布尔 `false` 是有效值，服务端不得按“未提供”处理。

## 5. 全局字段字典

| Wire 字段 | 类型 | 含义/约束 |
|---|---|---|
| `requestId` | string | 单次 HTTP 请求 ID，由边缘/API 生成 |
| `traceId` | string | 跨服务追踪 ID，不向用户泄露内部拓扑 |
| `clientRequestId` | string | 客户端生成的业务去重 ID，同一动作重试保持不变 |
| `idempotencyKey` | header string | 有副作用 HTTP 请求的幂等键，不放 JSON body |
| `schemaVersion` | string | 消息/事件 Schema 版本，如 `1.0` |
| `resourceVersion` | integer | 乐观锁版本，从 1 递增 |
| `userId` | string | 用户 ID，前缀 `usr_` 或 UUID/ULID |
| `deviceId` | string | 安装实例/登录设备 ID |
| `profileId` | string | 对象档案 ID |
| `memoryId` | string | 档案记忆 ID |
| `attachmentId` | string | 私有附件 ID |
| `ocrVersion` | integer | OCR 校正版本 |
| `generationId` | string | 生成任务 ID |
| `parentGenerationId` | string/null | 重生成或改写的父任务 ID |
| `candidateId` | string | 候选回复 ID |
| `conversationId` | string | 历史会话 ID |
| `quoteId` | string | 短期生成报价 ID |
| `modelId` | string | 对客户端公开的逻辑模型 ID，不暴露供应商密钥 |
| `modelRouteId` | string | 服务端路由版本引用 |
| `promptVersionId` | string | 实际使用的 Prompt 不可变版本 ID |
| `riskEventId` | string | 风控事件 ID |
| `appealId` | string | 申诉 ID |
| `planCode` | string enum | 订阅计划稳定编码，不使用展示名称判断权限 |
| `productId` | string | 可售商品 ID |
| `orderId` | string | 平台订单 ID，不等于渠道交易号 |
| `providerTransactionId` | string | 支付渠道交易 ID，敏感日志需掩码 |
| `subscriptionId` | string | 订阅关系 ID |
| `refundRequestId` | string | 用户退款申请 ID |
| `walletAccountId` | string | 钱包账户 ID |
| `energyAmount` | integer | 算力单位变化量，可正可负 |
| `energyBalance` | integer | 结算后的算力余额 |
| `reservedEnergy` | integer | 创建生成时预占 |
| `chargedEnergy` | integer | 成功后实际结算 |
| `inputTokens` | integer | 模型输入 Token，非负 |
| `outputTokens` | integer | 模型输出 Token，非负 |
| `consentType` | enum | 授权用途，如 `SERVICE_REQUIRED`, `MODEL_TRAINING` |
| `consentVersion` | string | 用户同意的文本版本 |
| `jobId` | string | 通用异步任务 ID |
| `ticketId` | string | 客服工单 ID |
| `noticeId` | string | 公告 ID |
| `featureFlagKey` | string | 稳定功能键，发布后不复用 |
| `experimentId` | string | 实验 ID |
| `variantId` | string | 实验变体 ID |
| `createdAt` | RFC 3339 string | 服务端创建时间，UTC |
| `updatedAt` | RFC 3339 string | 服务端更新时间，UTC |
| `expiresAt` | RFC 3339 string/null | 过期时间，无过期可为 null |

所有 ID 在客户端均视为不透明字符串，不解析前缀、不假设长度、不按字典序推断业务状态。

## 6. 公共枚举

公共枚举由 `ai-collaboration-manifest.yaml` 和未来 OpenAPI 共同维护。客户端必须对未知枚举提供 `UNKNOWN` 降级展示，但不能把 `UNKNOWN` 回传覆盖服务端真实值。

| 枚举 | 允许值 |
|---|---|
| `RelationshipStage` | `MATCHING`, `DATING`, `AMBIGUOUS`, `IN_RELATIONSHIP`, `CONFLICT`, `NO_CONTACT`, `OTHER` |
| `CommunicationGoal` | `START_CONVERSATION`, `KEEP_CONVERSATION`, `ACCEPT_INVITATION`, `DECLINE_POLITELY`, `INVITE_DATE`, `APOLOGIZE`, `SET_BOUNDARY`, `RESOLVE_CONFLICT`, `OTHER` |
| `ReplyStrategy` | `SAFE`, `PUSH_PULL`, `DIRECT` |
| `SpeakerRole` | `SELF`, `OTHER`, `UNKNOWN` |
| `AttachmentStatus` | `UPLOADING`, `SCANNING`, `PARSING`, `READY`, `REJECTED`, `DELETED` |
| `GenerationStatus` | `CREATED`, `QUOTA_RESERVED`, `PARSING`, `ANALYZING`, `GENERATING`, `FILTERING`, `SUCCEEDED`, `FAILED`, `CANCELLED` |
| `SafetyStatus` | `PENDING`, `PASSED`, `BLOCKED`, `REVIEW_REQUIRED` |
| `CandidateActionType` | `COPY`, `FAVORITE`, `SENT`, `LIKE`, `DISLIKE`, `OUTCOME` |
| `OrderStatus` | `CREATED`, `PENDING_PAYMENT`, `PAID`, `FAILED`, `CANCELLED`, `REFUND_PENDING`, `REFUNDED` |
| `RefundStatus` | `REQUESTED`, `REVIEWING`, `APPROVED`, `REJECTED`, `PROCESSING`, `REFUNDED`, `FAILED` |
| `JobStatus` | `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `EXPIRED` |
| `ContentStatus` | `DRAFT`, `IN_REVIEW`, `APPROVED`, `PUBLISHED`, `REVOKED` |
| `DataRequestStatus` | `REQUESTED`, `IDENTITY_VERIFIED`, `PROCESSING`, `COMPLETED`, `REJECTED`, `CANCELLED` |
| `ConsentType` | `TERMS_OF_SERVICE`, `PRIVACY_POLICY`, `SERVICE_REQUIRED`, `MODEL_TRAINING`, `MARKETING` |
| `SupportTicketType` | `GENERAL`, `BILLING`, `REFUND`, `PRIVACY`, `CONTENT_COMPLAINT`, `ACCOUNT_SECURITY` |

展示文案不等于枚举值。Android 与管理后台通过本地/远程 i18n 将枚举映射为中文，不把中文写入数据库状态列。

## 7. HTTP API 连接标准

### 7.1 环境与 Base URL

| 环境 | 用户 API | 管理 API | 说明 |
|---|---|---|---|
| local | `http://localhost:8080/v1` | `http://localhost:8080/admin/v1` | 仅本机 |
| dev | `https://api-dev.example.com/v1` | `https://admin-api-dev.example.com/admin/v1` | 共享开发环境 |
| staging | `https://api-staging.example.com/v1` | `https://admin-api-staging.example.com/admin/v1` | 支付沙箱和发布验收 |
| production | `https://api.example.com/v1` | `https://admin-api.example.com/admin/v1` | 域名由部署配置注入 |

代码中禁止硬编码域名、Token、模型名、产品价格、额度和功能开关。

### 7.2 必需请求头

| Header | 适用范围 | 说明 |
|---|---|---|
| `Authorization` | 登录后的用户/管理 API | `Bearer <accessToken>` |
| `X-Request-Id` | 全部，可由客户端提供 | 非法/重复时服务端可替换并返回最终值 |
| `X-Client-Version` | 客户端 API | App 语义版本 |
| `X-Platform` | 客户端 API | `ANDROID`, `ADMIN_WEB` |
| `X-Device-Id` | Android 登录后请求 | 安装实例 ID，不作为唯一鉴权依据 |
| `Accept-Language` | 展示内容接口 | BCP 47，如 `zh-CN` |
| `Idempotency-Key` | 有副作用且可重试请求 | 相同用户、接口和 key 返回同一业务结果 |
| `If-Match` | 受版本保护的更新 | 值为资源版本或 ETag |

服务端响应统一返回 `X-Request-Id`。限流响应返回标准 `Retry-After`，业务体同时提供 `retryAfterSeconds`。

### 7.3 Method 语义

* `GET`：只读、可安全重试，不产生业务副作用；曝光埋点使用独立事件接口。  
* `POST`：创建资源、执行命令或提交动作；创建/支付/结算/发布必须幂等。  
* `PUT`：完整替换已知子资源或设置确定状态，如 OCR 完整校正。  
* `PATCH`：部分更新，未出现字段保持不变，通常要求 `If-Match`。  
* `DELETE`：删除或发起删除；异步删除返回任务，不伪装同步完成。

### 7.4 `operationId` 与接口函数名

每个 OpenAPI operation 必须声明唯一的 lowerCamelCase `operationId`。生成的 Android/TypeScript Client 方法直接使用 `operationId`；后端应用 Handler 使用其 PascalCase 形式；契约测试使用 snake_case 形式。

| HTTP 行为 | operationId 模板 | 示例 |
|---|---|---|
| 列表 | `list<Entities>` | `listTargetProfiles` |
| 单项 | `get<Entity>` | `getGeneration` |
| 创建 | `create<Entity>` | `createGeneration` |
| 部分更新 | `update<Entity>` | `updateTargetProfile` |
| 删除 | `delete<Entity>` | `deleteConversation` |
| 明确动作 | `<verb><Entity>` | `cancelGeneration`, `publishPrompt`, `retryWebhookEvent` |
| 流 | `stream<Entity>Events` | `streamGenerationEvents` |

OpenAPI `tags` 必须使用 manifest 中的 `moduleCode`。禁止自动生成 `postGenerations`, `generationsPost`, `callApi1` 等与业务语义不稳定的名称。一个 operationId 发布后不可复用给另一条路径。

派生示例：

```text
OpenAPI operationId: createGeneration
TypeScript/Kotlin client: createGeneration(...)
Backend handler: CreateGenerationHandler
Contract test: create_generation_returns_reserved_task
Metric operation label: create_generation
```

### 7.5 成功响应

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "requestId": "req_01J...",
  "timestamp": "2026-08-07T12:30:00Z"
}
```

`message` 仅用于诊断或默认提示，正式 UI 优先按稳定 `code` 映射本地文案。

### 7.6 错误响应

```json
{
  "code": "INVALID_ARGUMENT",
  "message": "request validation failed",
  "data": null,
  "error": {
    "fieldErrors": [
      {"field": "context.relationshipStage", "reason": "UNSUPPORTED_VALUE"}
    ],
    "retryable": false,
    "retryAfterSeconds": null,
    "details": {}
  },
  "requestId": "req_01J...",
  "timestamp": "2026-08-07T12:30:00Z"
}
```

`details` 只能放契约允许的安全字段，禁止返回堆栈、SQL、Prompt、供应商密钥、内部 URL 或原始隐私数据。

### 7.7 分页、筛选和排序

* 游标分页：`cursor`, `limit`，默认 20，最大 100。  
* 列表响应：`items`, `nextCursor`, `hasMore`。  
* 时间筛选：`createdFrom`, `createdTo`，均为 RFC 3339。  
* 状态筛选：字段使用资源全名，如 `orderStatus`，可重复 query 或逗号分隔的方式由 OpenAPI 固定，不能混用。  
* 排序：`sort=createdAt:desc`；只允许 OpenAPI 白名单字段。  
* 关键词：统一 `query`，服务端规定可搜索字段，不允许客户端传任意 SQL 字段名。

### 7.8 幂等和并发

1. `Idempotency-Key` 的作用域是调用者 + method + normalized path，至少保存 24 小时。  
2. 同 key、同请求体返回原响应；同 key、不同请求体返回 `409 IDEMPOTENCY_KEY_REUSED`。  
3. 生成、订单、退款、权益调整、发布和 Webhook 消费均使用数据库唯一约束兜底。  
4. 可编辑资源携带 `resourceVersion`；版本不一致返回 `409 VERSION_CONFLICT`。  
5. 钱包和权益不允许“读取余额后写回”，只能通过追加 ledger entry 原子结算。

## 8. SSE、领域事件与 Webhook

### 8.1 SSE 连接

前端方法统一命名 `streamGenerationEvents(generationId, lastEventId?)`。Android 使用支持自定义 Header 的 HTTP Client；H5 如无法给 `EventSource` 设置 Authorization，应通过短期一次性 stream ticket，不把 access Token 放 URL。

SSE `data` 使用统一信封：

```json
{
  "schemaVersion": "1.0",
  "eventId": "18",
  "eventType": "candidate.completed",
  "occurredAt": "2026-08-07T12:30:02Z",
  "generationId": "gen_01J...",
  "sequence": 18,
  "payload": {}
}
```

客户端按 `eventId` 去重、按 `sequence` 发现缺口；`candidate.completed` 的完整文本覆盖本地 delta 拼接结果。断线先重连，收到 `410 STREAM_EXPIRED` 再查询 `GET /generations/{generationId}`。

### 8.2 内部领域事件

领域事件使用不可变过去式：`billing.order.paid.v1`, `generation.task.succeeded.v1`, `privacy.consent.revoked.v1`。公共字段：

```json
{
  "eventId": "evt_01J...",
  "eventType": "billing.order.paid.v1",
  "occurredAt": "2026-08-07T12:30:00Z",
  "producer": "billing-service",
  "aggregateType": "order",
  "aggregateId": "ord_01J...",
  "correlationId": "req_01J...",
  "causationId": "payevt_01J...",
  "schemaVersion": "1.0",
  "payload": {}
}
```

跨数据库副作用使用 transactional outbox，不允许“先提交数据库，再尽力发消息”。消费者按 `eventId` 幂等。

### 8.3 第三方 Webhook

每个 Provider Adapter 将外部字段映射为内部统一对象，业务服务不得直接依赖微信/支付宝字段名。原始回调只在加密审计存储保留。统一验证顺序：请求大小 → 时间窗 → 签名 → 商户身份 → 事件去重 → 订单金额/币种 → 状态机迁移 → 事务结算 → 供应商要求的 ACK。

## 9. 前端连接与变量标准

### 9.1 分层

```text
Screen/Component
  -> ViewModel/Store
    -> Domain UseCase
      -> xxxApi（手写薄封装）
        -> generated-api（OpenAPI 生成）
          -> HttpClient/SseClient
```

* Screen/Component 禁止直接 `fetch`, Retrofit 或拼 URL。  
* `generated-api` 禁止手改；业务友好方法放在 `xxxApi`。  
* API DTO 不直接作为 UI 状态；通过 mapper 转为 ViewModel，避免后端新增字段触发 UI 重构。  
* Token 刷新只在 HttpClient 拦截器处理一次，业务页面不重复实现。  
* 每个页面明确 `initial/loading/content/empty/error/offline/permissionDenied` 状态。

### 9.2 Client 方法命名

| 操作 | 命名模板 | 示例 |
|---|---|---|
| 获取单项 | `get<Entity>` | `getGeneration(generationId)` |
| 获取列表 | `list<Entities>` | `listTargetProfiles(params)` |
| 创建 | `create<Entity>` | `createGeneration(request)` |
| 更新 | `update<Entity>` | `updateTargetProfile(profileId, request)` |
| 删除 | `delete<Entity>` | `deleteConversation(conversationId)` |
| 命令动作 | `<verb><Entity>` | `cancelGeneration`, `publishPrompt` |
| 流式订阅 | `stream<Entity>Events` | `streamGenerationEvents` |
| 本地转换 | `map<X>To<Y>` | `mapGenerationDtoToUiModel` |

禁止 `doRequest`, `callApi`, `handleData`, `getInfo`, `submitForm` 等无法从名称判断资源和副作用的方法。

### 9.3 类型后缀

| 类型用途 | 后缀 | 示例 |
|---|---|---|
| 创建请求 | `CreateRequest` | `GenerationCreateRequest` |
| 更新请求 | `UpdateRequest` | `TargetProfileUpdateRequest` |
| 命令请求 | `<Verb>Request` | `GenerationCancelRequest` |
| API 响应数据 | `Response` | `GenerationResponse` |
| 列表项 | `ListItem` | `ConversationListItem` |
| UI 模型 | `UiModel` | `GenerationUiModel` |
| 页面状态 | `UiState` | `GenerationUiState` |
| 领域模型 | 无 DTO 后缀 | `Generation`, `Order` |

## 10. 后端分层与变量标准

### 10.1 调用方向

```text
Controller/Route
  -> Application Service / Command Handler
    -> Domain Model / Domain Service
      -> Repository Port / Provider Port
        -> Database Adapter / Provider Adapter
```

* Controller 只处理协议、鉴权上下文、Schema 校验和响应映射，不写业务规则。  
* Application Service 定义事务边界、幂等和跨领域编排。  
* Domain 不依赖 Web 框架、ORM、供应商 SDK 或管理后台。  
* Repository 不返回 ORM 对象到 Controller。  
* 支付、短信、模型、对象存储均通过 Provider Adapter 隔离。

### 10.2 后端类型命名

| 类型 | 命名 | 示例 |
|---|---|---|
| HTTP 输入 | `XxxRequest` | `GenerationCreateRequest` |
| HTTP 输出 | `XxxResponse` | `GenerationResponse` |
| 应用命令 | `XxxCommand` | `CreateGenerationCommand` |
| 应用查询 | `XxxQuery` | `GetGenerationQuery` |
| Handler | `XxxHandler` | `CreateGenerationHandler` |
| 领域实体 | 业务名 | `GenerationTask` |
| Repository 接口 | `XxxRepository` | `GenerationRepository` |
| 外部网关 | `XxxGateway` | `ModelGateway`, `PaymentGateway` |
| 数据库记录 | `XxxRecord`/语言 ORM 惯例 | `GenerationTaskRecord` |
| 映射器 | `XxxMapper` | `GenerationMapper` |

### 10.3 事务与领域边界

* `billing` 独占订单、钱包、权益和退款写入；其他模块只能调用其公开命令。  
* `generation` 可请求权益报价/预占，但不能直接更新钱包表。  
* `privacy` 独占授权、导出、删除和训练撤回状态。  
* `content` 发布后只生成新版本，不覆盖已发布版本。  
* 管理 API 复用应用服务，不复制一套不同业务规则。  
* 跨边界流程使用 saga/可靠事件并明确补偿，不使用分布式锁掩盖模型不清。

## 11. 数据库标准

### 11.1 命名与类型

* 表名使用复数 `snake_case`；主键列统一 `id`，外键为 `<entity>_id`。  
* 时间列使用 `created_at`, `updated_at`, `deleted_at`, `expires_at`，类型为带时区时间。  
* 乐观锁列 `resource_version BIGINT NOT NULL DEFAULT 1`。  
* 金额为 `BIGINT` 最小货币单位并配 `currency CHAR(3)`；禁止浮点。  
* Token/算力为 `BIGINT`；变化量和余额分列。  
* 枚举优先用受约束的稳定字符串；修改枚举需兼容旧值。  
* JSON/JSONB 只用于供应商原始载荷、版本化配置或真正扩展字段，核心查询字段必须结构化。  
* 用户可见资源应有 `user_id` 及必要复合索引，所有查询强制租户/用户边界。

### 11.2 迁移规则

1. 已在共享环境执行的迁移不可修改，只能新增迁移修正。  
2. 破坏性变更采用 expand → migrate → contract 三阶段。  
3. 新非空列先允许空/提供默认值，回填后再加约束。  
4. 删除列前至少跨一个兼容发布周期，并确认所有消费者已停止读取。  
5. 每个迁移说明回滚或前滚恢复策略、预计锁表时间和数据量影响。

### 11.3 不可变记录

`wallet_ledger`, `payment_events`, `refund_events`, `audit_logs`, `consent_records` 只追加不原地修改。纠错通过补偿记录表达，禁止直接改历史金额、授权或审计内容。

## 12. 配置、密钥和日志变量

### 12.1 环境变量

使用 `<DOMAIN>_<PURPOSE>_<QUALIFIER>`：

```text
APP_ENV
HTTP_PORT
DATABASE_URL
REDIS_URL
OBJECT_STORAGE_BUCKET_PRIVATE
MODEL_GATEWAY_BASE_URL
MODEL_GATEWAY_API_KEY
PAYMENT_WECHAT_MERCHANT_ID
PAYMENT_WECHAT_PRIVATE_KEY_REF
JWT_SIGNING_KEY_REF
OTEL_EXPORTER_OTLP_ENDPOINT
```

生产密钥值不进入仓库、日志、Markdown、测试快照或 AI 对话；配置文件只保存 Secret Manager 引用。

### 12.2 日志字段

结构化日志公共字段：`timestamp`, `level`, `service`, `moduleCode`, `environment`, `requestId`, `traceId`, `userIdHash`, `operation`, `result`, `durationMs`, `errorCode`。禁止记录 access Token、验证码、支付密钥、聊天全文、截图 URL、Prompt 全文和完整个人标识。

### 12.3 指标

指标名示例：

```text
love_reply_http_requests_total
love_reply_http_request_duration_seconds
love_reply_generation_tasks_total
love_reply_generation_duration_seconds
love_reply_generation_reserved_energy
love_reply_generation_charge_mismatch_total
love_reply_payment_webhook_total
love_reply_sse_reconnect_total
```

高基数字段如 `userId`, `generationId`, `requestId` 不得作为 metrics label。

## 13. 错误码命名与归属

错误码为 `UPPER_SNAKE_CASE`，稳定且与 HTTP 状态分离。模块专属错误优先使用明确业务名：

| 范围 | 示例 |
|---|---|
| 通用参数/资源 | `INVALID_ARGUMENT`, `RESOURCE_NOT_FOUND`, `VERSION_CONFLICT` |
| 认证 | `TOKEN_EXPIRED`, `SESSION_REVOKED`, `MFA_REQUIRED` |
| 权益账务 | `QUOTA_INSUFFICIENT`, `QUOTE_EXPIRED`, `LEDGER_CONFLICT` |
| OCR | `OCR_CONFIRMATION_REQUIRED`, `OCR_PARSE_FAILED` |
| 生成 | `GENERATION_TIMEOUT`, `MODEL_PROVIDER_UNAVAILABLE`, `STREAM_EXPIRED` |
| 安全 | `CONTENT_BLOCKED`, `REVIEW_REQUIRED`, `APPEAL_ALREADY_OPEN` |
| 支付 | `PAYMENT_SIGNATURE_INVALID`, `PAYMENT_AMOUNT_MISMATCH`, `ORDER_ALREADY_PAID` |
| 数据治理 | `CONSENT_REQUIRED`, `DATA_REQUEST_IN_PROGRESS`, `EXPORT_EXPIRED` |

新增错误码必须同时更新 OpenAPI、客户端映射、管理后台提示、契约样例和测试；禁止复用一个错误码表达多种用户动作。

## 14. 契约版本与变更流程

### 14.1 兼容性

兼容变更：新增可选字段、新增端点、新增不会改变默认行为的枚举之外能力。  
潜在破坏变更：删除/重命名字段、改变类型/含义、收紧校验、改变默认值、给封闭枚举新增调用方无法处理的值、修改状态迁移。

URL `/v1` 只在无法通过兼容演进解决时升级 `/v2`。字段重命名采用“新增新字段 → 双写/双读 → 消费者迁移 → 标记废弃 → 下一主版本删除”。

### 14.2 Contract-first 流程

1. 创建变更提案，写明 `moduleCode`、用户场景、Schema diff、兼容性、数据迁移和回滚。  
2. 更新 `ai-collaboration-manifest.yaml`（若模块/枚举/依赖变化）。  
3. 更新 OpenAPI/Event Schema 和固定请求响应样例。  
4. 运行 lint、breaking-change 检查和 Schema 示例校验。  
5. 重新生成 Android、TypeScript 和后端 DTO；生成目录不得手改。  
6. 先合入可向后兼容的 Provider，再合入 Consumer。  
7. 运行契约测试、端到端测试、安全测试和迁移测试。  
8. 更新联动矩阵、变更日志和必要 ADR 后发布。

## 15. 多 AI 工具协作规则

### 15.1 工作包格式

每个 AI 工具开始编码前必须获得或创建以下工作包记录：

```yaml
taskId: API-GENERATION-001
title: Implement generation create and snapshot APIs
moduleCode: GENERATION
owner: tool-or-agent-name
status: planned
allowedPaths:
  - services/api/src/generation/**
  - contracts/openapi/paths/generations.yaml
dependsOn:
  - API-ENTITLEMENT-001
contractVersion: 1.0.0
acceptanceTests:
  - generation_create_is_idempotent
  - failed_generation_releases_reservation
handoffNotes: ""
```

同一时刻一个路径只能有一个写入责任人。跨模块修改先通知对应模块责任人或拆成独立契约任务。

### 15.2 允许并行的任务

* Android UI 与后端实现可在 OpenAPI 和 fixtures 冻结后并行。  
* 管理后台与用户端可并行，但共享 generated types，不能复制类型。  
* 数据库迁移与 Repository 可在领域模型确认后并行。  
* Provider mock、契约测试和真实 Adapter 可并行。

### 15.3 禁止事项

* 禁止组件、页面或 Controller 自己拼接未登记 URL。  
* 禁止手改生成代码或复制一份相似 DTO。  
* 禁止未更新 manifest/OpenAPI 就重命名字段、枚举、路径、表或事件。  
* 禁止用假成功、静态余额、固定模型结果或吞掉异常来“完成联调”。  
* 禁止跨模块直接读写他人数据表。  
* 禁止把开发环境密钥、用户隐私数据或生产日志发送给 AI 工具。  
* 禁止在缺少幂等和账务测试时合入支付、退款、额度调整或生成结算。

### 15.4 交接模板

```text
Task ID:
Module code:
Contract version:
Changed files:
Implemented behavior:
Deliberately not implemented:
Migrations:
Feature flags:
Tests run and results:
Known risks:
Next consumer/provider task:
```

交接不能只写“已完成”。必须让另一个没有对话上下文的工具能通过文件、契约版本和测试复现结果。

## 16. 测试与合并门禁

每个模块至少具备：

1. **Schema 测试：** 请求、响应、事件和错误样例通过 Schema。  
2. **契约测试：** Client mock 与服务端 Provider 对相同 fixtures。  
3. **单元测试：** 状态迁移、权限、幂等、结算和映射。  
4. **集成测试：** 数据库唯一约束、事务、outbox、缓存和 Provider mock。  
5. **端到端测试：** 对应联动矩阵的正常与异常闭环。  
6. **安全测试：** 越权、注入、上传、重放、敏感日志和密钥扫描。  
7. **兼容测试：** OpenAPI breaking change 检查、旧客户端 fixtures 和数据库迁移。

合并最低条件：契约 lint 通过、生成代码无未提交差异、相关测试通过、无跨模块越权写入、文档/manifest 版本同步、所有 TODO 均有任务 ID。

## 17. 推荐开发顺序

1. 建立仓库结构、OpenAPI 3.1、公共 Schema、生成器和 CI 契约门禁。  
2. 实现 `AUTH`, `USER`, `CONSENT`, `APP_CONFIG` 基础能力。  
3. 实现 `ENTITLEMENT`, `WALLET` 的报价、预占、结算和账本。  
4. 实现 `GENERATION`, `CANDIDATE` 的文本生成、SSE 和失败释放。  
5. 实现 `CONVERSATION`, `FAVORITE`, `TELEMETRY` 和最小管理观测。  
6. 实现 `ATTACHMENT`, `OCR` 校正闭环，再开放截图能力。  
7. 实现 `PRODUCT`, `ORDER`, `SUBSCRIPTION`, `REFUND` 并通过支付沙箱。  
8. 实现 `SUPPORT`, `INBOX`, `RISK`, `DATA_GOVERNANCE`。  
9. 最后开放悬浮球、复杂 Agent、动态 Icon、广告奖励和训练数据集。

## 18. Definition of Ready / Done

### Ready

* 任务有唯一 `taskId` 和 `moduleCode`。  
* path、Schema、枚举、错误码和权限已进入契约。  
* 依赖任务、允许修改路径、迁移和验收测试已明确。  
* 没有悬而未决、会改变 wire contract 的产品问题。

### Done

* Provider、Consumer、数据库迁移、权限和异常状态均已实现。  
* 契约、单元、集成和相关端到端测试通过。  
* 监控、日志脱敏、审计和 Feature Flag 已接入。  
* 生成代码与 OpenAPI 无漂移，联动矩阵和交接记录已更新。  
* 不存在无任务 ID 的 TODO、硬编码密钥、固定测试数据或静默异常。
