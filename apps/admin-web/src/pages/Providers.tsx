/**
 * 供应商管理页面。
 * 支持创建/编辑草稿、按类型切换配置表单、发布与回滚操作。
 * 秘密密钥仅在创建时输入，不在表单回显。
 * 所有操作传入真实 resourceVersion 作为 ifMatch。
 * 完整展示 isError/error 中文错误提示。
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
import { Activity, KeyRound } from 'lucide-react';
import {
  ProviderKind,
  ProviderStatus,
  OpenAiCompatibleConfigurationAdapterTypeEnum,
  SmtpConfigurationAdapterTypeEnum,
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
  SmtpConfiguration,
  SmsConfiguration,
  EpayConfiguration,
  CredentialName,
  CredentialSecretInput,
} from '../api/models';

/* ── 表单 DTO 定义 ── */

interface ProviderFormDTO {
  providerName: string;
  kind: ProviderKind;
  retryLimit: number;
  priority: number;
  /* AI 配置字段 */
  ai_baseUrl: string;
  ai_timeoutMs: number;
  /* SMTP 配置字段 */
  smtp_host: string;
  smtp_port: number;
  smtp_tlsMode: TlsMode;
  smtp_senderAddress: string;
  smtp_senderName: string;
  smtp_timeoutMs: number;
  /* SMS 配置字段 */
  sms_region: string;
  sms_signatureId: string;
  sms_templateId: string;
  sms_timeoutMs: number;
  /* Epay 配置字段 */
  epay_gatewayBaseUrl: string;
  epay_submitPath: string;
  epay_queryPath: string;
  epay_refundPath: string;
  epay_merchantId: string;
  epay_notifyUrl: string;
  epay_returnUrl: string;
  epay_callbackAckText: string;
  epay_callbackTimeWindowSeconds: number;
  epay_checkoutTtlSeconds: number;
  epay_timeoutMs: number;
  /* 审计原因 */
  auditReason: string;
}

/** 返回空白表单 DTO */
function blankForm(): ProviderFormDTO {
  return {
    providerName: '',
    kind: ProviderKind.Ai,
    retryLimit: 3,
    priority: 1,
    ai_baseUrl: 'https://api.openai.com/v1',
    ai_timeoutMs: 30000,
    smtp_host: '',
    smtp_port: 465,
    smtp_tlsMode: TlsMode.Implicit,
    smtp_senderAddress: '',
    smtp_senderName: '',
    smtp_timeoutMs: 10000,
    sms_region: '',
    sms_signatureId: '',
    sms_templateId: '',
    sms_timeoutMs: 5000,
    epay_gatewayBaseUrl: '',
    epay_submitPath: '/submit',
    epay_queryPath: '/query',
    epay_refundPath: '/refund',
    epay_merchantId: '',
    epay_notifyUrl: '',
    epay_returnUrl: '',
    epay_callbackAckText: 'success',
    epay_callbackTimeWindowSeconds: 300,
    epay_checkoutTtlSeconds: 900,
    epay_timeoutMs: 10000,
    auditReason: '',
  };
}

