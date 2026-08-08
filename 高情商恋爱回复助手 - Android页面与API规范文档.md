# 《高情商恋爱回复助手》Android 页面与前后台 API 联动规范

> 文档版本：2.1  
> 文档状态：设计基线，可用于原型、客户端、服务端和管理后台联调  
> 验证范围：功能覆盖、接口映射、状态流转、异常恢复、安全与运维闭环  
> 非验证范围：生产可用性、模型效果、支付渠道资质和 ROM 实机兼容性，这些必须通过实现、测试和外部审核验证

> 协同开发规则：模块编码、变量命名、代码分层和变更门禁遵循《多 AI 协同开发接口命名与连接标准》；机器可读模块、枚举与依赖清单见 `ai-collaboration-manifest.yaml`。OpenAPI 生成前本文档是 HTTP 行为基线，生成后 `contracts/openapi/openapi.yaml` 是 wire contract 单一事实来源。

## 1. 系统边界与可行性结论

系统由 Android 客户端、业务 API、AI 编排服务、对象存储、PostgreSQL/Redis、管理后台和第三方支付/模型服务组成。

1. Android 系统分享面板可作为稳定的快捷入口；悬浮窗需要用户单独授权，只能作为增强功能。  
2. 不使用无障碍服务自动读取或填写微信/QQ，不承诺跨应用“一键填入”。生成结果通过系统剪贴板或分享面板交还用户。  
3. OCR/Vision 可以提取聊天内容，但说话人、顺序和表情含义可能识别错误，客户端必须提供校正页。  
4. SSE 在移动网络切换或 App 进入后台时会断开，必须支持 `Last-Event-ID` 重连和任务状态查询。  
5. Token 消耗只能在生成完成后精确获知，因此采用“生成前报价、创建时预占、完成后结算、失败后释放”的账务模型。  
6. 动态图标只能切换 APK 内预置的 `activity-alias`；主题和 i18n 远程配置必须有签名、版本和本地回退。  
7. 服务端私有部署模型可作为上游故障兜底；不把 7B 模型端侧运行作为默认能力。

## 2. 用户角色与权限

| 角色 | 权限范围 |
|---|---|
| 游客 | 查看公开锦囊、产品与隐私说明，不可生成或保存数据 |
| 注册用户 | 使用本人额度、管理本人会话/档案/收藏/订单/隐私设置 |
| 内容运营 | 管理锦囊、公告和多语言内容，不可查看原始私聊内容 |
| 客服/财务 | 按授权查看用户权益、订单和退款，不可读取模型密钥 |
| AI 运营 | 管理模型路由、Prompt 和评测集脱敏样本 |
| 风控审核员 | 处理风险事件和申诉，敏感内容按工单临时授权展示 |
| 系统管理员 | 管理角色、系统配置和发布，不默认拥有业务敏感数据读取权 |
| 审计员 | 只读查看操作审计、配置版本和账务流水 |

管理后台采用 RBAC 和最小权限原则。高风险操作要求二次确认，密钥变更、退款、权益调整、数据集导出和风险放行必须记录审计日志。

## 3. Android 信息架构

### 3.1 四个主 Tab

| Tab | 核心页面 | 主要能力 |
|---|---|---|
| 帮回 | 输入与配置 | 文本/截图、关系阶段、沟通目标、风格、对象档案、额度报价 |
| 锦囊 | 分类与搜索 | 场景卡片、案例、收藏、相关推荐 |
| 档案 | 对象档案 | 多对象、偏好/禁忌、记忆开关、逐条编辑与删除 |
| 我的 | 账户中心 | 历史、收藏、会员钱包、订单、消息、客服、设备、隐私、安全和设置 |

### 3.2 五个二级页面

1. **截图校正页：** 显示 OCR 文本、说话人和顺序，用户确认后才能生成。  
2. **生成结果页：** 流式展示分析、风险提示和三条候选，支持复制、收藏、改写和反馈。  
3. **历史详情页：** 查看输入、配置、候选、用量和反馈，支持删除。  
4. **会员/钱包页：** 展示权益、产品、额度流水、订单与订阅管理。  
5. **隐私与数据页：** 管理保存策略、训练授权、数据导出和账号注销。

### 3.3 全局入口

* **系统分享入口：** 接收 `text/plain` 与 `image/*`，进入输入页或截图校正页。  
* **悬浮球：** 用户主动授权后开启，仅负责拉起输入面板；权限拒绝、系统回收和厂商限制必须有降级说明。  
* **剪贴板：** 只在用户点击粘贴/复制时访问，不在后台静默读取。

## 4. 管理后台信息架构

管理后台共 9 个一级模块、28 个子页面：

| 一级模块 | 子页面 |
|---|---|
| 1. 仪表大盘 | 运行总览；营收与模型成本；质量与安全指标 |
| 2. 用户与权益 | 用户列表；用户详情与设备；权益钱包与调整流水 |
| 3. AI 模型与 Gateway | 供应商密钥；模型与路由；Prompt 版本；评测与质量门禁 |
| 4. 动态运营 | 公告；主题与预置图标；i18n 词典；功能开关与实验 |
| 5. 支付与财务 | 商品订阅；订单退款；对账与回调异常 |
| 6. 内容 CMS | 分类标签；内容编辑；审核发布 |
| 7. 系统配置 | App 版本；全局配置；第三方集成 |
| 8. 日志与风控 | 请求日志；策略/事件/申诉；告警与限流 |
| 9. 数据治理 | 授权与用户数据请求；数据集与导出任务 |

