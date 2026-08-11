/**
 * 数据访问层。
 * 封装 Mock 与真实 HTTP API 的统一 Repository 接口。
 * Mock 数据使用完整的生成模型类型，所有必填字段正确填充。
 * HTTP 模式通过已构建的 @love-reply/generated-api 包中的 API 客户端类发起请求。
 */
import {
  Configuration,
  ADMINPROVIDERApi,
  ADMINCOMMERCEApi,
  ADMINAIApi,
  ADMINRBACApi,
  ADMINPLATFORMApi,
  ADMINSUPPORTApi,
  ProviderKind,
  ProviderStatus,
  OrderStatus,
  RefundStatus,
  ProductPublicationStatus,
  ProductType,
  SalesChannel,
  RenewalType,
  TlsMode,
  OpenAiCompatibleConfigurationAdapterTypeEnum,
  SmtpConfigurationAdapterTypeEnum,
  SmsConfigurationAdapterTypeEnum,
  EpayConfigurationAdapterTypeEnum,
  EpayConfigurationPaymentTypesEnum,
  EpayConfigurationSigningPresetEnum,
  PaymentMethod,
  PaymentAttemptStatus,
  AiResourceStatus,
  AiScenario,
  AiModality,
  AiRiskPolicyPromptInjectionActionEnum,
  AiRiskPolicyWriteRequestPromptInjectionActionEnum,
  AiEvaluationRunStatusEnum,
  AuditEventCategoryEnum,
  AuditEventOutcomeEnum,
  AuditEventSeverityEnum,
  AuditEventActorTypeEnum,
  AccountStatus,
  SupportTicketStatusEnum,
  SupportTicketPriorityEnum,
  NoticeVersionStatusEnum,
  LedgerEntryType,
  SupportMessageSenderTypeEnum,
  AdminUserStatusRequestStatusEnum,
  AdminUpdateSupportTicketRequestStatusEnum,
  AdminUpdateSupportTicketRequestPriorityEnum,
  SystemConfigVersionStatusEnum,
  ADMINREFERRALApi,
  ReferralCampaignStatus,
  ReferralMilestoneCode,
  ReferralBeneficiary,
  RewardUnit,
} from './models';
import type {
  SystemConfigVersion,
} from '@love-reply/generated-api';

export interface SystemConfigResult {
  publishedConfig?: SystemIdentityConfig;
  draftConfig?: SystemIdentityConfig;
  hasUnpublishedChanges: boolean;
  publishedAt?: Date;
  version: number;
  publishedResourceVersion?: number;
  draftResourceVersion?: number;
  resourceVersion?: number;
}
import type {
  Provider,
  AdminOrder,
  AdminProductVersion,
  AdminRefund,
  ProviderWriteRequest,
  CredentialSecretInput,
  AdminProductWriteRequest,
  AdminRefundDecisionRequest,
  AdminRefundExecuteRequest,
  Order,
  BenefitGrant,
  PaymentAttempt,
  ProductOrderSnapshot,
  OpenAiCompatibleConfiguration,
  SmtpConfiguration,
  SmsConfiguration,
  EpayConfiguration,
  AiModelMapping,
  AiModelMappingWriteRequest,
  AiRoute,
  AiRouteTarget,
  AiRouteWriteRequest,
  AiPromptTemplate,
  AiPromptWriteRequest,
  AiRiskPolicy,
  AiRiskPolicyWriteRequest,
  AiEvaluationRun,
  AiEvaluationRunRequest,
  AiPublishRequest,
  AiRollbackRequest,
  AuditEvent,
  AuditIntegrityData,
  SensitiveContentData,
  AuditExportData,
  AuditExportContentData,
  AuditExportRequest,
  AdminUserSummary,
  AdminUserDetail,
  Device,
  Entitlement,
  WalletLedgerEntry,
  NoticeVersion,
  NoticeWriteRequest,
  SystemConfigWriteRequest,
  SystemIdentityConfig,
  SupportTicket,
  SupportMessage,
  PaymentReconciliation,
  ReferralCampaign,
  ReferralCampaignWriteRequest,
  PublishReferralCampaignRequest,
  RollbackReferralCampaignRequest,
  ReferralCampaignVersion,
} from './models';

/* ── 仓库接口 ── */

export interface AuditFilterParams {
  cursor?: string;
  limit?: number;
  category?: AuditEventCategoryEnum | string;
  eventType?: string;
  outcome?: AuditEventOutcomeEnum | string;
  userId?: string;
  adminId?: string;
  orderId?: string;
  generationId?: string;
  requestId?: string;
  from?: Date;
  to?: Date;
}

export interface AuditListResult {
  events: AuditEvent[];
  nextCursor?: string;
}

export interface AiEditorDefaults {
  modelMapping: AiModelMappingWriteRequest;
  route: AiRouteWriteRequest;
  prompt: AiPromptWriteRequest;
  riskPolicy: AiRiskPolicyWriteRequest;
  evaluationRun: AiEvaluationRunRequest;
  publish: AiPublishRequest;
  rollback: AiRollbackRequest;
}

export interface Repository {
  getSystemHealth(): Promise<{ status: string; issues: string[] }>;
  getPendingOrdersCount(): Promise<number>;
  getPendingRefundsCount(): Promise<number>;

  getProviders(): Promise<Provider[]>;
  saveProviderDraft(provider: ProviderWriteRequest, id?: string, resourceVersion?: number): Promise<void>;
  publishProvider(id: string, resourceVersion: number, rolloutPercentage: number, effectiveAt: Date, auditReason: string): Promise<void>;
  rotateProviderCredentials(providerId: string, resourceVersion: number, secrets: CredentialSecretInput[], auditReason: string): Promise<void>;
  rollbackProvider(id: string, resourceVersion: number, targetVersion: number, auditReason: string): Promise<void>;
  disableProvider(providerId: string, resourceVersion: number, auditReason: string): Promise<void>;
  checkProviderHealth(id: string, administratorTestDestination?: string | null, auditReason?: string): Promise<void>;

  getProducts(): Promise<AdminProductVersion[]>;
  saveProductDraft(product: AdminProductWriteRequest, id?: string, resourceVersion?: number): Promise<void>;
  publishProduct(productVersionId: string, resourceVersion: number): Promise<void>;
  rollbackProduct(productCode: string, _resourceVersion: number, targetProductVersionId: string): Promise<void>;

  getOrders(cursor?: string): Promise<AdminOrder[]>;
  getRefunds(): Promise<AdminRefund[]>;
  auditRefund(refundId: string, request: AdminRefundDecisionRequest, resourceVersion: number): Promise<void>;
  executeRefund(refundId: string, request: AdminRefundExecuteRequest, resourceVersion: number): Promise<void>;

  /* AI 运行配置 */
  getAiModelMappings(): Promise<AiModelMapping[]>;
  saveAiModelMapping(request: AiModelMappingWriteRequest, modelMappingId?: string, resourceVersion?: number): Promise<void>;

  getAiRoutes(): Promise<AiRoute[]>;
  saveAiRoute(request: AiRouteWriteRequest, routeId?: string, resourceVersion?: number): Promise<void>;
  publishAiRoute(routeId: string, resourceVersion: number, request: AiPublishRequest): Promise<void>;
  rollbackAiRoute(routeId: string, resourceVersion: number, request: AiRollbackRequest): Promise<void>;

  getAiPrompts(): Promise<AiPromptTemplate[]>;
  saveAiPrompt(request: AiPromptWriteRequest, promptId?: string, resourceVersion?: number): Promise<void>;
  publishAiPrompt(promptId: string, resourceVersion: number, request: AiPublishRequest): Promise<void>;
  rollbackAiPrompt(promptId: string, resourceVersion: number, request: AiRollbackRequest): Promise<void>;

  getAiRiskPolicies(): Promise<AiRiskPolicy[]>;
  saveAiRiskPolicy(request: AiRiskPolicyWriteRequest, riskPolicyId?: string, resourceVersion?: number): Promise<void>;
  publishAiRiskPolicy(riskPolicyId: string, resourceVersion: number, request: AiPublishRequest): Promise<void>;
  rollbackAiRiskPolicy(riskPolicyId: string, resourceVersion: number, request: AiRollbackRequest): Promise<void>;

  runAiEvaluation(request: AiEvaluationRunRequest): Promise<AiEvaluationRun>;
  getAiEvaluationRun(evaluationRunId: string): Promise<AiEvaluationRun | null>;

  getAiEditorDefaults(): Promise<AiEditorDefaults>;

  /* 合规审计管理 */
  getAuditEvents(filter?: AuditFilterParams): Promise<AuditListResult>;
  verifyAuditIntegrity(): Promise<AuditIntegrityData>;
  readAuditSensitiveContent(eventId: string, reason: string): Promise<SensitiveContentData>;
  changeAuditLegalHold(eventId: string, enabled: boolean, reason: string): Promise<AuditEvent>;
  createAuditExport(request: AuditExportRequest): Promise<AuditExportData>;
  readAuditExport(exportId: string, reason: string): Promise<AuditExportContentData>;

  /* 用户管理 */
  getAdminUsers(params?: { search?: string; status?: string; cursor?: string; limit?: number }): Promise<{ users: AdminUserSummary[]; nextCursor?: string; totalCount?: number }>;
  getAdminUserDetail(userId: string): Promise<{ detail: AdminUserDetail; devices: Device[]; entitlements: Entitlement[]; walletEntries: WalletLedgerEntry[] }>;
  changeAdminUserStatus(userId: string, status: AccountStatus, auditReason: string, ifMatch?: string): Promise<void>;

  /* 公告运营 */
  getAdminNotices(params?: { status?: string; type?: string; platform?: string; cursor?: string; limit?: number }): Promise<{ notices: NoticeVersion[]; nextCursor?: string }>;
  createAdminNotice(request: NoticeWriteRequest): Promise<NoticeVersion>;
  updateAdminNotice(noticeId: string, request: NoticeWriteRequest, ifMatch?: string): Promise<NoticeVersion>;
  publishAdminNotice(noticeId: string, auditReason: string, ifMatch?: string): Promise<NoticeVersion>;
  revokeAdminNotice(noticeId: string, auditReason: string, ifMatch?: string): Promise<NoticeVersion>;

  /* 网站设置 */
  getAdminSystemConfig(): Promise<SystemConfigResult>;
  updateAdminSystemConfig(request: SystemConfigWriteRequest, ifMatch?: string): Promise<void>;
  publishAdminSystemConfig(auditReason: string, ifMatch?: string): Promise<void>;

  /* 支付对账 */
  runPaymentReconciliation(staleBefore: Date | string, maxOrders: number, auditReason: string): Promise<PaymentReconciliation>;

  /* 客服工单 */
  getAdminSupportTickets(params?: { status?: string; priority?: string; category?: string; assigneeId?: string; search?: string; cursor?: string; limit?: number }): Promise<{ tickets: SupportTicket[]; nextCursor?: string; totalCount?: number }>;
  getAdminSupportTicketDetail(ticketId: string): Promise<{ ticket: SupportTicket; messages: SupportMessage[] }>;
  updateAdminSupportTicket(ticketId: string, update: { status?: string; priority?: string; assigneeId?: string; replyContent?: string; isInternalNote?: boolean; auditReason?: string }, ifMatch?: string): Promise<SupportTicket>;

  /* 邀请推广 */
  getAdminReferralCampaigns(): Promise<ReferralCampaign[]>;
  getAdminReferralCampaignVersions(campaignId: string): Promise<ReferralCampaignVersion[]>;
  saveAdminReferralCampaign(request: ReferralCampaignWriteRequest, campaignId?: string, resourceVersion?: number): Promise<ReferralCampaign>;
  publishAdminReferralCampaign(campaignId: string, resourceVersion: number, request: PublishReferralCampaignRequest): Promise<ReferralCampaign>;
  rollbackAdminReferralCampaign(campaignId: string, resourceVersion: number, request: RollbackReferralCampaignRequest): Promise<ReferralCampaign>;
}


/* ── HTTP 配置 ── */

function getConfiguration(): Configuration {
  const token = localStorage.getItem('love_reply_admin_access_token');
  if (!token && import.meta.env.VITE_API_BASE_URL) {
    throw new Error('缺少访问令牌');
  }
  return new Configuration({
    basePath: import.meta.env.VITE_API_BASE_URL,
    accessToken: token ?? '',
  });
}


/* ── Mock 数据 ── */

const now = new Date();
const yesterday = new Date(now.getTime() - 86_400_000);

const aiConfig: OpenAiCompatibleConfiguration = {
  adapterType: OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat,
  baseUrl: 'https://api.openai.com/v1',
  timeoutMs: 30_000,
};

const smtpConfig: SmtpConfiguration = {
  adapterType: SmtpConfigurationAdapterTypeEnum.Smtp,
  host: 'smtp.exmail.qq.com',
  port: 465,
  tlsMode: TlsMode.Implicit,
  senderAddress: 'noreply@lovereply.app',
  senderName: '心语助手',
  timeoutMs: 10_000,
};

const smsConfig: SmsConfiguration = {
  adapterType: SmsConfigurationAdapterTypeEnum.AliyunSms,
  region: 'cn-hangzhou',
  signatureId: 'SMS_SIGN_001',
  templateId: 'SMS_TPL_001',
  timeoutMs: 5_000,
};

const epayConfig: EpayConfiguration = {
  adapterType: EpayConfigurationAdapterTypeEnum.EpayCompat,
  gatewayBaseUrl: 'https://pay.example.com',
  submitPath: '/submit',
  queryPath: '/query',
  refundPath: '/refund',
  merchantId: 'M100001',
  paymentTypes: new Set<EpayConfigurationPaymentTypesEnum>([
    EpayConfigurationPaymentTypesEnum.Alipay,
    EpayConfigurationPaymentTypesEnum.WechatPay,
  ]),
  signingPreset: EpayConfigurationSigningPresetEnum.EpayMd5Canonical,
  callbackAckText: 'success',
  notifyUrl: 'https://api.lovereply.app/webhooks/payment',
  returnUrl: 'https://lovereply.app/payment/return',
  callbackTimeWindowSeconds: 300,
  checkoutTtlSeconds: 900,
  timeoutMs: 10_000,
};

