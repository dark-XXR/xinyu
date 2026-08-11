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
| W01 | 管理后台工程与运行说明 | `apps/admin-web/package.json`、`apps/admin-web/README.zh-CN.md` | 已创建：安装、启动、类型检查、代码检查和生产构建命令 |
| W02 | 页面入口和路由表 | `apps/admin-web/src/main.tsx`、`apps/admin-web/src/App.tsx` | 已完成：按需加载工作台、用户、公告、客服、商品、订单、支付、邀请推广、供应商、AI、审计和网站设置路由 |
| W03 | 全局导航和移动菜单 | `apps/admin-web/src/components/Layout.tsx` | 已完成：平台/商业/技术合规分组、动态已发布品牌名、移动菜单、当前页高亮和 Escape 关闭 |
| W04 | 管理工作台页面 `/` | `apps/admin-web/src/pages/Dashboard.tsx` | 已完成：系统状态、待办指标、已发布商品、最近活动和快捷入口 |
| W05 | 供应商配置页面 `/providers` | `apps/admin-web/src/pages/Providers.tsx` | 已完成：12 种 AI/邮件/短信/易支付适配器表单、按适配器凭据、配置与真实线上状态、健康检查、发布、回滚和紧急停用；高风险操作要求至少 8 字理由，停用还要求供应商全名二次确认 |
| W06 | 套餐与价格页面 `/commerce/products` | `apps/admin-web/src/pages/commerce/Products.tsx` | 已完成：价格、次数、权益、销售渠道和版本均由后台数据维护，支持发布与真实历史版本回滚 |
| W07 | 订单与退款页面 `/commerce/orders` | `apps/admin-web/src/pages/commerce/Orders.tsx` | 已完成：订单搜索、支付尝试、商品快照、退款审批和退款执行 |
| W08 | 前端数据接口切换层 | `apps/admin-web/src/api/repository.ts` | 已完成：统一 Mock/HTTP 调用，包含供应商、AI、商业、邀请历史版本和合规审计；全部版本化写操作使用真实十进制 `If-Match`，HTTP 使用自动生成客户端，密钥只写不读 |
| W09 | 自动生成模型的引用入口 | `apps/admin-web/src/api/models.ts` | 已完成：集中导出页面使用的供应商、商业、AI 和合规审计接口类型与枚举；不要在此写业务值 |
| W10 | 全局 UI 参数 | `apps/admin-web/src/styles/design-system.css` | 已完成首批：颜色、字号、间距、页签、表格、抽屉、对话框和 390px 卡片布局 |
| W11 | 通用按钮、输入和状态标签 | `apps/admin-web/src/components/ui/Button.tsx`、`Input.tsx`、`Badge.tsx` | 已完成：修改按钮外观、输入框和状态颜色时使用这些文件 |
| W12 | 通用卡片、抽屉和确认框 | `apps/admin-web/src/components/ui/Card.tsx`、`Drawer.tsx`、`Dialog.tsx` | 已完成：焦点约束、Escape 关闭和关闭后恢复焦点 |
| W13 | AI 运行配置页面 `/ai` | `apps/admin-web/src/pages/ai/AiOperations.tsx` | 已完成：模型映射、场景多目标路由、提示词 JSON Schema、评测闸门、风控、灰度发布和真实历史版本回滚 |
| W14 | 合规审计与监管取证页面 `/audit` | `apps/admin-web/src/pages/audit/AuditOperations.tsx` | 已完成：登录、AI 输入输出、充值支付、管理员配置和网站运行日志检索；敏感正文默认不读取，必须填写理由后二次确认；支持法务冻结、哈希链检查和加密导出 |
| W15 | 邀请推广页面 `/referrals` | `apps/admin-web/src/pages/referrals/ReferralsPage.tsx` | 已完成：活动草稿、渠道/绑定门槛、动态奖励规则、反作弊、灰度发布和只选择真实已发布历史的回滚；页面不写死奖励与阈值 |
| W16 | AI 表单下拉框与多行输入 | `apps/admin-web/src/components/ui/Select.tsx`、`apps/admin-web/src/components/ui/Textarea.tsx` | 已完成：AI 配置页的枚举选择、Prompt、JSON Schema 和审计原因输入；错误信息可直接显示在输入框下方 |
| W17 | 用户管理页面 `/users` | `apps/admin-web/src/pages/users/UsersPage.tsx` | 已完成：脱敏搜索与详情；资料编辑、验证码登录安全重置、单设备撤销、冻结/恢复、增减量调额和已发布套餐分配；高风险操作要求理由及用户/设备 ID 确认 |
| W18 | 公告运营页面 `/operations/notices` | `apps/admin-web/src/pages/operations/NoticesPage.tsx` | 已完成：草稿、类型、平台/语言/版本/频次/时间定向、发布和撤回 |
| W19 | 网站设置页面 `/system/settings` | `apps/admin-web/src/pages/system/SettingsPage.tsx` | 已完成：网站/App 名、主体、Logo、客服/隐私邮箱、语言、备案、维护模式及草稿/发布分离 |
| W20 | 支付运营页面 `/commerce/payments` | `apps/admin-web/src/pages/commerce/PaymentsPage.tsx` | 已完成：易支付线上摘要、支付方式、回调地址、订单退款指标和参数化主动对账；不显示商户密钥 |
| W21 | 客服工单页面 `/support` | `apps/admin-web/src/pages/support/SupportPage.tsx` | 已完成：队列、会话、公开回复、内部备注、状态、优先级、分派和审计理由 |