总数校验：`3 + 3 + 4 + 4 + 3 + 3 + 3 + 3 + 2 = 28`。

## 5. API 通用规范

### 5.1 基础约定

* Base URL：`https://api.example.com/v1`；管理端为 `/admin/v1`；服务间回调为 `/internal/v1`。  
* JSON 使用 UTF-8 和小写驼峰命名。时间统一为 ISO 8601 UTC，例如 `2026-08-07T12:30:00Z`。  
* ID 使用不可枚举的 UUID/ULID 字符串；金额使用最小货币单位整数；Token/额度使用整数。  
* 普通 JSON 请求使用 `Content-Type: application/json`；图片使用 `multipart/form-data`；SSE 使用 `text/event-stream`。  
* 用户 API 使用 `Authorization: Bearer <accessToken>`；管理 API 使用独立管理身份和 MFA。  
* 所有创建、扣费、退款、权益调整和发布请求必须携带 `Idempotency-Key`。  
* 更新资源使用 `resourceVersion` 或 `If-Match` 做乐观锁，避免覆盖他人修改。  
* 列表统一使用游标分页：`?cursor=&limit=20`，响应返回 `items`、`nextCursor`、`hasMore`。

### 5.2 通用 JSON 响应

```json
{
  "code": "OK",
  "message": "success",
  "data": {},
  "requestId": "req_01J...",
  "timestamp": "2026-08-07T12:30:00Z"
}
```

HTTP 状态码表达协议结果，`code` 表达稳定业务错误。SSE、文件下载和第三方 Webhook 不使用该包装。

错误响应统一增加 `error` 对象：

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

客户端按稳定 `code` 决定动作，不能解析 `message` 判断业务。`details` 禁止返回堆栈、SQL、Prompt、密钥、内部 URL 或原始隐私数据。

### 5.3 核心错误码

| HTTP | code | 客户端处理 |
|---|---|---|
| 400 | `INVALID_ARGUMENT` | 标记具体字段，不清空用户输入 |
| 401 | `TOKEN_EXPIRED` | 单次刷新 Token 后重放安全请求 |
| 403 | `CONSENT_REQUIRED` | 跳转对应授权说明 |
| 403 | `FEATURE_NOT_ENTITLED` | 展示所需权益，不自动下单 |
| 404 | `RESOURCE_NOT_FOUND` | 返回上一页并刷新列表 |
| 409 | `VERSION_CONFLICT` | 拉取新版本后提示用户合并 |
| 409 | `DUPLICATE_REQUEST` | 使用原请求结果，禁止重复扣费 |
| 413 | `ATTACHMENT_TOO_LARGE` | 展示大小限制并允许重选 |
| 422 | `OCR_CONFIRMATION_REQUIRED` | 进入截图校正页 |
| 422 | `CONTENT_BLOCKED` | 展示安全说明和申诉入口 |
| 429 | `RATE_LIMITED` | 按 `retryAfterSeconds` 重试 |
| 429 | `QUOTA_INSUFFICIENT` | 展示权益/钱包，不丢失草稿 |
| 500 | `INTERNAL_ERROR` | 可重试且不扣费 |
| 502 | `MODEL_PROVIDER_UNAVAILABLE` | 查询任务状态或使用服务端降级 |
| 504 | `GENERATION_TIMEOUT` | 允许恢复任务，不能直接重复创建 |

## 6. 核心数据对象

### 6.1 用户权益

```json
{
  "userId": "usr_01J...",
  "planCode": "VIP_STANDARD",
  "planExpiresAt": "2026-09-07T00:00:00Z",
  "benefits": {
    "textRemaining": 280,
    "visionRemaining": 26,
    "allowedModelIds": ["model_fast", "model_quality"],
    "allowedStyleIds": ["warm", "humorous", "steady"]
  },
  "wallet": {"energyBalance": 98000},
  "resourceVersion": 7
}
```

客户端只展示服务端返回的权益，不根据会员名称推断次数、模型或价格。

### 6.2 对象档案

```json
{
  "profileId": "prf_01J...",
  "displayName": "相亲对象 A",
  "relationshipStage": "DATING",
  "traits": ["慢热"],
  "preferences": ["喜欢徒步"],
  "boundaries": ["不喜欢被催促"],
  "memoryEnabled": true,
  "resourceVersion": 3,
  "createdAt": "2026-08-07T12:30:00Z",
  "updatedAt": "2026-08-07T12:30:00Z"
}
```

### 6.3 附件与 OCR

```json
{
  "attachmentId": "att_01J...",
  "status": "READY",
  "mediaType": "image/jpeg",
  "expiresAt": "2026-08-08T12:30:00Z",
  "ocr": {
    "confirmed": false,
    "turns": [
      {"turnId": "turn_1", "speaker": "OTHER", "text": "周末有空吗", "confidence": 0.93}
    ]
  },
  "resourceVersion": 1
}
```

### 6.4 生成请求

