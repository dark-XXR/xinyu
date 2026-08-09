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
} from './models';
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
} from './models';

/* ── 仓库接口 ── */

export interface Repository {
  getSystemHealth(): Promise<{ status: string; issues: string[] }>;
  getPendingOrdersCount(): Promise<number>;
  getPendingRefundsCount(): Promise<number>;

  getProviders(): Promise<Provider[]>;
  saveProviderDraft(provider: ProviderWriteRequest, id?: string, resourceVersion?: number): Promise<void>;
  publishProvider(id: string, resourceVersion: number): Promise<void>;
  rotateProviderCredentials(providerId: string, resourceVersion: number, secrets: CredentialSecretInput[], auditReason: string): Promise<void>;
  rollbackProvider(id: string, resourceVersion: number, targetVersion: number): Promise<void>;
  checkProviderHealth(id: string): Promise<void>;

  getProducts(): Promise<AdminProductVersion[]>;
  saveProductDraft(product: AdminProductWriteRequest, id?: string, resourceVersion?: number): Promise<void>;
  publishProduct(productVersionId: string, resourceVersion: number): Promise<void>;
  rollbackProduct(productCode: string, _resourceVersion: number, targetProductVersionId: string): Promise<void>;

  getOrders(cursor?: string): Promise<AdminOrder[]>;
  getRefunds(): Promise<AdminRefund[]>;
  auditRefund(refundId: string, request: AdminRefundDecisionRequest, resourceVersion: number): Promise<void>;
  executeRefund(refundId: string, request: AdminRefundExecuteRequest, resourceVersion: number): Promise<void>;
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
} = {
  providers: [
    {
      providerId: 'prov-ai-001',
      providerName: 'OpenAI 官方',
      kind: ProviderKind.Ai,
      status: ProviderStatus.Active,
      _configuration: aiConfig,
      retryLimit: 3,
      priority: 1,
      rolloutPercentage: 100,
      credentialConfigured: true,
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
      retryLimit: 2,
      priority: 1,
      rolloutPercentage: 0,
      credentialConfigured: false,
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
      retryLimit: 3,
      priority: 1,
      rolloutPercentage: 100,
      credentialConfigured: true,
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
      retryLimit: 2,
      priority: 1,
      rolloutPercentage: 100,
      credentialConfigured: true,
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
          retryLimit: req.retryLimit,
          priority: req.priority,
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
        retryLimit: req.retryLimit,
        priority: req.priority,
        rolloutPercentage: 0,
        credentialConfigured: false,
        resourceVersion: 1,
        createdAt: new Date(),
        updatedAt: new Date(),
      });
    }
  },

  async publishProvider(id) {
    const p = mockState.providers.find((item) => item.providerId === id);
    if (p) {
      p.status = ProviderStatus.Active;
      p.rolloutPercentage = 100;
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async rollbackProvider(id, _rv, _tv) {
    const p = mockState.providers.find((item) => item.providerId === id);
    if (p) {
      p.status = ProviderStatus.Draft;
      p.rolloutPercentage = 0;
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async rotateProviderCredentials(providerId, _resourceVersion, _secrets, _auditReason) {
    const p = mockState.providers.find((item) => item.providerId === providerId);
    if (p) {
      p.credentialConfigured = true;
      Object.assign(p, {
        credentialFingerprint: 'mock-fingerprint-' + Date.now(),
        credentialRotatedAt: new Date(),
      });
      p.resourceVersion += 1;
      p.updatedAt = new Date();
    }
  },

  async checkProviderHealth() {
    /* mock 健康检查 - 无副作用 */
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
        ifMatch: `W/"${resourceVersion}"`,
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

  async publishProvider(id, resourceVersion) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.publishAdminProvider({
      providerId: id,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      publishProviderRequest: { rolloutPercentage: 100, effectiveAt: new Date(), auditReason: '管理后台发布' },
    });
  },

  async rollbackProvider(id, resourceVersion, targetVersion) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.rollbackAdminProvider({
      providerId: id,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      rollbackProviderRequest: { targetResourceVersion: targetVersion, auditReason: '管理后台回滚' },
    });
  },

  async rotateProviderCredentials(providerId, resourceVersion, secrets, auditReason) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.rotateAdminProviderCredentials({
      providerId,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      ifMatch: `W/"${resourceVersion}"`,
      rotateCredentialsRequest: { secrets, auditReason },
    });
  },

  async checkProviderHealth(id) {
    const api = new ADMINPROVIDERApi(getConfiguration());
    await api.checkAdminProviderHealth({
      providerId: id,
      ...commonHeaders,
      idempotencyKey: Date.now().toString(),
      healthCheckRequest: { auditReason: '管理后台检查' },
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
};

/** 根据环境变量决定使用 HTTP 还是 Mock 仓库 */
export const repository: Repository = import.meta.env.VITE_API_BASE_URL ? httpRepository : mockRepository;