## 后端接口与业务文件

| 编号 | 功能 | 文件路径 | 说明 |
| --- | --- | --- | --- |
| B01 | 后端应用入口与请求审计 | `services/api/src/love_reply_api/main.py` | 注册全部路由；记录请求状态、耗时和匿名 IP 哈希，管理后台写操作请求体经脱敏后审计，普通用户 AI 正文不进入普通元数据 |
| B02 | 普通用户注册/登录接口 | `services/api/src/love_reply_api/transport/http/routes/auth.py` | 邮箱和短信验证码、登录、刷新与退出接口 |
| B03 | 注册/登录业务规则 | `services/api/src/love_reply_api/application/auth.py` | 验证码、频率限制、渠道策略、账号与会话创建 |
| B04 | 管理员登录与 MFA | `services/api/src/love_reply_api/application/admin_auth.py` | 管理员密码、TOTP、多因素会话和权限 |
| B05 | 外部供应商管理接口 | `services/api/src/love_reply_api/transport/http/routes/admin_providers.py` | 列表、新增、读取、更新、密钥、健康检查、发布、回滚和独立权限紧急停用共 9 个操作 |
| B06 | 外部供应商业务服务 | `services/api/src/love_reply_api/application/providers.py` | 加密密钥、不可变版本、审计、发布与停用运行时熔断；停用将线上灰度归零但保留发布锚点供回滚恢复 |
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
| B17 | 邀请推广用户与管理接口 | `services/api/src/love_reply_api/transport/http/routes/referrals.py` | 活动、不可变版本历史、个人邀请码、绑定、进度、奖励、发布和回滚共 11 个操作 |
| B18 | 邀请推广业务规则 | `services/api/src/love_reply_api/application/referrals.py` | 单层绑定、设备和支付身份风控、里程碑、冷静期、发奖、撤销及按版本倒序读取不可变历史 |
| B19 | 邀请推广接口参数 | `services/api/src/love_reply_api/transport/http/referral_schemas.py` | 活动配置、奖励规则、绑定、历史版本发布标记及响应字段校验 |
| B20 | 统一合规审计业务服务 | `services/api/src/love_reply_api/application/audit.py` | 敏感正文加密、凭据脱敏、HMAC-SHA256 哈希链、筛选、法务冻结、完整性校验和加密监管导出 |
| B21 | 管理员合规审计接口 | `services/api/src/love_reply_api/transport/http/routes/admin_audit.py` | 日志列表、敏感正文受控读取、法务冻结、完整性检查、监管导出创建和读取共 6 个操作 |
| B22 | 合规审计接口参数 | `services/api/src/love_reply_api/transport/http/audit_schemas.py` | 审计筛选、正文读取理由、冻结理由和导出理由校验；理由最少 8 字由后端契约控制 |
| B23 | 用户/公告/网站设置管理接口 | `services/api/src/love_reply_api/transport/http/routes/admin_platform.py` | 用户检索、资料、状态、登录重置、设备撤销、发布套餐发放，以及网站配置和公告版本操作；高风险操作使用独立权限、理由、精确 ID 确认和适用的乐观锁 |
| B24 | 平台运营业务规则 | `services/api/src/love_reply_api/application/admin_platform.py` | 用户脱敏、非凭据资料、验证码/会话作废、设备撤销、发布套餐快照发放，以及网站配置/公告版本和追加式业务审计 |
| B25 | 客服用户与管理员接口 | `services/api/src/love_reply_api/transport/http/routes/support.py`、`admin_support.py` | 本人工单创建/读取/回复及管理员队列、内部备注、分派、优先级和解决关闭 |
| B26 | 客服工单业务规则 | `services/api/src/love_reply_api/application/support.py` | 工单归属隔离、关闭门禁、内部备注可见性、乐观锁和管理员审计；正文进入加密敏感审计 |

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
| D10 | 合规审计账本与监管导出表 | `services/api/src/love_reply_api/infrastructure/audit_records.py`、`database/migrations/versions/b91e63a4d2f0_add_compliance_audit_ledger.py` | 追加式统一审计事件、加密正文摘要、保留截止、法务冻结、前序哈希、事件哈希和短效加密导出包 |
| D11 | 供应商紧急停用权限升级 | `database/migrations/versions/c42f19e7ab31_add_provider_disable_permission.py` | 新增 `PROVIDER_DISABLE` 权限并为已有平台所有者安全回填；降级时仅移除该权限 |
| D12 | 平台运营数据表和升级 | `services/api/src/love_reply_api/infrastructure/platform_records.py`、`database/migrations/versions/e31a6d8c4f20_add_core_admin_platform.py` | 网站配置版本、公告版本和平台业务审计 |
| D13 | 客服工单升级 | `database/migrations/versions/f7c216b8a904_add_support_tickets.py` | 工单、消息、索引及客服读写权限回填 |
| D14 | 用户运营写权限升级 | `database/migrations/versions/a82d91c4e630_add_user_operations_permissions.py` | 新增资料编辑、会话撤销和套餐发放权限并为平台所有者回填；已验证升级、降级和再升级 |