```json
{
  "clientRequestId": "01J4CLIENTUNIQUE",
  "input": {
    "text": "对方：周末有空吗？",
    "attachmentIds": [],
    "confirmedOcrVersion": null
  },
  "context": {
    "targetProfileId": "prf_01J...",
    "relationshipStage": "DATING",
    "communicationGoal": "ACCEPT_INVITATION",
    "styleIds": ["warm", "humorous"],
    "additionalContext": "希望自然一点"
  },
  "modelId": "model_quality",
  "saveToHistory": true,
  "quoteId": "quo_01J..."
}
```

服务端校验 `quoteId`、权益版本、OCR 确认版本和附件所有权。`additionalContext` 与所有用户输入均作为不可信数据处理。

### 6.5 生成结果

```json
{
  "generationId": "gen_01J...",
  "status": "SUCCEEDED",
  "analysis": {
    "possibleIntent": "对方可能在试探你是否愿意见面",
    "emotion": "期待但不确定",
    "uncertaintyNote": "仅依据当前上下文推测",
    "riskTips": ["避免替对方下确定结论"]
  },
  "candidates": [
    {
      "candidateId": "can_01J...",
      "strategy": "SAFE",
      "styleId": "warm",
      "text": "有呀，你这是准备安排我周末了吗？",
      "safetyStatus": "PASSED"
    }
  ],
  "usage": {
    "modelId": "model_quality",
    "inputTokens": 320,
    "outputTokens": 180,
    "reservedEnergy": 1200,
    "chargedEnergy": 1040,
    "chargedFrom": "SUBSCRIPTION_THEN_WALLET"
  }
}
```

## 7. Android 客户端 API

### 7.1 启动、认证与账户

| 方法与路径 | 用途 | 关键说明 |
|---|---|---|
| `GET /app/bootstrap` | 启动配置 | 返回最低版本、功能开关、模型/风格目录、主题版本、公告摘要和隐私版本 |
| `POST /auth/sms/send` | 发送验证码 | 图形验证、频率限制和设备风险检查 |
| `POST /auth/sms/login` | 登录/注册 | 返回 access/refresh Token、用户和待同意协议 |
| `POST /auth/refresh` | 刷新令牌 | refresh Token 轮换，旧令牌立即失效 |
| `POST /auth/logout` | 当前设备退出 | 撤销当前 refresh Token |
| `POST /auth/logout-all` | 全设备退出 | 撤销用户全部会话 |
| `GET /me` | 获取账户 | 基础资料、状态和权限摘要 |
| `PATCH /me` | 修改资料 | 昵称、头像、语言、时区等非敏感资料 |
| `GET /me/devices` | 登录设备 | 支持撤销单个设备 |
| `DELETE /me/devices/{deviceId}` | 撤销设备 | 当前设备撤销后要求重新登录 |
| `GET /me/consents` | 授权状态 | 返回协议版本、同意时间和用途 |
| `PUT /me/consents/{consentType}` | 更新授权 | 训练授权可撤回，服务必需授权不可伪装为可选 |
| `POST /me/data-export` | 申请数据导出 | 返回异步任务 ID 和过期下载时间 |
| `GET /me/data-requests/{requestId}` | 查询数据请求 | 返回处理进度、失败原因或短期下载地址 |
| `GET /me/deletion` | 查询注销状态 | 返回冷静期、预计完成时间和阻塞项 |
| `POST /me/deletion` | 申请注销 | 返回冷静期、影响范围和取消方式 |
| `DELETE /me/deletion` | 取消注销 | 仅在冷静期内可用 |
| `GET /me/notification-preferences` | 通知偏好 | 区分服务、安全和营销通知 |
| `PUT /me/notification-preferences` | 更新通知偏好 | 服务必需通知不可伪装为营销开关 |
| `PUT /me/devices/{deviceId}/push-token` | 注册/轮换推送 Token | Token 归属设备，退出或失效时删除 |
| `GET /jobs/{jobId}` | 查询本人异步任务 | 用于批量删除、分享图等通用任务 |

### 7.2 对象档案

| 方法与路径 | 用途 |
|---|---|
| `GET /target-profiles` | 档案列表 |
| `POST /target-profiles` | 新建档案 |
| `GET /target-profiles/{profileId}` | 档案详情 |
| `PATCH /target-profiles/{profileId}` | 更新档案，要求 `resourceVersion` 或 `If-Match` |
| `DELETE /target-profiles/{profileId}` | 删除并解除与历史会话的引用 |
| `GET /target-profiles/{profileId}/memories` | 查看逐条记忆 |
| `POST /target-profiles/{profileId}/memories` | 用户主动新增记忆 |
| `PATCH /memories/{memoryId}` | 修改或停用记忆 |
| `DELETE /memories/{memoryId}` | 删除记忆 |

### 7.3 图片、OCR 与校正

| 方法与路径 | 用途 | 关键说明 |
|---|---|---|
| `POST /attachments` | 上传截图 | `multipart/form-data`；校验类型、大小、病毒和图片炸弹 |
| `GET /attachments/{attachmentId}` | 查询解析状态 | 返回 `UPLOADING/SCANNING/PARSING/READY/REJECTED` |
| `PUT /attachments/{attachmentId}/ocr` | 提交校正 | 传完整 turns、原 `resourceVersion` 和 `confirmed=true` |
| `DELETE /attachments/{attachmentId}` | 立即删除 | 终止未开始任务；已引用任务按保留策略解除 |

附件默认短期过期。没有 `confirmedOcrVersion` 的截图生成请求返回 `OCR_CONFIRMATION_REQUIRED`。