/** 从 Provider 模型填充表单 DTO（编辑时使用，不回显秘密密钥） */
function providerToForm(p: Provider): ProviderFormDTO {
  const base = blankForm();
  base.providerName = p.providerName;
  base.kind = p.kind;
  base.retryLimit = p.retryLimit;
  base.priority = p.priority;

  const cfg = p._configuration;
  if (cfg) {
    if ('baseUrl' in cfg) {
      const c = cfg as OpenAiCompatibleConfiguration;
      base.ai_baseUrl = c.baseUrl ?? '';
      base.ai_timeoutMs = c.timeoutMs ?? 30000;
    }
    if ('host' in cfg) {
      const c = cfg as SmtpConfiguration;
      base.smtp_host = c.host ?? '';
      base.smtp_port = c.port ?? 465;
      base.smtp_tlsMode = c.tlsMode ?? TlsMode.Implicit;
      base.smtp_senderAddress = c.senderAddress ?? '';
      base.smtp_senderName = c.senderName ?? '';
      base.smtp_timeoutMs = c.timeoutMs ?? 10000;
    }
    if ('signatureId' in cfg) {
      const c = cfg as SmsConfiguration;
      base.sms_region = c.region ?? '';
      base.sms_signatureId = c.signatureId ?? '';
      base.sms_templateId = c.templateId ?? '';
      base.sms_timeoutMs = c.timeoutMs ?? 5000;
    }
    if ('merchantId' in cfg) {
      const c = cfg as EpayConfiguration;
      base.epay_gatewayBaseUrl = c.gatewayBaseUrl ?? '';
      base.epay_submitPath = c.submitPath ?? '';
      base.epay_queryPath = c.queryPath ?? '';
      base.epay_refundPath = c.refundPath ?? '';
      base.epay_merchantId = c.merchantId ?? '';
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

/** 拆分的配置构造函数 */
function buildAi(form: ProviderFormDTO): OpenAiCompatibleConfiguration {
  return {
    adapterType: OpenAiCompatibleConfigurationAdapterTypeEnum.OpenaiCompat,
    baseUrl: form.ai_baseUrl,
    timeoutMs: form.ai_timeoutMs,
  };
}

function buildEmail(form: ProviderFormDTO): SmtpConfiguration {
  return {
    adapterType: SmtpConfigurationAdapterTypeEnum.Smtp,
    host: form.smtp_host,
    port: form.smtp_port,
    tlsMode: form.smtp_tlsMode,
    senderAddress: form.smtp_senderAddress,
    senderName: form.smtp_senderName,
    timeoutMs: form.smtp_timeoutMs,
  };
}

function buildSms(form: ProviderFormDTO): SmsConfiguration {
  return {
    adapterType: SmsConfigurationAdapterTypeEnum.AliyunSms,
    region: form.sms_region,
    signatureId: form.sms_signatureId,
    templateId: form.sms_templateId,
    timeoutMs: form.sms_timeoutMs,
  };
}

function buildEpay(form: ProviderFormDTO): EpayConfiguration {
  return {
    adapterType: EpayConfigurationAdapterTypeEnum.EpayCompat,
    gatewayBaseUrl: form.epay_gatewayBaseUrl,
    submitPath: form.epay_submitPath,
    queryPath: form.epay_queryPath,
    refundPath: form.epay_refundPath,
    merchantId: form.epay_merchantId,
    paymentTypes: new Set<EpayConfigurationPaymentTypesEnum>([
      EpayConfigurationPaymentTypesEnum.Alipay,
      EpayConfigurationPaymentTypesEnum.WechatPay,
    ]),
    signingPreset: EpayConfigurationSigningPresetEnum.EpayMd5Canonical,
    callbackAckText: form.epay_callbackAckText,
    notifyUrl: form.epay_notifyUrl,
    returnUrl: form.epay_returnUrl,
    callbackTimeWindowSeconds: form.epay_callbackTimeWindowSeconds,
    checkoutTtlSeconds: form.epay_checkoutTtlSeconds,
    timeoutMs: form.epay_timeoutMs,
  };
}

/** 从表单 DTO 构造 ProviderConfiguration */
function buildConfiguration(form: ProviderFormDTO): ProviderConfiguration {
  switch (form.kind) {
    case ProviderKind.Ai: return buildAi(form);
    case ProviderKind.Email: return buildEmail(form);
    case ProviderKind.Sms: return buildSms(form);
    case ProviderKind.Payment: return buildEpay(form);
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

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Provider | null>(null);
  const [form, setForm] = useState<ProviderFormDTO>(blankForm());
  const [confirmPublish, setConfirmPublish] = useState<Provider | null>(null);
  const [confirmRollback, setConfirmRollback] = useState<Provider | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [filterKeyword, setFilterKeyword] = useState('');
  const [filterKind, setFilterKind] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [credentialProvider, setCredentialProvider] = useState<Provider | null>(null);
  const [credentialValues, setCredentialValues] = useState<Record<string, string>>({});

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

  const saveMutation = useMutation({
    mutationFn: (params: { req: ProviderWriteRequest; id?: string; rv?: number }) =>
      repository.saveProviderDraft(params.req, params.id, params.rv),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      setDrawerOpen(false);
      setMutationError(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const publishMutation = useMutation({
    mutationFn: (p: Provider) => repository.publishProvider(p.providerId, p.resourceVersion),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      setConfirmPublish(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
      setConfirmPublish(null);
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (p: Provider) => repository.rollbackProvider(p.providerId, p.resourceVersion, p.resourceVersion - 1),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      setConfirmRollback(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
      setConfirmRollback(null);
    },
  });

  const checkHealthMutation = useMutation({
    mutationFn: (p: Provider) => repository.checkProviderHealth(p.providerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['providers'] }),
    onError: (err: unknown) => setMutationError(err instanceof Error ? err.message : String(err)),
  });

  const rotateCredentialsMutation = useMutation({
    mutationFn: (params: { p: Provider; secrets: CredentialSecretInput[] }) =>
      repository.rotateProviderCredentials(params.p.providerId, params.p.resourceVersion, params.secrets, '配置密钥'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      setCredentialProvider(null);
      setCredentialValues({});
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

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
    const req: ProviderWriteRequest = {
      providerName: form.providerName,
      kind: form.kind,
      _configuration: buildConfiguration(form),
      retryLimit: form.retryLimit,
      priority: form.priority,
    };
    saveMutation.mutate({
      req,
      id: editingProvider?.providerId,
      rv: editingProvider?.resourceVersion,
    });
  };

  const getStatusBadge = (status: ProviderStatus) => {
    switch (status) {
      case ProviderStatus.Active: return <Badge variant="success">在线</Badge>;
      case ProviderStatus.Draft: return <Badge variant="warning">草稿</Badge>;
      case ProviderStatus.Disabled: return <Badge variant="danger">已禁用</Badge>;
      case ProviderStatus.Superseded: return <Badge variant="default">已替换</Badge>;
      default: return <Badge variant="default">{status}</Badge>;
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

  const handleCredentialSave = () => {
    if (!credentialProvider) return;
    const secrets: CredentialSecretInput[] = Object.entries(credentialValues)
      .filter(([_, v]) => v.trim() !== '')
      .map(([k, v]) => ({ name: k as CredentialName, value: v }));
    if (secrets.length === 0) {
      setMutationError('至少需要输入一项凭据');
      return;
    }
    rotateCredentialsMutation.mutate({ p: credentialProvider, secrets });
  };

  const getCredentialKeys = (kind: ProviderKind): CredentialName[] => {
    switch(kind) {
      case ProviderKind.Ai: return ['apiKey' as CredentialName];
      case ProviderKind.Email: return ['username' as CredentialName, 'password' as CredentialName];
      case ProviderKind.Sms: return ['accessKeyId' as CredentialName, 'accessKeySecret' as CredentialName];
      case ProviderKind.Payment: return ['merchantKey' as CredentialName];
      default: return [];
    }
  };

  return (
    <div>
      <div className="page-title-group" style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600 }}>供应商配置</h1>
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>管理外部服务和网关凭据</div>
      </div>

      <div className="toolbar" style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <Input placeholder="搜索供应商名称/ID" value={filterKeyword} onChange={e => setFilterKeyword(e.target.value)} style={{ width: '240px', marginBottom: 0 }} />
        <select className="input" style={{ width: 'auto' }} value={filterKind} onChange={e => setFilterKind(e.target.value)}>
          <option value="">所有类型</option>
          {Object.values(ProviderKind).map(k => <option key={k} value={k}>{kindLabel(k)}</option>)}
        </select>
        <select className="input" style={{ width: 'auto' }} value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">所有状态</option>
          {Object.values(ProviderStatus).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <div style={{ flex: 1 }}></div>
        <Button ref={triggerRef} variant="primary" onClick={handleCreate}>
          新增供应商
        </Button>
      </div>

      {mutationError && (
        <div style={{ background: 'var(--color-danger-bg, #fef2f2)', color: 'var(--color-danger)', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px' }}>
          操作失败：{mutationError}
          <button onClick={() => setMutationError(null)} style={{ marginLeft: '8px', border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', textDecoration: 'underline' }}>
            关闭
          </button>
        </div>
      )}

      <Card>
        {isLoading && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
        {isError && (
          <div style={{ color: 'var(--color-danger)', padding: '12px' }}>
            获取供应商列表失败：{fetchError instanceof Error ? fetchError.message : String(fetchError)}
          </div>
        )}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table className="responsive-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>优先级</th>
                  <th>版本</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredProviders.map((p) => (
                  <tr key={p.providerId}>
                    <td data-label="名称">{p.providerName}</td>
                    <td data-label="类型">{kindLabel(p.kind)}</td>
                    <td data-label="状态">{getStatusBadge(p.status)}</td>
                    <td data-label="优先级">{p.priority}</td>
                    <td data-label="版本">v{p.resourceVersion}</td>
                    <td data-label="操作">
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <Button variant="ghost" onClick={() => handleEdit(p)}>编辑</Button>
                        <Button variant="ghost" onClick={() => checkHealthMutation.mutate(p)} disabled={checkHealthMutation.isPending} title="健康检查">
                          <Activity size={14} /> <span className="hide-on-mobile">健康检查</span>
                        </Button>
                        <Button variant="ghost" onClick={() => setCredentialProvider(p)} title="凭据">
                          <KeyRound size={14} /> <span className="hide-on-mobile">凭据</span>
                        </Button>
                        {p.status === ProviderStatus.Draft && (
                          <Button variant="primary" onClick={() => setConfirmPublish(p)}>发布</Button>
                        )}
                        {p.status === ProviderStatus.Active && p.resourceVersion > 1 && (
                          <Button variant="danger" onClick={() => setConfirmRollback(p)}>回滚</Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredProviders.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-tertiary)' }}>
                      暂无供应商配置
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 编辑/新增抽屉 */}
      <Drawer
        open={drawerOpen}
        title={editingProvider ? `编辑供应商 - ${editingProvider.providerName}` : '新增供应商'}
        onClose={() => setDrawerOpen(false)}
        returnFocusRef={triggerRef}
        footer={
          <>
            <Button variant="default" onClick={() => setDrawerOpen(false)}>取消</Button>
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
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
            <label style={{ fontSize: '13px', fontWeight: 500 }}>种类</label>
            <select
              className="input"
              value={form.kind}
              onChange={(e) => updateField('kind', e.target.value as ProviderKind)}
              disabled={!!editingProvider}
            >
              {Object.values(ProviderKind).map((k) => (
                <option key={k} value={k}>{kindLabel(k)}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <div style={{ flex: 1 }}>
              <Input label="重试次数" type="number" value={form.retryLimit} onChange={(e) => updateField('retryLimit', parseInt(e.target.value, 10) || 0)} />
            </div>
            <div style={{ flex: 1 }}>
              <Input label="优先级" type="number" value={form.priority} onChange={(e) => updateField('priority', parseInt(e.target.value, 10) || 1)} />
            </div>
          </div>

          {/* 按种类显示不同配置字段 */}
          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px', marginTop: '4px' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>
              {kindLabel(form.kind)} 配置
            </div>

            {form.kind === ProviderKind.Ai && (
              <>
                <Input label="Base URL" value={form.ai_baseUrl} onChange={(e) => updateField('ai_baseUrl', e.target.value)} />
                <Input label="超时 (ms)" type="number" value={form.ai_timeoutMs} onChange={(e) => updateField('ai_timeoutMs', parseInt(e.target.value, 10) || 30000)} />
              </>
            )}

            {form.kind === ProviderKind.Email && (
              <>
                <Input label="SMTP 主机" value={form.smtp_host} onChange={(e) => updateField('smtp_host', e.target.value)} />
                <div style={{ display: 'flex', gap: '8px' }}>
                  <div style={{ flex: 1 }}>
                    <Input label="端口" type="number" value={form.smtp_port} onChange={(e) => updateField('smtp_port', parseInt(e.target.value, 10) || 465)} />
                  </div>
                  <div style={{ flex: 1 }}>
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
                <Input label="发件人地址" value={form.smtp_senderAddress} onChange={(e) => updateField('smtp_senderAddress', e.target.value)} />
                <Input label="发件人名称" value={form.smtp_senderName} onChange={(e) => updateField('smtp_senderName', e.target.value)} />
                <Input label="超时 (ms)" type="number" value={form.smtp_timeoutMs} onChange={(e) => updateField('smtp_timeoutMs', parseInt(e.target.value, 10) || 10000)} />
              </>
            )}

            {form.kind === ProviderKind.Sms && (
              <>
                <Input label="区域" value={form.sms_region} onChange={(e) => updateField('sms_region', e.target.value)} />
                <Input label="签名 ID" value={form.sms_signatureId} onChange={(e) => updateField('sms_signatureId', e.target.value)} />
                <Input label="模板 ID" value={form.sms_templateId} onChange={(e) => updateField('sms_templateId', e.target.value)} />
                <Input label="超时 (ms)" type="number" value={form.sms_timeoutMs} onChange={(e) => updateField('sms_timeoutMs', parseInt(e.target.value, 10) || 5000)} />
              </>
            )}

            {form.kind === ProviderKind.Payment && (
              <>
                <Input label="支付网关 URL" value={form.epay_gatewayBaseUrl} onChange={(e) => updateField('epay_gatewayBaseUrl', e.target.value)} />
                <div style={{ display: 'flex', gap: '8px' }}>
                  <div style={{ flex: 1 }}><Input label="提交路径" value={form.epay_submitPath} onChange={(e) => updateField('epay_submitPath', e.target.value)} /></div>
                  <div style={{ flex: 1 }}><Input label="查询路径" value={form.epay_queryPath} onChange={(e) => updateField('epay_queryPath', e.target.value)} /></div>
                  <div style={{ flex: 1 }}><Input label="退款路径" value={form.epay_refundPath} onChange={(e) => updateField('epay_refundPath', e.target.value)} /></div>
                </div>
                <Input label="商户 ID" value={form.epay_merchantId} onChange={(e) => updateField('epay_merchantId', e.target.value)} />
                <Input label="通知 URL" value={form.epay_notifyUrl} onChange={(e) => updateField('epay_notifyUrl', e.target.value)} />
                <Input label="返回 URL" value={form.epay_returnUrl} onChange={(e) => updateField('epay_returnUrl', e.target.value)} />
                <Input label="回调确认文本" value={form.epay_callbackAckText} onChange={(e) => updateField('epay_callbackAckText', e.target.value)} />
                <div style={{ display: 'flex', gap: '8px' }}>
                  <div style={{ flex: 1 }}><Input label="回调时间窗 (秒)" type="number" value={form.epay_callbackTimeWindowSeconds} onChange={(e) => updateField('epay_callbackTimeWindowSeconds', parseInt(e.target.value, 10) || 300)} /></div>
                  <div style={{ flex: 1 }}><Input label="结账 TTL (秒)" type="number" value={form.epay_checkoutTtlSeconds} onChange={(e) => updateField('epay_checkoutTtlSeconds', parseInt(e.target.value, 10) || 900)} /></div>
                </div>
                <Input label="超时 (ms)" type="number" value={form.epay_timeoutMs} onChange={(e) => updateField('epay_timeoutMs', parseInt(e.target.value, 10) || 10000)} />
              </>
            )}
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px', marginTop: '12px' }}>
            <Input label="审计原因 (可选)" value={form.auditReason} onChange={(e) => updateField('auditReason', e.target.value)} />
          </div>

          {mutationError && (
            <div style={{ color: 'var(--color-danger)', fontSize: '13px', marginTop: '8px' }}>
              {mutationError}
            </div>
          )}
        </div>
      </Drawer>

      {/* 发布确认 */}
      <Dialog
        open={!!confirmPublish}
        title="确认发布供应商"
        onClose={() => setConfirmPublish(null)}
        footer={
          <>
            <Button variant="default" onClick={() => setConfirmPublish(null)}>取消</Button>
            <Button
              variant="primary"
              onClick={() => confirmPublish && publishMutation.mutate(confirmPublish)}
              disabled={publishMutation.isPending}
            >
              {publishMutation.isPending ? '发布中...' : '确认发布'}
            </Button>
          </>
        }
      >
        确定要发布「{confirmPublish?.providerName}」(v{confirmPublish?.resourceVersion}) 吗？
      </Dialog>

      {/* 回滚确认 */}
      <Dialog
        open={!!confirmRollback}
        title="确认回滚供应商"
        onClose={() => setConfirmRollback(null)}
        footer={
          <>
            <Button variant="default" onClick={() => setConfirmRollback(null)}>取消</Button>
            <Button
              variant="danger"
              onClick={() => confirmRollback && rollbackMutation.mutate(confirmRollback)}
              disabled={rollbackMutation.isPending}
            >
              {rollbackMutation.isPending ? '回滚中...' : '确认回滚'}
            </Button>
          </>
        }
      >
        确定要回滚「{confirmRollback?.providerName}」至上一版本 (v{confirmRollback ? confirmRollback.resourceVersion - 1 : 0}) 吗？
      </Dialog>

      {/* 凭据配置抽屉 */}
      <Drawer
        open={!!credentialProvider}
        title={`配置凭据 - ${credentialProvider?.providerName}`}
        onClose={() => { setCredentialProvider(null); setCredentialValues({}); }}
        footer={
          <>
            <Button variant="default" onClick={() => { setCredentialProvider(null); setCredentialValues({}); }}>取消</Button>
            <Button variant="primary" onClick={handleCredentialSave} disabled={rotateCredentialsMutation.isPending}>
              {rotateCredentialsMutation.isPending ? '保存中...' : '保存凭据'}
            </Button>
          </>
        }
      >
        <div style={{ paddingBottom: '20px' }}>
          {credentialProvider && (
            <div style={{ marginBottom: '16px', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              状态：{credentialProvider.credentialConfigured ? '已配置' : '未配置'}
            </div>
          )}
          {credentialProvider && getCredentialKeys(credentialProvider.kind).map(key => (
            <div key={key} style={{ marginBottom: '12px' }}>
              <Input
                label={key}
                type="password"
                value={credentialValues[key] || ''}
                onChange={e => setCredentialValues(prev => ({ ...prev, [key]: e.target.value }))}
                placeholder="输入新凭据"
              />
            </div>
          ))}
          <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)', marginTop: '8px' }}>
            提示：至少输入一项才能提交。为了安全，现有凭据值不会被显示。
          </div>
        </div>
      </Drawer>
    </div>
  );
};