## 契约与配置

| 编号 | 功能 | 文件路径 | 说明 |
| --- | --- | --- | --- |
| C01 | OpenAPI 总入口 | `contracts/openapi/openapi.yaml` | 前后端共享接口总目录 |
| C02 | 外部供应商接口契约 | `contracts/openapi/admin/providers.yaml` | 供应商后台 9 个操作，包含独立紧急停用、乐观锁、审计理由和冲突错误 |
| C03 | 外部供应商数据结构 | `contracts/openapi/schemas/admin-providers.yaml` | AI、邮件、短信、易支付配置，以及真实线上版本/灰度/生效时间和停用请求结构 |
| C04 | AI 管理接口契约 | `contracts/openapi/admin/model-gateway.yaml` 等 | AI 模型、提示词、评测和风控接口 |
| C05 | AI 管理数据结构 | `contracts/openapi/schemas/admin-ai.yaml` | AI 价格、次数、预算、安全阈值和版本字段 |
| C06 | 产品与套餐建议规格 | `docs/product/provider-and-subscription-spec.md` | 产品决策参考；最终运行值由后台配置发布 |
| C07 | 合规审计接口契约 | `contracts/openapi/admin/audit.yaml`、`contracts/openapi/schemas/admin-audit.yaml` | 管理员日志检索、敏感正文、冻结、完整性检查和监管导出的共享前后端契约 |
| C07 | 当前开发进度 | `docs/handoffs/DEVELOPMENT_STATUS.md` | 已完成功能、验证结果和下一步计划 |
| C08 | 管理员商业接口契约 | `contracts/openapi/admin/finance.yaml` | 商品、订单、退款、对账和权益调整接口定义 |
| C09 | 管理员商业数据结构 | `contracts/openapi/schemas/admin-business.yaml` | 后台商品价格、次数、权益、审批和财务操作字段 |
| C10 | 邀请推广接口契约 | `contracts/openapi/paths/referrals.yaml`、`contracts/openapi/admin/referrals.yaml` | 用户邀请流程、管理员活动操作和合法回滚目标的不可变历史读取 |
| C11 | 邀请推广数据结构 | `contracts/openapi/schemas/referrals.yaml` | 活动、里程碑、奖励、风控、绑定状态和历史版本发布标记字段 |
| C12 | 管理后台全量功能矩阵 | `docs/product/admin-console-feature-matrix.md` | 对照产品文档跟踪用户、客服、公告、支付运营、CMS、网站配置、RBAC、告警和数据治理，防止局部完成被误报为全部完成 |
| C13 | 用户、公告和网站配置契约 | `contracts/openapi/admin/platform.yaml`、`contracts/openapi/schemas/admin-platform.yaml` | 管理员用户资料、状态、登录重置、设备撤销、发布套餐发放，以及配置版本、公告版本和公共公告接口 |
| C14 | 客服工单契约 | `contracts/openapi/paths/support.yaml`、`contracts/openapi/admin/support.yaml`、`contracts/openapi/schemas/support.yaml` | 用户工单与管理员队列、会话、内部备注和处理字段 |

## 目录维护规则

1. 新增页面时，必须在“Android 前端页面”或“管理后台前端”增加一行。
2. 一个文件包含多个页面时，必须写出具体函数或组件名称。
3. 移动或重命名文件时，同一提交内更新本文档。
4. 新增第三方接口时，在“后端接口与业务文件”和“契约与配置”各补一行。
5. 每次开发进度报告应说明本目录是否同步更新。

## 工程质量配置

| 编号 | 功能 | 文件路径 | 说明 |
| --- | --- | --- | --- |
| Q01 | Python 依赖与质量门禁 | `pyproject.toml` | Ruff、严格 MyPy、Pytest 配置；集成测试统一使用会话级 asyncio 循环，避免 Windows 下共享 asyncpg 连接池复用已关闭循环 |