### 7.4 生成、流式结果与反馈

| 方法与路径 | 用途 | 关键说明 |
|---|---|---|
| `POST /generations/quote` | 生成前报价 | 返回可用模型、预计消耗、扣费来源、`quoteId` 和过期时间 |
| `POST /generations` | 创建任务 | 要求 `Idempotency-Key`，成功后完成额度预占 |
| `GET /generations/{generationId}` | 查询快照 | SSE 断开、App 恢复或超时后使用 |
| `GET /generations/{generationId}/events` | SSE 流 | 支持 `Last-Event-ID`，只允许任务所有者访问 |
| `POST /generations/{generationId}/cancel` | 取消任务 | 已结算任务不可取消；未消耗部分释放 |
| `POST /generations/{generationId}/regenerate` | 整体重生成 | 新建子任务并重新报价/预占，不覆盖原结果 |
| `POST /candidates/{candidateId}/refine` | 单条改写 | 传 `instructionCode` 或受限自定义要求 |
| `POST /candidates/{candidateId}/actions` | 用户动作 | `COPY/FAVORITE/SENT/LIKE/DISLIKE/OUTCOME`，同一事件幂等 |
| `POST /risk-events/{riskEventId}/appeals` | 风控申诉 | 返回申诉工单状态，不自动绕过拦截 |

### 7.5 SSE 事件协议

响应头：

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

单个事件：

```text
id: 18
event: candidate.completed
data: {"schemaVersion":"1.0","eventId":"18","eventType":"candidate.completed","occurredAt":"2026-08-07T12:30:02Z","generationId":"gen_01J...","sequence":18,"payload":{"candidate":{"candidateId":"can_01J...","strategy":"SAFE","text":"..."}}}
```

所有事件 `data` 均使用 `schemaVersion`、`eventId`、`eventType`、`occurredAt`、`generationId`、`sequence` 和 `payload` 信封；事件专属字段只放在 `payload`。

事件类型及顺序：

| 事件 | 数据 | 客户端动作 |
|---|---|---|
| `task.accepted` | 任务 ID、预占额度 | 建立生成页并允许取消 |
| `task.stage` | `PARSING/ANALYZING/GENERATING/FILTERING` | 更新稳定的阶段状态，不展示模型思维链 |
| `analysis.completed` | 可展示的简短分析 | 渲染分析区 |
| `candidate.delta` | 候选 ID、序号、文本增量 | 追加到对应候选，按序去重 |
| `candidate.completed` | 完整候选对象 | 用服务端完整文本校正增量结果 |
| `usage.settled` | 实际用量和扣费 | 刷新本地权益缓存 |
| `task.completed` | 最终快照版本 | 关闭流并拉取最终快照核对 |
| `task.failed` | 错误码、是否可恢复 | 查询快照；禁止盲目新建任务 |
| `heartbeat` | 服务端时间 | 保活，不进入业务日志 |

重连规则：客户端保存最后一个事件 ID，指数退避重连；若服务端返回 `410 STREAM_EXPIRED`，改用任务查询接口获取最终快照。SSE 不传输内部思维链、Prompt 或密钥信息。

### 7.6 历史、收藏与锦囊

| 方法与路径 | 用途 |
|---|---|
| `GET /conversations` | 会话历史列表，支持档案、时间和关键词筛选 |
| `GET /conversations/{conversationId}` | 历史详情 |
| `DELETE /conversations/{conversationId}` | 删除历史及可删除附件 |
| `POST /conversations/batch-delete` | 批量删除，返回异步任务 |
| `GET /favorites` | 收藏列表 |
| `POST /favorites` | 收藏候选或锦囊 |
| `DELETE /favorites/{favoriteId}` | 取消收藏 |
| `GET /knowledge/categories` | 锦囊分类 |
| `GET /knowledge/cards` | 已发布卡片列表和搜索 |
| `GET /knowledge/cards/{cardId}` | 卡片详情并记录匿名化曝光 |
| `POST /knowledge/cards/{cardId}/actions` | 收藏、点赞、踩和分享事件 |
| `POST /share-cards` | 创建脱敏分享图任务，返回隐私预览和任务 ID |
| `POST /share-cards/{shareCardId}/confirm` | 用户确认脱敏预览后生成可分享文件 |

### 7.7 会员、钱包、订单与广告奖励

| 方法与路径 | 用途 | 关键说明 |
|---|---|---|
| `GET /entitlements` | 当前权益 | App 启动、支付成功和结算后刷新 |
| `GET /wallet` | 钱包余额 | 返回余额和最近结算摘要 |
| `GET /wallet/ledger` | 不可变流水 | 支持类型和时间筛选，不允许客户端改写 |
| `GET /products` | 可售商品 | 服务端按渠道、地区、实验和版本返回 |
| `POST /orders` | 创建订单 | 返回服务端订单和支付参数 |
| `GET /orders` | 订单列表 | 用户只能访问本人订单 |
| `GET /orders/{orderId}` | 查询订单 | 支付客户端回调后仍以服务端状态为准 |
| `POST /orders/{orderId}/cancel` | 取消未支付订单 | 已支付订单走退款/客服流程 |
| `POST /orders/{orderId}/refund-requests` | 提交退款申请 | 返回工单和预计处理时间，不直接承诺退款成功 |
| `GET /refund-requests` | 查询本人退款申请 | 返回渠道退款与权益回收状态 |
| `GET /subscriptions/current` | 当前订阅 | 返回续订状态和渠道 |
| `POST /subscriptions/{subscriptionId}/cancel-renewal` | 关闭续订 | 不提前删除已付权益 |
| `POST /ad-rewards/sessions` | 创建广告奖励会话 | 返回短期 session ID |
| `GET /ad-rewards/sessions/{sessionId}` | 查询奖励 | 奖励只由服务端验证回调后发放 |

