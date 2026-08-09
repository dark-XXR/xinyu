# 文件与页面功能目录

本文档面向不熟悉软件研发的维护人员，用于快速找到页面、UI 参数、接口和后台配置所在文件。

## 修改前须知

- `packages/generated-api/**` 和 `apps/android/api-client/**` 是根据 OpenAPI 自动生成的代码，不要手工修改。
- `database/migrations/versions/**` 是数据库升级历史；已经进入生产环境的迁移文件不要改写，应新增迁移。
- 价格、套餐权益、调用次数、模型名称、重试次数、奖励额度等业务值必须从后台配置读取，不能写死在前端。
- 页面颜色、字号和间距优先修改主题或对应的 Compose 函数，不要修改接口生成代码。
- 新增业务代码应写中文模块说明；复杂规则、安全边界和状态转换应写中文注释。

## Android 前端页面

| 编号 | 功能或页面 | 主要文件与位置 | 可进行的简单修改 |
| --- | --- | --- | --- |
| A01 | 应用启动入口 | `apps/android/app/src/main/kotlin/com/lovereply/app/MainActivity.kt` | 应用启动时加载的根界面 |
| A02 | 全局页面导航与根布局 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`LoveReplyApp` 函数 | 页面切换、全局背景、顶部区域 |
| A03 | 注册/登录页面前端文件 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`LoginScreen` 函数 | 登录文案、输入框、验证码按钮、邮箱/短信切换布局 |
| A04 | 注册/登录页面状态与校验 | `apps/android/app/src/main/kotlin/com/lovereply/app/MainViewModel.kt`，`LoginUiState` 与登录相关函数 | 输入校验、倒计时、错误提示和提交状态 |
| A05 | 回复消息输入页面 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`ComposerScreen` 函数 | 原消息输入、关系、目标、风格和模型选择布局 |
| A06 | 回复消息页面 UI 参数 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`ComposerScreen`、`QuoteConfirmation` 函数 | 控件间距、按钮、字数显示和确认区域 |
| A07 | 回复生成报价确认 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`QuoteConfirmation` 函数 | 报价展示和确认按钮布局；价格值来自后端，不能写死 |
| A08 | 回复结果页面 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`ResultScreen` 函数 | 意图、情绪、风险提示和三种回复策略布局 |
| A09 | 单条回复候选卡片 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`CandidateCard` 函数 | 回复文本、策略标签和复制按钮 |
| A10 | 页面错误提示 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/LoveReplyApp.kt`，`ErrorBanner` 函数 | 错误条样式和提示布局 |
| A11 | 页面业务状态中心 | `apps/android/app/src/main/kotlin/com/lovereply/app/MainViewModel.kt` | 登录、输入、报价、生成、轮询和错误状态转换 |
| A12 | 前端接口调用与数据转换 | `apps/android/app/src/main/kotlin/com/lovereply/app/data/LoveReplyRepository.kt` | 调用后端接口、刷新令牌和响应转换 |
| A13 | 登录凭证本地加密存储 | `apps/android/app/src/main/kotlin/com/lovereply/app/data/SessionStore.kt` | 登录会话保存与清除；不要记录明文令牌 |
| A14 | 全局颜色与字体主题 | `apps/android/app/src/main/kotlin/com/lovereply/app/ui/theme/Theme.kt` | 全局颜色、明暗模式和 Material 主题 |
| A15 | Android 功能开关 | `apps/android/app/src/main/kotlin/com/lovereply/app/FeatureFlags.kt` | 控制尚未开放的入口；服务端开关仍是最终依据 |
| A16 | Android 页面自动化测试 | `apps/android/app/src/androidTest/kotlin/com/lovereply/app/ui/LoveReplyAppTest.kt` | 页面显示、点击流程和紧凑屏幕适配测试 |

## 管理后台前端

| 编号 | 功能或页面 | 主要文件与位置 | 当前状态 |
| --- | --- | --- | --- |
| W01 | 管理后台工程 | `apps/admin-web/` | 尚未创建；后续只通过 Antigravity CLI 开发 |
| W02 | 供应商配置页面 | 计划位于 `apps/admin-web/src/pages/providers/` | 待开发：AI、邮件、短信、易支付配置和密钥轮换 |
| W03 | AI 模型与路由页面 | 计划位于 `apps/admin-web/src/pages/ai/` | 待开发：模型映射、提示词、评测、风控、发布和回滚 |
| W04 | 套餐与价格页面 | 计划位于 `apps/admin-web/src/pages/commerce/` | 待开发：套餐价格、次数和权益版本配置 |
| W05 | 邀请推广页面 | 计划位于 `apps/admin-web/src/pages/referrals/` | 待开发：活动、门槛、奖励和回滚配置 |

管理后台创建后，应在本表补充真实文件路径，不能只保留计划路径。

## 后端接口与业务文件

| 编号 | 功能 | 文件路径 | 说明 |
| --- | --- | --- | --- |
| B01 | 后端应用入口与路由注册 | `services/api/src/love_reply_api/main.py` | 注册所有 HTTP 路由和运行时适配器 |
| B02 | 普通用户注册/登录接口 | `services/api/src/love_reply_api/transport/http/routes/auth.py` | 邮箱和短信验证码、登录、刷新与退出接口 |
| B03 | 注册/登录业务规则 | `services/api/src/love_reply_api/application/auth.py` | 验证码、频率限制、渠道策略、账号与会话创建 |
| B04 | 管理员登录与 MFA | `services/api/src/love_reply_api/application/admin_auth.py` | 管理员密码、TOTP、多因素会话和权限 |
| B05 | 外部供应商管理接口 | `services/api/src/love_reply_api/transport/http/routes/admin_providers.py` | 新增、更新、密钥、健康检查、发布和回滚 |
| B06 | 外部供应商业务服务 | `services/api/src/love_reply_api/application/providers.py` | 加密密钥、不可变版本、审计与发布规则 |
| B07 | 邮件/短信供应商运行时 | `services/api/src/love_reply_api/application/provider_runtime.py` | 解析已发布供应商并发送邮件或短信 |
| B07.1 | 邮件/短信原生协议与签名 | `services/api/src/love_reply_api/application/delivery_adapters.py` | SES、SendGrid、Resend、Mailgun、阿里云和腾讯云请求与签名 |
| B07.2 | 易支付原生协议与验签 | `services/api/src/love_reply_api/application/payment_adapters.py` | 收银台、查询、退款、MD5 签名和服务端回调验签 |
| B08 | AI 管理接口 | `services/api/src/love_reply_api/transport/http/routes/admin_ai.py` | AI 模型、路由、提示词、评测和风控的 22 个接口 |
| B09 | AI 管理业务规则 | `services/api/src/love_reply_api/application/ai_admin.py` | 评测门禁、预算校验、发布快照和回滚 |
| B10 | AI 真实模型调用 | `services/api/src/love_reply_api/application/ai_gateway.py` | OpenAI、Anthropic、Gemini 和兼容协议调用与故障转移 |
| B11 | 回复生成接口 | `services/api/src/love_reply_api/transport/http/routes/generations.py` | 报价确认后的生成、查询和取消接口 |
| B12 | 回复生成业务规则 | `services/api/src/love_reply_api/application/generation.py` | 次数预留、模型调用、失败释放和结果保存 |
| B13 | 套餐、订单、订阅和退款接口 | `services/api/src/love_reply_api/transport/http/routes/billing.py` | 商品目录、订单、支付同步、回调、订阅取消和退款申请 |
| B13.1 | 商业结算业务服务 | `services/api/src/love_reply_api/application/commerce.py` | 订单快照、幂等结算、权益发放、订阅和退款规则 |
| B13.2 | 管理员商品、退款和对账接口 | `services/api/src/love_reply_api/transport/http/routes/admin_commerce.py` | 套餐草稿、发布、回滚、订单、退款、对账和权益调整共 14 个后台操作 |
| B13.3 | 管理员商业业务规则 | `services/api/src/love_reply_api/application/commerce_admin.py` | 商品双人审批、网关退款、未消费权益回收、对账和人工调整幂等规则 |
| B13.4 | 管理员商业接口参数 | `services/api/src/love_reply_api/transport/http/admin_business_schemas.py` | 后台页面提交的价格、次数、权益、退款和对账字段校验 |
| B14 | 运行时业务配置 | `services/api/src/love_reply_api/application/runtime_config.py` | 免费额度、模型、风格、开关和认证渠道配置读取 |
| B15 | 通用依赖注入 | `services/api/src/love_reply_api/transport/http/dependencies.py` | 为接口装配数据库、认证和供应商运行时 |
| B16 | 数据库连接 | `services/api/src/love_reply_api/infrastructure/database.py` | 数据库引擎和每次请求的事务会话 |
| B17 | 邀请推广用户与管理接口 | `services/api/src/love_reply_api/transport/http/routes/referrals.py` | 活动、个人邀请码、绑定、进度、奖励、发布和回滚共 10 个操作 |
| B18 | 邀请推广业务规则 | `services/api/src/love_reply_api/application/referrals.py` | 单层绑定、设备和支付身份风控、里程碑、冷静期、发奖和撤销 |
| B19 | 邀请推广接口参数 | `services/api/src/love_reply_api/transport/http/referral_schemas.py` | 活动配置、奖励规则、绑定及响应字段校验 |

## 数据表和迁移

| 编号 | 功能 | 文件路径 | 说明 |
| --- | --- | --- | --- |
| D01 | 用户、验证码和会话表 | `services/api/src/love_reply_api/infrastructure/identity_records.py` | 用户身份、设备、邮箱/短信挑战和会话 |
| D02 | 供应商、密钥和审计表 | `services/api/src/love_reply_api/infrastructure/provider_records.py` | 加密密钥版本、健康检查、发布快照和审计 |
| D03 | AI 配置和调用记录表 | `services/api/src/love_reply_api/infrastructure/ai_gateway_records.py` | 模型、路由、提示词、评测、风控和调用记录 |
| D04 | 生成、权益和钱包表 | `services/api/src/love_reply_api/infrastructure/generation_records.py` | 回复生成任务、次数、钱包和权益 |
| D05 | 数据库升级文件目录 | `database/migrations/versions/` | 按版本升级数据库；已有文件不可随意改写 |
| D06 | 商品、订单、支付和退款表 | `services/api/src/love_reply_api/infrastructure/commerce_records.py` | 商品版本、订单快照、支付事件、订阅和退款 |
| D07 | 商业后台升级文件 | `database/migrations/versions/f5b1c27a9e10_add_commerce_administration.py` | 商品审批、退款执行人、权益发放快照、商业审计、人工调整和对账批次表 |
| D08 | 邀请推广数据表 | `services/api/src/love_reply_api/infrastructure/referral_records.py` | 活动版本、邀请码、绑定、支付身份哈希、奖励和审计记录 |
| D09 | 邀请推广升级文件 | `database/migrations/versions/a6ce441f72d8_add_referral_runtime.py` | 创建邀请推广运行时全部数据表和索引 |

## 契约与配置

| 编号 | 功能 | 文件路径 | 说明 |
| --- | --- | --- | --- |
| C01 | OpenAPI 总入口 | `contracts/openapi/openapi.yaml` | 前后端共享接口总目录 |
| C02 | 外部供应商接口契约 | `contracts/openapi/admin/providers.yaml` | 供应商后台接口定义 |
| C03 | 外部供应商数据结构 | `contracts/openapi/schemas/admin-providers.yaml` | AI、邮件、短信和易支付配置字段 |
| C04 | AI 管理接口契约 | `contracts/openapi/admin/model-gateway.yaml` 等 | AI 模型、提示词、评测和风控接口 |
| C05 | AI 管理数据结构 | `contracts/openapi/schemas/admin-ai.yaml` | AI 价格、次数、预算、安全阈值和版本字段 |
| C06 | 产品与套餐建议规格 | `docs/product/provider-and-subscription-spec.md` | 产品决策参考；最终运行值由后台配置发布 |
| C07 | 当前开发进度 | `docs/handoffs/DEVELOPMENT_STATUS.md` | 已完成功能、验证结果和下一步计划 |
| C08 | 管理员商业接口契约 | `contracts/openapi/admin/finance.yaml` | 商品、订单、退款、对账和权益调整接口定义 |
| C09 | 管理员商业数据结构 | `contracts/openapi/schemas/admin-business.yaml` | 后台商品价格、次数、权益、审批和财务操作字段 |
| C10 | 邀请推广接口契约 | `contracts/openapi/paths/referrals.yaml`、`contracts/openapi/admin/referrals.yaml` | 用户邀请流程和管理员活动版本操作 |
| C11 | 邀请推广数据结构 | `contracts/openapi/schemas/referrals.yaml` | 活动、里程碑、奖励、风控和绑定状态字段 |

## 目录维护规则

1. 新增页面时，必须在“Android 前端页面”或“管理后台前端”增加一行。
2. 一个文件包含多个页面时，必须写出具体函数或组件名称。
3. 移动或重命名文件时，同一提交内更新本文档。
4. 新增第三方接口时，在“后端接口与业务文件”和“契约与配置”各补一行。
5. 每次开发进度报告应说明本目录是否同步更新。
