# 心语运营台 (Admin Web)

心语运营台是用于管理后台的核心管理系统。支持以下核心能力：

## 主要功能

1. **工作台 (Dashboard)**
   - 核心指标展示（系统健康状态、待支付订单、待审退款、在线商品等）
   - 最新系统活动动态追踪（最新操作及流水）
   - 快捷操作入口，一键管理各类资源

2. **供应商管理 (Providers)**
   - 支持 AI、邮件、短信及支付四类外部网关配置
   - 发布/回滚能力与优先级、限流管理
   - 安全的密钥配置与旋转机制 (Credential Rotations)，确保密码不落地回显
   - 系统级接口连通性健康检查

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