支付与广告服务端回调：

| 方法与路径 | 来源 | 必须校验 |
|---|---|---|
| `POST /internal/v1/webhooks/payments/{provider}` | 微信/支付宝/应用商店 | 签名、时间戳、金额、商户号、订单号、重放和幂等 |
| `POST /internal/v1/webhooks/ads/{provider}` | 广告平台 | 签名、用户映射、奖励会话、重放和幂等 |

客户端支付成功页面不能直接发放权益。服务端确认回调后，在同一事务中更新订单、权益和账务流水。

### 7.8 公告、配置与版本

| 方法与路径 | 用途 |
|---|---|
| `GET /notices` | 获取适用公告，服务端完成用户/版本/地区定向 |
| `POST /notices/{noticeId}/read` | 已读/关闭，支持频次控制 |
| `GET /app/theme/{version}` | 下载签名主题配置，失败使用内置主题 |
| `GET /app/i18n/{locale}/{version}` | 下载签名词典，缺键回退 APK 内词典 |
| `GET /app/releases/latest` | 检查推荐更新、强更和下载渠道 |

### 7.9 消息、客服、法律文本与最小化埋点

| 方法与路径 | 用途 | 关键说明 |
|---|---|---|
| `GET /inbox/messages` | 站内消息列表 | 订单、退款、数据请求、安全和系统消息 |
| `POST /inbox/messages/{messageId}/read` | 标记已读 | 幂等，不影响同类后续消息 |
| `GET /support-tickets` | 本人工单列表 | 不在列表中回显完整敏感附件 |
| `POST /support-tickets` | 创建客服/账务/隐私/投诉工单 | 类型决定 SLA、必填字段和授权范围 |
| `GET /support-tickets/{ticketId}` | 工单详情与时间线 | 用户只能访问本人工单 |
| `POST /support-tickets/{ticketId}/messages` | 补充消息或附件 | 附件复用安全上传流程 |
| `POST /support-tickets/{ticketId}/close` | 用户关闭工单 | 关闭后可按规则重新开启或新建 |
| `GET /legal-documents` | 当前和历史法律文本 | 返回版本、摘要、生效时间和完整内容地址 |
| `POST /telemetry/events` | 批量上报白名单事件 | 禁止携带聊天原文、截图、密钥或自由文本 |

实验分组在 `/app/bootstrap` 返回。客户端仅在实际曝光时上报实验 ID、变体、时间和匿名会话标识，不能把页面加载等同于曝光。

## 8. 管理后台 API

### 8.1 仪表大盘

| 方法与路径 | 页面/用途 |
|---|---|
| `GET /admin/v1/dashboard/operations` | 请求量、成功率、延迟、SSE 重连、供应商健康度 |
| `GET /admin/v1/dashboard/finance` | GMV、退款、模型成本、贡献毛利；均返回统计口径 |
| `GET /admin/v1/dashboard/quality-safety` | 采纳代理指标、负反馈、拦截、申诉和评测趋势 |

### 8.2 用户与权益

| 方法与路径 | 页面/用途 |
|---|---|
| `GET /admin/v1/users` | 用户搜索和筛选；默认屏蔽敏感字段 |
| `GET /admin/v1/users/{userId}` | 账户、设备、状态、授权摘要 |
| `PATCH /admin/v1/users/{userId}/status` | 冻结/恢复，要求原因和审计 |
| `GET /admin/v1/users/{userId}/entitlements` | 权益和钱包摘要 |
| `POST /admin/v1/users/{userId}/entitlement-adjustments` | 人工补发/扣回；双重确认、幂等和不可变流水 |
| `GET /admin/v1/users/{userId}/ledger` | 用户账务流水，只读 |
| `GET /admin/v1/support-tickets` | 客服、账务、隐私和投诉工单队列 |
| `GET /admin/v1/support-tickets/{ticketId}` | 工单详情；敏感内容按角色临时授权 |
| `POST /admin/v1/support-tickets/{ticketId}/messages` | 客服回复并发送站内消息 |
| `POST /admin/v1/support-tickets/{ticketId}/decisions` | 记录退款、补偿、驳回或升级决定 |

### 8.3 AI 模型、路由、Prompt 与评测

