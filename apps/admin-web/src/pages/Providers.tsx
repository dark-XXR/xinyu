/**
 * 供应商管理页面。
 *
 * 【完整生命周期与线上运行状态说明】
 * - 供应商状态生命周期：
 *   - DRAFT（草稿）：刚创建或编辑后尚未发起的配置；若该供应商曾发布过上线（publishedRolloutPercentage > 0），
 *     则线上旧版本（publishedResourceVersion）仍然在运行分发流量，避免管理员因配置草稿而误判线上中断；
 *   - VALIDATING / READY：预上线准备与联调校验状态（必须先完成凭据轮换并通过探针健康检查才转为 READY）；
 *   - ACTIVE（在线）：已完成灰度发布并处于正常线上分发状态；
 *   - DISABLED（已停用）：已从邮件/短信/AI/支付运行时选择中移除（线上灰度已降为 0%），
 *     但保留其版本历史（publishedResourceVersion）供后续回滚或重新发布；
 *   - SUPERSEDED（已替换）：已被后续发布版本替代。
 *
 * 【危险停用与恢复机制】
 * - 停用触发条件：以 publishedResourceVersion != null 且 publishedRolloutPercentage > 0 为判定依据，不单凭 status == ACTIVE 判断；
 * - 停用校验门禁：要求二次输入供应商完整名称确认，并填写至少 8 个字符的审计理由；
 * - 恢复方式：已停用的供应商允许编辑、轮换凭据、健康检查和版本回滚；只有完成验证并重新发布或执行回滚后才能重新进入运行时。
 *
 * 【发布控制门禁】
 * - 发布按钮仅在 status === ProviderStatus.Ready 时显示。草稿 (DRAFT) 状态需先轮换凭据并通过探针健康检查方可发布，防止误踩 409 异常。
 * - canRollback 仅在 publishedResourceVersion != null 时显示，防止从未发布的草稿发起失败回滚。
 *
 * 【并发控制契约】
 * - 所有写操作（保存/发布/回滚/凭据轮换/停用）If-Match 标头必须传入纯十进制字符串 String(resourceVersion)，不得带 W/"..." 弱 ETag 前缀。
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { repository } from '../api/repository';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Drawer } from '../components/ui/Drawer';
import { Dialog } from '../components/ui/Dialog';
import { Input } from '../components/ui/Input';
import { Activity, KeyRound, Power, RotateCcw, Send, AlertCircle } from 'lucide-react';
import {
  ProviderKind,
  ProviderStatus,
  OpenAiCompatibleConfigurationAdapterTypeEnum,
  NativeAiConfigurationAdapterTypeEnum,
  SmtpConfigurationAdapterTypeEnum,
  EmailApiConfigurationAdapterTypeEnum,
  SmsConfigurationAdapterTypeEnum,
  EpayConfigurationAdapterTypeEnum,
  EpayConfigurationPaymentTypesEnum,
  EpayConfigurationSigningPresetEnum,
  TlsMode,
} from '../api/models';
import type {
  Provider,
  ProviderWriteRequest,
  ProviderConfiguration,
  OpenAiCompatibleConfiguration,
  NativeAiConfiguration,
  SmtpConfiguration,
  EmailApiConfiguration,
  SmsConfiguration,
  EpayConfiguration,
  CredentialName,
  CredentialSecretInput,
} from '../api/models';

/** 适配器类型中文说明 */
function adapterLabel(adapterType: string): string {
  switch (adapterType) {
    case OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat: return 'OpenAI 兼容协议';
    case NativeAiConfigurationAdapterTypeEnum.Openai: return 'OpenAI 原生 API';
    case NativeAiConfigurationAdapterTypeEnum.Anthropic: return 'Anthropic Claude 原生 API';
    case NativeAiConfigurationAdapterTypeEnum.Gemini: return 'Google Gemini 原生 API';
    case SmtpConfigurationAdapterTypeEnum.Smtp: return 'SMTP 邮件协议';
    case EmailApiConfigurationAdapterTypeEnum.SesApi: return 'AWS SES API 邮件';
    case EmailApiConfigurationAdapterTypeEnum.SendgridApi: return 'SendGrid API 邮件';
    case EmailApiConfigurationAdapterTypeEnum.ResendApi: return 'Resend API 邮件';
    case EmailApiConfigurationAdapterTypeEnum.MailgunApi: return 'Mailgun API 邮件';
    case SmsConfigurationAdapterTypeEnum.AliyunSms: return '阿里云短信 API';
    case SmsConfigurationAdapterTypeEnum.TencentSms: return '腾讯云短信 API';
    case EpayConfigurationAdapterTypeEnum.EpayCompat: return '易支付网关兼容协议';
    default: return adapterType;
  }
}

/* ── 表单 DTO 定义 ── */

interface ProviderFormDTO {
  providerName: string;
  kind: ProviderKind;
  dataRegion: string;
  retentionStatement: string;
  retryLimit: number;
  priority: number;

  /* 核心适配器类型 */
  adapterType: string;

  /* AI 配置字段 */
  ai_baseUrl: string;
  ai_organization: string;
  ai_project: string;
  ai_timeoutMs: number;

  /* Email 配置字段 */
  smtp_host: string;
  smtp_port: number;
  smtp_tlsMode: TlsMode;
  email_senderAddress: string;
  email_senderName: string;
  email_replyToAddress: string;
  email_region: string;
  email_baseUrl: string;
  email_timeoutMs: number;

  /* SMS 配置字段 */
  sms_region: string;
  sms_applicationId: string;
  sms_signatureId: string;
  sms_templateId: string;
  sms_timeoutMs: number;

  /* Epay 配置字段 */
  epay_gatewayBaseUrl: string;
  epay_submitPath: string;
  epay_queryPath: string;
  epay_refundPath: string;
  epay_merchantId: string;
  epay_applicationId: string;
  epay_paymentTypes: EpayConfigurationPaymentTypesEnum[];
  epay_notifyUrl: string;
  epay_returnUrl: string;
  epay_callbackAckText: string;
  epay_callbackTimeWindowSeconds: number;
  epay_checkoutTtlSeconds: number;
  epay_timeoutMs: number;
}

/** 返回空白表单 DTO */
function blankForm(): ProviderFormDTO {
  return {
    providerName: '',
    kind: ProviderKind.Ai,
    dataRegion: '',
    retentionStatement: '',
    retryLimit: 3,
    priority: 1,
    adapterType: OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat,

    ai_baseUrl: 'https://api.openai.com/v1',
    ai_organization: '',
    ai_project: '',
    ai_timeoutMs: 30000,

    smtp_host: '',
    smtp_port: 465,
    smtp_tlsMode: TlsMode.Implicit,
    email_senderAddress: '',
    email_senderName: '',
    email_replyToAddress: '',
    email_region: '',
    email_baseUrl: '',
    email_timeoutMs: 10000,

    sms_region: 'cn-hangzhou',
    sms_applicationId: '',
    sms_signatureId: '',
    sms_templateId: '',
    sms_timeoutMs: 5000,

    epay_gatewayBaseUrl: '',
    epay_submitPath: '/submit',
    epay_queryPath: '/query',
    epay_refundPath: '/refund',
    epay_merchantId: '',
    epay_applicationId: '',
    epay_paymentTypes: [
      EpayConfigurationPaymentTypesEnum.Alipay,
      EpayConfigurationPaymentTypesEnum.WechatPay,
    ],
    epay_notifyUrl: '',
    epay_returnUrl: '',
    epay_callbackAckText: 'success',
    epay_callbackTimeWindowSeconds: 300,
    epay_checkoutTtlSeconds: 900,
    epay_timeoutMs: 10000,
  };
}

