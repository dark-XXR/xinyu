# 心语运营台 (Admin Web)

心语运营台是用于管理后台的核心管理系统。支持以下核心能力：

## 主要功能

1. **工作台 (Dashboard)**
   - 核心指标展示（系统健康状态、待支付订单、待审退款、在线商品等）
   - 最新系统活动动态追踪（最新操作及流水）
   - 快捷操作入口，一键管理各类资源

2. **供应商管理 (Providers - `/providers`)**
   - **全面适配器支持**：支持 AI 推理（`OPENAI_COMPAT` 必填 Base URL 且可选 organization/project，以及 `OPENAI`、`ANTHROPIC`、`GEMINI` 原生，Base URL 可选）、邮件服务（`SMTP` 凭据/TLS、`SES_API` 必须 region、`SENDGRID_API`、`RESEND_API`、`MAILGUN_API` 必须 Base URL）、短信服务（`ALIYUN_SMS`、`TENCENT_SMS` 必须 applicationId）及支付网关（`EPAY_COMPAT` 支持可选 applicationId 和 `ALIPAY`/`WECHAT_PAY` 多选且至少选一种）
   - **凭据按适配器区分**：凭据轮换按适配器 `adapterType` 自动解析密钥要求（AI / SendGrid / Resend / Mailgun 为 `apiKey`；SMTP 为 `username`+`password`；SES / 阿里云为 `accessKeyId`+`accessKeySecret`；腾讯云为 `secretId`+`secretKey`；易支付为 `merchantKey`）
   - **就绪发布与阻断规则**：发布按钮仅在供应商配置状态处于 `READY` 时显示。保存草稿或轮换凭据后状态设为 `DRAFT` 且清空健康检查状态，必须先配置凭据并成功通过探针健康检查转为 `READY` 后方可发起发布，Mock 演示与真实后端保持一致
   - **版本回滚与停用机制**：回滚（设为 `ACTIVE` 且灰度 100%）与停用（设为 `DISABLED` 且灰度 0%）保持版本自增与生效时间更新，并保留已发布线上历史版本（`publishedResourceVersion`），支持安全的版本演进与降级恢复
   - **优先级机制**：优先级说明统一设定为数值越大越优先，运行时按降序规则选择可用供应商
   - **线上版本与分流展示**：明确展示配置状态（DRAFT/READY/ACTIVE/DISABLED/SUPERSEDED）与线上运行状态（线上发布版本 `publishedResourceVersion`、灰度比例 `publishedRolloutPercentage` 和生效时间）。当处于 `DRAFT` 状态且 `publishedRolloutPercentage > 0` 时，清晰标示线上旧版本仍在线分流
   - **危险停用机制**：停用按钮显示条件为 `publishedResourceVersion != null && publishedRolloutPercentage > 0`。停用弹窗详细解释会立即从邮件/短信/AI/支付运行时选择中移除（线上灰度比例降为 0%）但保留版本历史；要求填写至少 8 字审计理由并二次输入供应商完整名称确认
   - **已停用恢复途径**：已停用项允许继续编辑、轮换凭据、健康检查和版本回滚；只有完成验证并重新发布或执行回滚后才能重新进入运行时
   - **理由门禁与敏感信息清理**：发布、回滚、健康检查、凭据轮换和停用均强制要求至少 8 字审计理由。健康检查结果与审计理由留痕，测试目标脱敏处理。凭据与各类 Dialog 关闭时自动清理临时数据与理由输入
   - **真实 If-Match 契约**：所有写操作（保存/发布/回滚/轮换/停用）If-Match 标头统一使用纯十进制字符串 `String(resourceVersion)`（如 `"2"`），不包含 `W/"..."` 弱 ETag 前缀

3. **AI 运行配置 (AI Operations)**
   - 逻辑模型至供应商上游模型的动态绑定与成本、模态、Context Window 阈值管理
   - 场景化路由 (Scenario Route) 配置、优先级 Targets 及灰度发布与真实历史版本回滚
   - 提示词 (Prompt Template) 管理与 Output JSON Schema 严格校验
   - 安全与风控策略 (Risk Policies) 配置（敏感词阻断/复核、提示词注入防范、最低安全分及申诉规则）
   - 评测与发布闸门 (Evaluations & Publishing)，保障发布前质量与安全检查无缝衔接

4. **商品与套餐管理 (Products)**
   - 自定义能量包与订阅类商品
   - 设定文本/视觉额度与专属能力项
   - 发布流控制及基于历史版本的版本回滚