| 方法与路径 | 页面/用途 |
|---|---|
| `GET/POST /admin/v1/model-providers` | 供应商列表/新增；密钥只写不回显 |
| `PATCH /admin/v1/model-providers/{providerId}` | 更新非密钥配置或轮换密钥 |
| `POST /admin/v1/model-providers/{providerId}/health-checks` | 创建健康检查任务 |
| `GET/POST /admin/v1/models` | 模型目录和倍率 |
| `GET/POST /admin/v1/model-routes` | 场景路由、超时、重试、降级和熔断 |
| `PATCH /admin/v1/model-routes/{routeId}` | 带版本更新路由 |
| `GET/POST /admin/v1/prompts` | Prompt 列表/草稿；变量使用白名单 |
| `POST /admin/v1/prompts/{promptId}/validate` | Schema、安全和离线集验证 |
| `POST /admin/v1/prompts/{promptId}/publish` | 发布版本；必须通过质量门禁 |
| `POST /admin/v1/prompts/{promptId}/rollback` | 回滚到已知版本 |
| `GET/POST /admin/v1/evaluation-suites` | 脱敏评测集和阈值 |
| `POST /admin/v1/evaluation-runs` | 创建评测任务 |
| `GET /admin/v1/evaluation-runs/{runId}` | 查看质量、成本和安全结果 |

### 8.4 动态运营

| 方法与路径 | 页面/用途 |
|---|---|
| `GET/POST /admin/v1/notices` | 公告列表/草稿 |
| `PATCH /admin/v1/notices/{noticeId}` | 内容、定向、频次、起止时间 |
| `POST /admin/v1/notices/{noticeId}/publish` | 发布并记录版本 |
| `POST /admin/v1/notices/{noticeId}/revoke` | 撤回公告 |
| `GET/POST /admin/v1/themes` | 主题草稿；校验颜色和资源清单 |
| `POST /admin/v1/themes/{themeId}/publish` | 签名发布和灰度 |
| `GET/POST /admin/v1/share-card-templates` | 分享图模板和隐私遮盖规则 |
| `POST /admin/v1/share-card-templates/{templateId}/publish` | 校验脱敏预览后发布模板 |
| `GET /admin/v1/app-icons` | APK 内预置 alias 清单，不上传任意图标 |
| `POST /admin/v1/app-icons/{iconId}/activate` | 设置目标 alias 和生效范围 |
| `GET/PUT /admin/v1/i18n/{locale}` | 词典编辑，要求基准键完整 |
| `POST /admin/v1/i18n/{locale}/publish` | 签名发布和回滚点 |
| `GET/POST /admin/v1/feature-flags` | 功能开关 |
| `PATCH /admin/v1/feature-flags/{flagId}` | 更新规则，必须有默认值和熔断值 |
| `GET/POST /admin/v1/experiments` | 实验设计和互斥组 |
| `POST /admin/v1/experiments/{experimentId}/stop` | 停止并保留结果 |

### 8.5 支付与财务

| 方法与路径 | 页面/用途 |
|---|---|
| `GET/POST /admin/v1/products` | 商品列表/草稿 |
| `PATCH /admin/v1/products/{productId}` | 渠道、价格、权益和上下架范围 |
| `GET /admin/v1/orders` | 订单查询与导出任务创建入口 |
| `GET /admin/v1/orders/{orderId}` | 订单、支付回调和权益发放链路 |
| `POST /admin/v1/orders/{orderId}/refunds` | 发起退款，要求权限、原因和幂等 |
| `GET /admin/v1/refunds` | 退款状态 |
| `POST /admin/v1/reconciliations` | 上传/拉取渠道账单并创建对账任务 |
| `GET /admin/v1/reconciliations/{jobId}` | 差异明细和处理状态 |
| `GET /admin/v1/webhook-events` | 回调验签、处理和重试记录 |
| `POST /admin/v1/webhook-events/{eventId}/retry` | 对幂等处理器安全重放 |

### 8.6 内容 CMS

| 方法与路径 | 页面/用途 |
|---|---|
| `GET/POST /admin/v1/content-categories` | 分类和排序 |
| `GET/POST /admin/v1/content-cards` | 内容列表/草稿 |
| `PATCH /admin/v1/content-cards/{cardId}` | 编辑正文、标签、正反例和来源 |
| `POST /admin/v1/content-cards/{cardId}/submit-review` | 提交审核 |
| `POST /admin/v1/content-cards/{cardId}/approve` | 审核通过，编辑者不能自审 |
| `POST /admin/v1/content-cards/{cardId}/publish` | 发布/定时发布 |
| `POST /admin/v1/content-cards/{cardId}/unpublish` | 下线并保留版本 |

### 8.7 系统配置与版本发布

| 方法与路径 | 页面/用途 |
|---|---|
| `GET/POST /admin/v1/app-releases` | 版本列表/草稿 |
| `POST /admin/v1/app-releases/{releaseId}/publish` | 灰度、最低版本、强更和回滚渠道 |
| `GET/PATCH /admin/v1/system-config` | 非密钥全局配置，使用版本控制 |
| `GET/POST /admin/v1/integrations` | 第三方集成，凭据只写 |
| `POST /admin/v1/integrations/{integrationId}/tests` | 创建连通性测试 |
| `GET/POST /admin/v1/legal-documents` | 法律文本草稿和历史版本 |
| `POST /admin/v1/legal-documents/{documentId}/publish` | 发布并触发必要的重新授权 |
| `GET/PUT /admin/v1/telemetry-schema` | 埋点事件白名单、字段和保留周期 |

### 8.8 日志、风控、申诉与告警