const mockState: {
  providers: Provider[];
  products: AdminProductVersion[];
  orders: AdminOrder[];
  refunds: AdminRefund[];
  aiModelMappings: AiModelMapping[];
  aiRoutes: AiRoute[];
  aiPrompts: AiPromptTemplate[];
  aiRiskPolicies: AiRiskPolicy[];
  aiEvaluationRuns: AiEvaluationRun[];
  auditEvents: AuditEvent[];
  users: AdminUserSummary[];
  userDetails: Record<string, { detail: AdminUserDetail; devices: Device[]; entitlements: Entitlement[]; walletEntries: WalletLedgerEntry[] }>;
  notices: NoticeVersion[];
  systemConfig: {
    publishedConfig: SystemIdentityConfig;
    draftConfig?: SystemIdentityConfig;
    hasUnpublishedChanges: boolean;
    publishedAt?: Date;
    version: number;
    publishedResourceVersion: number;
    draftResourceVersion?: number;
  };
  supportTickets: SupportTicket[];
  supportMessages: Record<string, SupportMessage[]>;
  referralCampaigns: ReferralCampaign[];
  referralCampaignVersions: ReferralCampaignVersion[];
} = {
  providers: [
    {
      providerId: 'prov-ai-001',
      providerName: 'OpenAI 官方',
      kind: ProviderKind.Ai,
      status: ProviderStatus.Active,
      _configuration: aiConfig,
      dataRegion: 'US-EAST',
      retentionStatement: '30-day log retention',
      retryLimit: 3,
      priority: 1,
      rolloutPercentage: 100,
      credentialConfigured: true,
      publishedResourceVersion: 2,
      publishedRolloutPercentage: 100,
      publishedEffectiveAt: yesterday,
      resourceVersion: 2,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies Provider,
    {
      providerId: 'prov-email-001',
      providerName: '腾讯企业邮 SMTP',
      kind: ProviderKind.Email,
      status: ProviderStatus.Draft,
      _configuration: smtpConfig,
      dataRegion: 'CN-SOUTH',
      retentionStatement: 'No log retention',
      retryLimit: 2,
      priority: 1,
      rolloutPercentage: 0,
      credentialConfigured: false,
      publishedResourceVersion: null,
      publishedRolloutPercentage: 0,
      publishedEffectiveAt: null,
      resourceVersion: 1,
      createdAt: yesterday,
      updatedAt: yesterday,
    } satisfies Provider,
    {
      providerId: 'prov-sms-001',
      providerName: '阿里云短信',
      kind: ProviderKind.Sms,
      status: ProviderStatus.Active,
      _configuration: smsConfig,
      dataRegion: 'CN-HANGZHOU',
      retentionStatement: '90-day log retention',
      retryLimit: 3,
      priority: 1,
      rolloutPercentage: 100,
      credentialConfigured: true,
      publishedResourceVersion: 3,
      publishedRolloutPercentage: 100,
      publishedEffectiveAt: yesterday,
      resourceVersion: 3,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies Provider,
    {
      providerId: 'prov-pay-001',
      providerName: '易支付网关',
      kind: ProviderKind.Payment,
      status: ProviderStatus.Active,
      _configuration: epayConfig,
      dataRegion: 'CN-SHANGHAI',
      retentionStatement: 'Financial log retention',
      retryLimit: 2,
      priority: 1,
      rolloutPercentage: 100,
      credentialConfigured: true,
      publishedResourceVersion: 4,
      publishedRolloutPercentage: 100,
      publishedEffectiveAt: yesterday,
      resourceVersion: 4,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies Provider,
  ],

  products: [
    {
      productVersionId: 'pv-001',
      productCode: 'MONTHLY_BASIC',
      version: 2,
      productType: ProductType.Plan,
      displayName: '基础月度套餐',
      description: '每月基础回复额度',
      currency: 'CNY',
      amountMinor: 990,
      region: 'CN',
      salesChannels: new Set<SalesChannel>([SalesChannel.Android]),
      renewalType: RenewalType.None,
      termDays: 30,
      benefitWindowDays: 30,
      benefits: { textQuota: 100, visionQuota: 10, energyAmount: 0, allowedModelIds: new Set<string>(), allowedStyleIds: new Set<string>(), deepAnalysisEnabled: false } satisfies BenefitGrant,
      status: ProductPublicationStatus.Active,
      effectiveAt: yesterday,
      resourceVersion: 2,
      createdByAdminId: 'admin-001',
      createdAt: yesterday,
      updatedAt: now,
    } satisfies AdminProductVersion,
    {
      productVersionId: 'pv-000',
      productCode: 'MONTHLY_BASIC',
      version: 1,
      productType: ProductType.Plan,
      displayName: '基础月度套餐 v1',
      description: '初版基础套餐',
      currency: 'CNY',
      amountMinor: 790,
      region: 'CN',
      salesChannels: new Set<SalesChannel>([SalesChannel.Android]),
      renewalType: RenewalType.None,
      termDays: 30,
      benefitWindowDays: 30,
      benefits: { textQuota: 80, visionQuota: 8, energyAmount: 0, allowedModelIds: new Set<string>(), allowedStyleIds: new Set<string>(), deepAnalysisEnabled: false } satisfies BenefitGrant,
      status: ProductPublicationStatus.Retired,
      effectiveAt: new Date(yesterday.getTime() - 86_400_000),
      resourceVersion: 1,
      createdByAdminId: 'admin-001',
      createdAt: new Date(yesterday.getTime() - 86_400_000),
      updatedAt: yesterday,
    } satisfies AdminProductVersion,
    {
      productVersionId: 'pv-002',
      productCode: 'ENERGY_50',
      version: 1,
      productType: ProductType.EnergyPack,
      displayName: '50 能量包',
      description: '即买即用能量充值包',
      currency: 'CNY',
      amountMinor: 500,
      region: 'CN',
      salesChannels: new Set<SalesChannel>([SalesChannel.Android, SalesChannel.AdminAssisted]),
      renewalType: RenewalType.None,
      benefitWindowDays: 365,
      benefits: { textQuota: 50, visionQuota: 5, energyAmount: 50, allowedModelIds: new Set<string>(), allowedStyleIds: new Set<string>(), deepAnalysisEnabled: false } satisfies BenefitGrant,
      status: ProductPublicationStatus.Draft,
      effectiveAt: now,
      resourceVersion: 1,
      createdByAdminId: 'admin-001',
      createdAt: now,
      updatedAt: now,
    } satisfies AdminProductVersion,
  ],

  orders: [
    {
      userId: 'user-001',
      order: {
        orderId: 'ord-20240801-001',
        status: OrderStatus.Paid,
        product: {
          productVersionId: 'pv-001',
          productCode: 'MONTHLY_BASIC',
          version: 2,
          displayName: '基础月度套餐',
          currency: 'CNY',
          amountMinor: 990,
          renewalType: RenewalType.None,
          termDays: 30,
          benefitWindowDays: 30,
          benefits: { textQuota: 100, visionQuota: 10, energyAmount: 0, allowedModelIds: new Set<string>(), allowedStyleIds: new Set<string>(), deepAnalysisEnabled: false } satisfies BenefitGrant,
        } satisfies ProductOrderSnapshot,
        currency: 'CNY',
        amountMinor: 990,
        paidAmountMinor: 990,
        paidAt: now,
        paymentAttempts: [
          {
            paymentAttemptId: 'pa-001',
            paymentMethod: PaymentMethod.Alipay,
            status: PaymentAttemptStatus.Succeeded,
            amountMinor: 990,
            currency: 'CNY',
            createdAt: now,
            updatedAt: now,
          } satisfies PaymentAttempt,
        ],
        entitlementGranted: true,
        resourceVersion: 1,
        createdAt: yesterday,
        updatedAt: now,
      } satisfies Order,
    } satisfies AdminOrder,
    {
      userId: 'user-002',
      order: {
        orderId: 'ord-20240802-001',
        status: OrderStatus.Created,
        product: {
          productVersionId: 'pv-002',
          productCode: 'ENERGY_50',
          version: 1,
          displayName: '50 能量包',
          currency: 'CNY',
          amountMinor: 500,
          renewalType: RenewalType.None,
          termDays: null,
          benefitWindowDays: 365,
          benefits: { textQuota: 50, visionQuota: 5, energyAmount: 50, allowedModelIds: new Set<string>(), allowedStyleIds: new Set<string>(), deepAnalysisEnabled: false } satisfies BenefitGrant,
        } satisfies ProductOrderSnapshot,
        currency: 'CNY',
        amountMinor: 500,
        paidAmountMinor: 0,
        paymentAttempts: [],
        entitlementGranted: false,
        resourceVersion: 1,
        createdAt: now,
        updatedAt: now,
      } satisfies Order,
    } satisfies AdminOrder,
  ],

  refunds: [
    {
      refundId: 'ref-001',
      orderId: 'ord-20240801-001',
      status: RefundStatus.Requested,
      currency: 'CNY',
      requestedAmountMinor: 990,
      refundedAmountMinor: 0,
      reasonCode: 'USER_REQUEST',
      entitlementRecoveryStatus: 'PENDING',
      resourceVersion: 1,
      createdAt: now,
      updatedAt: now,
      userId: 'user-001',
    } satisfies AdminRefund,
  ],

  aiModelMappings: [
    {
      modelMappingId: 'mm-001',
      logicalModelId: 'gpt-4o-mini',
      providerId: 'prov-ai-001',
      providerModelName: 'gpt-4o-mini-2024-07-18',
      inputModalities: new Set<AiModality>([AiModality.Text]),
      outputModalities: new Set<AiModality>([AiModality.Text]),
      contextWindowTokens: 128000,
      maxOutputTokens: 16384,
      inputCostMicrounitsPerMillionTokens: 150,
      outputCostMicrounitsPerMillionTokens: 600,
      currency: 'USD',
      qualityTier: 'STANDARD',
      dataRegion: 'GLOBAL',
      retentionPolicy: 'ZERO_DATA_RETENTION',
      status: AiResourceStatus.Active,
      enabled: true,
      resourceVersion: 1,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies AiModelMapping,
    {
      modelMappingId: 'mm-002',
      logicalModelId: 'deepseek-r1',
      providerId: 'prov-ai-001',
      providerModelName: 'deepseek-reasoner',
      inputModalities: new Set<AiModality>([AiModality.Text]),
      outputModalities: new Set<AiModality>([AiModality.Text]),
      contextWindowTokens: 64000,
      maxOutputTokens: 8192,
      inputCostMicrounitsPerMillionTokens: 550,
      outputCostMicrounitsPerMillionTokens: 2190,
      currency: 'USD',
      qualityTier: 'HIGH',
      dataRegion: 'GLOBAL',
      retentionPolicy: 'ZERO_DATA_RETENTION',
      status: AiResourceStatus.Draft,
      enabled: false,
      resourceVersion: 1,
      createdAt: now,
      updatedAt: now,
    } satisfies AiModelMapping,
  ],

  aiRoutes: [
    {
      routeId: 'rt-reply-v2',
      version: 2,
      scenario: AiScenario.ReplyGeneration,
      logicalModelId: 'gpt-4o-mini',
      targets: [
        {
          modelMappingId: 'mm-001',
          priority: 1,
          timeoutMs: 15000,
          retryLimit: 2,
        } satisfies AiRouteTarget,
      ],
      maxInputTokens: 4096,
      maxOutputTokens: 2048,
      budgetCeilingMicrounits: 5000,
      totalAttemptLimit: 3,
      safetyPolicyId: 'pol-strict-01',
      status: AiResourceStatus.Active,
      rolloutPercentage: 100,
      effectiveAt: yesterday,
      resourceVersion: 2,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies AiRoute,
    {
      routeId: 'rt-reply-v1',
      version: 1,
      scenario: AiScenario.ReplyGeneration,
      logicalModelId: 'gpt-4o-mini',
      targets: [
        {
          modelMappingId: 'mm-001',
          priority: 1,
          timeoutMs: 20000,
          retryLimit: 1,
        } satisfies AiRouteTarget,
      ],
      maxInputTokens: 2048,
      maxOutputTokens: 1024,
      budgetCeilingMicrounits: 3000,
      totalAttemptLimit: 2,
      safetyPolicyId: 'pol-strict-01',
      status: AiResourceStatus.Superseded,
      rolloutPercentage: 0,
      effectiveAt: yesterday,
      resourceVersion: 1,
      createdAt: yesterday,
      updatedAt: yesterday,
    } satisfies AiRoute,
  ],

  aiPrompts: [
    {
      promptId: 'prompt-reply-v2',
      version: 2,
      promptCode: 'REPLY_DEFAULT',
      scenario: AiScenario.ReplyGeneration,
      systemTemplate: '你是一个高情商恋爱回复助手，请根据对方的聊天消息生成体贴且幽默的回复。',
      userTemplate: '对方消息：{{message}}；期望语气：{{tone}}',
      allowedInputFields: new Set<string>(['message', 'tone']),
      outputSchema: {
        type: 'object',
        properties: {
          replies: {
            type: 'array',
            items: { type: 'string' },
          },
        },
        required: ['replies'],
      },
      safetyPolicyId: 'pol-strict-01',
      status: AiResourceStatus.Active,
      effectiveAt: yesterday,
      resourceVersion: 2,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies AiPromptTemplate,
    {
      promptId: 'prompt-reply-v1',
      version: 1,
      promptCode: 'REPLY_DEFAULT',
      scenario: AiScenario.ReplyGeneration,
      systemTemplate: '你是一个恋爱助手。',
      userTemplate: '对方消息：{{message}}',
      allowedInputFields: new Set<string>(['message']),
      outputSchema: {
        type: 'object',
        properties: {
          replies: { type: 'array', items: { type: 'string' } },
        },
      },
      safetyPolicyId: 'pol-strict-01',
      status: AiResourceStatus.Superseded,
      effectiveAt: yesterday,
      resourceVersion: 1,
      createdAt: yesterday,
      updatedAt: yesterday,
    } satisfies AiPromptTemplate,
  ],

  aiRiskPolicies: [
    {
      riskPolicyId: 'pol-strict-01',
      version: 1,
      policyCode: 'STRICT_SAFETY',
      blockedCategories: new Set<string>(['HATE_SPEECH', 'HARASSMENT', 'EXPLICIT_CONTENT']),
      reviewCategories: new Set<string>(['SENSITIVE_POLITICS']),
      inputModerationEnabled: true,
      outputModerationEnabled: true,
      promptInjectionAction: AiRiskPolicyPromptInjectionActionEnum.Block,
      minimumSafetyScore: 85,
      allowAppeals: true,
      status: AiResourceStatus.Active,
      effectiveAt: yesterday,
      resourceVersion: 1,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies AiRiskPolicy,
    {
      riskPolicyId: 'pol-strict-00',
      version: 0,
      policyCode: 'STRICT_SAFETY',
      blockedCategories: new Set<string>(['HATE_SPEECH']),
      reviewCategories: new Set<string>(['SENSITIVE_POLITICS']),
      inputModerationEnabled: true,
      outputModerationEnabled: false,
      promptInjectionAction: AiRiskPolicyPromptInjectionActionEnum.Review,
      minimumSafetyScore: 70,
      allowAppeals: false,
      status: AiResourceStatus.Superseded,
      effectiveAt: yesterday,
      resourceVersion: 1,
      createdAt: yesterday,
      updatedAt: yesterday,
    } satisfies AiRiskPolicy,
  ],

  aiEvaluationRuns: [
    {
      evaluationRunId: 'eval-run-001',
      promptId: 'prompt-reply-v2',
      routeId: 'rt-reply-v2',
      suiteIds: ['suite-general-01', 'suite-safety-01'],
      status: AiEvaluationRunStatusEnum.Succeeded,
      passed: true,
      totalCases: 100,
      completedCases: 100,
      score: 96.5,
      safetyPassed: true,
      costMicrounits: 12000,
      failureCode: null,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies AiEvaluationRun,
  ],

  auditEvents: [
    {
      eventId: 'evt-auth-001',
      occurredAt: new Date(now.getTime() - 3600_000 * 2),
      category: AuditEventCategoryEnum.Auth,
      eventType: 'login.success',
      outcome: AuditEventOutcomeEnum.Succeeded,
      severity: AuditEventSeverityEnum.Info,
      actorType: AuditEventActorTypeEnum.User,
      actorId: 'user-001',
      userId: 'user-001',
      sessionId: 'sess-auth-8801',
      requestId: 'req-auth-001',
      clientPlatform: 'ANDROID',
      clientVersion: '1.2.0',
      summary: '用户通过邮件验证码成功登录系统',
      // 真实后端只保存部署密钥 HMAC 哈希，不保存原始 IP 地址
      metadata: { loginChannel: 'EMAIL', ipHash: 'hmac-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
      containsSensitiveContent: false,
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: '0000000000000000000000000000000000000000000000000000000000000000',
      eventHash: 'a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890',
    } satisfies AuditEvent,
    {
      eventId: 'evt-auth-002',
      occurredAt: new Date(now.getTime() - 3600_000 * 5),
      category: AuditEventCategoryEnum.Auth,
      eventType: 'login.failed',
      outcome: AuditEventOutcomeEnum.Failed,
      severity: AuditEventSeverityEnum.Warning,
      actorType: AuditEventActorTypeEnum.Admin,
      actorId: 'admin-002',
      adminId: 'admin-002',
      requestId: 'req-auth-002',
      clientPlatform: 'ADMIN_WEB',
      clientVersion: '1.0.0',
      summary: '管理员 MFA 动态口令校验失败（连续尝试 2 次）',
      // 真实后端只保存部署密钥 HMAC 哈希，不保存原始 IP 地址
      metadata: { failureReason: 'MFA_CODE_MISMATCH', attemptCount: 2, ipHash: 'hmac-sha256:5d41402abc4b2a76b9719d911017c592abe8f495f5700c291d28023d01d4c1d0' },
      containsSensitiveContent: false,
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: 'a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890',
      eventHash: 'b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1',
    } satisfies AuditEvent,
    {
      eventId: 'evt-ai-001',
      occurredAt: new Date(now.getTime() - 3600_000 * 12),
      category: AuditEventCategoryEnum.Ai,
      eventType: 'ai.generation.completed',
      outcome: AuditEventOutcomeEnum.Succeeded,
      severity: AuditEventSeverityEnum.Info,
      actorType: AuditEventActorTypeEnum.User,
      actorId: 'user-001',
      userId: 'user-001',
      requestId: 'req-ai-1001',
      generationId: 'gen-20240809-001',
      providerId: 'prov-ai-001',
      summary: '恋爱高情商回复生成完成（耗时 1250ms）',
      metadata: { scenario: 'ReplyGeneration', tokensUsed: 380, model: 'gpt-4o-mini' },
      containsSensitiveContent: true,
      sensitivePayloadDigest: 'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: 'b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1',
      eventHash: 'c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2',
    } satisfies AuditEvent,
    {
      eventId: 'evt-ai-002',
      occurredAt: new Date(now.getTime() - 3600_000 * 18),
      category: AuditEventCategoryEnum.Ai,
      eventType: 'content.moderated',
      outcome: AuditEventOutcomeEnum.Failed,
      severity: AuditEventSeverityEnum.High,
      actorType: AuditEventActorTypeEnum.User,
      actorId: 'user-003',
      userId: 'user-003',
      requestId: 'req-ai-1002',
      generationId: 'gen-20240809-002',
      summary: '风控策略阻断违规提示词输入',
      metadata: { ruleId: 'RULE_PROMPT_INJECTION_001', action: 'BLOCK' },
      containsSensitiveContent: true,
      sensitivePayloadDigest: 'sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: true,
      previousEventHash: 'c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2',
      eventHash: 'd4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3',
    } satisfies AuditEvent,
    {
      eventId: 'evt-pay-001',
      occurredAt: new Date(now.getTime() - 3600_000 * 24),
      category: AuditEventCategoryEnum.Payment,
      eventType: 'order.created',
      outcome: AuditEventOutcomeEnum.Succeeded,
      severity: AuditEventSeverityEnum.Info,
      actorType: AuditEventActorTypeEnum.User,
      actorId: 'user-001',
      userId: 'user-001',
      orderId: 'ord-20240801-001',
      summary: '创建基础月度套餐购买订单 (¥9.90)',
      metadata: { amountMinor: 990, currency: 'CNY', productCode: 'MONTHLY_BASIC' },
      containsSensitiveContent: false,
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: 'd4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3',
      eventHash: 'e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4',
    } satisfies AuditEvent,
    {
      eventId: 'evt-pay-002',
      occurredAt: new Date(now.getTime() - 3600_000 * 23.5),
      category: AuditEventCategoryEnum.Payment,
      eventType: 'payment.succeeded',
      outcome: AuditEventOutcomeEnum.Succeeded,
      severity: AuditEventSeverityEnum.Info,
      actorType: AuditEventActorTypeEnum.System,
      userId: 'user-001',
      orderId: 'ord-20240801-001',
      providerId: 'prov-pay-001',
      summary: '易支付网关支付回调校验成功并自动到账',
      metadata: { paymentMethod: 'ALIPAY', paidAmountMinor: 990, gatewayTxnId: 'epay_txn_99887711' },
      containsSensitiveContent: false,
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: 'e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4',
      eventHash: 'f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5',
    } satisfies AuditEvent,
    {
      eventId: 'evt-admin-001',
      occurredAt: new Date(now.getTime() - 3600_000 * 30),
      category: AuditEventCategoryEnum.Admin,
      eventType: 'provider.updated',
      outcome: AuditEventOutcomeEnum.Succeeded,
      severity: AuditEventSeverityEnum.Critical,
      actorType: AuditEventActorTypeEnum.Admin,
      actorId: 'admin-001',
      adminId: 'admin-001',
      resourceType: 'PROVIDER',
      resourceId: 'prov-ai-001',
      summary: '管理员安全轮换 OpenAI 上游 API Key 凭据',
      metadata: { auditReason: '例行安全密钥轮换及凭据合规审计' },
      containsSensitiveContent: false,
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: 'f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5',
      eventHash: '7890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f6',
    } satisfies AuditEvent,
    {
      eventId: 'evt-ops-001',
      occurredAt: new Date(now.getTime() - 3600_000 * 36),
      category: AuditEventCategoryEnum.Operations,
      eventType: 'system.error',
      outcome: AuditEventOutcomeEnum.Failed,
      severity: AuditEventSeverityEnum.Error,
      actorType: AuditEventActorTypeEnum.System,
      requestId: 'req-err-9901',
      summary: '数据库主从同步延迟引发连接池瞬间超时',
      metadata: { errorStack: 'DBPoolTimeoutException: Timeout waiting for connection', poolSize: 50 },
      containsSensitiveContent: false,
      retentionUntil: new Date(now.getTime() + 86400_000 * 365),
      legalHold: false,
      previousEventHash: '7890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f6',
      eventHash: '890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67',
    } satisfies AuditEvent,
  ],
  users: [
    {
      userId: 'usr_10000001',
      maskedPhone: '138****8888',
      maskedEmail: 'w***g@example.com',
      nickname: '活跃测试者',
      locale: 'zh-CN',
      timeZone: 'Asia/Shanghai',
      status: AccountStatus.Active,
      planCode: 'VIP_MONTHLY',
      planExpiresAt: new Date(now.getTime() + 20 * 86400000),
      textRemaining: 82,
      visionRemaining: 15,
      energyBalance: 520000,
      deviceCount: 2,
      resourceVersion: 1,
      createdAt: new Date(now.getTime() - 30 * 86400000),
      updatedAt: new Date(now.getTime() - 10 * 60000),
    },
    {
      userId: 'usr_10000002',
      maskedPhone: '159****6666',
      maskedEmail: 'z***g@example.com',
      nickname: '体验用户',
      locale: 'zh-CN',
      timeZone: 'Asia/Shanghai',
      status: AccountStatus.Suspended,
      planCode: 'FREE',
      planExpiresAt: undefined,
      textRemaining: 0,
      visionRemaining: 0,
      energyBalance: 0,
      deviceCount: 1,
      resourceVersion: 1,
      createdAt: new Date(now.getTime() - 60 * 86400000),
      updatedAt: new Date(now.getTime() - 2 * 86400000),
    },
    {
      userId: 'usr_10000003',
      maskedPhone: '186****3333',
      maskedEmail: 'l***i@example.com',
      nickname: '尊享年卡用户',
      locale: 'zh-CN',
      timeZone: 'Asia/Shanghai',
      status: AccountStatus.Active,
      planCode: 'VIP_YEARLY',
      planExpiresAt: new Date(now.getTime() + 300 * 86400000),
      textRemaining: 9999,
      visionRemaining: 999,
      energyBalance: 1500000,
      deviceCount: 3,
      resourceVersion: 1,
      createdAt: new Date(now.getTime() - 90 * 86400000),
      updatedAt: new Date(now.getTime() - 2 * 60000),
    },
  ],
  userDetails: {
    usr_10000001: {
      detail: {
        userId: 'usr_10000001',
        maskedPhone: '138****8888',
        maskedEmail: 'w***g@example.com',
        nickname: '活跃测试者',
        locale: 'zh-CN',
        timeZone: 'Asia/Shanghai',
        status: AccountStatus.Active,
        planCode: 'VIP_MONTHLY',
        planExpiresAt: new Date(now.getTime() + 20 * 86400000),
        textRemaining: 82,
        visionRemaining: 15,
        energyBalance: 520000,
        deviceCount: 2,
        resourceVersion: 1,
        createdAt: new Date(now.getTime() - 30 * 86400000),
        updatedAt: new Date(now.getTime() - 10 * 60000),
        devices: [
          { deviceId: 'dev_101', platform: 'ANDROID', appVersion: '2.4.0', deviceModel: 'Xiaomi 13 Pro', ipMasked: '221.192.***.12', lastLoginAt: new Date() },
        ],
        consents: [
          { consentId: 'cst_01', type: 'PRIVACY_POLICY', version: 'v1.2', agreedAt: new Date() },
        ],
      },
      devices: [
        {
          deviceId: 'dev_101',
          platform: 'ANDROID' as const,
          model: 'Xiaomi 13 Pro',
          current: true,
          lastSeenAt: new Date(now.getTime() - 10 * 60000),
          createdAt: new Date(now.getTime() - 30 * 86400000),
        },
      ],
      entitlements: [
        {
          userId: 'usr_10000001',
          planCode: 'VIP_MONTHLY',
          planExpiresAt: new Date(now.getTime() + 20 * 86400000),
          benefits: { textRemaining: 82, visionRemaining: 15, allowedModelIds: new Set(['gpt-4o', 'deepseek-r1']), allowedStyleIds: new Set(['default']) },
          wallet: { energyBalance: 520000, energyReserved: 0, energyAvailable: 520000 },
          resourceVersion: 1,
          updatedAt: new Date(),
        },
      ],
      walletEntries: [
        {
          ledgerEntryId: 'led_201',
          entryType: LedgerEntryType.Credit,
          energyDelta: 500000,
          reservedDelta: 0,
          balanceAfter: 520000,
          reservedAfter: 0,
          reasonCode: 'ANNUAL_VIP_REWARD',
          createdAt: new Date(now.getTime() - 86400000),
        },
      ],
    },
  },
  notices: [
    {
      noticeVersionId: 'ntc_v101',
      noticeId: 'ntc_101',
      version: 1,
      title: '系统版本 v2.4.0 升级通知',
      body: '包含更稳定的大模型接入机制、全新的客服工单系统与优化体验。',
      noticeType: 'GENERAL',
      targetPlatforms: ['ADMIN_WEB', 'ANDROID'],
      targetLocales: ['zh-CN'],
      displayFrequency: 'ONCE',
      status: NoticeVersionStatusEnum.Published,
      startsAt: new Date(now.getTime() - 7 * 86400000),
      createdByAdminId: 'admin_master',
      createdAt: new Date(now.getTime() - 7 * 86400000),
      updatedAt: new Date(now.getTime() - 7 * 86400000),
      resourceVersion: 1,
    },
    {
      noticeVersionId: 'ntc_v102',
      noticeId: 'ntc_102',
      version: 1,
      title: '微信支付通道例行维护公告',
      body: '微信支付服务商进行底层例行维护，维护期间推荐优先使用支付宝支付。',
      noticeType: 'MAINTENANCE',
      targetPlatforms: ['ANDROID'],
      targetLocales: ['zh-CN'],
      displayFrequency: 'EVERY_LAUNCH',
      status: NoticeVersionStatusEnum.Draft,
      startsAt: new Date(now.getTime() + 1 * 86400000),
      createdByAdminId: 'admin_master',
      createdAt: new Date(now.getTime() - 1 * 86400000),
      updatedAt: new Date(now.getTime() - 1 * 86400000),
      resourceVersion: 1,
    },
    {
      noticeVersionId: 'ntc_v103',
      noticeId: 'ntc_103',
      version: 1,
      title: '新春限时特惠活动已开启',
      body: '即日起解锁年度 VIP 尊享买一送一，限时赠送 1,000,000 Token！',
      noticeType: 'PROMOTION',
      targetPlatforms: ['ANDROID'],
      targetLocales: ['zh-CN'],
      displayFrequency: 'ONCE_PER_VERSION',
      status: NoticeVersionStatusEnum.Revoked,
      startsAt: new Date(now.getTime() - 15 * 86400000),
      createdByAdminId: 'admin_master',
      createdAt: new Date(now.getTime() - 16 * 86400000),
      updatedAt: new Date(now.getTime() - 1 * 86400000),
      resourceVersion: 1,
    },
  ],
  systemConfig: {
    publishedConfig: {
      websiteName: '爱回复 Web 运营管理后台',
      appName: '爱回复 APP',
      companyName: '爱回复科技（北京）有限公司',
      logoUrl: 'https://cdn.example.com/logo.png',
      customerServiceEmail: 'support@lovereply.app',
      privacyEmail: 'privacy@lovereply.app',
      defaultLocale: 'zh-CN',
      officialWebsiteUrl: 'https://lovereply.app',
      filingInformation: '京ICP备20260999号-2A',
      maintenanceMode: false,
      maintenanceMessage: '系统例行维护中，请稍后再试。',
    },
    draftConfig: undefined,
    hasUnpublishedChanges: false,
    version: 1,
    publishedResourceVersion: 1,
    draftResourceVersion: undefined,
    publishedAt: new Date(now.getTime() - 10 * 86400000),
  },
  supportTickets: [
    {
      ticketId: 'tkt_9001',
      userId: 'usr_10000001',
      category: 'RECHARGE',
      subject: '微信支付成功但订单状态显示待支付',
      status: SupportTicketStatusEnum.WaitingSupport,
      priority: SupportTicketPriorityEnum.High,
      assignedAdminId: 'admin_master',
      lastMessageAt: new Date(now.getTime() - 15 * 60000),
      createdAt: new Date(now.getTime() - 2 * 3600000),
      updatedAt: new Date(now.getTime() - 15 * 60000),
      resourceVersion: 1,
    },
    {
      ticketId: 'tkt_9002',
      userId: 'usr_10000002',
      category: 'AI_MODEL',
      subject: '深度思考模型生成卡顿与超时失败反馈',
      status: SupportTicketStatusEnum.Open,
      priority: SupportTicketPriorityEnum.Normal,
      assignedAdminId: null,
      lastMessageAt: new Date(now.getTime() - 45 * 60000),
      createdAt: new Date(now.getTime() - 5 * 3600000),
      updatedAt: new Date(now.getTime() - 45 * 60000),
      resourceVersion: 1,
    },
    {
      ticketId: 'tkt_9003',
      userId: 'usr_10000003',
      category: 'ACCOUNT',
      subject: '申请解冻账号与异常登录提醒核验',
      status: SupportTicketStatusEnum.Resolved,
      priority: SupportTicketPriorityEnum.Urgent,
      assignedAdminId: 'admin_sec',
      lastMessageAt: new Date(now.getTime() - 1 * 86400000),
      createdAt: new Date(now.getTime() - 2 * 86400000),
      updatedAt: new Date(now.getTime() - 1 * 86400000),
      resourceVersion: 2,
    },
  ],
  supportMessages: {
    tkt_9001: [
      {
        messageId: 'msg_01',
        ticketId: 'tkt_9001',
        senderType: 'USER',
        senderId: 'usr_10000001',
        body: '我刚刚通过微信支付了 29.00 元购买 VIP 月卡，扣款成功了但是账户里没收到额度。订单号是 ord_2026020901',
        internal: false,
        createdAt: new Date(now.getTime() - 2 * 3600000),
      },
      {
        messageId: 'msg_02',
        ticketId: 'tkt_9001',
        senderType: 'ADMIN',
        senderId: 'admin_master',
        body: '已收悉您的反馈，已为您触发主动补单与对账逻辑，请问您现在的刷新余额是否有更新？',
        internal: false,
        createdAt: new Date(now.getTime() - 15 * 60000),
      },
      {
        messageId: 'msg_03',
        ticketId: 'tkt_9001',
        senderType: 'ADMIN',
        senderId: 'admin_master',
        body: '【内部备注】供应商回调日志显示 IP 匹配异常，触发延迟对账机制，已手动触发补发。',
        internal: true,
        createdAt: new Date(now.getTime() - 10 * 60000),
      },
    ],
  },
  referralCampaigns: [
    {
      campaignId: 'ref-camp-001',
      version: 2,
      campaignCode: 'SUMMER_INVITE_2024',
      displayName: '2024暑期裂变邀请大促',
      description: '邀请好友成功注册并完成首充，双方均可获得高额能量包与文本额度奖励。',
      status: ReferralCampaignStatus.Active,
      region: 'CN',
      salesChannels: new Set<SalesChannel>([SalesChannel.Android]),
      bindingWindowHours: 72,
      maxQualifiedInvitesPerInviter: 100,
      rewardRules: [
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 10,
          coolingOffHours: 0,
        },
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Invitee,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 10,
          coolingOffHours: 0,
        },
        {
          milestoneCode: ReferralMilestoneCode.FirstPurchase,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 50,
          coolingOffHours: 24,
        },
      ],
      antiAbusePolicy: {
        blockSelfReferral: true,
        blockSameDevice: true,
        blockSamePaymentIdentity: true,
        requireVerifiedPrimaryChannel: true,
        riskReviewScore: 80,
      },
      rolloutPercentage: 100,
      effectiveAt: yesterday,
      resourceVersion: 2,
      createdAt: yesterday,
      updatedAt: now,
    } satisfies ReferralCampaign,
    {
      campaignId: 'ref-camp-002',
      version: 1,
      campaignCode: 'NEW_USER_WELCOME',
      displayName: '新用户好礼邀请计划',
      description: '针对新用户注册后发起拉新的基础奖励计划，双向赠送对话额度。',
      status: ReferralCampaignStatus.Draft,
      region: 'CN',
      salesChannels: new Set<SalesChannel>([SalesChannel.Android, SalesChannel.AdminAssisted]),
      bindingWindowHours: 168,
      maxQualifiedInvitesPerInviter: 50,
      rewardRules: [
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.TextQuota,
          rewardAmount: 20,
          coolingOffHours: 0,
        },
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Invitee,
          rewardUnit: RewardUnit.TextQuota,
          rewardAmount: 20,
          coolingOffHours: 0,
        },
      ],
      antiAbusePolicy: {
        blockSelfReferral: true,
        blockSameDevice: true,
        blockSamePaymentIdentity: false,
        requireVerifiedPrimaryChannel: true,
        riskReviewScore: 60,
      },
      rolloutPercentage: 0,
      effectiveAt: now,
      resourceVersion: 1,
      createdAt: now,
      updatedAt: now,
    } satisfies ReferralCampaign,
  ],
  referralCampaignVersions: [
    {
      campaignVersionId: 'ver-ref-001-v1',
      campaignId: 'ref-camp-001',
      version: 1,
      campaignCode: 'SUMMER_INVITE_2024',
      displayName: '2024暑期裂变邀请大促 (v1基础版)',
      description: '基础版拉新激励',
      region: 'CN',
      salesChannels: [SalesChannel.Android],
      bindingWindowHours: 48,
      maxQualifiedInvitesPerInviter: 50,
      rewardRules: [
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 10,
          coolingOffHours: 0,
        },
      ],
      antiAbusePolicy: {
        blockSelfReferral: true,
        blockSameDevice: true,
        blockSamePaymentIdentity: false,
        requireVerifiedPrimaryChannel: false,
        riskReviewScore: 60,
      },
      wasPublished: true,
      action: 'PUBLISH',
      createdByAdminId: 'admin_001',
      createdAt: yesterday,
    },
    {
      campaignVersionId: 'ver-ref-001-v2',
      campaignId: 'ref-camp-001',
      version: 2,
      campaignCode: 'SUMMER_INVITE_2024',
      displayName: '2024暑期裂变邀请大促',
      description: '邀请好友成功注册并完成首充，双方均可获得高额能量包与文本额度奖励。',
      region: 'CN',
      salesChannels: [SalesChannel.Android],
      bindingWindowHours: 72,
      maxQualifiedInvitesPerInviter: 100,
      rewardRules: [
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 10,
          coolingOffHours: 0,
        },
        {
          milestoneCode: ReferralMilestoneCode.AccountVerified,
          beneficiary: ReferralBeneficiary.Invitee,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 10,
          coolingOffHours: 0,
        },
        {
          milestoneCode: ReferralMilestoneCode.FirstPurchase,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 50,
          coolingOffHours: 24,
        },
      ],
      antiAbusePolicy: {
        blockSelfReferral: true,
        blockSameDevice: true,
        blockSamePaymentIdentity: true,
        requireVerifiedPrimaryChannel: true,
        riskReviewScore: 80,
      },
      wasPublished: true,
      action: 'PUBLISH',
      createdByAdminId: 'admin_001',
      createdAt: now,
    },
  ] satisfies ReferralCampaignVersion[],
};

const mockSensitiveStore: Record<string, Record<string, any>> = {
  'evt-ai-001': {
    userPrompt: '对方发送：“今天加班好累啊，感觉整个人都被掏空了”，我该如何回应？',
    aiReply: '推荐回复：“辛苦啦！赶紧泡个热水澡放松一下，今晚啥都别想，好好休息，做个好梦~”',
    contextMetadata: { tone: 'EMPATHETIC', length: 'SHORT', style: 'WARM' },
  },
  'evt-ai-002': {
    rawInputText: '用户在对话框中尝试调试异常控制流指令...',
    blockedRule: 'RULE_PROMPT_INJECTION_001',
    safetyAnalysis: { riskScore: 0.96, category: 'PROMPT_INJECTION' },
  },
};

/* ── Mock 仓库 ── */

const mockRepository: Repository = {
  async getSystemHealth() {
    const unhealthy = mockState.providers.filter(
      (p) => p.status !== ProviderStatus.Active && p.status !== ProviderStatus.Draft,
    );
    return {
      status: unhealthy.length === 0 ? 'healthy' : 'warning',
      issues: unhealthy.map((p) => `${p.providerName} 状态异常: ${p.status}`),
    };
  },

  async getPendingOrdersCount() {
    return mockState.orders.filter((o) => o.order.status === OrderStatus.Created).length;
  },

  async getPendingRefundsCount() {
    return mockState.refunds.filter((r) => r.status === RefundStatus.Requested).length;
  },

  async getProviders() {
    return [...mockState.providers];
  },

  async saveProviderDraft(req, id, _resourceVersion) {
    if (id) {
      const idx = mockState.providers.findIndex((p) => p.providerId === id);
      if (idx !== -1) {
        const existing = mockState.providers[idx];
        mockState.providers[idx] = {
          ...existing,
          providerName: req.providerName,
          kind: req.kind,
          _configuration: req._configuration,
          dataRegion: req.dataRegion ?? null,
          retentionStatement: req.retentionStatement ?? null,
          retryLimit: req.retryLimit,
          priority: req.priority,
          status: ProviderStatus.Draft,
          rolloutPercentage: 0,
          effectiveAt: null,
          lastHealthStatus: null,
          resourceVersion: existing.resourceVersion + 1,
          updatedAt: new Date(),
        };
      }
    } else {
      mockState.providers.push({
        providerId: `prov-${Date.now()}`,
        providerName: req.providerName,
        kind: req.kind,
        status: ProviderStatus.Draft,
        _configuration: req._configuration,
        dataRegion: req.dataRegion ?? null,
        retentionStatement: req.retentionStatement ?? null,
        retryLimit: req.retryLimit,
        priority: req.priority,
        rolloutPercentage: 0,
        credentialConfigured: false,
        publishedResourceVersion: null,
        publishedRolloutPercentage: 0,
        publishedEffectiveAt: null,
        lastHealthStatus: null,
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async publishProvider(id, _rv, rolloutPercentage, effectiveAt, _auditReason) {
    const p = mockState.providers.find((item) => item.providerId === id);
    if (p) {
      p.status = ProviderStatus.Active;
      p.rolloutPercentage = rolloutPercentage;
      p.effectiveAt = effectiveAt;
      p.publishedResourceVersion = p.resourceVersion;
      p.publishedRolloutPercentage = rolloutPercentage;
      p.publishedEffectiveAt = effectiveAt;
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async rollbackProvider(id, _rv, targetVersion, _auditReason) {
    const p = mockState.providers.find((item) => item.providerId === id);
    if (p) {
      const now = new Date();
      p.status = ProviderStatus.Active;
      p.rolloutPercentage = 100;
      p.effectiveAt = now;
      p.publishedResourceVersion = targetVersion;
      p.publishedRolloutPercentage = 100;
      p.publishedEffectiveAt = now;
      p.resourceVersion += 1;
      p.updatedAt = now;
    }
  },

  async disableProvider(providerId, _rv, _auditReason) {
    const p = mockState.providers.find((item) => item.providerId === providerId);
    if (p) {
      p.status = ProviderStatus.Disabled;
      p.rolloutPercentage = 0;
      p.effectiveAt = null;
      p.publishedRolloutPercentage = 0;
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async rotateProviderCredentials(providerId, _resourceVersion, _secrets, _auditReason) {
    const p = mockState.providers.find((item) => item.providerId === providerId);
    if (p) {
      p.credentialConfigured = true;
      p.status = ProviderStatus.Draft;
      p.lastHealthStatus = null;
      // 凭据轮换成功后，生成草稿，设置灰度比例为 0% 且生效时间置空
      p.rolloutPercentage = 0;
      p.effectiveAt = null;
      // 保留 publishedResourceVersion、publishedRolloutPercentage、publishedEffectiveAt，以模拟旧线上快照继续运行
      Object.assign(p, {
        credentialFingerprint: 'mock-fingerprint-' + Date.now(),
        credentialRotatedAt: new Date(),
      });
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async checkProviderHealth(id, _administratorTestDestination, _auditReason) {
    const p = mockState.providers.find((item) => item.providerId === id);
    if (p && p.credentialConfigured) {
      p.lastHealthStatus = 'HEALTHY';
      p.status = ProviderStatus.Ready;
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async getProducts() {
    return [...mockState.products];
  },

  async saveProductDraft(req, id, _rv) {
    if (id) {
      const idx = mockState.products.findIndex((p) => p.productVersionId === id);
      if (idx !== -1) {
        const existing = mockState.products[idx];
        mockState.products[idx] = {
          ...existing,
          displayName: req.displayName,
          productType: req.productType,
          currency: req.currency,
          amountMinor: req.amountMinor,
          region: req.region,
          salesChannels: req.salesChannels,
          renewalType: req.renewalType,
          termDays: req.termDays ?? undefined,
          benefitWindowDays: req.benefitWindowDays,
          benefits: req.benefits,
          description: req.description ?? undefined,
          resourceVersion: existing.resourceVersion + 1,
          updatedAt: new Date(),
        };
      }
    } else {
      mockState.products.push({
        productVersionId: `pv-${Date.now()}`,
        productCode: req.productCode,
        version: 1,
        productType: req.productType,
        displayName: req.displayName,
        description: req.description ?? undefined,
        currency: req.currency,
        amountMinor: req.amountMinor,
        region: req.region,
        salesChannels: req.salesChannels,
        renewalType: req.renewalType,
        termDays: req.termDays ?? undefined,
        benefitWindowDays: req.benefitWindowDays,
        benefits: req.benefits,
        status: ProductPublicationStatus.Draft,
        effectiveAt: new Date(),
        resourceVersion: 1,
        createdByAdminId: 'admin-001',
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async publishProduct(pvId, _rv) {
    const p = mockState.products.find((item) => item.productVersionId === pvId);
    if (p) {
      p.status = ProductPublicationStatus.Active;
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async rollbackProduct(productCode, _rv, targetProductVersionId) {
    const active = mockState.products.find(
      (item) => item.productCode === productCode && item.status === ProductPublicationStatus.Active,
    );
    if (active) {
      active.status = ProductPublicationStatus.Retired;
      active.resourceVersion += 1;
      active.updatedAt = new Date();
    }
    const target = mockState.products.find(
      (item) => item.productVersionId === targetProductVersionId,
    );
    if (target) {
      target.status = ProductPublicationStatus.Active;
      target.resourceVersion += 1;
      target.updatedAt = new Date();
    }
  },

  async getOrders() {
    return [...mockState.orders];
  },

  async getRefunds() {
    return [...mockState.refunds];
  },

  async auditRefund(refundId, req) {
    const r = mockState.refunds.find((item) => item.refundId === refundId);
    if (r) {
      r.status = req.decision === 'APPROVE' ? RefundStatus.Approved : RefundStatus.Rejected;
      r.resourceVersion += 1;
      r.updatedAt = new Date();
    }
  },

  async executeRefund(refundId) {
    const r = mockState.refunds.find((item) => item.refundId === refundId);
    if (r) {
      r.status = RefundStatus.Succeeded;
      r.refundedAmountMinor = r.requestedAmountMinor;
      r.resourceVersion += 1;
      r.updatedAt = new Date();

      /* 同步更新订单状态 */
      const adminOrder = mockState.orders.find((o) => o.order.orderId === r.orderId);
      if (adminOrder) {
        const totalRefunded = mockState.refunds
          .filter((ref) => ref.orderId === r.orderId && ref.status === RefundStatus.Succeeded)
          .reduce((sum, ref) => sum + ref.refundedAmountMinor, 0);

        if (totalRefunded >= adminOrder.order.amountMinor) {
          adminOrder.order.status = OrderStatus.Refunded;
        } else {
          adminOrder.order.status = OrderStatus.PartiallyRefunded;
        }
        adminOrder.order.resourceVersion += 1;
        adminOrder.order.updatedAt = new Date();
      }
    }
  },

  /* ── AI 运行配置 Mock 实现 ── */
  async getAiModelMappings() {
    return [...mockState.aiModelMappings];
  },

  async saveAiModelMapping(req, id, _rv) {
    if (id) {
      const idx = mockState.aiModelMappings.findIndex((m) => m.modelMappingId === id);
      if (idx !== -1) {
        const existing = mockState.aiModelMappings[idx];
        mockState.aiModelMappings[idx] = {
          ...existing,
          logicalModelId: req.logicalModelId,
          providerId: req.providerId,
          providerModelName: req.providerModelName,
          inputModalities: req.inputModalities,
          outputModalities: req.outputModalities,
          contextWindowTokens: req.contextWindowTokens,
          maxOutputTokens: req.maxOutputTokens,
          inputCostMicrounitsPerMillionTokens: req.inputCostMicrounitsPerMillionTokens,
          outputCostMicrounitsPerMillionTokens: req.outputCostMicrounitsPerMillionTokens,
          currency: req.currency,
          qualityTier: req.qualityTier ?? undefined,
          dataRegion: req.dataRegion ?? undefined,
          retentionPolicy: req.retentionPolicy ?? undefined,
          enabled: req.enabled,
          resourceVersion: existing.resourceVersion + 1,
          updatedAt: new Date(),
        };
      }
    } else {
      mockState.aiModelMappings.push({
        modelMappingId: `mm-${Date.now()}`,
        logicalModelId: req.logicalModelId,
        providerId: req.providerId,
        providerModelName: req.providerModelName,
        inputModalities: req.inputModalities,
        outputModalities: req.outputModalities,
        contextWindowTokens: req.contextWindowTokens,
        maxOutputTokens: req.maxOutputTokens,
        inputCostMicrounitsPerMillionTokens: req.inputCostMicrounitsPerMillionTokens,
        outputCostMicrounitsPerMillionTokens: req.outputCostMicrounitsPerMillionTokens,
        currency: req.currency,
        qualityTier: req.qualityTier ?? undefined,
        dataRegion: req.dataRegion ?? undefined,
        retentionPolicy: req.retentionPolicy ?? undefined,
        status: AiResourceStatus.Draft,
        enabled: req.enabled,
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async getAiRoutes() {
    return [...mockState.aiRoutes];
  },

  async saveAiRoute(req, id, _rv) {
    if (id) {
      const idx = mockState.aiRoutes.findIndex((r) => r.routeId === id);
      if (idx !== -1) {
        const existing = mockState.aiRoutes[idx];
        mockState.aiRoutes[idx] = {
          ...existing,
          scenario: req.scenario,
          logicalModelId: req.logicalModelId,
          targets: req.targets,
          maxInputTokens: req.maxInputTokens,
          maxOutputTokens: req.maxOutputTokens,
          budgetCeilingMicrounits: req.budgetCeilingMicrounits,
          totalAttemptLimit: req.totalAttemptLimit,
          safetyPolicyId: req.safetyPolicyId,
          resourceVersion: existing.resourceVersion + 1,
          updatedAt: new Date(),
        };
      }
    } else {
      const existingMaxVer = mockState.aiRoutes
        .filter((r) => r.scenario === req.scenario)
        .reduce((max, r) => Math.max(max, r.version), 0);
      mockState.aiRoutes.push({
        routeId: `rt-${Date.now()}`,
        version: existingMaxVer + 1,
        scenario: req.scenario,
        logicalModelId: req.logicalModelId,
        targets: req.targets,
        maxInputTokens: req.maxInputTokens,
        maxOutputTokens: req.maxOutputTokens,
        budgetCeilingMicrounits: req.budgetCeilingMicrounits,
        totalAttemptLimit: req.totalAttemptLimit,
        safetyPolicyId: req.safetyPolicyId,
        status: AiResourceStatus.Draft,
        rolloutPercentage: 0,
        effectiveAt: new Date(),
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async publishAiRoute(id, _rv, req) {
    const route = mockState.aiRoutes.find((r) => r.routeId === id);
    if (route) {
      mockState.aiRoutes.forEach((r) => {
        if (r.scenario === route.scenario && r.status === AiResourceStatus.Active) {
          r.status = AiResourceStatus.Superseded;
          r.rolloutPercentage = 0;
          r.resourceVersion += 1;
          r.updatedAt = new Date();
        }
      });
      route.status = AiResourceStatus.Active;
      route.rolloutPercentage = req.rolloutPercentage;
      route.effectiveAt = req.effectiveAt;
      route.resourceVersion += 1;
      route.updatedAt = new Date();
    }
  },

  async rollbackAiRoute(id, _rv, req) {
    const current = mockState.aiRoutes.find((r) => r.routeId === id);
    if (current) {
      current.status = AiResourceStatus.Superseded;
      current.rolloutPercentage = 0;
      current.resourceVersion += 1;
      current.updatedAt = new Date();

      const target = mockState.aiRoutes.find(
        (r) => r.scenario === current.scenario && r.version === req.targetVersion,
      );
      if (target) {
        target.status = AiResourceStatus.Active;
        target.rolloutPercentage = 100;
        target.resourceVersion += 1;
        target.updatedAt = new Date();
      }
    }
  },

  async getAiPrompts() {
    return [...mockState.aiPrompts];
  },

  async saveAiPrompt(req, id, _rv) {
    if (id) {
      const idx = mockState.aiPrompts.findIndex((p) => p.promptId === id);
      if (idx !== -1) {
        const existing = mockState.aiPrompts[idx];
        mockState.aiPrompts[idx] = {
          ...existing,
          promptCode: req.promptCode,
          scenario: req.scenario,
          systemTemplate: req.systemTemplate,
          userTemplate: req.userTemplate,
          allowedInputFields: req.allowedInputFields,
          outputSchema: req.outputSchema,
          safetyPolicyId: req.safetyPolicyId ?? undefined,
          resourceVersion: existing.resourceVersion + 1,
          updatedAt: new Date(),
        };
      }
    } else {
      const maxVer = mockState.aiPrompts
        .filter((p) => p.promptCode === req.promptCode)
        .reduce((max, p) => Math.max(max, p.version), 0);
      mockState.aiPrompts.push({
        promptId: `prompt-${Date.now()}`,
        version: maxVer + 1,
        promptCode: req.promptCode,
        scenario: req.scenario,
        systemTemplate: req.systemTemplate,
        userTemplate: req.userTemplate,
        allowedInputFields: req.allowedInputFields,
        outputSchema: req.outputSchema,
        safetyPolicyId: req.safetyPolicyId ?? undefined,
        status: AiResourceStatus.Draft,
        effectiveAt: new Date(),
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async publishAiPrompt(id, _rv, req) {
    const prompt = mockState.aiPrompts.find((p) => p.promptId === id);
    if (prompt) {
      mockState.aiPrompts.forEach((p) => {
        if (p.promptCode === prompt.promptCode && p.status === AiResourceStatus.Active) {
          p.status = AiResourceStatus.Superseded;
          p.resourceVersion += 1;
          p.updatedAt = new Date();
        }
      });
      prompt.status = AiResourceStatus.Active;
      prompt.effectiveAt = req.effectiveAt;
      prompt.resourceVersion += 1;
      prompt.updatedAt = new Date();
    }
  },

  async rollbackAiPrompt(id, _rv, req) {
    const current = mockState.aiPrompts.find((p) => p.promptId === id);
    if (current) {
      current.status = AiResourceStatus.Superseded;
      current.resourceVersion += 1;
      current.updatedAt = new Date();

      const target = mockState.aiPrompts.find(
        (p) => p.promptCode === current.promptCode && p.version === req.targetVersion,
      );
      if (target) {
        target.status = AiResourceStatus.Active;
        target.resourceVersion += 1;
        target.updatedAt = new Date();
      }
    }
  },

  async getAiRiskPolicies() {
    return [...mockState.aiRiskPolicies];
  },

  async saveAiRiskPolicy(req, id, _rv) {
    if (id) {
      const idx = mockState.aiRiskPolicies.findIndex((p) => p.riskPolicyId === id);
      if (idx !== -1) {
        const existing = mockState.aiRiskPolicies[idx];
        mockState.aiRiskPolicies[idx] = {
          ...existing,
          policyCode: req.policyCode,
          blockedCategories: req.blockedCategories,
          reviewCategories: req.reviewCategories,
          inputModerationEnabled: req.inputModerationEnabled,
          outputModerationEnabled: req.outputModerationEnabled,
          promptInjectionAction: req.promptInjectionAction,
          minimumSafetyScore: req.minimumSafetyScore,
          allowAppeals: req.allowAppeals,
          resourceVersion: existing.resourceVersion + 1,
          updatedAt: new Date(),
        };
      }
    } else {
      const maxVer = mockState.aiRiskPolicies
        .filter((p) => p.policyCode === req.policyCode)
        .reduce((max, p) => Math.max(max, p.version), 0);
      mockState.aiRiskPolicies.push({
        riskPolicyId: `pol-${Date.now()}`,
        version: maxVer + 1,
        policyCode: req.policyCode,
        blockedCategories: req.blockedCategories,
        reviewCategories: req.reviewCategories,
        inputModerationEnabled: req.inputModerationEnabled,
        outputModerationEnabled: req.outputModerationEnabled,
        promptInjectionAction: req.promptInjectionAction,
        minimumSafetyScore: req.minimumSafetyScore,
        allowAppeals: req.allowAppeals,
        status: AiResourceStatus.Draft,
        effectiveAt: new Date(),
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async publishAiRiskPolicy(id, _rv, req) {
    const pol = mockState.aiRiskPolicies.find((p) => p.riskPolicyId === id);
    if (pol) {
      mockState.aiRiskPolicies.forEach((p) => {
        if (p.policyCode === pol.policyCode && p.status === AiResourceStatus.Active) {
          p.status = AiResourceStatus.Superseded;
          p.resourceVersion += 1;
          p.updatedAt = new Date();
        }
      });
      pol.status = AiResourceStatus.Active;
      pol.effectiveAt = req.effectiveAt;
      pol.resourceVersion += 1;
      pol.updatedAt = new Date();
    }
  },

  async rollbackAiRiskPolicy(id, _rv, req) {
    const current = mockState.aiRiskPolicies.find((p) => p.riskPolicyId === id);
    if (current) {
      current.status = AiResourceStatus.Superseded;
      current.resourceVersion += 1;
      current.updatedAt = new Date();

      const target = mockState.aiRiskPolicies.find(
        (p) => p.policyCode === current.policyCode && p.version === req.targetVersion,
      );
      if (target) {
        target.status = AiResourceStatus.Active;
        target.resourceVersion += 1;
        target.updatedAt = new Date();
      }
    }
  },

  async runAiEvaluation(req) {
    const newRun: AiEvaluationRun = {
      evaluationRunId: `eval-${Date.now()}`,
      promptId: req.promptId,
      routeId: req.routeId,
      suiteIds: Array.from(req.suiteIds),
      status: AiEvaluationRunStatusEnum.Succeeded,
      passed: true,
      totalCases: 50,
      completedCases: 50,
      score: 95.0,
      safetyPassed: true,
      costMicrounits: Math.min(req.maxCostMicrounits, 8500),
      failureCode: null,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    mockState.aiEvaluationRuns.unshift(newRun);
    return newRun;
  },

  async getAiEvaluationRun(evaluationRunId) {
    return mockState.aiEvaluationRuns.find((r) => r.evaluationRunId === evaluationRunId) ?? null;
  },

  async getAiEditorDefaults(): Promise<AiEditorDefaults> {
    return {
      modelMapping: {
        logicalModelId: 'gpt-4o-mini',
        providerId: mockState.providers[0]?.providerId ?? 'prov-ai-001',
        providerModelName: 'gpt-4o-mini-2024-07-18',
        inputModalities: new Set<AiModality>([AiModality.Text]),
        outputModalities: new Set<AiModality>([AiModality.Text]),
        contextWindowTokens: 128000,
        maxOutputTokens: 4096,
        inputCostMicrounitsPerMillionTokens: 150,
        outputCostMicrounitsPerMillionTokens: 600,
        currency: 'USD',
        qualityTier: 'STANDARD',
        dataRegion: 'GLOBAL',
        retentionPolicy: 'ZERO_DATA_RETENTION',
        enabled: true,
      },
      route: {
        scenario: AiScenario.ReplyGeneration,
        logicalModelId: 'gpt-4o-mini',
        targets: [
          {
            modelMappingId: mockState.aiModelMappings[0]?.modelMappingId ?? 'mm-001',
            priority: 1,
            timeoutMs: 15000,
            retryLimit: 2,
          },
        ],
        maxInputTokens: 4096,
        maxOutputTokens: 2048,
        budgetCeilingMicrounits: 5000,
        totalAttemptLimit: 3,
        safetyPolicyId: mockState.aiRiskPolicies[0]?.riskPolicyId ?? 'pol-strict-01',
      },
      prompt: {
        promptCode: 'REPLY_NEW',
        scenario: AiScenario.ReplyGeneration,
        systemTemplate: '你是一个高情商聊天助手。',
        userTemplate: '用户输入：{{message}}',
        allowedInputFields: new Set<string>(['message']),
        outputSchema: {
          type: 'object',
          properties: {
            reply: { type: 'string' },
          },
          required: ['reply'],
        },
        safetyPolicyId: mockState.aiRiskPolicies[0]?.riskPolicyId ?? 'pol-strict-01',
      },
      riskPolicy: {
        policyCode: 'NEW_SAFETY_POLICY',
        blockedCategories: new Set<string>(['HATE_SPEECH', 'HARASSMENT']),
        reviewCategories: new Set<string>(['SENSITIVE_POLITICS']),
        inputModerationEnabled: true,
        outputModerationEnabled: true,
        promptInjectionAction: AiRiskPolicyWriteRequestPromptInjectionActionEnum.Block,
        minimumSafetyScore: 80,
        allowAppeals: true,
      },
      evaluationRun: {
        promptId: mockState.aiPrompts[0]?.promptId ?? 'prompt-reply-v2',
        routeId: mockState.aiRoutes[0]?.routeId ?? 'rt-reply-v2',
        suiteIds: new Set<string>(['suite-general-01', 'suite-safety-01']),
        evaluatorLogicalModelId: 'gpt-4o-mini',
        maxCostMicrounits: 50000,
      },
      publish: {
        rolloutPercentage: 100,
        effectiveAt: new Date(),
        evaluationRunId: mockState.aiEvaluationRuns[0]?.evaluationRunId ?? 'eval-run-001',
        auditReason: '管理后台发布新版本',
      },
      rollback: {
        targetVersion: 1,
        auditReason: '管理后台误操作紧急回滚',
      },
    };
  },

  /* ── 合规审计 Mock 实现 ── */
  async getAuditEvents(filter) {
    let list = [...mockState.auditEvents];
    if (filter?.category && filter.category !== 'ALL') {
      list = list.filter((e) => e.category === filter.category);
    }
    if (filter?.outcome && filter.outcome !== 'ALL') {
      list = list.filter((e) => e.outcome === filter.outcome);
    }
    if (filter?.userId?.trim()) {
      const uId = filter.userId.trim().toLowerCase();
      list = list.filter((e) => e.userId?.toLowerCase().includes(uId));
    }
    if (filter?.adminId?.trim()) {
      const aId = filter.adminId.trim().toLowerCase();
      list = list.filter((e) => e.adminId?.toLowerCase().includes(aId));
    }
    if (filter?.orderId?.trim()) {
      const oId = filter.orderId.trim().toLowerCase();
      list = list.filter((e) => e.orderId?.toLowerCase().includes(oId));
    }
    if (filter?.generationId?.trim()) {
      const gId = filter.generationId.trim().toLowerCase();
      list = list.filter((e) => e.generationId?.toLowerCase().includes(gId));
    }
    if (filter?.requestId?.trim()) {
      const rId = filter.requestId.trim().toLowerCase();
      list = list.filter((e) => e.requestId?.toLowerCase().includes(rId));
    }
    if (filter?.from) {
      const fromTime = new Date(filter.from).getTime();
      list = list.filter((e) => e.occurredAt.getTime() >= fromTime);
    }
    if (filter?.to) {
      const toTime = new Date(filter.to).getTime();
      list = list.filter((e) => e.occurredAt.getTime() <= toTime);
    }
    list.sort((a, b) => b.occurredAt.getTime() - a.occurredAt.getTime());
    return { events: list };
  },

  async verifyAuditIntegrity() {
    return {
      valid: true,
      checkedCount: mockState.auditEvents.length,
      firstInvalidEventId: null,
    };
  },

  async readAuditSensitiveContent(eventId, reason) {
    if (!reason || reason.trim().length < 8) {
      throw new Error('审查敏感正文必须填写至少 8 个字符的具体理由');
    }
    const content = mockSensitiveStore[eventId] || {
      notice: '该日志已被严格脱敏安全归档',
      context: '系统敏感正文数据哈希校验一致，没有敏感凭据泄漏风险',
    };
    return { eventId, content };
  },

  async changeAuditLegalHold(eventId, enabled, reason) {
    if (!reason || reason.trim().length < 8) {
      throw new Error('法务冻结控制必须填写至少 8 个字符的具体理由');
    }
    const evt = mockState.auditEvents.find((e) => e.eventId === eventId);
    if (!evt) {
      throw new Error(`未找到 ID 为 ${eventId} 的审计日志`);
    }
    evt.legalHold = enabled;
    return { ...evt };
  },

  async createAuditExport(request) {
    if (!request.auditReason || request.auditReason.trim().length < 8) {
      throw new Error('创建审计导出包必须填写至少 8 个字符的具体理由');
    }
    const exportId = `exp-${Date.now()}`;
    const expiresAt = new Date(Date.now() + 3600_000 * 24);
    return {
      exportId,
      includeSensitiveContent: request.includeSensitiveContent,
      eventCount: mockState.auditEvents.length,
      bundleDigest: 'sha256:7f83b1657ff1...[防篡改签名链]',
      createdAt: new Date(),
      expiresAt,
    };
  },

  async readAuditExport(exportId, reason) {
    if (!reason || reason.trim().length < 8) {
      throw new Error('读取导出数据必须填写至少 8 个字符的具体理由');
    }
    return {
      exportId,
      bundle: {
        exportId,
        readReason: reason,
        generatedAt: new Date().toISOString(),
        totalRecords: mockState.auditEvents.length,
        integrityStatus: 'VERIFIED_CHAIN_OK',
        records: mockState.auditEvents.map((e: AuditEvent) => ({
          eventId: e.eventId,
          occurredAt: e.occurredAt.toISOString(),
          category: e.category,
          eventType: e.eventType,
          summary: e.summary,
          eventHash: e.eventHash,
        })),
      },
    };
  },

  /* 用户管理 */
  async getAdminUsers(params) {
    let list = mockState.users;
    if (params?.search) {
      const q = params.search.toLowerCase();
      list = list.filter(
        (u) =>
          u.userId.toLowerCase().includes(q) ||
          (u.maskedPhone && u.maskedPhone.includes(q)) ||
          (u.maskedEmail && u.maskedEmail.toLowerCase().includes(q)),
      );
    }
    if (params?.status) {
      list = list.filter((u) => u.status === params.status);
    }
    return { users: list, totalCount: list.length };
  },

  async getAdminUserDetail(userId) {
    const data = mockState.userDetails[userId] || {
      detail: {
        userId,
        maskedPhone: '138****0000',
        maskedEmail: 'u***r@example.com',
        nickname: '用户',
        locale: 'zh-CN',
        timeZone: 'Asia/Shanghai',
        status: AccountStatus.Active,
        textRemaining: 10,
        visionRemaining: 5,
        energyBalance: 10000,
        deviceCount: 1,
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
        devices: [],
        consents: [],
      },
      devices: [
        {
          deviceId: 'dev_mock_01',
          platform: 'ANDROID' as const,
          model: 'Android Device',
          current: true,
          lastSeenAt: new Date(),
          createdAt: new Date(),
        },
      ],
      entitlements: [
        {
          userId,
          planCode: 'STANDARD_QUOTA',
          planExpiresAt: new Date(Date.now() + 30 * 86400000),
          benefits: { textRemaining: 10, visionRemaining: 5 },
          wallet: { energyBalance: 10000, reservedBalance: 0 },
          resourceVersion: 1,
          updatedAt: new Date(),
        },
      ],
      walletEntries: [
        {
          ledgerEntryId: 'led_mock',
          entryType: LedgerEntryType.Credit,
          energyDelta: 10000,
          reservedDelta: 0,
          balanceAfter: 10000,
          reservedAfter: 0,
          reasonCode: 'WELCOME',
          createdAt: new Date(),
        },
      ],
    };
    return data;
  },

  async changeAdminUserStatus(userId, status, _auditReason) {
    const user = mockState.users.find((u) => u.userId === userId);
    if (user) {
      user.status = status;
    }
    if (mockState.userDetails[userId]) {
      mockState.userDetails[userId].detail.status = status;
    }
  },

  /* 公告运营 Mock */
  async getAdminNotices(params) {
    let list = mockState.notices;
    if (params?.status) {
      list = list.filter((n) => n.status === params.status);
    }
    if (params?.type) {
      list = list.filter((n) => n.noticeType === params.type);
    }
    return { notices: list };
  },

  async createAdminNotice(request) {
    const newNotice: NoticeVersion = {
      noticeVersionId: 'ntc_v_' + Date.now(),
      noticeId: 'ntc_' + Date.now(),
      version: 1,
      title: request.title,
      body: request.body,
      noticeType: request.noticeType,
      targetPlatforms: Array.from(request.targetPlatforms),
      targetLocales: Array.from(request.targetLocales),
      displayFrequency: request.displayFrequency,
      status: NoticeVersionStatusEnum.Draft,
      startsAt: request.startsAt,
      createdByAdminId: 'admin_master',
      createdAt: new Date(),
      updatedAt: new Date(),
      resourceVersion: 1,
    };
    mockState.notices.unshift(newNotice);
    return newNotice;
  },

  async updateAdminNotice(noticeId, request) {
    const item = mockState.notices.find((n) => n.noticeId === noticeId);
    if (item) {
      item.title = request.title;
      item.body = request.body;
      item.noticeType = request.noticeType;
      item.targetPlatforms = Array.from(request.targetPlatforms);
      item.targetLocales = Array.from(request.targetLocales);
      item.displayFrequency = request.displayFrequency;
      item.startsAt = request.startsAt;
      item.updatedAt = new Date();
      return item;
    }
    throw new Error('公告不存在');
  },

  async publishAdminNotice(noticeId, _auditReason) {
    const item = mockState.notices.find((n) => n.noticeId === noticeId);
    if (item) {
      item.status = NoticeVersionStatusEnum.Published;
      return item;
    }
    throw new Error('公告不存在');
  },

  async revokeAdminNotice(noticeId, _auditReason) {
    const item = mockState.notices.find((n) => n.noticeId === noticeId);
    if (item) {
      item.status = NoticeVersionStatusEnum.Revoked;
      return item;
    }
    throw new Error('公告不存在');
  },

  /* 网站设置 Mock 实现 */
  async getAdminSystemConfig(): Promise<SystemConfigResult> {
    const hasUnpublished = mockState.systemConfig.hasUnpublishedChanges;
    return {
      publishedConfig: mockState.systemConfig.publishedConfig,
      draftConfig: hasUnpublished ? mockState.systemConfig.draftConfig : undefined,
      hasUnpublishedChanges: hasUnpublished,
      publishedAt: mockState.systemConfig.publishedAt,
      version: mockState.systemConfig.version,
      publishedResourceVersion: mockState.systemConfig.publishedResourceVersion,
      draftResourceVersion: hasUnpublished ? mockState.systemConfig.draftResourceVersion : undefined,
      resourceVersion: hasUnpublished
        ? mockState.systemConfig.draftResourceVersion
        : mockState.systemConfig.publishedResourceVersion,
    };
  },

  async updateAdminSystemConfig(request) {
    const currentResVer = mockState.systemConfig.draftResourceVersion ?? mockState.systemConfig.publishedResourceVersion;
    mockState.systemConfig.draftConfig = { ...request._configuration };
    mockState.systemConfig.hasUnpublishedChanges = true;
    mockState.systemConfig.draftResourceVersion = currentResVer + 1;
  },

  async publishAdminSystemConfig(_auditReason) {
    if (mockState.systemConfig.draftConfig) {
      mockState.systemConfig.publishedConfig = { ...mockState.systemConfig.draftConfig };
      mockState.systemConfig.draftConfig = undefined;
    }
    const currentResVer = mockState.systemConfig.draftResourceVersion ?? mockState.systemConfig.publishedResourceVersion;
    mockState.systemConfig.hasUnpublishedChanges = false;
    mockState.systemConfig.version += 1;
    mockState.systemConfig.publishedResourceVersion = currentResVer + 1;
    mockState.systemConfig.draftResourceVersion = undefined;
    mockState.systemConfig.publishedAt = new Date();
  },

  /* 支付对账 */
  async runPaymentReconciliation(_staleBefore, maxOrders, _auditReason) {
    return {
      reconciliationId: 'rec_' + Date.now(),
      scannedCount: Math.min(maxOrders, 36),
      settledCount: Math.min(maxOrders, 34),
      recoveredCount: 2,
      conflictCount: 0,
      startedAt: new Date(now.getTime() - 5000),
      completedAt: new Date(),
    };
  },

  /* 邀请推广 */
  async getAdminReferralCampaigns(): Promise<ReferralCampaign[]> {
    return [...mockState.referralCampaigns];
  },

  async getAdminReferralCampaignVersions(campaignId: string): Promise<ReferralCampaignVersion[]> {
    return mockState.referralCampaignVersions.filter((v: ReferralCampaignVersion) => v.campaignId === campaignId);
  },

  async saveAdminReferralCampaign(
    request: ReferralCampaignWriteRequest,
    campaignId?: string,
    resourceVersion?: number
  ): Promise<ReferralCampaign> {
    if (campaignId) {
      const idx = mockState.referralCampaigns.findIndex((c) => c.campaignId === campaignId);
      if (idx === -1) {
        throw new Error('未找到要保存草稿的邀请活动');
      }
      const existing = mockState.referralCampaigns[idx];
      const nextVersion = existing.version + 1;
      const nextResourceVersion = (resourceVersion ?? existing.resourceVersion) + 1;
      const updatedCampaign: ReferralCampaign = {
        ...existing,
        campaignCode: request.campaignCode,
        displayName: request.displayName,
        description: request.description,
        region: request.region,
        salesChannels: request.salesChannels,
        bindingWindowHours: request.bindingWindowHours,
        maxQualifiedInvitesPerInviter: request.maxQualifiedInvitesPerInviter,
        rewardRules: request.rewardRules,
        antiAbusePolicy: request.antiAbusePolicy,
        status: ReferralCampaignStatus.Draft,
        version: nextVersion,
        resourceVersion: nextResourceVersion,
        updatedAt: new Date(),
      };
      mockState.referralCampaigns[idx] = updatedCampaign;

      mockState.referralCampaignVersions.unshift({
        campaignVersionId: `ver-${campaignId}-v${nextVersion}`,
        campaignId,
        version: nextVersion,
        campaignCode: request.campaignCode,
        displayName: request.displayName,
        description: request.description,
        region: request.region,
        salesChannels: Array.from(request.salesChannels),
        bindingWindowHours: request.bindingWindowHours,
        maxQualifiedInvitesPerInviter: request.maxQualifiedInvitesPerInviter,
        rewardRules: request.rewardRules,
        antiAbusePolicy: request.antiAbusePolicy,
        wasPublished: false,
        action: 'SAVE_DRAFT',
        createdByAdminId: 'admin_current',
        createdAt: new Date(),
      });
      return updatedCampaign;
    } else {
      const newId = `ref-camp-${Date.now().toString(36)}`;
      const newCampaign: ReferralCampaign = {
        campaignId: newId,
        version: 1,
        campaignCode: request.campaignCode,
        displayName: request.displayName,
        description: request.description,
        status: ReferralCampaignStatus.Draft,
        region: request.region,
        salesChannels: request.salesChannels,
        bindingWindowHours: request.bindingWindowHours,
        maxQualifiedInvitesPerInviter: request.maxQualifiedInvitesPerInviter,
        rewardRules: request.rewardRules,
        antiAbusePolicy: request.antiAbusePolicy,
        rolloutPercentage: 0,
        effectiveAt: new Date(),
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      mockState.referralCampaigns.unshift(newCampaign);

      mockState.referralCampaignVersions.unshift({
        campaignVersionId: `ver-${newId}-v1`,
        campaignId: newId,
        version: 1,
        campaignCode: request.campaignCode,
        displayName: request.displayName,
        description: request.description,
        region: request.region,
        salesChannels: Array.from(request.salesChannels),
        bindingWindowHours: request.bindingWindowHours,
        maxQualifiedInvitesPerInviter: request.maxQualifiedInvitesPerInviter,
        rewardRules: request.rewardRules,
        antiAbusePolicy: request.antiAbusePolicy,
        wasPublished: false,
        action: 'CREATE_DRAFT',
        createdByAdminId: 'admin_current',
        createdAt: new Date(),
      });
      return newCampaign;
    }
  },

  async publishAdminReferralCampaign(
    campaignId: string,
    resourceVersion: number,
    request: PublishReferralCampaignRequest
  ): Promise<ReferralCampaign> {
    const idx = mockState.referralCampaigns.findIndex((c) => c.campaignId === campaignId);
    if (idx === -1) {
      throw new Error('未找到要发布的邀请活动');
    }
    const existing = mockState.referralCampaigns[idx];
    const updatedCampaign: ReferralCampaign = {
      ...existing,
      status: ReferralCampaignStatus.Active,
      rolloutPercentage: request.rolloutPercentage,
      effectiveAt: new Date(request.effectiveAt),
      expiresAt: request.expiresAt ? new Date(request.expiresAt) : undefined,
      resourceVersion: resourceVersion + 1,
      updatedAt: new Date(),
    };
    mockState.referralCampaigns[idx] = updatedCampaign;

    const verIdx = mockState.referralCampaignVersions.findIndex(
      (v: ReferralCampaignVersion) => v.campaignId === campaignId && v.version === existing.version
    );
    if (verIdx !== -1) {
      mockState.referralCampaignVersions[verIdx].wasPublished = true;
      mockState.referralCampaignVersions[verIdx].action = 'PUBLISH';
    } else {
      mockState.referralCampaignVersions.unshift({
        campaignVersionId: `ver-${campaignId}-v${existing.version}`,
        campaignId,
        version: existing.version,
        campaignCode: existing.campaignCode,
        displayName: existing.displayName,
        description: existing.description,
        region: existing.region,
        salesChannels: Array.from(existing.salesChannels),
        bindingWindowHours: existing.bindingWindowHours,
        maxQualifiedInvitesPerInviter: existing.maxQualifiedInvitesPerInviter,
        rewardRules: existing.rewardRules,
        antiAbusePolicy: existing.antiAbusePolicy,
        wasPublished: true,
        action: 'PUBLISH',
        createdByAdminId: 'admin_current',
        createdAt: new Date(),
      });
    }
    return updatedCampaign;
  },

  async rollbackAdminReferralCampaign(
    campaignId: string,
    resourceVersion: number,
    request: RollbackReferralCampaignRequest
  ): Promise<ReferralCampaign> {
    const idx = mockState.referralCampaigns.findIndex((c) => c.campaignId === campaignId);
    if (idx === -1) {
      throw new Error('未找到要回退的邀请活动');
    }
    const existing = mockState.referralCampaigns[idx];

    const targetVersion = mockState.referralCampaignVersions.find(
      (v: ReferralCampaignVersion) => v.campaignId === campaignId && v.version === request.targetVersion
    );
    if (!targetVersion || !targetVersion.wasPublished || targetVersion.version >= existing.version) {
      throw new Error('非法回退目标版本：目标版本必须为已发布的历史版本');
    }

    const nextVersion = existing.version + 1;
    const updatedCampaign: ReferralCampaign = {
      ...existing,
      campaignCode: targetVersion.campaignCode,
      displayName: targetVersion.displayName,
      description: targetVersion.description,
      region: targetVersion.region,
      salesChannels: new Set(targetVersion.salesChannels),
      bindingWindowHours: targetVersion.bindingWindowHours,
      maxQualifiedInvitesPerInviter: targetVersion.maxQualifiedInvitesPerInviter,
      rewardRules: targetVersion.rewardRules,
      antiAbusePolicy: targetVersion.antiAbusePolicy,
      status: ReferralCampaignStatus.Active,
      rolloutPercentage: 100,
      effectiveAt: new Date(),
      expiresAt: undefined,
      version: nextVersion,
      resourceVersion: resourceVersion + 1,
      updatedAt: new Date(),
    };
    mockState.referralCampaigns[idx] = updatedCampaign;

    mockState.referralCampaignVersions.unshift({
      campaignVersionId: `ver-${campaignId}-v${nextVersion}`,
      campaignId,
      version: nextVersion,
      campaignCode: targetVersion.campaignCode,
      displayName: targetVersion.displayName,
      description: targetVersion.description,
      region: targetVersion.region,
      salesChannels: targetVersion.salesChannels,
      bindingWindowHours: targetVersion.bindingWindowHours,
      maxQualifiedInvitesPerInviter: targetVersion.maxQualifiedInvitesPerInviter,
      rewardRules: targetVersion.rewardRules,
      antiAbusePolicy: targetVersion.antiAbusePolicy,
      wasPublished: true,
      action: 'ROLLBACK',
      createdByAdminId: 'admin_current',
      createdAt: new Date(),
    });
    return updatedCampaign;
  },

  /* 客服工单 Mock */
  async getAdminSupportTickets(params) {
    let list = mockState.supportTickets;
    if (params?.status) {
      list = list.filter((t) => t.status === params.status);
    }
    if (params?.priority) {
      list = list.filter((t) => t.priority === params.priority);
    }
    if (params?.search) {
      const q = params.search.toLowerCase();
      list = list.filter(
        (t) =>
          t.ticketId.toLowerCase().includes(q) ||
          t.subject.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q),
      );
    }
    return { tickets: list, totalCount: list.length };
  },

  async getAdminSupportTicketDetail(ticketId) {
    const ticket = mockState.supportTickets.find((t) => t.ticketId === ticketId);
    if (!ticket) {
      throw new Error('工单不存在');
    }
    const msgs = mockState.supportMessages[ticketId] || [
      {
        messageId: 'msg_default',
        ticketId,
        senderType: SupportMessageSenderTypeEnum.User,
        senderId: ticket.userId,
        body: ticket.subject,
        internal: false,
        createdAt: ticket.createdAt,
      },
    ];
    return { ticket, messages: msgs };
  },

  async updateAdminSupportTicket(ticketId, update) {
    const ticket = mockState.supportTickets.find((t) => t.ticketId === ticketId);
    if (!ticket) {
      throw new Error('工单不存在');
    }
    if (update.status) ticket.status = update.status as SupportTicketStatusEnum;
    if (update.priority) ticket.priority = update.priority as SupportTicketPriorityEnum;
    if (update.assigneeId !== undefined) ticket.assignedAdminId = update.assigneeId;

    if (update.replyContent) {
      if (!mockState.supportMessages[ticketId]) {
        mockState.supportMessages[ticketId] = [];
      }
      mockState.supportMessages[ticketId].push({
        messageId: 'msg_' + Date.now(),
        ticketId,
        senderType: SupportMessageSenderTypeEnum.Admin,
        senderId: 'admin_master',
        body: update.replyContent,
        internal: !!update.isInternalNote,
        createdAt: new Date(),
      });
      ticket.lastMessageAt = new Date();
    }
    ticket.updatedAt = new Date();
    return ticket;
  },
};

/* ── HTTP 仓库 ── */

const commonHeaders = {
  xClientVersion: '1.0.0',
  xPlatform: 'ADMIN_WEB',
  acceptLanguage: 'zh-CN',
} as const;

const httpRepository: Repository = {
  async getSystemHealth() {
    const api = new ADMINPROVIDERApi(getConfiguration());
    try {
      const res = await api.listAdminProviders({ ...commonHeaders });
      const items = res.data?.items ?? [];
      const issues = items
        .filter((p: Provider) => p.status !== ProviderStatus.Active)
        .map((p: Provider) => `${p.providerName} 状态异常: ${p.status}`);
      return { status: issues.length === 0 ? 'healthy' : 'warning', issues };
    } catch (err: unknown) {
      return { status: 'error', issues: [String(err)] };
    }
  },

  async getPendingOrdersCount() {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    const res = await api.listAdminOrders({ ...commonHeaders, limit: 100 });
    return (res.data?.items ?? []).filter((o: AdminOrder) => o.order.status === OrderStatus.Created).length;
  },

  async getPendingRefundsCount() {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    const res = await api.listAdminRefunds({ ...commonHeaders, limit: 100 });
    return (res.data?.items ?? []).filter((r: AdminRefund) => r.status === RefundStatus.Requested).length;
  },

  async getProviders() {
    const api = new ADMINPROVIDERApi(getConfiguration());
    const res = await api.listAdminProviders({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async saveProviderDraft(req, id, resourceVersion) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    if (id && resourceVersion !== undefined) {
      await api.updateAdminProvider({
        providerId: id,
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        ifMatch: String(resourceVersion),
        providerWriteRequest: req,
      });
    } else {
      await api.createAdminProvider({
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        providerWriteRequest: req,
      });
    }
  },

  async publishProvider(id, resourceVersion, rolloutPercentage, effectiveAt, auditReason) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.publishAdminProvider({
      providerId: id,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: String(resourceVersion),
      publishProviderRequest: { rolloutPercentage, effectiveAt, auditReason },
    });
  },

  async rollbackProvider(id, resourceVersion, targetVersion, auditReason) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.rollbackAdminProvider({
      providerId: id,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: String(resourceVersion),
      rollbackProviderRequest: { targetResourceVersion: targetVersion, auditReason },
    });
  },

  async disableProvider(providerId, resourceVersion, auditReason) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.disableAdminProvider({
      providerId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: String(resourceVersion),
      disableProviderRequest: { auditReason },
    });
  },

  async rotateProviderCredentials(providerId, resourceVersion, secrets, auditReason) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.rotateAdminProviderCredentials({
      providerId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: String(resourceVersion),
      rotateCredentialsRequest: { secrets, auditReason },
    });
  },

  async checkProviderHealth(id, administratorTestDestination, auditReason) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.checkAdminProviderHealth({
      providerId: id,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      healthCheckRequest: {
        administratorTestDestination: administratorTestDestination ?? null,
        auditReason: auditReason || '管理员健康检查',
      },
    });
  },

  async getProducts() {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    const res = await api.listAdminProducts({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async saveProductDraft(req, id, resourceVersion) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    if (id && resourceVersion !== undefined) {
      await api.updateAdminProduct({
        productVersionId: id,
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        ifMatch: `W/"${resourceVersion}"`,
        adminProductWriteRequest: req,
      });
    } else {
      await api.createAdminProduct({
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        adminProductWriteRequest: req,
      });
    }
  },

  async publishProduct(pvId, resourceVersion) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    await api.publishAdminProduct({
      productVersionId: pvId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      adminProductPublishRequest: {
        effectiveAt: new Date(),
        auditReason: '管理后台发布',
      },
    });
  },

  async rollbackProduct(productCode, _resourceVersion, targetProductVersionId) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    await api.rollbackAdminProduct({
      productCode,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      adminProductRollbackRequest: {
        targetProductVersionId,
        effectiveAt: new Date(),
        auditReason: '管理后台回滚',
      },
    });
  },

  async getOrders(cursor) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    const res = await api.listAdminOrders({ ...commonHeaders, cursor });
    return res.data?.items ?? [];
  },

  async getRefunds() {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    const res = await api.listAdminRefunds({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async auditRefund(refundId, req, resourceVersion) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    await api.decideAdminRefund({
      refundId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      adminRefundDecisionRequest: req,
    });
  },

  async executeRefund(refundId, req, resourceVersion) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    await api.executeAdminRefund({
      refundId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      adminRefundExecuteRequest: req,
    });
  },

  /* ── AI 运行配置 HTTP 实现 ── */
  async getAiModelMappings() {
    const api = new ADMINAIApi(getConfiguration());
    const res = await api.listAdminAiModelMappings({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async saveAiModelMapping(request, modelMappingId, resourceVersion) {
    const api = new ADMINAIApi(getConfiguration());
    if (modelMappingId && resourceVersion !== undefined) {
      await api.updateAdminAiModelMapping({
        modelMappingId,
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        ifMatch: `W/"${resourceVersion}"`,
        aiModelMappingWriteRequest: request,
      });
    } else {
      await api.createAdminAiModelMapping({
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        aiModelMappingWriteRequest: request,
      });
    }
  },

  async getAiRoutes() {
    const api = new ADMINAIApi(getConfiguration());
    const res = await api.listAdminAiRoutes({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async saveAiRoute(request, routeId, resourceVersion) {
    const api = new ADMINAIApi(getConfiguration());
    if (routeId && resourceVersion !== undefined) {
      await api.updateAdminAiRoute({
        routeId,
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        ifMatch: `W/"${resourceVersion}"`,
        aiRouteWriteRequest: request,
      });
    } else {
      await api.createAdminAiRoute({
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        aiRouteWriteRequest: request,
      });
    }
  },

  async publishAiRoute(routeId, resourceVersion, request) {
    const api = new ADMINAIApi(getConfiguration());
    await api.publishAdminAiRoute({
      routeId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      aiPublishRequest: request,
    });
  },

  async rollbackAiRoute(routeId, resourceVersion, request) {
    const api = new ADMINAIApi(getConfiguration());
    await api.rollbackAdminAiRoute({
      routeId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      aiRollbackRequest: request,
    });
  },

  async getAiPrompts() {
    const api = new ADMINAIApi(getConfiguration());
    const res = await api.listAdminAiPrompts({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async saveAiPrompt(request, promptId, resourceVersion) {
    const api = new ADMINAIApi(getConfiguration());
    if (promptId && resourceVersion !== undefined) {
      await api.updateAdminAiPrompt({
        promptId,
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        ifMatch: `W/"${resourceVersion}"`,
        aiPromptWriteRequest: request,
      });
    } else {
      await api.createAdminAiPrompt({
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        aiPromptWriteRequest: request,
      });
    }
  },

  async publishAiPrompt(promptId, resourceVersion, request) {
    const api = new ADMINAIApi(getConfiguration());
    await api.publishAdminAiPrompt({
      promptId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      aiPublishRequest: request,
    });
  },

  async rollbackAiPrompt(promptId, resourceVersion, request) {
    const api = new ADMINAIApi(getConfiguration());
    await api.rollbackAdminAiPrompt({
      promptId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      aiRollbackRequest: request,
    });
  },

  async getAiRiskPolicies() {
    const api = new ADMINAIApi(getConfiguration());
    const res = await api.listAdminAiRiskPolicies({ ...commonHeaders });
    return res.data?.items ?? [];
  },

  async saveAiRiskPolicy(request, riskPolicyId, resourceVersion) {
    const api = new ADMINAIApi(getConfiguration());
    if (riskPolicyId && resourceVersion !== undefined) {
      await api.updateAdminAiRiskPolicy({
        riskPolicyId,
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        ifMatch: `W/"${resourceVersion}"`,
        aiRiskPolicyWriteRequest: request,
      });
    } else {
      await api.createAdminAiRiskPolicy({
        ...commonHeaders,
        idempotencyKey: Date.now().toString(),
        aiRiskPolicyWriteRequest: request,
      });
    }
  },

  async publishAiRiskPolicy(riskPolicyId, resourceVersion, request) {
    const api = new ADMINAIApi(getConfiguration());
    await api.publishAdminAiRiskPolicy({
      riskPolicyId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      aiPublishRequest: request,
    });
  },

  async rollbackAiRiskPolicy(riskPolicyId, resourceVersion, request) {
    const api = new ADMINAIApi(getConfiguration());
    await api.rollbackAdminAiRiskPolicy({
      riskPolicyId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      aiRollbackRequest: request,
    });
  },

  async runAiEvaluation(request) {
    const api = new ADMINAIApi(getConfiguration());
    const res = await api.createAdminAiEvaluationRun({
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      aiEvaluationRunRequest: request,
    });
    return res.data;
  },

  async getAiEvaluationRun(evaluationRunId) {
    const api = new ADMINAIApi(getConfiguration());
    const res = await api.getAdminAiEvaluationRun({
      evaluationRunId,
      ...commonHeaders,
    });
    return res.data ?? null;
  },

  async getAiEditorDefaults(): Promise<AiEditorDefaults> {
    // 从真实 HTTP 接口中并行拉取已有资源数据
    const [providers, mappings, routes, prompts, policies] = await Promise.all([
      this.getProviders(),
      this.getAiModelMappings(),
      this.getAiRoutes(),
      this.getAiPrompts(),
      this.getAiRiskPolicies(),
    ]);

    // 获取服务器已有的参考项（若无资源则设为 undefined，后续使用安全中性边界值）
    const refProvider = providers[0];
    const refMapping = mappings[0];
    const refRoute = routes[0];
    const refPrompt = prompts[0];
    const refPolicy = policies[0];

    // 模型映射编辑默认模板：新 ID / 模型名为空字符串，数值复制自服务器已有资源或使用中性 0 值
    const modelMapping: AiModelMappingWriteRequest = {
      logicalModelId: '',
      providerId: refProvider?.providerId ?? '',
      providerModelName: '',
      inputModalities: refMapping ? new Set(refMapping.inputModalities) : new Set<AiModality>([AiModality.Text]),
      outputModalities: refMapping ? new Set(refMapping.outputModalities) : new Set<AiModality>([AiModality.Text]),
      contextWindowTokens: refMapping?.contextWindowTokens ?? 0,
      maxOutputTokens: refMapping?.maxOutputTokens ?? 0,
      inputCostMicrounitsPerMillionTokens: refMapping?.inputCostMicrounitsPerMillionTokens ?? 0,
      outputCostMicrounitsPerMillionTokens: refMapping?.outputCostMicrounitsPerMillionTokens ?? 0,
      currency: refMapping?.currency ?? 'CNY',
      qualityTier: refMapping?.qualityTier ?? undefined,
      dataRegion: refMapping?.dataRegion ?? undefined,
      retentionPolicy: refMapping?.retentionPolicy ?? undefined,
      enabled: true,
    };

    // 场景路由编辑默认模板：数值与 Target 尽量派生自服务器已有路由
    const route: AiRouteWriteRequest = {
      scenario: refRoute?.scenario ?? AiScenario.ReplyGeneration,
      logicalModelId: refRoute?.logicalModelId ?? (refMapping?.logicalModelId ?? ''),
      targets: refRoute && refRoute.targets.length > 0
        ? refRoute.targets.map((t: AiRouteTarget) => ({ ...t }))
        : [
            {
              modelMappingId: refMapping?.modelMappingId ?? '',
              priority: 1,
              timeoutMs: 0,
              retryLimit: 0,
            },
          ],
      maxInputTokens: refRoute?.maxInputTokens ?? 0,
      maxOutputTokens: refRoute?.maxOutputTokens ?? 0,
      budgetCeilingMicrounits: refRoute?.budgetCeilingMicrounits ?? 0,
      totalAttemptLimit: refRoute?.totalAttemptLimit ?? 1,
      safetyPolicyId: refRoute?.safetyPolicyId ?? (refPolicy?.riskPolicyId ?? ''),
    };

    // 提示词编辑默认模板
    const prompt: AiPromptWriteRequest = {
      promptCode: '',
      scenario: refPrompt?.scenario ?? AiScenario.ReplyGeneration,
      systemTemplate: '',
      userTemplate: '',
      allowedInputFields: refPrompt ? new Set(refPrompt.allowedInputFields) : new Set<string>(),
      outputSchema: refPrompt?.outputSchema ?? { type: 'object', properties: {} },
      safetyPolicyId: refPrompt?.safetyPolicyId ?? (refPolicy?.riskPolicyId ?? ''),
    };

    // 风控策略编辑默认模板
    const riskPolicy: AiRiskPolicyWriteRequest = {
      policyCode: '',
      blockedCategories: refPolicy ? new Set(refPolicy.blockedCategories) : new Set<string>(),
      reviewCategories: refPolicy ? new Set(refPolicy.reviewCategories) : new Set<string>(),
      inputModerationEnabled: refPolicy?.inputModerationEnabled ?? true,
      outputModerationEnabled: refPolicy?.outputModerationEnabled ?? true,
      promptInjectionAction: refPolicy?.promptInjectionAction ?? AiRiskPolicyWriteRequestPromptInjectionActionEnum.Block,
      minimumSafetyScore: refPolicy?.minimumSafetyScore ?? 0,
      allowAppeals: refPolicy?.allowAppeals ?? true,
    };

    // 评测运行默认模板：maxCost 从服务器路由的预算上限派生
    const evaluationRun: AiEvaluationRunRequest = {
      promptId: refPrompt?.promptId ?? '',
      routeId: refRoute?.routeId ?? '',
      suiteIds: new Set<string>(),
      evaluatorLogicalModelId: refRoute?.logicalModelId ?? (refMapping?.logicalModelId ?? ''),
      maxCostMicrounits: refRoute?.budgetCeilingMicrounits ?? 0,
    };

    // 发布默认模板：evaluationRunId 默认为空，发布前必须由真实评测校验；rollout 从已有路由派生或使用 0
    const publish: AiPublishRequest = {
      rolloutPercentage: refRoute?.rolloutPercentage ?? 0,
      effectiveAt: new Date(),
      evaluationRunId: '',
      auditReason: '',
    };

    // 回滚默认模板
    const rollback: AiRollbackRequest = {
      targetVersion: 0,
      auditReason: '',
    };

    return {
      modelMapping,
      route,
      prompt,
      riskPolicy,
      evaluationRun,
      publish,
      rollback,
    };
  },

  /* ── 合规审计 HTTP 实现 ── */
  async getAuditEvents(filter) {
    const api = new ADMINRBACApi(getConfiguration());
    const res = await api.listAdminAuditEvents({
      ...commonHeaders,
      cursor: filter?.cursor,
      limit: filter?.limit,
      category: filter?.category as AuditEventCategoryEnum | undefined,
      eventType: filter?.eventType,
      outcome: filter?.outcome as AuditEventOutcomeEnum | undefined,
      userId: filter?.userId,
      adminId: filter?.adminId,
      requestId: filter?.requestId,
      orderId: filter?.orderId,
      generationId: filter?.generationId,
      from: filter?.from,
      to: filter?.to,
    });
    return {
      events: res.data?.items ?? [],
      nextCursor: res.data?.nextCursor ?? undefined,
    };
  },

  async verifyAuditIntegrity() {
    const api = new ADMINRBACApi(getConfiguration());
    const res = await api.verifyAdminAuditIntegrity({
      ...commonHeaders,
    });
    return res.data;
  },

  async readAuditSensitiveContent(eventId, reason) {
    const api = new ADMINRBACApi(getConfiguration());
    const res = await api.readAdminAuditSensitiveContent({
      eventId,
      ...commonHeaders,
      sensitiveContentReadRequest: { auditReason: reason },
    });
    return res.data;
  },

  async changeAuditLegalHold(eventId, enabled, reason) {
    const api = new ADMINRBACApi(getConfiguration());
    const res = await api.changeAdminAuditLegalHold({
      eventId,
      ...commonHeaders,
      legalHoldRequest: { enabled, auditReason: reason },
    });
    return res.data;
  },

  async createAuditExport(request) {
    const api = new ADMINRBACApi(getConfiguration());
    const res = await api.createAdminAuditExport({
      ...commonHeaders,
      auditExportRequest: request,
    });
    return res.data;
  },

  async readAuditExport(exportId, reason) {
    const api = new ADMINRBACApi(getConfiguration());
    const res = await api.readAdminAuditExport({
      exportId,
      ...commonHeaders,
      auditExportReadRequest: { auditReason: reason },
    });
    return res.data;
  },

  /* 用户管理 HTTP 实现 */
  async getAdminUsers(params) {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const res = await api.listAdminUsers({
      ...commonHeaders,
      search: params?.search,
      status: params?.status as AccountStatus | undefined,
      cursor: params?.cursor,
      limit: params?.limit,
    });
    return {
      users: res.data?.items ?? [],
      nextCursor: undefined,
      totalCount: res.data?.items?.length,
    };
  },

  async getAdminUserDetail(userId) {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const userRes = await api.getAdminUser({ ...commonHeaders, userId });
    const entRes = await api.getAdminUserEntitlements({ ...commonHeaders, userId });
    const ledgerRes = await api.listAdminUserLedger({ ...commonHeaders, userId, limit: 50 });
    if (!userRes.data) {
      throw new Error('未找到指定用户详情');
    }
    return {
      detail: userRes.data,
      devices: (userRes.data.devices as unknown as Device[]) ?? [],
      entitlements: entRes.data ? [entRes.data as unknown as Entitlement] : [],
      walletEntries: (ledgerRes.data?.items as unknown as WalletLedgerEntry[]) ?? [],
    };
  },

  async changeAdminUserStatus(userId, status, auditReason, ifMatch) {
    if (!ifMatch) {
      throw new Error('修改用户状态必须传入 If-Match (resourceVersion)');
    }
    const api = new ADMINPLATFORMApi(getConfiguration());
    await api.changeAdminUserStatus({
      ...commonHeaders,
      userId,
      ifMatch,
      adminUserStatusRequest: {
        status: status as unknown as AdminUserStatusRequestStatusEnum,
        auditReason,
        confirmationUserId: userId,
      },
    });
  },

  /* 公告运营 HTTP 实现 */
  async getAdminNotices(params) {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const res = await api.listAdminNotices({
      ...commonHeaders,
    });
    let items = res.data?.items ?? [];
    if (params?.type) {
      items = items.filter((n: NoticeVersion) => n.noticeType === params.type);
    }
    if (params?.status) {
      items = items.filter((n: NoticeVersion) => n.status === params.status);
    }
    return {
      notices: items,
      nextCursor: undefined,
    };
  },

  async createAdminNotice(request) {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const res = await api.createAdminNotice({
      ...commonHeaders,
      noticeWriteRequest: request,
    });
    return res.data;
  },

  async updateAdminNotice(noticeId, request, ifMatch = '*') {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const res = await api.updateAdminNotice({
      ...commonHeaders,
      noticeId,
      ifMatch,
      noticeWriteRequest: request,
    });
    return res.data;
  },

  async publishAdminNotice(noticeId, auditReason, ifMatch = '*') {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const res = await api.publishAdminNotice({
      ...commonHeaders,
      noticeId,
      ifMatch,
      auditReasonRequest: { auditReason },
    });
    return res.data;
  },

  async revokeAdminNotice(noticeId, auditReason, ifMatch = '*') {
    const api = new ADMINPLATFORMApi(getConfiguration());
    const res = await api.revokeAdminNotice({
      ...commonHeaders,
      noticeId,
      ifMatch,
      auditReasonRequest: { auditReason },
    });
    return res.data;
  },

  /* 网站设置 HTTP 真实语义实现 */
  async getAdminSystemConfig(): Promise<SystemConfigResult> {
    const api = new ADMINPLATFORMApi(getConfiguration());

    // 1. 分别请求 publishedOnly=true 获得线上发布版本
    let publishedVersionObj: SystemConfigVersion | null = null;
    try {
      const publishedRes = await api.getAdminSystemConfig({ ...commonHeaders, publishedOnly: true });
      publishedVersionObj = publishedRes.data ?? null;
    } catch {
      // 线上尚无发布版本或报错时容错处理
      publishedVersionObj = null;
    }

    // 2. 请求 publishedOnly=false 获得最新版本
    const latestRes = await api.getAdminSystemConfig({ ...commonHeaders, publishedOnly: false });
    const latestVersionObj = latestRes.data;

    // 3. 仅当最新版本 status 为 DRAFT 时作为 draftConfig 和 hasUnpublishedChanges=true；否则 draftConfig 可为空、hasUnpublishedChanges=false。
    const isDraft = (latestVersionObj?.status as unknown) === SystemConfigVersionStatusEnum.Draft || (latestVersionObj?.status as string) === 'DRAFT';
    const draftConfig = isDraft ? latestVersionObj?._configuration : undefined;
    const hasUnpublishedChanges = isDraft;
    const draftResourceVersion = isDraft ? latestVersionObj?.resourceVersion : undefined;
    const publishedResourceVersion = publishedVersionObj?.resourceVersion;

    const publishedConfig = publishedVersionObj?._configuration;
    const publishedAt = publishedVersionObj?.publishedAt ?? undefined;
    const version = latestVersionObj?.version ?? publishedVersionObj?.version ?? 1;

    return {
      publishedConfig,
      draftConfig,
      hasUnpublishedChanges,
      publishedAt,
      version,
      publishedResourceVersion,
      draftResourceVersion,
      resourceVersion: isDraft ? draftResourceVersion : (publishedResourceVersion ?? latestVersionObj?.resourceVersion),
    };
  },

  async updateAdminSystemConfig(request, ifMatch) {
    if (!ifMatch) {
      throw new Error('保存配置草稿必须传入 If-Match (resourceVersion) 请求头');
    }
    const api = new ADMINPLATFORMApi(getConfiguration());
    await api.updateAdminSystemConfig({
      ...commonHeaders,
      ifMatch,
      systemConfigWriteRequest: request,
    });
  },

  async publishAdminSystemConfig(auditReason, ifMatch) {
    if (!ifMatch) {
      throw new Error('发布线上配置必须传入 If-Match (resourceVersion) 请求头');
    }
    const api = new ADMINPLATFORMApi(getConfiguration());
    await api.publishAdminSystemConfig({
      ...commonHeaders,
      ifMatch,
      auditReasonRequest: { auditReason },
    });
  },

  /* 支付对账 HTTP 实现 */
  async runPaymentReconciliation(staleBefore, maxOrders, auditReason) {
    const api = new ADMINCOMMERCEApi(getConfiguration());
    const res = await api.runAdminPaymentReconciliation({
      ...commonHeaders,
      idempotencyKey: 'rec_' + Date.now(),
      paymentReconciliationRequest: {
        staleBefore: typeof staleBefore === 'string' ? new Date(staleBefore) : staleBefore,
        maxOrders,
        auditReason,
      },
    });
    return res.data;
  },

  /* 客服工单 HTTP 实现 */
  async getAdminSupportTickets(params) {
    const api = new ADMINSUPPORTApi(getConfiguration());
    const res = await api.listAdminSupportTickets({
      ...commonHeaders,
      status: params?.status,
    });
    let tickets = res.data?.items ?? [];
    if (params?.search) {
      const q = params.search.toLowerCase();
      tickets = tickets.filter(
        (t: SupportTicket) =>
          t.ticketId.toLowerCase().includes(q) ||
          t.subject.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q),
      );
    }
    return {
      tickets,
      nextCursor: undefined,
      totalCount: tickets.length,
    };
  },

  async getAdminSupportTicketDetail(ticketId) {
    const api = new ADMINSUPPORTApi(getConfiguration());
    const res = await api.getAdminSupportTicket({ ...commonHeaders, ticketId });
    if (!res.data) {
      throw new Error('未找到指定工单详情');
    }
    return {
      ticket: res.data.ticket,
      messages: res.data.messages ?? [],
    };
  },

  async updateAdminSupportTicket(ticketId, update, ifMatch = '*') {
    const api = new ADMINSUPPORTApi(getConfiguration());
    const reqStatus = (update.status ?? SupportTicketStatusEnum.Open) as unknown as AdminUpdateSupportTicketRequestStatusEnum;
    const reqPriority = (update.priority ?? SupportTicketPriorityEnum.Normal) as unknown as AdminUpdateSupportTicketRequestPriorityEnum;

    const res = await api.updateAdminSupportTicket({
      ...commonHeaders,
      ticketId,
      ifMatch,
      adminUpdateSupportTicketRequest: {
        status: reqStatus,
        priority: reqPriority,
        assignedAdminId: update.assigneeId ?? undefined,
        body: update.replyContent,
        internal: !!update.isInternalNote,
        auditReason: update.auditReason || '客服管理工单处理',
      },
    });
    if (!res.data) {
      throw new Error('更新客服工单失败，服务器响应无有效工单数据');
    }
    return res.data;
  },

  /* 邀请推广 HTTP 实现 */
  async getAdminReferralCampaigns(): Promise<ReferralCampaign[]> {
    const api = new ADMINREFERRALApi(getConfiguration());
    const res = await api.listAdminReferralCampaigns({
      ...commonHeaders,
    });
    return res.data?.items || [];
  },

  async getAdminReferralCampaignVersions(campaignId: string): Promise<ReferralCampaignVersion[]> {
    const api = new ADMINREFERRALApi(getConfiguration());
    const res = await api.listAdminReferralCampaignVersions({
      ...commonHeaders,
      campaignId,
    });
    return res.data?.items || [];
  },

  async saveAdminReferralCampaign(
    request: ReferralCampaignWriteRequest,
    campaignId?: string,
    resourceVersion?: number
  ): Promise<ReferralCampaign> {
    const api = new ADMINREFERRALApi(getConfiguration());
    const idempotencyKey = `ref_save_${Date.now()}`;
    if (campaignId && resourceVersion !== undefined) {
      const res = await api.updateAdminReferralCampaign({
        ...commonHeaders,
        campaignId,
        ifMatch: String(resourceVersion),
        idempotencyKey,
        referralCampaignWriteRequest: request,
      });
      return res.data;
    } else {
      const res = await api.createAdminReferralCampaign({
        ...commonHeaders,
        idempotencyKey,
        referralCampaignWriteRequest: request,
      });
      return res.data;
    }
  },

  async publishAdminReferralCampaign(
    campaignId: string,
    resourceVersion: number,
    request: PublishReferralCampaignRequest
  ): Promise<ReferralCampaign> {
    const api = new ADMINREFERRALApi(getConfiguration());
    const idempotencyKey = `ref_pub_${Date.now()}`;
    const res = await api.publishAdminReferralCampaign({
      ...commonHeaders,
      campaignId,
      ifMatch: String(resourceVersion),
      idempotencyKey,
      publishReferralCampaignRequest: request,
    });
    return res.data;
  },

  async rollbackAdminReferralCampaign(
    campaignId: string,
    resourceVersion: number,
    request: RollbackReferralCampaignRequest
  ): Promise<ReferralCampaign> {
    const api = new ADMINREFERRALApi(getConfiguration());
    const idempotencyKey = `ref_rb_${Date.now()}`;
    const res = await api.rollbackAdminReferralCampaign({
      ...commonHeaders,
      campaignId,
      ifMatch: String(resourceVersion),
      idempotencyKey,
      rollbackReferralCampaignRequest: request,
    });
    return res.data;
  },
};

/** 根据环境变量决定使用 HTTP 还是 Mock 仓库 */
export const repository: Repository = import.meta.env.VITE_API_BASE_URL ? httpRepository : mockRepository;