/** 从 Provider 模型填充表单 DTO（编辑时使用，从实际 adapterType 回填） */
function providerToForm(p: Provider): ProviderFormDTO {
  const base = blankForm();
  base.providerName = p.providerName;
  base.kind = p.kind;
  base.dataRegion = p.dataRegion ?? '';
  base.retentionStatement = p.retentionStatement ?? '';
  base.retryLimit = p.retryLimit;
  base.priority = p.priority;

  const cfg = p._configuration as ProviderConfiguration | undefined;
  if (cfg) {
    base.adapterType = cfg.adapterType;
    if (cfg.adapterType === OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat) {
      const c = cfg as OpenAiCompatibleConfiguration;
      base.ai_baseUrl = c.baseUrl ?? '';
      base.ai_organization = c.organization ?? '';
      base.ai_project = c.project ?? '';
      base.ai_timeoutMs = c.timeoutMs ?? 30000;
    } else if (
      cfg.adapterType === NativeAiConfigurationAdapterTypeEnum.Openai ||
      cfg.adapterType === NativeAiConfigurationAdapterTypeEnum.Anthropic ||
      cfg.adapterType === NativeAiConfigurationAdapterTypeEnum.Gemini
    ) {
      const c = cfg as NativeAiConfiguration;
      base.ai_baseUrl = c.baseUrl ?? '';
      base.ai_timeoutMs = c.timeoutMs ?? 30000;
    } else if (cfg.adapterType === SmtpConfigurationAdapterTypeEnum.Smtp) {
      const c = cfg as SmtpConfiguration;
      base.smtp_host = c.host ?? '';
      base.smtp_port = c.port ?? 465;
      base.smtp_tlsMode = c.tlsMode ?? TlsMode.Implicit;
      base.email_senderAddress = c.senderAddress ?? '';
      base.email_senderName = c.senderName ?? '';
      base.email_replyToAddress = c.replyToAddress ?? '';
      base.email_timeoutMs = c.timeoutMs ?? 10000;
    } else if (
      cfg.adapterType === EmailApiConfigurationAdapterTypeEnum.SesApi ||
      cfg.adapterType === EmailApiConfigurationAdapterTypeEnum.SendgridApi ||
      cfg.adapterType === EmailApiConfigurationAdapterTypeEnum.ResendApi ||
      cfg.adapterType === EmailApiConfigurationAdapterTypeEnum.MailgunApi
    ) {
      const c = cfg as EmailApiConfiguration;
      base.email_region = c.region ?? '';
      base.email_baseUrl = c.baseUrl ?? '';
      base.email_senderAddress = c.senderAddress ?? '';
      base.email_senderName = c.senderName ?? '';
      base.email_replyToAddress = (c as any).replyToAddress ?? '';
      base.email_timeoutMs = c.timeoutMs ?? 10000;
    } else if (
      cfg.adapterType === SmsConfigurationAdapterTypeEnum.AliyunSms ||
      cfg.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms
    ) {
      const c = cfg as SmsConfiguration;
      base.sms_region = c.region ?? '';
      base.sms_applicationId = c.applicationId ?? '';
      base.sms_signatureId = c.signatureId ?? '';
      base.sms_templateId = c.templateId ?? '';
      base.sms_timeoutMs = c.timeoutMs ?? 5000;
    } else if (cfg.adapterType === EpayConfigurationAdapterTypeEnum.EpayCompat) {
      const c = cfg as EpayConfiguration;
      base.epay_gatewayBaseUrl = c.gatewayBaseUrl ?? '';
      base.epay_submitPath = c.submitPath ?? '';
      base.epay_queryPath = c.queryPath ?? '';
      base.epay_refundPath = c.refundPath ?? '';
      base.epay_merchantId = c.merchantId ?? '';
      base.epay_applicationId = c.applicationId ?? '';
      if (c.paymentTypes) {
        base.epay_paymentTypes = Array.from(c.paymentTypes);
      }
      base.epay_notifyUrl = c.notifyUrl ?? '';
      base.epay_returnUrl = c.returnUrl ?? '';
      base.epay_callbackAckText = c.callbackAckText ?? '';
      base.epay_callbackTimeWindowSeconds = c.callbackTimeWindowSeconds ?? 300;
      base.epay_checkoutTtlSeconds = c.checkoutTtlSeconds ?? 900;
      base.epay_timeoutMs = c.timeoutMs ?? 10000;
    }
  }
  return base;
}

/** 按 adapterType 构造正确生成类型 */
function buildConfiguration(form: ProviderFormDTO): ProviderConfiguration {
  switch (form.adapterType) {
    case OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat: {
      const cfg: OpenAiCompatibleConfiguration = {
        adapterType: OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat,
        baseUrl: form.ai_baseUrl.trim(),
        organization: form.ai_organization.trim() || null,
        project: form.ai_project.trim() || null,
        timeoutMs: form.ai_timeoutMs,
      };
      return cfg;
    }
    case NativeAiConfigurationAdapterTypeEnum.Openai:
    case NativeAiConfigurationAdapterTypeEnum.Anthropic:
    case NativeAiConfigurationAdapterTypeEnum.Gemini: {
      const cfg: NativeAiConfiguration = {
        adapterType: form.adapterType as NativeAiConfigurationAdapterTypeEnum,
        baseUrl: form.ai_baseUrl.trim() || null,
        timeoutMs: form.ai_timeoutMs,
      };
      return cfg;
    }
    case SmtpConfigurationAdapterTypeEnum.Smtp: {
      const cfg: SmtpConfiguration = {
        adapterType: SmtpConfigurationAdapterTypeEnum.Smtp,
        host: form.smtp_host.trim(),
        port: form.smtp_port,
        tlsMode: form.smtp_tlsMode,
        senderAddress: form.email_senderAddress.trim(),
        senderName: form.email_senderName.trim(),
        replyToAddress: form.email_replyToAddress.trim() || null,
        timeoutMs: form.email_timeoutMs,
      };
      return cfg;
    }
    case EmailApiConfigurationAdapterTypeEnum.SesApi:
    case EmailApiConfigurationAdapterTypeEnum.SendgridApi:
    case EmailApiConfigurationAdapterTypeEnum.ResendApi:
    case EmailApiConfigurationAdapterTypeEnum.MailgunApi: {
      const cfg: EmailApiConfiguration = {
        adapterType: form.adapterType as EmailApiConfigurationAdapterTypeEnum,
        region: form.email_region.trim() || null,
        baseUrl: form.email_baseUrl.trim() || null,
        senderAddress: form.email_senderAddress.trim(),
        senderName: form.email_senderName.trim(),
        timeoutMs: form.email_timeoutMs,
      };
      if (form.email_replyToAddress.trim()) {
        (cfg as any).replyToAddress = form.email_replyToAddress.trim();
      }
      return cfg;
    }
    case SmsConfigurationAdapterTypeEnum.AliyunSms:
    case SmsConfigurationAdapterTypeEnum.TencentSms: {
      const cfg: SmsConfiguration = {
        adapterType: form.adapterType as SmsConfigurationAdapterTypeEnum,
        region: form.sms_region.trim(),
        applicationId: form.sms_applicationId.trim() || null,
        signatureId: form.sms_signatureId.trim(),
        templateId: form.sms_templateId.trim(),
        timeoutMs: form.sms_timeoutMs,
      };
      return cfg;
    }
    case EpayConfigurationAdapterTypeEnum.EpayCompat: {
      const cfg: EpayConfiguration = {
        adapterType: EpayConfigurationAdapterTypeEnum.EpayCompat,
        gatewayBaseUrl: form.epay_gatewayBaseUrl.trim(),
        submitPath: form.epay_submitPath.trim(),
        queryPath: form.epay_queryPath.trim(),
        refundPath: form.epay_refundPath.trim(),
        merchantId: form.epay_merchantId.trim(),
        applicationId: form.epay_applicationId.trim() || null,
        paymentTypes: new Set<EpayConfigurationPaymentTypesEnum>(form.epay_paymentTypes),
        signingPreset: EpayConfigurationSigningPresetEnum.EpayMd5Canonical,
        callbackAckText: form.epay_callbackAckText.trim(),
        notifyUrl: form.epay_notifyUrl.trim(),
        returnUrl: form.epay_returnUrl.trim(),
        callbackTimeWindowSeconds: form.epay_callbackTimeWindowSeconds,
        checkoutTtlSeconds: form.epay_checkoutTtlSeconds,
        timeoutMs: form.epay_timeoutMs,
      };
      return cfg;
    }
    default:
      throw new Error(`未知的 adapterType: ${form.adapterType}`);
  }
}