| 方法与路径 | 页面/用途 |
|---|---|
| `GET /admin/v1/request-logs` | 按 requestId 查询脱敏请求链路 |
| `GET/POST /admin/v1/risk-policies` | 风控策略草稿和版本 |
| `POST /admin/v1/risk-policies/{policyId}/publish` | 评测通过后发布 |
| `GET /admin/v1/risk-events` | 风险事件；默认不展示完整原文 |
| `GET /admin/v1/appeals` | 申诉队列 |
| `POST /admin/v1/appeals/{appealId}/decisions` | 审核决定、理由和补救动作 |
| `GET/POST /admin/v1/rate-limit-rules` | 用户、IP、设备和接口限流 |
| `GET/POST /admin/v1/alert-rules` | 告警规则和接收组 |
| `GET /admin/v1/incidents` | 事故记录、影响和处置时间线 |

### 8.9 数据治理与数据集

| 方法与路径 | 页面/用途 |
|---|---|
| `GET /admin/v1/consent-metrics` | 按协议版本统计授权与撤回 |
| `GET /admin/v1/data-requests` | 导出、删除、撤回训练授权工单 |
| `POST /admin/v1/data-requests/{requestId}/complete` | 完成工单并记录证据 |
| `GET/POST /admin/v1/datasets` | 数据集版本；只接收已授权、脱敏样本 |
| `POST /admin/v1/datasets/{datasetId}/validation` | 隐私、重复、质量和污染检查 |
| `POST /admin/v1/datasets/{datasetId}/exports` | 创建加密导出任务，要求审批 |
| `GET /admin/v1/export-jobs/{jobId}` | 导出状态、下载过期时间和审计信息 |

### 8.10 管理权限与审计

| 方法与路径 | 用途 |
|---|---|
| `GET/POST /admin/v1/roles` | 角色和权限集合 |
| `GET/POST /admin/v1/admin-users` | 管理员和角色绑定 |
| `POST /admin/v1/admin-users/{adminId}/mfa-reset` | MFA 重置，要求更高权限和审计 |
| `GET /admin/v1/audit-logs` | 只读审计日志，支持资源和操作者筛选 |

## 9. 状态机与一致性规则

### 9.1 生成任务

```text
CREATED -> QUOTA_RESERVED -> PARSING -> ANALYZING -> GENERATING -> FILTERING
                                                        |             |
                                                        +-------> SUCCEEDED
任一未完成状态 -----------------------------------------------> FAILED
用户取消且尚未完成 -------------------------------------------> CANCELLED
```

* `SUCCEEDED` 必须存在最终结果和结算流水。  
* `FAILED/CANCELLED` 必须释放未结算预占；重试创建新任务并关联 `parentGenerationId`。  
* Worker 重复执行、SSE 重连或客户端重复请求不能重复扣费。

### 9.2 订单与退款

```text
CREATED -> PENDING_PAYMENT -> PAID
   |              |             |
CANCELLED       FAILED          +-> REFUND_PENDING -> REFUNDED
```

权益发放以服务端验签回调为准。订单、权益和账务流水必须在同一事务或可靠事务消息中保持一致。

### 9.3 内容与配置发布

```text
DRAFT -> IN_REVIEW -> APPROVED -> PUBLISHED -> REVOKED
```

每次发布生成不可变版本，支持灰度、回滚和客户端缓存失效。编辑者与审核者应分离。

### 9.4 用户数据请求

```text
REQUESTED -> IDENTITY_VERIFIED -> PROCESSING -> COMPLETED
                                      |
                                      +-> REJECTED（必须记录法定理由）
```

## 10. 前端、业务 API 与管理后台联动矩阵

| 前端功能 | 用户 API | 管理控制/观测 | 必须覆盖的异常 |
|---|---|---|---|
| App 启动 | `/app/bootstrap`、`/app/releases/latest` | 版本、主题、i18n、开关、公告 | 配置验签失败、离线回退、强更 |
| 登录与设备 | `/auth/*`、`/me/devices` | 用户状态、设备、限流 | 验证码限流、Token 轮换、封禁 |
| 文本帮回 | `/generations/quote`、`/generations` | 模型路由、Prompt、评测、日志 | 额度不足、模型超时、内容拦截 |
| 截图帮回 | `/attachments`、OCR 校正 | 上传策略、Vision 路由、风险日志 | 大图、解析失败、说话人纠错、过期 |
| 流式结果 | `/generations/{id}/events`、快照查询 | 供应商健康、延迟和错误监控 | 断线、重复事件、流过期、后台恢复 |
| 复制/改写/反馈 | candidate actions/refine | 行为指标、质量看板、申诉 | 幂等、被删候选、风险误杀 |
| 历史与收藏 | `/conversations`、`/favorites` | 保存策略、数据请求工单 | 跨用户访问、批量删除、同步冲突 |
| 对象档案 | `/target-profiles`、`/memories` | 用户授权摘要 | 版本冲突、关闭记忆、级联删除 |
| 锦囊 | `/knowledge/*` | CMS 分类、审核、发布 | 草稿泄漏、内容下线、缓存更新 |
| 会员与钱包 | `/entitlements`、`/wallet/*` | 商品、权益调整、账务审计 | 重复扣费、失败释放、过期权益 |
| 支付与订阅 | `/products`、`/orders`、`/subscriptions` | 订单、退款、对账、Webhook | 假回调、金额不符、回调延迟、退款 |
| 广告奖励 | `/ad-rewards/sessions` | 集成、奖励流水、回调日志 | 伪造完成、重复奖励、回调丢失 |
| 公告与运营 | `/notices`、`/notices/{id}/read` | 公告定向、频次和撤回 | 重复弹窗、过期、撤回和离线 |
| 隐私与注销 | `/me/consents`、data-export/deletion | 数据请求、授权指标、审计 | 撤回训练授权、导出过期、注销取消 |
| 消息与客服 | `/inbox/messages`、`/support-tickets` | 工单队列、用户详情、退款/补偿审计 | 越权查看、敏感附件、超时升级、重复补偿 |
| 分享图 | `/share-cards`、确认接口 | 模板与脱敏规则 | 原文泄漏、模板下线、任务失败、链接过期 |
| 实验与埋点 | bootstrap 分组、`/telemetry/events` | 实验、事件白名单、指标看板 | 重复曝光、敏感字段、离线重放、分组漂移 |
| 系统分享/悬浮球 | 本地入口 + 正常生成 API | 功能开关、版本和崩溃指标 | 权限拒绝、服务被杀、无障碍禁用 |