5. **订单与退款 (Orders & Refunds)**
   - 查询全站交易与履约状态
   - 基于订单快照的完整溯源
   - 订单侧执行退款请求的人工审计（通过 / 驳回）

6. **用户管理 (`/users`)**
   - **脱敏列表与检索**：支持按用户 ID、手机号、邮箱、昵称及账户状态（`ACTIVE` / `SUSPENDED` / `DELETION_PENDING`）进行多维度筛选。
   - **详情抽屉 (Drawer)**：下发包含设备摘要（关联设备 model, 平台, 登录时间及当前在线状态）、授权与生效权益（文本/视觉余量与到期时间）、钱包交易流水（`RECHARGE` / `CONSUMPTION` 额度与变动后结余）。
   - **冻结/恢复高风险约束**：显示“冻结账号将立刻撤销该用户所有活跃 Session 凭据并强制下线”的清晰风险提示；强制要求输入至少 8 字中文审计理由，并要求手动输入完整 `userId` 进行二次确认。

7. **公告运营 (`/operations/notices`)**
   - **版本与状态展示**：维护草稿 (`DRAFT`)、已发布 (`PUBLISHED`) 与已撤回 (`REVOKED`) 三类状态。
   - **草稿新建与编辑**：全面支持配置公告标题、正文、公告类型（`GENERAL` / `MAINTENANCE` / `PROMOTION` / `SECURITY`）、定向平台 (全端 / ADMIN_WEB / ANDROID)、语言、客户端版本范围 (`minClientVersion` ~ `maxClientVersion`)、展示频次 (`ONCE` / `ONCE_PER_VERSION` / `EVERY_LAUNCH`) 及起止时间。
   - **发布与撤回审计**：发布与撤回高风险变更均强制要求填写至少 8 字中文审计理由。

8. **网站设置 (`/system/settings`)**
   - **全站品牌与法务身份**：配置网站名称、App 名称、公司主体、Logo 图标 URL、客服支持邮箱、隐私合规邮箱、默认语言、官网链接、ICP 备案号及紧急全站例行维护模式/提示文案。
   - **草稿 vs 已发布解耦**：清晰区分线上已发布版本（包含上次发布时间与版本号）与当前编辑草稿。草稿变更有明确未发布提示 Badge。
   - **独立发布与动态品牌读取**：保存草稿与线上发布分离；线上发布强制要求至少 8 字中文审计理由。Layout 导航与 Topbar 品牌名异步读取配置更新，读取失败或加载中自动回退至“运营管理台”安全占位。

9. **支付运营与主动对账 (`/commerce/payments`)**
   - **通道健康度监控**：聚合易支付 (Epay) 供应商通信状态、商户号、异步通知回调 (Notify URL) 与同步返回 (Return URL)。快捷跳转至 `/providers` 高级配置。
   - **安全凭据防泄露**：严禁显示 API Secret / Key 密钥明文，显示为安全遮罩密文；绝不在前端写死具体价格或硬编码阈值。
   - **主动对账机制**：支持设定截止停滞时间 (`staleBefore`) 和单次最大扫描笔数 (`maxOrders`)；强制填写至少 8 字中文审计理由；对账完成后实时反馈已扫描笔数、平账数、权益补发数与冲突挂起数。

10. **客服工单运营 (`/support`)**
    - **队列筛选**：按工单状态（待处理 / 客服待回复 / 等待用户反馈 / 已解决 / 已关闭）、优先级（紧急 / 高 / 普通 / 低）和分类进行检索。
    - **会话历史与双模式回复**：以水流消息卡片呈现历史对话；支持自由切换“公开回复用户”与“仅团队内部可见的私密备注 (`internal: true`)”。
    - **状态与更替门禁**：工单状态、优先级变更与消息回复提交均要求填写至少 8 字中文审计理由。

## 技术栈与设计原则

- 基于 **React** (Vite + TS) 及 **React Router v7** Future Flag 的单页应用
- 全功能 **TypeScript** 严格检查与 Lint 支持
- 基于 **TanStack Query** 实现的客户端缓存和状态管理
- 定制化设计系统，遵循“安静、专业、紧凑”的设计原则：不依赖大面积亮色，采用沉稳色系及 1400px 最大内容区
- 对极窄屏幕 (390px) 实施完全的表单卡片化响应式降级，拒绝内容拥挤

## 运行与检查

- `npm run dev`：启动本地开发环境
- `npm run build`：生产环境构建
- `npm run typecheck`：TypeScript 类型检查
- `npm run lint`：通过 oxlint 执行极速语法检查