/** 中文供应商种类标签 */
function kindLabel(kind: ProviderKind): string {
  switch (kind) {
    case ProviderKind.Ai: return 'AI 推理';
    case ProviderKind.Email: return '邮件';
    case ProviderKind.Sms: return '短信';
    case ProviderKind.Payment: return '支付';
    default: return String(kind);
  }
}

/* ── 页面组件 ── */

export const Providers: React.FC = () => {
  const queryClient = useQueryClient();

  const {
    data: providers = [],
    isLoading,
    isError,
    error: fetchError,
  } = useQuery({
    queryKey: ['providers'],
    queryFn: () => repository.getProviders(),
  });

  /* 表单与抽屉状态 */
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [form, setForm] = useState<ProviderFormDTO>(blankForm());

  /* 各种弹窗/抽屉状态 */
  const [confirmPublish, setConfirmPublish] = useState<Provider | null>(null);
  const [publishRollout, setPublishRollout] = useState<number>(100);
  const [publishEffectiveAt, setPublishEffectiveAt] = useState<string>('');
  const [publishAuditReason, setPublishAuditReason] = useState<string>('');

  const [confirmRollback, setConfirmRollback] = useState<Provider | null>(null);
  const [rollbackTargetVer, setRollbackTargetVer] = useState<number>(1);
  const [rollbackAuditReason, setRollbackAuditReason] = useState<string>('');

  const [confirmDisable, setConfirmDisable] = useState<Provider | null>(null);
  const [disableAuditReason, setDisableAuditReason] = useState<string>('');
  const [disableConfirmName, setDisableConfirmName] = useState<string>('');

  const [confirmHealth, setConfirmHealth] = useState<Provider | null>(null);
  const [healthTestDestination, setHealthTestDestination] = useState<string>('');
  const [healthAuditReason, setHealthAuditReason] = useState<string>('');

  const [credentialProvider, setCredentialProvider] = useState<Provider | null>(null);
  const [credentialValues, setCredentialValues] = useState<Record<string, string>>({});
  const [credentialAuditReason, setCredentialAuditReason] = useState<string>('');

  /* 消息与筛选 */
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [operationSuccessNotice, setOperationSuccessNotice] = useState<string | null>(null);

  const [filterKeyword, setFilterKeyword] = useState('');
  const [filterKind, setFilterKind] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  const triggerRef = useRef<HTMLButtonElement>(null);
  const drawerFocusRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (drawerOpen && drawerFocusRef.current) {
      const first = drawerFocusRef.current.querySelector<HTMLElement>('input, select');
      first?.focus();
    }
  }, [drawerOpen]);

  const updateField = useCallback(
    <K extends keyof ProviderFormDTO>(key: K, value: ProviderFormDTO[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  /* 切换 Kind 时自动设置对应的默认适配器 */
  const handleKindChange = (newKind: ProviderKind) => {
    let defaultAdapter: string = form.adapterType;
    if (newKind === ProviderKind.Ai) {
      defaultAdapter = OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat;
    } else if (newKind === ProviderKind.Email) {
      defaultAdapter = SmtpConfigurationAdapterTypeEnum.Smtp;
    } else if (newKind === ProviderKind.Sms) {
      defaultAdapter = SmsConfigurationAdapterTypeEnum.AliyunSms;
    } else if (newKind === ProviderKind.Payment) {
      defaultAdapter = EpayConfigurationAdapterTypeEnum.EpayCompat;
    }
    setForm((prev) => ({
      ...prev,
      kind: newKind,
      adapterType: defaultAdapter,
    }));
  };

  /* ── 弹窗关闭及清理辅助函数 ── */

  const handleCloseDrawer = () => {
    setDrawerOpen(false);
    setEditingProvider(null);
  };

  const handleClosePublish = () => {
    setConfirmPublish(null);
    setPublishRollout(100);
    setPublishEffectiveAt('');
    setPublishAuditReason('');
  };

  const handleCloseRollback = () => {
    setConfirmRollback(null);
    setRollbackTargetVer(1);
    setRollbackAuditReason('');
  };

  const handleCloseDisable = () => {
    setConfirmDisable(null);
    setDisableAuditReason('');
    setDisableConfirmName('');
  };

  const handleCloseHealth = () => {
    setConfirmHealth(null);
    setHealthTestDestination('');
    setHealthAuditReason('');
  };

  const handleCloseCredential = () => {
    setCredentialProvider(null);
    setCredentialValues({});
    setCredentialAuditReason('');
  };

  /* ── Mutations ── */

  const saveMutation = useMutation({
    mutationFn: (params: { req: ProviderWriteRequest; id?: string; rv?: number }) =>
      repository.saveProviderDraft(params.req, params.id, params.rv),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      handleCloseDrawer();
      setMutationError(null);
      setOperationSuccessNotice('供应商草稿保存成功');
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const publishMutation = useMutation({
    mutationFn: (params: { p: Provider; rollout: number; effectiveAt: Date; auditReason: string }) =>
      repository.publishProvider(
        params.p.providerId,
        params.p.resourceVersion,
        params.rollout,
        params.effectiveAt,
        params.auditReason,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      handleClosePublish();
      setMutationError(null);
      setOperationSuccessNotice('供应商线上发布成功');
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (params: { p: Provider; targetVersion: number; auditReason: string }) =>
      repository.rollbackProvider(
        params.p.providerId,
        params.p.resourceVersion,
        params.targetVersion,
        params.auditReason,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      handleCloseRollback();
      setMutationError(null);
      setOperationSuccessNotice('供应商版本回滚成功');
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const disableMutation = useMutation({
    mutationFn: (params: { p: Provider; auditReason: string }) =>
      repository.disableProvider(params.p.providerId, params.p.resourceVersion, params.auditReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      handleCloseDisable();
      setMutationError(null);
      setOperationSuccessNotice('供应商已成功停用，线上灰度流量降为 0%');
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const checkHealthMutation = useMutation({
    mutationFn: (params: { p: Provider; testDest?: string; auditReason: string }) =>
      repository.checkProviderHealth(params.p.providerId, params.testDest, params.auditReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      handleCloseHealth();
      setMutationError(null);
      setOperationSuccessNotice('供应商健康检查请求发起成功，探针已就绪');
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const rotateCredentialsMutation = useMutation({
    mutationFn: (params: { p: Provider; secrets: CredentialSecretInput[]; auditReason: string }) =>
      repository.rotateProviderCredentials(
        params.p.providerId,
        params.p.resourceVersion,
        params.secrets,
        params.auditReason,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      handleCloseCredential();
      setMutationError(null);
      setOperationSuccessNotice('凭据安全轮换成功，密钥输入及审计理由已清理');
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  /* ── 按钮触发处理 ── */

  const handleCreate = () => {
    setEditingProvider(null);
    setForm(blankForm());
    setMutationError(null);
    setDrawerOpen(true);
  };

  const handleEdit = (p: Provider) => {
    setEditingProvider(p);
    setForm(providerToForm(p));
    setMutationError(null);
    setDrawerOpen(true);
  };

  const handleSave = () => {
    if (!form.providerName.trim()) {
      setMutationError('供应商名称不能为空');
      return;
    }

    /* 校验各适配器专用必填项 */
    if (form.adapterType === OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat) {
      if (!form.ai_baseUrl.trim()) {
        setMutationError('OpenAI 兼容适配器 Base URL 不能为空');
        return;
      }
    } else if (form.adapterType === SmtpConfigurationAdapterTypeEnum.Smtp) {
      if (!form.smtp_host.trim()) { setMutationError('SMTP 主机不能为空'); return; }
      if (!form.email_senderAddress.trim()) { setMutationError('发件人地址不能为空'); return; }
      if (!form.email_senderName.trim()) { setMutationError('发件人显示名称不能为空'); return; }
    } else if (
      form.adapterType === EmailApiConfigurationAdapterTypeEnum.SesApi ||
      form.adapterType === EmailApiConfigurationAdapterTypeEnum.SendgridApi ||
      form.adapterType === EmailApiConfigurationAdapterTypeEnum.ResendApi ||
      form.adapterType === EmailApiConfigurationAdapterTypeEnum.MailgunApi
    ) {
      if (form.adapterType === EmailApiConfigurationAdapterTypeEnum.SesApi && !form.email_region.trim()) {
        setMutationError('SES 邮件 API 适配器 region 不能为空');
        return;
      }
      if (form.adapterType === EmailApiConfigurationAdapterTypeEnum.MailgunApi && !form.email_baseUrl.trim()) {
        setMutationError('Mailgun 邮件 API 适配器 Base URL 不能为空');
        return;
      }
      if (!form.email_senderAddress.trim()) { setMutationError('发件人地址不能为空'); return; }
      if (!form.email_senderName.trim()) { setMutationError('发件人显示名称不能为空'); return; }
    } else if (
      form.adapterType === SmsConfigurationAdapterTypeEnum.AliyunSms ||
      form.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms
    ) {
      if (!form.sms_region.trim()) { setMutationError('短信区域 (region) 不能为空'); return; }
      if (form.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms && !form.sms_applicationId.trim()) {
        setMutationError('腾讯云短信适配器必须提供应用 ID (applicationId)');
        return;
      }
      if (!form.sms_signatureId.trim()) { setMutationError('短信签名 ID 不能为空'); return; }
      if (!form.sms_templateId.trim()) { setMutationError('短信模板 ID 不能为空'); return; }
    } else if (form.adapterType === EpayConfigurationAdapterTypeEnum.EpayCompat) {
      if (!form.epay_gatewayBaseUrl.trim()) { setMutationError('易支付网关 Base URL 不能为空'); return; }
      if (!form.epay_merchantId.trim()) { setMutationError('商户 ID 不能为空'); return; }
      if (!form.epay_notifyUrl.trim()) { setMutationError('异步通知 Webhook URL 不能为空'); return; }
      if (!form.epay_returnUrl.trim()) { setMutationError('前端跳转 Return URL 不能为空'); return; }
      if (form.epay_paymentTypes.length === 0) {
        setMutationError('易支付必须至少选择一种支付方式 (ALIPAY / WECHAT_PAY)');
        return;
      }
    }

    try {
      const req: ProviderWriteRequest = {
        providerName: form.providerName.trim(),
        kind: form.kind,
        _configuration: buildConfiguration(form),
        dataRegion: form.dataRegion.trim() || null,
        retentionStatement: form.retentionStatement.trim() || null,
        retryLimit: form.retryLimit,
        priority: form.priority,
      };
      saveMutation.mutate({
        req,
        id: editingProvider?.providerId,
        rv: editingProvider?.resourceVersion,
      });
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleOpenPublish = (p: Provider) => {
    setConfirmPublish(p);
    setPublishRollout(100);
    const nowLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    setPublishEffectiveAt(nowLocal);
    setPublishAuditReason('');
    setMutationError(null);
  };

  const handleExecutePublish = () => {
    if (!confirmPublish) return;
    if (publishRollout < 1 || publishRollout > 100) {
      setMutationError('发布灰度比例必须在 1% 至 100% 之间');
      return;
    }
    if (!publishEffectiveAt) {
      setMutationError('请指定生效时间');
      return;
    }
    if (publishAuditReason.trim().length < 8) {
      setMutationError('发布审计理由必须至少填写 8 个字符');
      return;
    }
    publishMutation.mutate({
      p: confirmPublish,
      rollout: publishRollout,
      effectiveAt: new Date(publishEffectiveAt),
      auditReason: publishAuditReason.trim(),
    });
  };

  const handleOpenRollback = (p: Provider) => {
    setConfirmRollback(p);
    const defaultVer = p.publishedResourceVersion ?? (p.resourceVersion > 1 ? p.resourceVersion - 1 : 1);
    setRollbackTargetVer(defaultVer);
    setRollbackAuditReason('');
    setMutationError(null);
  };

  const handleExecuteRollback = () => {
    if (!confirmRollback) return;
    if (!rollbackTargetVer || rollbackTargetVer <= 0) {
      setMutationError('目标已发布版本必须大于 0');
      return;
    }
    if (rollbackAuditReason.trim().length < 8) {
      setMutationError('回滚审计理由必须至少填写 8 个字符');
      return;
    }
    rollbackMutation.mutate({
      p: confirmRollback,
      targetVersion: rollbackTargetVer,
      auditReason: rollbackAuditReason.trim(),
    });
  };

  const handleOpenDisable = (p: Provider) => {
    setConfirmDisable(p);
    setDisableAuditReason('');
    setDisableConfirmName('');
    setMutationError(null);
  };

  const handleExecuteDisable = () => {
    if (!confirmDisable) return;
    if (disableAuditReason.trim().length < 8) {
      setMutationError('停用审计理由必须至少填写 8 个字符');
      return;
    }
    if (disableConfirmName.trim() !== confirmDisable.providerName) {
      setMutationError('二次确认的供应商名称与当前供应商不匹配');
      return;
    }
    disableMutation.mutate({
      p: confirmDisable,
      auditReason: disableAuditReason.trim(),
    });
  };

  const handleOpenHealth = (p: Provider) => {
    setConfirmHealth(p);
    setHealthTestDestination('');
    setHealthAuditReason('');
    setMutationError(null);
  };

  const handleExecuteHealth = () => {
    if (!confirmHealth) return;
    const isEmailOrSms = confirmHealth.kind === ProviderKind.Email || confirmHealth.kind === ProviderKind.Sms;
    if (isEmailOrSms && !healthTestDestination.trim()) {
      setMutationError('邮件与短信供应商健康检查必须输入测试目标');
      return;
    }
    if (healthAuditReason.trim().length < 8) {
      setMutationError('健康检查审计理由必须至少填写 8 个字符');
      return;
    }
    checkHealthMutation.mutate({
      p: confirmHealth,
      testDest: healthTestDestination.trim() || undefined,
      auditReason: healthAuditReason.trim(),
    });
  };

  const handleOpenCredential = (p: Provider) => {
    setCredentialProvider(p);
    setCredentialValues({});
    setCredentialAuditReason('');
    setMutationError(null);
  };

  const handleCredentialSave = () => {
    if (!credentialProvider) return;
    const secrets: CredentialSecretInput[] = Object.entries(credentialValues)
      .filter(([_, v]) => v.trim() !== '')
      .map(([k, v]) => ({ name: k as CredentialName, value: v.trim() }));
    if (secrets.length === 0) {
      setMutationError('至少需要输入一项有效凭据密钥');
      return;
    }
    if (credentialAuditReason.trim().length < 8) {
      setMutationError('轮换凭据审计理由必须至少填写 8 个字符');
      return;
    }
    rotateCredentialsMutation.mutate({
      p: credentialProvider,
      secrets,
      auditReason: credentialAuditReason.trim(),
    });
  };

  /* ── 视图辅助函数 ── */

  const getStatusBadge = (status: ProviderStatus) => {
    switch (status) {
      case ProviderStatus.Active: return <Badge variant="success">在线 (ACTIVE)</Badge>;
      case ProviderStatus.Draft: return <Badge variant="warning">草稿 (DRAFT)</Badge>;
      case ProviderStatus.Disabled: return <Badge variant="danger">已停用 (DISABLED)</Badge>;
      case ProviderStatus.Superseded: return <Badge variant="default">已替换 (SUPERSEDED)</Badge>;
      case ProviderStatus.Ready: return <Badge variant="success">就绪 (READY)</Badge>;
      case ProviderStatus.Validating: return <Badge variant="default">校验中</Badge>;
      default: return <Badge variant="default">{status}</Badge>;
    }
  };

  const getOnlineStatusBadge = (p: Provider) => {
    const pubVersion = p.publishedResourceVersion;
    const rollout = p.publishedRolloutPercentage ?? 0;
    const isOnline = pubVersion != null && rollout > 0;

    if (isOnline) {
      if (p.status === ProviderStatus.Draft) {
        return (
          <span title={`线上旧版 v${pubVersion} 仍分流 ${rollout}%，草稿发布前旧版持续生效`}>
            <Badge variant="warning">线上旧版 v{pubVersion} ({rollout}%)</Badge>
          </span>
        );
      }
      return (
        <span title={`已发布上线 v${pubVersion}，分发流量 ${rollout}%`}>
          <Badge variant="success">v{pubVersion} ({rollout}%)</Badge>
        </span>
      );
    }

    if (pubVersion != null) {
      return (
        <span title={`未分发流量，历史已发布版本为 v${pubVersion}`}>
          <Badge variant="default">0% (保留 v{pubVersion})</Badge>
        </span>
      );
    }

    return <Badge variant="default">未上线 (0%)</Badge>;
  };

  /** 按当前 Provider._configuration.adapterType 返回对应凭据 Key */
  const getCredentialKeys = (p: Provider): CredentialName[] => {
    const cfg = p._configuration;
    const adapterType = cfg?.adapterType;
    if (adapterType) {
      switch (adapterType) {
        case OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat:
        case NativeAiConfigurationAdapterTypeEnum.Openai:
        case NativeAiConfigurationAdapterTypeEnum.Anthropic:
        case NativeAiConfigurationAdapterTypeEnum.Gemini:
          return ['apiKey' as CredentialName];
        case SmtpConfigurationAdapterTypeEnum.Smtp:
          return ['username' as CredentialName, 'password' as CredentialName];
        case EmailApiConfigurationAdapterTypeEnum.SesApi:
          return ['accessKeyId' as CredentialName, 'accessKeySecret' as CredentialName];
        case EmailApiConfigurationAdapterTypeEnum.SendgridApi:
        case EmailApiConfigurationAdapterTypeEnum.ResendApi:
        case EmailApiConfigurationAdapterTypeEnum.MailgunApi:
          return ['apiKey' as CredentialName];
        case SmsConfigurationAdapterTypeEnum.AliyunSms:
          return ['accessKeyId' as CredentialName, 'accessKeySecret' as CredentialName];
        case SmsConfigurationAdapterTypeEnum.TencentSms:
          return ['secretId' as CredentialName, 'secretKey' as CredentialName];
        case EpayConfigurationAdapterTypeEnum.EpayCompat:
          return ['merchantKey' as CredentialName];
      }
    }
    // 降级策略
    switch (p.kind) {
      case ProviderKind.Ai: return ['apiKey' as CredentialName];
      case ProviderKind.Email: return ['username' as CredentialName, 'password' as CredentialName];
      case ProviderKind.Sms: return ['accessKeyId' as CredentialName, 'accessKeySecret' as CredentialName];
      case ProviderKind.Payment: return ['merchantKey' as CredentialName];
      default: return [];
    }
  };

  const filteredProviders = providers.filter((p) => {
    if (filterKind && p.kind !== filterKind) return false;
    if (filterStatus && p.status !== filterStatus) return false;
    if (filterKeyword) {
      const lower = filterKeyword.toLowerCase();
      return p.providerName.toLowerCase().includes(lower) || p.providerId.toLowerCase().includes(lower);
    }
    return true;
  });

  /* 易支付复选框切换助手 */
  const toggleEpayPaymentType = (type: EpayConfigurationPaymentTypesEnum) => {
    setForm((prev) => {
      const current = prev.epay_paymentTypes;
      const exists = current.includes(type);
      const updated = exists ? current.filter((t) => t !== type) : [...current, type];
      return { ...prev, epay_paymentTypes: updated };
    });
  };

  return (
    <div>
      <div className="page-title-group" style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600 }}>供应商配置管理</h1>
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
          管理上游 AI 推理（OpenAI 兼容/原生、Anthropic、Gemini）、邮件 API 与 SMTP、短信（阿里云/腾讯云）及易支付网关。支持版本草稿、轮换凭据、健康探针、灰度发布、紧急停用与回滚闭环。
        </div>
      </div>

      <div className="toolbar" style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <Input
          placeholder="搜索供应商名称/ID"
          value={filterKeyword}
          onChange={(e) => setFilterKeyword(e.target.value)}
          style={{ width: '240px', marginBottom: 0 }}
        />
        <select className="input" style={{ width: 'auto' }} value={filterKind} onChange={(e) => setFilterKind(e.target.value)}>
          <option value="">所有服务类型</option>
          {Object.values(ProviderKind).map((k) => (
            <option key={k} value={k}>{kindLabel(k)}</option>
          ))}
        </select>
        <select className="input" style={{ width: 'auto' }} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">所有配置状态</option>
          {Object.values(ProviderStatus).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <div style={{ flex: 1 }}></div>
        <Button ref={triggerRef} variant="primary" onClick={handleCreate}>
          新增供应商配置
        </Button>
      </div>

      {mutationError && (
        <div style={{ background: 'var(--color-danger-bg, #fef2f2)', color: 'var(--color-danger)', padding: '12px 16px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>操作失败：{mutationError}</span>
          <button onClick={() => setMutationError(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', textDecoration: 'underline', marginLeft: '12px' }}>
            关闭提示
          </button>
        </div>
      )}

      {operationSuccessNotice && (
        <div style={{ background: 'var(--color-success-bg, #f0fdf4)', color: 'var(--color-success, #166534)', padding: '12px 16px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>✓ {operationSuccessNotice}</span>
          <button onClick={() => setOperationSuccessNotice(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', textDecoration: 'underline', marginLeft: '12px' }}>
            关闭提示
          </button>
        </div>
      )}

      <Card>
        {isLoading && <div style={{ color: 'var(--color-text-tertiary)', padding: '20px' }}>供应商配置加载中...</div>}
        {isError && (
          <div style={{ color: 'var(--color-danger)', padding: '16px' }}>
            获取供应商列表失败：{fetchError instanceof Error ? fetchError.message : String(fetchError)}
          </div>
        )}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table className="responsive-table">
              <thead>
                <tr>
                  <th>供应商名称</th>
                  <th>服务类型与适配器</th>
                  <th>配置状态</th>
                  <th>线上运行状态</th>
                  <th>优先级 (数值越大越优先)</th>
                  <th>资源版本</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredProviders.map((p) => {
                  /* 停用按钮显隐依据：publishedResourceVersion != null 且 publishedRolloutPercentage > 0 */
                  const canDisable = p.publishedResourceVersion != null && (p.publishedRolloutPercentage ?? 0) > 0;
                  /* 可发布条件：仅当 status === ProviderStatus.Ready 时显示 */
                  const canPublish = p.status === ProviderStatus.Ready;
                  /* 可回滚条件：仅在 publishedResourceVersion != null 时显示 */
                  const canRollback = p.publishedResourceVersion != null;

                  return (
                    <tr key={p.providerId}>
                      <td data-label="供应商名称">
                        <div style={{ fontWeight: 600 }}>{p.providerName}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>{p.providerId}</div>
                      </td>
                      <td data-label="服务类型与适配器">
                        <div>{kindLabel(p.kind)}</div>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                          {p._configuration?.adapterType ? adapterLabel(p._configuration.adapterType) : '-'}
                        </div>
                      </td>
                      <td data-label="配置状态">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {getStatusBadge(p.status)}
                          {p.status === ProviderStatus.Draft && (
                            <span style={{ fontSize: '11px', color: 'var(--color-warning-text, #b45309)', display: 'flex', alignItems: 'center', gap: '2px' }} title="请先轮换凭据并通过探针健康检查">
                              <AlertCircle size={12} /> 需轮换凭据与健康检查就绪
                            </span>
                          )}
                        </div>
                      </td>
                      <td data-label="线上运行状态">{getOnlineStatusBadge(p)}</td>
                      <td data-label="优先级">{p.priority}</td>
                      <td data-label="资源版本">v{p.resourceVersion}</td>
                      <td data-label="操作">
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                          <Button variant="ghost" onClick={() => handleEdit(p)} title="编辑配置">
                            编辑
                          </Button>

                          <Button variant="ghost" onClick={() => handleOpenHealth(p)} title="审计健康检查">
                            <Activity size={14} /> <span className="hide-on-mobile">检查</span>
                          </Button>

                          <Button variant="ghost" onClick={() => handleOpenCredential(p)} title="凭据安全轮换">
                            <KeyRound size={14} /> <span className="hide-on-mobile">凭据</span>
                          </Button>

                          {canPublish && (
                            <Button variant="primary" onClick={() => handleOpenPublish(p)}>
                              <Send size={13} style={{ marginRight: '4px' }} /> 发布
                            </Button>
                          )}

                          {canRollback && (
                            <Button variant="default" onClick={() => handleOpenRollback(p)} title="版本回滚">
                              <RotateCcw size={13} style={{ marginRight: '4px' }} /> 回滚
                            </Button>
                          )}

                          {canDisable && (
                            <Button variant="danger" onClick={() => handleOpenDisable(p)}>
                              <Power size={13} style={{ marginRight: '4px' }} /> 停用
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredProviders.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-tertiary)' }}>
                      未查找到匹配的供应商配置
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ── 1. 编辑 / 新增抽屉 ── */}
      <Drawer
        open={drawerOpen}
        title={editingProvider ? `编辑供应商 - ${editingProvider.providerName}` : '新增供应商配置'}
        onClose={handleCloseDrawer}
        returnFocusRef={triggerRef}
        footer={
          <>
            <Button variant="default" onClick={handleCloseDrawer}>取消</Button>
            <Button variant="primary" onClick={handleSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? '保存中...' : '保存草稿'}
            </Button>
          </>
        }
      >
        <div ref={drawerFocusRef} style={{ paddingBottom: '20px' }}>
          <Input
            label="供应商名称"
            value={form.providerName}
            onChange={(e) => updateField('providerName', e.target.value)}
            required
            placeholder="例如：OpenAI 官方通道 / 阿里云主短信"
          />

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '160px', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>服务种类 (Kind)</label>
              <select
                className="input"
                value={form.kind}
                onChange={(e) => handleKindChange(e.target.value as ProviderKind)}
                disabled={!!editingProvider}
              >
                {Object.values(ProviderKind).map((k) => (
                  <option key={k} value={k}>{kindLabel(k)}</option>
                ))}
              </select>
            </div>

            <div style={{ flex: 1, minWidth: '160px', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>适配器类型 (Adapter Type)</label>
              <select
                className="input"
                value={form.adapterType}
                onChange={(e) => updateField('adapterType', e.target.value)}
              >
                {form.kind === ProviderKind.Ai && (
                  <>
                    <option value={OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat}>
                      OPENAI_COMPAT (OpenAI 兼容协议)
                    </option>
                    <option value={NativeAiConfigurationAdapterTypeEnum.Openai}>
                      OPENAI (OpenAI 原生)
                    </option>
                    <option value={NativeAiConfigurationAdapterTypeEnum.Anthropic}>
                      ANTHROPIC (Anthropic Claude 原生)
                    </option>
                    <option value={NativeAiConfigurationAdapterTypeEnum.Gemini}>
                      GEMINI (Google Gemini 原生)
                    </option>
                  </>
                )}
                {form.kind === ProviderKind.Email && (
                  <>
                    <option value={SmtpConfigurationAdapterTypeEnum.Smtp}>
                      SMTP (SMTP 邮件传输)
                    </option>
                    <option value={EmailApiConfigurationAdapterTypeEnum.SesApi}>
                      SES_API (AWS SES API)
                    </option>
                    <option value={EmailApiConfigurationAdapterTypeEnum.SendgridApi}>
                      SENDGRID_API (SendGrid API)
                    </option>
                    <option value={EmailApiConfigurationAdapterTypeEnum.ResendApi}>
                      RESEND_API (Resend API)
                    </option>
                    <option value={EmailApiConfigurationAdapterTypeEnum.MailgunApi}>
                      MAILGUN_API (Mailgun API)
                    </option>
                  </>
                )}
                {form.kind === ProviderKind.Sms && (
                  <>
                    <option value={SmsConfigurationAdapterTypeEnum.AliyunSms}>
                      ALIYUN_SMS (阿里云短信)
                    </option>
                    <option value={SmsConfigurationAdapterTypeEnum.TencentSms}>
                      TENCENT_SMS (腾讯云短信)
                    </option>
                  </>
                )}
                {form.kind === ProviderKind.Payment && (
                  <option value={EpayConfigurationAdapterTypeEnum.EpayCompat}>
                    EPAY_COMPAT (易支付网关兼容协议)
                  </option>
                )}
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '160px' }}>
              <Input
                label="数据区域 (dataRegion)"
                value={form.dataRegion}
                onChange={(e) => updateField('dataRegion', e.target.value)}
                placeholder="例如：US-EAST / CN-HANGZHOU"
              />
            </div>
            <div style={{ flex: 1, minWidth: '160px' }}>
              <Input
                label="留存声明 (retentionStatement)"
                value={form.retentionStatement}
                onChange={(e) => updateField('retentionStatement', e.target.value)}
                placeholder="例如：ZERO_LOG_RETENTION"
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '160px' }}>
              <Input
                label="重试次数"
                type="number"
                value={form.retryLimit}
                onChange={(e) => updateField('retryLimit', parseInt(e.target.value, 10) || 0)}
              />
            </div>
            <div style={{ flex: 1, minWidth: '160px' }}>
              <Input
                label="优先级 (数值越大越优先，运行时按降序选择)"
                type="number"
                value={form.priority}
                onChange={(e) => updateField('priority', parseInt(e.target.value, 10) || 1)}
              />
            </div>
          </div>

          {/* 按具体适配器渲染配置参数 */}
          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px', marginTop: '8px' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>
              {adapterLabel(form.adapterType)} 详细参数配置
            </div>

            {/* AI 兼容协议 */}
            {form.adapterType === OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat && (
              <>
                <Input
                  label="Base URL"
                  value={form.ai_baseUrl}
                  onChange={(e) => updateField('ai_baseUrl', e.target.value)}
                  required
                  placeholder="https://api.openai.com/v1"
                />
                <Input
                  label="Organization (可选组织 ID)"
                  value={form.ai_organization}
                  onChange={(e) => updateField('ai_organization', e.target.value)}
                  placeholder="org-xxx"
                />
                <Input
                  label="Project (可选项目 ID)"
                  value={form.ai_project}
                  onChange={(e) => updateField('ai_project', e.target.value)}
                  placeholder="proj-xxx"
                />
                <Input
                  label="超时 (ms)"
                  type="number"
                  value={form.ai_timeoutMs}
                  onChange={(e) => updateField('ai_timeoutMs', parseInt(e.target.value, 10) || 30000)}
                />
              </>
            )}

            {/* AI 原生类型 */}
            {(form.adapterType === NativeAiConfigurationAdapterTypeEnum.Openai ||
              form.adapterType === NativeAiConfigurationAdapterTypeEnum.Anthropic ||
              form.adapterType === NativeAiConfigurationAdapterTypeEnum.Gemini) && (
              <>
                <Input
                  label="Base URL (可选，留空使用标准默认端点)"
                  value={form.ai_baseUrl}
                  onChange={(e) => updateField('ai_baseUrl', e.target.value)}
                  placeholder="留空使用官方默认 API 地址"
                />
                <Input
                  label="超时 (ms)"
                  type="number"
                  value={form.ai_timeoutMs}
                  onChange={(e) => updateField('ai_timeoutMs', parseInt(e.target.value, 10) || 30000)}
                />
              </>
            )}

            {/* SMTP 邮件协议 */}
            {form.adapterType === SmtpConfigurationAdapterTypeEnum.Smtp && (
              <>
                <Input
                  label="SMTP 主机"
                  value={form.smtp_host}
                  onChange={(e) => updateField('smtp_host', e.target.value)}
                  required
                  placeholder="smtp.exmail.qq.com"
                />
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '140px' }}>
                    <Input
                      label="端口"
                      type="number"
                      value={form.smtp_port}
                      onChange={(e) => updateField('smtp_port', parseInt(e.target.value, 10) || 465)}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '140px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
                      <label style={{ fontSize: '13px', fontWeight: 500 }}>TLS 模式</label>
                      <select className="input" value={form.smtp_tlsMode} onChange={(e) => updateField('smtp_tlsMode', e.target.value as TlsMode)}>
                        {Object.values(TlsMode).map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
                <Input
                  label="发件人地址"
                  value={form.email_senderAddress}
                  onChange={(e) => updateField('email_senderAddress', e.target.value)}
                  required
                  placeholder="noreply@lovereply.app"
                />
                <Input
                  label="发件人显示名称"
                  value={form.email_senderName}
                  onChange={(e) => updateField('email_senderName', e.target.value)}
                  required
                  placeholder="心语助手"
                />
                <Input
                  label="回复地址 (Reply-To，可选)"
                  value={form.email_replyToAddress}
                  onChange={(e) => updateField('email_replyToAddress', e.target.value)}
                  placeholder="support@lovereply.app"
                />
                <Input
                  label="超时 (ms)"
                  type="number"
                  value={form.email_timeoutMs}
                  onChange={(e) => updateField('email_timeoutMs', parseInt(e.target.value, 10) || 10000)}
                />
              </>
            )}

            {/* API 邮件 (SES / SendGrid / Resend / Mailgun) */}
            {(form.adapterType === EmailApiConfigurationAdapterTypeEnum.SesApi ||
              form.adapterType === EmailApiConfigurationAdapterTypeEnum.SendgridApi ||
              form.adapterType === EmailApiConfigurationAdapterTypeEnum.ResendApi ||
              form.adapterType === EmailApiConfigurationAdapterTypeEnum.MailgunApi) && (
              <>
                <Input
                  label={`区域 (Region${form.adapterType === EmailApiConfigurationAdapterTypeEnum.SesApi ? '，SES 必填' : '，可选'})`}
                  value={form.email_region}
                  onChange={(e) => updateField('email_region', e.target.value)}
                  required={form.adapterType === EmailApiConfigurationAdapterTypeEnum.SesApi}
                  placeholder="us-east-1"
                />
                <Input
                  label={`Base URL (${form.adapterType === EmailApiConfigurationAdapterTypeEnum.MailgunApi ? 'Mailgun 必填' : '可选'})`}
                  value={form.email_baseUrl}
                  onChange={(e) => updateField('email_baseUrl', e.target.value)}
                  required={form.adapterType === EmailApiConfigurationAdapterTypeEnum.MailgunApi}
                  placeholder="https://api.mailgun.net/v3"
                />
                <Input
                  label="发件人地址"
                  value={form.email_senderAddress}
                  onChange={(e) => updateField('email_senderAddress', e.target.value)}
                  required
                  placeholder="noreply@lovereply.app"
                />
                <Input
                  label="发件人显示名称"
                  value={form.email_senderName}
                  onChange={(e) => updateField('email_senderName', e.target.value)}
                  required
                  placeholder="心语助手"
                />
                <Input
                  label="回复地址 (Reply-To，可选)"
                  value={form.email_replyToAddress}
                  onChange={(e) => updateField('email_replyToAddress', e.target.value)}
                  placeholder="support@lovereply.app"
                />
                <Input
                  label="超时 (ms)"
                  type="number"
                  value={form.email_timeoutMs}
                  onChange={(e) => updateField('email_timeoutMs', parseInt(e.target.value, 10) || 10000)}
                />
              </>
            )}

            {/* 短信配置 (阿里云 / 腾讯云) */}
            {(form.adapterType === SmsConfigurationAdapterTypeEnum.AliyunSms ||
              form.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms) && (
              <>
                <Input
                  label="区域 (Region)"
                  value={form.sms_region}
                  onChange={(e) => updateField('sms_region', e.target.value)}
                  required
                  placeholder="cn-hangzhou"
                />
                <Input
                  label={`应用 ID (Application ID${form.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms ? '，腾讯云必填' : '，可选'})`}
                  value={form.sms_applicationId}
                  onChange={(e) => updateField('sms_applicationId', e.target.value)}
                  required={form.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms}
                  placeholder={form.adapterType === SmsConfigurationAdapterTypeEnum.TencentSms ? '1400xxxxxx' : '可选应用标识'}
                />
                <Input
                  label="签名 ID (Signature ID)"
                  value={form.sms_signatureId}
                  onChange={(e) => updateField('sms_signatureId', e.target.value)}
                  required
                />
                <Input
                  label="模板 ID (Template ID)"
                  value={form.sms_templateId}
                  onChange={(e) => updateField('sms_templateId', e.target.value)}
                  required
                />
                <Input
                  label="超时 (ms)"
                  type="number"
                  value={form.sms_timeoutMs}
                  onChange={(e) => updateField('sms_timeoutMs', parseInt(e.target.value, 10) || 5000)}
                />
              </>
            )}

            {/* 易支付网关配置 */}
            {form.adapterType === EpayConfigurationAdapterTypeEnum.EpayCompat && (
              <>
                <Input
                  label="支付网关 URL"
                  value={form.epay_gatewayBaseUrl}
                  onChange={(e) => updateField('epay_gatewayBaseUrl', e.target.value)}
                  required
                  placeholder="https://epay.example.com"
                />
                <Input
                  label="应用 ID (Application ID，可选)"
                  value={form.epay_applicationId}
                  onChange={(e) => updateField('epay_applicationId', e.target.value)}
                  placeholder="可选子应用 AppID"
                />

                <div style={{ marginBottom: '12px' }}>
                  <label style={{ fontSize: '13px', fontWeight: 500, display: 'block', marginBottom: '6px' }}>
                    支持的支付方式 (paymentTypes，至少选一种)
                  </label>
                  <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                    <label style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={form.epay_paymentTypes.includes(EpayConfigurationPaymentTypesEnum.Alipay)}
                        onChange={() => toggleEpayPaymentType(EpayConfigurationPaymentTypesEnum.Alipay)}
                      />
                      ALIPAY (支付宝)
                    </label>
                    <label style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={form.epay_paymentTypes.includes(EpayConfigurationPaymentTypesEnum.WechatPay)}
                        onChange={() => toggleEpayPaymentType(EpayConfigurationPaymentTypesEnum.WechatPay)}
                      />
                      WECHAT_PAY (微信支付)
                    </label>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '120px' }}>
                    <Input label="提交路径" value={form.epay_submitPath} onChange={(e) => updateField('epay_submitPath', e.target.value)} />
                  </div>
                  <div style={{ flex: 1, minWidth: '120px' }}>
                    <Input label="查询路径" value={form.epay_queryPath} onChange={(e) => updateField('epay_queryPath', e.target.value)} />
                  </div>
                  <div style={{ flex: 1, minWidth: '120px' }}>
                    <Input label="退款路径" value={form.epay_refundPath} onChange={(e) => updateField('epay_refundPath', e.target.value)} />
                  </div>
                </div>

                <Input
                  label="商户 ID (Merchant ID)"
                  value={form.epay_merchantId}
                  onChange={(e) => updateField('epay_merchantId', e.target.value)}
                  required
                />
                <Input
                  label="异步通知 Webhook URL"
                  value={form.epay_notifyUrl}
                  onChange={(e) => updateField('epay_notifyUrl', e.target.value)}
                  required
                />
                <Input
                  label="前端跳转 Return URL"
                  value={form.epay_returnUrl}
                  onChange={(e) => updateField('epay_returnUrl', e.target.value)}
                  required
                />
                <Input label="回调确认响应文本" value={form.epay_callbackAckText} onChange={(e) => updateField('epay_callbackAckText', e.target.value)} />
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '140px' }}>
                    <Input label="回调校验时间窗 (秒)" type="number" value={form.epay_callbackTimeWindowSeconds} onChange={(e) => updateField('epay_callbackTimeWindowSeconds', parseInt(e.target.value, 10) || 300)} />
                  </div>
                  <div style={{ flex: 1, minWidth: '140px' }}>
                    <Input label="收银台 TTL (秒)" type="number" value={form.epay_checkoutTtlSeconds} onChange={(e) => updateField('epay_checkoutTtlSeconds', parseInt(e.target.value, 10) || 900)} />
                  </div>
                </div>
                <Input label="超时 (ms)" type="number" value={form.epay_timeoutMs} onChange={(e) => updateField('epay_timeoutMs', parseInt(e.target.value, 10) || 10000)} />
              </>
            )}
          </div>
        </div>
      </Drawer>

      {/* ── 2. 灰度发布 Dialog ── */}
      <Dialog
        open={!!confirmPublish}
        title={`发布上线 - ${confirmPublish?.providerName}`}
        onClose={handleClosePublish}
        footer={
          <>
            <Button variant="default" onClick={handleClosePublish}>取消</Button>
            <Button
              variant="primary"
              onClick={handleExecutePublish}
              disabled={
                publishMutation.isPending ||
                publishRollout < 1 ||
                publishRollout > 100 ||
                !publishEffectiveAt ||
                publishAuditReason.trim().length < 8
              }
            >
              {publishMutation.isPending ? '发布中...' : '确认上线发布'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            将当前状态为 READY 的配置版本发布上线。所有写请求要求传入 If-Match 并带至少 8 个字符的变更审计理由。
          </div>

          <Input
            label="灰度比例 (1 - 100%)"
            type="number"
            value={publishRollout}
            onChange={(e) => setPublishRollout(Math.min(100, Math.max(1, parseInt(e.target.value, 10) || 1)))}
            required
          />

          <Input
            label="生效时间 (effectiveAt)"
            type="datetime-local"
            value={publishEffectiveAt}
            onChange={(e) => setPublishEffectiveAt(e.target.value)}
            required
          />

          <Input
            label="审计理由 (至少 8 个字符)"
            value={publishAuditReason}
            onChange={(e) => setPublishAuditReason(e.target.value)}
            placeholder="如：例行版本发布并开启 100% 灰度测试"
            required
          />
        </div>
      </Dialog>

      {/* ── 3. 版本回滚 Dialog ── */}
      <Dialog
        open={!!confirmRollback}
        title={`版本回滚 - ${confirmRollback?.providerName}`}
        onClose={handleCloseRollback}
        footer={
          <>
            <Button variant="default" onClick={handleCloseRollback}>取消</Button>
            <Button
              variant="danger"
              onClick={handleExecuteRollback}
              disabled={
                rollbackMutation.isPending ||
                !rollbackTargetVer ||
                rollbackTargetVer <= 0 ||
                rollbackAuditReason.trim().length < 8
              }
            >
              {rollbackMutation.isPending ? '回滚中...' : '确认回滚版本'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            紧急将供应商在线分发目标版本回滚至指定的已有已发布版本数字。
          </div>

          <Input
            label="目标已发布版本 (targetResourceVersion)"
            type="number"
            value={rollbackTargetVer}
            onChange={(e) => setRollbackTargetVer(parseInt(e.target.value, 10) || 1)}
            required
          />

          <Input
            label="审计理由 (至少 8 个字符)"
            value={rollbackAuditReason}
            onChange={(e) => setRollbackAuditReason(e.target.value)}
            placeholder="如：线上网关异常，紧急回滚至上个稳定版本"
            required
          />
        </div>
      </Dialog>

      {/* ── 4. 危险停用 Dialog ── */}
      <Dialog
        open={!!confirmDisable}
        title={`危险操作：停用供应商 - ${confirmDisable?.providerName}`}
        onClose={handleCloseDisable}
        footer={
          <>
            <Button variant="default" onClick={handleCloseDisable}>取消</Button>
            <Button
              variant="danger"
              onClick={handleExecuteDisable}
              disabled={
                disableMutation.isPending ||
                disableAuditReason.trim().length < 8 ||
                disableConfirmName.trim() !== confirmDisable?.providerName
              }
            >
              {disableMutation.isPending ? '停用中...' : '确认立即停用'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ background: 'var(--color-danger-bg, #fef2f2)', color: 'var(--color-danger)', padding: '12px', borderRadius: '6px', fontSize: '13px', lineHeight: '1.5' }}>
            ⚠️ <strong>警告：</strong> 停用将立即把该供应商从邮件/短信/AI/支付运行时选择中移除（线上灰度置为 0%），
            但系统会保留其版本历史 (v{confirmDisable?.publishedResourceVersion ?? confirmDisable?.resourceVersion}) 供后续恢复。
          </div>

          <Input
            label="审计理由 (至少 8 个字符)"
            value={disableAuditReason}
            onChange={(e) => setDisableAuditReason(e.target.value)}
            placeholder="如：上游网关欠费，暂停路由分发"
            required
          />

          <Input
            label={`二次确认：请输入供应商完整名称「${confirmDisable?.providerName}」`}
            value={disableConfirmName}
            onChange={(e) => setDisableConfirmName(e.target.value)}
            placeholder={confirmDisable?.providerName}
            required
          />
        </div>
      </Dialog>

      {/* ── 5. 健康检查 Dialog ── */}
      <Dialog
        open={!!confirmHealth}
        title={`审计健康检查 - ${confirmHealth?.providerName}`}
        onClose={handleCloseHealth}
        footer={
          <>
            <Button variant="default" onClick={handleCloseHealth}>取消</Button>
            <Button
              variant="primary"
              onClick={handleExecuteHealth}
              disabled={
                checkHealthMutation.isPending ||
                ((confirmHealth?.kind === ProviderKind.Email || confirmHealth?.kind === ProviderKind.Sms) && !healthTestDestination.trim()) ||
                healthAuditReason.trim().length < 8
              }
            >
              {checkHealthMutation.isPending ? '检查中...' : '发起健康检查'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            向目标供应商发送探针或测试投递。测试目标会按脱敏规则处理，健康结果和审计理由会留审计记录。
          </div>

          {(confirmHealth?.kind === ProviderKind.Email || confirmHealth?.kind === ProviderKind.Sms) && (
            <Input
              label={`测试接收目标 (${confirmHealth.kind === ProviderKind.Email ? '邮箱地址' : '手机号码'})`}
              value={healthTestDestination}
              onChange={(e) => setHealthTestDestination(e.target.value)}
              placeholder={confirmHealth.kind === ProviderKind.Email ? 'admin-test@lovereply.app' : '13800138000'}
              required
            />
          )}

          <Input
            label="审计理由 (至少 8 个字符)"
            value={healthAuditReason}
            onChange={(e) => setHealthAuditReason(e.target.value)}
            placeholder="如：例行检查服务探针连接可用性"
            required
          />
        </div>
      </Dialog>

      {/* ── 6. 凭据轮换抽屉 ── */}
      <Drawer
        open={!!credentialProvider}
        title={`轮换凭据 - ${credentialProvider?.providerName}`}
        onClose={handleCloseCredential}
        footer={
          <>
            <Button variant="default" onClick={handleCloseCredential}>
              取消
            </Button>
            <Button
              variant="primary"
              onClick={handleCredentialSave}
              disabled={
                rotateCredentialsMutation.isPending ||
                Object.values(credentialValues).every((v) => !v.trim()) ||
                credentialAuditReason.trim().length < 8
              }
            >
              {rotateCredentialsMutation.isPending ? '保存中...' : '确认安全轮换凭据'}
            </Button>
          </>
        }
      >
        <div style={{ paddingBottom: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {credentialProvider && (
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              当前配置状态：{credentialProvider.credentialConfigured ? '✓ 已配置密钥' : '✕ 未配置密钥'}
            </div>
          )}

          {credentialProvider &&
            getCredentialKeys(credentialProvider).map((key) => (
              <Input
                key={key}
                label={key}
                type="password"
                value={credentialValues[key] || ''}
                onChange={(e) =>
                  setCredentialValues((prev) => ({ ...prev, [key]: e.target.value }))
                }
                placeholder="请输入新加密密钥（提交后清除）"
              />
            ))}

          <Input
            label="轮换审计理由 (至少 8 个字符)"
            value={credentialAuditReason}
            onChange={(e) => setCredentialAuditReason(e.target.value)}
            placeholder="如：三季度例行密钥轮换与泄露排查"
            required
          />

          <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
            提示：密钥只写不回显。提交完成后，密钥输入框与审计理由将自动清空。
          </div>
        </div>
      </Drawer>
    </div>
  );
};