矩阵中的每个用户操作均有用户 API，每项动态行为均有管理配置或观测入口，每个有副作用的操作均有幂等、审计或状态恢复规则。

## 11. 安全、隐私与运维要求

1. **数据最小化：** 默认不记录原始 Prompt、聊天全文和截图到普通应用日志；requestId 可追踪但不可反推出用户。  
2. **访问隔离：** 所有用户资源按 `userId` 强制鉴权，不能只依赖客户端传参；管理端敏感查看使用临时授权和水印。  
3. **凭据安全：** 模型、支付、短信和对象存储密钥保存在 KMS/Secrets Manager；管理 API 永不回显完整密钥。  
4. **Webhook 安全：** 验证签名、时间窗、随机数、金额、商户身份和事件唯一 ID，原始载荷加密留存用于审计。  
5. **上传安全：** 重新编码图片、限制像素/帧数/大小、清理 EXIF、病毒扫描、短期签名 URL、禁止公开桶。  
6. **模型安全：** 输入视为不可信内容；结构化输出校验；模型路由和 Prompt 版本写入每次生成记录。  
7. **隐私生命周期：** 记录用途、法律依据、保存期限、授权版本和删除任务；备份中的删除遵循明确周期。  
8. **可观测性：** 监控成功率、首事件延迟、完整延迟、断线恢复、供应商错误、预占未释放、重复扣费和安全指标。  
9. **灾难恢复：** 数据库定期备份并演练恢复；账务流水与审计日志采用不可变或防篡改存储。  
10. **发布门禁：** Prompt、模型路由、风控、支付、主题和强更配置都必须支持验证、灰度、监控和回滚。

## 12. 联调与验收清单

### 12.1 契约测试

* 所有 JSON 请求/响应通过 OpenAPI Schema 校验；枚举、空值、长度和错误码一致。  
* Android、业务 API 和管理后台使用同一份生成的 API 模型或契约测试样例。  
* 每个写接口验证幂等；每个更新接口验证版本冲突；每个资源验证越权访问。  
* SSE 测试乱序、重复、丢失、重连、过期和任务已完成场景。  
* Webhook 测试伪造签名、重复通知、乱序通知、金额不符和重试。

### 12.2 端到端闭环

1. 文本生成成功、复制、反馈、历史查询和删除。  
2. 截图上传、OCR 失败、校正、生成、附件过期和立即删除。  
3. 免费额度耗尽、钱包补充、预占、结算、失败释放和重复请求。  
4. 支付成功但客户端断网、回调延迟、重复回调、退款和对账差异。  
5. SSE 中断后恢复、App 被系统回收后查询最终结果。  
6. Prompt/路由灰度发布、指标异常自动停用和人工回滚。  
7. 公告定向、只展示一次、撤回、过期和离线缓存。  
8. 训练授权撤回、数据级联删除、导出和账号注销。  
9. 风险拦截、申诉、人工决定和审计记录。  
10. 不同管理员角色访问、越权阻断和高风险操作二次确认。
11. 退款申请、客服回复、站内消息、补偿幂等和工单敏感附件授权。  
12. 分享图脱敏预览、用户确认、文件过期和模板下线。  
13. 实验稳定分组、真实曝光、离线批量上报和敏感字段拒收。

### 12.3 上线门槛

* P0/P1 接口无未定义状态，OpenAPI 与实现一致。  
* 核心端到端用例全部通过，重复扣费和越权访问测试为零失败。  
* 隐私政策、第三方 SDK 清单、支付资质、模型供应商数据条款完成法务确认。  
* 主流 Android 版本和目标厂商 ROM 完成分享入口、后台恢复、通知和可选悬浮窗实机测试。  
* 可用性、毛利率、识别准确率和采纳率只能在真实监控达到门槛后对外声明。

## 13. 文档完整性结论

本版本在设计层面已覆盖：4 个主 Tab、5 个二级页面、全局分享/悬浮入口、9 个管理模块、28 个子页面，以及认证、上传、OCR、生成、SSE、反馈、历史、档案、内容、权益、支付、退款、广告、消息、客服、分享图、配置、埋点、风控、数据治理、审计和异常恢复接口。

“接口联动完整”表示需求中的每个已知页面动作都有对应 API、状态、权限、管理控制或观测入口；不表示代码已经实现，也不替代 OpenAPI 文件、数据库迁移、自动化契约测试、支付沙箱测试和 Android 实机测试。若后续新增功能，必须先更新第 10 节联动矩阵，再进入开发。
