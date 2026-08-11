/**
 * 支付运营与主动对账页面。
 * 聚合第三方易支付 (EPAY_COMPAT) 供应商运行状态、真实回调 URL、动态订单/退款统计摘要。
 * 安全原则：密钥区域完全删除（接口本就不回显秘密）。
 * 提供主动对账表单 (staleBefore, maxOrders, 至少8字审计理由)。
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CreditCard,
  ExternalLink,
  RefreshCw,
  Play,
  CheckCircle2,
  AlertCircle,
  AlertOctagon,
  ShoppingBag,
  Clock,
  RotateCcw,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { Textarea } from '../../components/ui/Textarea';
import { repository } from '../../api/repository';
import {
  ProviderKind,
  EpayConfigurationAdapterTypeEnum,
  OrderStatus,
  RefundStatus,
  ProviderStatus,
} from '../../api/models';
import type {
  Provider,
  AdminOrder,
  AdminRefund,
  EpayConfiguration,
  PaymentReconciliation,
} from '../../api/models';

export const PaymentsPage: React.FC = () => {
  const navigate = useNavigate();

  // 数据加载状态
  const [dataLoading, setDataLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // 易支付供应商及配置
  const [epayProvider, setEpayProvider] = useState<Provider | null>(null);
  const [epayConfig, setEpayConfig] = useState<EpayConfiguration | null>(null);

  // 订单与退款真实/Mock 数据
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [refunds, setRefunds] = useState<AdminRefund[]>([]);

  // 操作反馈
  const [reconciliationLoading, setReconciliationLoading] = useState<boolean>(false);
  const [reconciliationError, setReconciliationError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 主动对账表单 state
  const [staleBefore, setStaleBefore] = useState<string>(
    new Date(Date.now() - 3600000).toISOString().slice(0, 16),
  );
  const [maxOrders, setMaxOrders] = useState<number>(50);
  const [auditReason, setAuditReason] = useState<string>('系统对账任务手动触发');
  const [reconciliationResult, setReconciliationResult] = useState<PaymentReconciliation | null>(null);

  // 检查并安全提取易支付配置
  const extractEpayConfig = (provider: Provider): EpayConfiguration | null => {
    if (provider.kind !== ProviderKind.Payment || !provider._configuration) {
      return null;
    }
    const cfg = provider._configuration;
    if (
      cfg.adapterType === EpayConfigurationAdapterTypeEnum.EpayCompat ||
      (cfg.adapterType as string) === 'EPAY_COMPAT'
    ) {
      return cfg as EpayConfiguration;
    }
    return null;
  };

  // 加载数据：异步获取供应商、订单、退款列表
  const loadData = async () => {
    setDataLoading(true);
    setFetchError(null);
    try {
      const [providersData, ordersData, refundsData] = await Promise.all([
        repository.getProviders(),
        repository.getOrders(),
        repository.getRefunds(),
      ]);

      setOrders(ordersData);
      setRefunds(refundsData);

      // 选择 kind=PAYMENT 且配置 adapterType=EPAY_COMPAT 的供应商
      let foundProv: Provider | null = null;
      let foundCfg: EpayConfiguration | null = null;

      for (const p of providersData) {
        const cfg = extractEpayConfig(p);
        if (cfg) {
          foundProv = p;
          foundCfg = cfg;
          break;
        }
      }

      setEpayProvider(foundProv);
      setEpayConfig(foundCfg);
    } catch (err: unknown) {
      setFetchError(err instanceof Error ? err.message : '加载支付网关及运营数据失败');
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // 执行主动对账任务
  const handleRunReconciliation = async (e: React.FormEvent) => {
    e.preventDefault();
    setReconciliationLoading(true);
    setReconciliationError(null);
    setReconciliationResult(null);
    try {
      const res = await repository.runPaymentReconciliation(
        staleBefore,
        maxOrders,
        auditReason.trim(),
      );
      setReconciliationResult(res);
      setSuccessMsg(`对账任务执行成功，批次单号: ${res.reconciliationId}`);
      // 对账完成后刷新列表
      loadData();
    } catch (err: unknown) {
      setReconciliationError(err instanceof Error ? err.message : '主动对账任务执行失败');
    } finally {
      setReconciliationLoading(false);
    }
  };

  const isReasonValid = auditReason.trim().length >= 8;
  const canRunReconciliation = isReasonValid && maxOrders >= 1 && maxOrders <= 500 && !reconciliationLoading;

  // 格式化支付方式文本
  const formatPaymentTypes = (typesSet?: Set<string> | Array<string>) => {
    if (!typesSet) return '未配置支付方式';
    const list = Array.from(typesSet);
    if (list.length === 0) return '未启用任何支付方式';
    return list
      .map((t) => {
        if (t === 'ALIPAY') return '支付宝 (ALIPAY)';
        if (t === 'WECHAT_PAY') return '微信支付 (WECHAT_PAY)';
        return t;
      })
      .join('、');
  };

  // 动态统计计算（明确口径）
  const totalOrdersCount = orders.length;
  const paidOrdersCount = orders.filter(
    (o) => o.order.status === OrderStatus.Paid || (o.order.status as string) === 'PAID',
  ).length;
  const pendingOrdersCount = orders.filter(
    (o) => o.order.status === OrderStatus.Created || (o.order.status as string) === 'CREATED',
  ).length;
  const pendingRefundsCount = refunds.filter(
    (r) => r.status === RefundStatus.Requested || (r.status as string) === 'REQUESTED',
  ).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部标题与操作 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)' }}>支付运营与主动对账</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            监控第三方易支付 (EPAY_COMPAT) 通道状态、核验支付回调 URL、发起单批次补单与漏单主动对账。
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <Button variant="default" onClick={loadData} disabled={dataLoading}>
            <RefreshCw size={14} className={dataLoading ? 'spin' : ''} /> 刷新数据
          </Button>
          <Button variant="primary" onClick={() => navigate('/providers')}>
            <ExternalLink size={14} /> 供应商配置 (/providers)
          </Button>
        </div>
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', background: 'var(--color-success-bg)', color: 'var(--color-success)', borderRadius: 'var(--radius-sm)', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>
      )}

      {fetchError && (
        <Card style={{ borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--color-danger)' }}>
            <AlertOctagon size={18} />
            <div style={{ flex: 1, fontSize: '13px' }}>{fetchError}</div>
            <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={loadData}>重试</Button>
          </div>
        </Card>
      )}

      {reconciliationError && (
        <Card style={{ borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--color-danger)' }}>
            <AlertCircle size={18} />
            <div style={{ flex: 1, fontSize: '13px' }}>{reconciliationError}</div>
          </div>
        </Card>
      )}

      {/* Loading 状态 */}
      {dataLoading && !epayProvider && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '30px', color: 'var(--color-text-secondary)', fontSize: '14px' }}>
            <RefreshCw size={18} className="spin" /> 正在加载支付网关与交易数据...
          </div>
        </Card>
      )}

      {/* 空网关配置状态：提示用户前往配置，绝不显示写死硬编码假数据 */}
      {!dataLoading && !epayProvider && (
        <Card style={{ borderColor: 'var(--color-warning)', background: '#fffbe6' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '14px', color: 'var(--color-warning)' }}>
              <AlertCircle size={18} /> 未检测到易支付 (EPAY_COMPAT) 供应商配置
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              当前系统尚未配置类型为 EPAY_COMPAT 且分类为 PAYMENT 的支付供应商。系统无法发起在线扫码及回调处理。
            </div>
            <Button variant="primary" onClick={() => navigate('/providers')} style={{ marginTop: '4px' }}>
              <ExternalLink size={14} /> 前往供应商管理页面添加支付配置
            </Button>
          </div>
        </Card>
      )}

      {/* 真实易支付 (Epay) 运行状态概览卡片（删除所有 API Key / 签名密钥硬编码遮罩） */}
      {!dataLoading && epayProvider && epayConfig && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '14px' }}>
              <CreditCard size={18} style={{ color: 'var(--color-primary)' }} />
              聚合易支付通道状态: <strong>{epayProvider.providerName}</strong>
            </div>
            <Badge variant={epayProvider.status === ProviderStatus.Active ? 'success' : 'warning'}>
              {epayProvider.status === ProviderStatus.Active ? '通道运行正常' : `状态: ${epayProvider.status}`}
            </Badge>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', fontSize: '13px' }}>
            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>商户号 (Merchant ID)</div>
              <div style={{ fontWeight: 600, marginTop: '2px', fontFamily: 'monospace' }}>
                {epayConfig.merchantId || '未设置'}
              </div>
            </div>

            {epayConfig.applicationId && (
              <div>
                <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>应用 ID (App ID)</div>
                <div style={{ fontWeight: 500, marginTop: '2px', fontFamily: 'monospace' }}>
                  {epayConfig.applicationId}
                </div>
              </div>
            )}

            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>已启用支付方式</div>
              <div style={{ fontWeight: 500, marginTop: '2px' }}>
                {formatPaymentTypes(epayConfig.paymentTypes)}
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>网关 Base URL</div>
              <div style={{ fontSize: '12px', marginTop: '2px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                {epayConfig.gatewayBaseUrl || '未设置'}
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>异步通知回调 URL (Notify)</div>
              <div style={{ fontSize: '12px', marginTop: '2px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                {epayConfig.notifyUrl || '未配置服务器回调'}
              </div>
            </div>

            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>同步前端返回 URL (Return)</div>
              <div style={{ fontSize: '12px', marginTop: '2px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                {epayConfig.returnUrl || '未配置跳转链接'}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 动态聚合统计指标 (彻底清除写死 148 笔、99.3%、1 笔假数据) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <Card style={{ background: 'var(--color-surface-sub)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
            <ShoppingBag size={14} /> 订单总笔数 (数据源动态)
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '6px' }}>
            {totalOrdersCount} <span style={{ fontSize: '12px', fontWeight: 400 }}>笔</span>
          </div>
        </Card>

        <Card style={{ background: 'var(--color-surface-sub)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
            <CheckCircle2 size={14} style={{ color: 'var(--color-success)' }} /> 已完成/已支付订单
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-success)', marginTop: '6px' }}>
            {paidOrdersCount} <span style={{ fontSize: '12px', fontWeight: 400 }}>笔</span>
          </div>
        </Card>

        <Card style={{ background: 'var(--color-surface-sub)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
            <Clock size={14} style={{ color: 'var(--color-warning)' }} /> 待支付/处理中订单
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-warning)', marginTop: '6px' }}>
            {pendingOrdersCount} <span style={{ fontSize: '12px', fontWeight: 400 }}>笔</span>
          </div>
        </Card>

        <Card style={{ background: 'var(--color-surface-sub)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
            <RotateCcw size={14} style={{ color: 'var(--color-danger)' }} /> 待处理退款申请
          </div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-danger)', marginTop: '6px' }}>
            {pendingRefundsCount} <span style={{ fontSize: '12px', fontWeight: 400 }}>笔</span>
          </div>
        </Card>
      </div>

      {/* 主动对账表单卡片 */}
      <Card>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Play size={16} /> 触发主动补单与延迟订单对账
        </h3>

        <form onSubmit={handleRunReconciliation} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                截止停滞时间 (Stale Before) *
              </label>
              <Input
                type="datetime-local"
                value={staleBefore}
                onChange={(e) => setStaleBefore(e.target.value)}
                required
              />
              <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                仅扫描在该时间前发起但尚未确认支付完成的订单
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                单次最大扫描订单笔数 (Max Orders) *
              </label>
              <Input
                type="number"
                min={1}
                max={500}
                value={maxOrders}
                onChange={(e) => setMaxOrders(parseInt(e.target.value, 10) || 1)}
                required
              />
              <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                后端对账接口单批次允许范围: 1 - 500 笔
              </div>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              对账审计理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
            </label>
            <Textarea
              placeholder="请输入手动触发主动对账的明确审计原因（例如：例行维护后补算充值延迟订单）"
              value={auditReason}
              onChange={(e) => setAuditReason(e.target.value)}
              rows={2}
            />
            <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
              当前字数: {auditReason.trim().length} / 至少 8 字
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button variant="primary" type="submit" disabled={!canRunReconciliation}>
              <RefreshCw size={14} className={reconciliationLoading ? 'spin' : ''} />
              {reconciliationLoading ? '对账执行中...' : '开始执行对账'}
            </Button>
          </div>
        </form>
      </Card>

      {/* 对账结果卡片 */}
      {reconciliationResult && (
        <Card style={{ borderColor: 'var(--color-success)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '14px', marginBottom: '12px', color: 'var(--color-success)' }}>
            <CheckCircle2 size={18} />
            主动对账批次完成通知
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', fontSize: '13px' }}>
            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>批次任务 ID</div>
              <div style={{ fontWeight: 600, marginTop: '2px', fontFamily: 'monospace' }}>{reconciliationResult.reconciliationId}</div>
            </div>
            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>扫描订单总笔数</div>
              <div style={{ fontWeight: 600, marginTop: '2px' }}>{reconciliationResult.scannedCount} 笔</div>
            </div>
            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>成功平账笔数</div>
              <div style={{ fontWeight: 600, marginTop: '2px', color: 'var(--color-success)' }}>{reconciliationResult.settledCount} 笔</div>
            </div>
            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>成功补发权益数</div>
              <div style={{ fontWeight: 600, marginTop: '2px', color: 'var(--color-primary)' }}>{reconciliationResult.recoveredCount} 笔</div>
            </div>
            <div>
              <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>对账异常冲突数</div>
              <div style={{ fontWeight: 600, marginTop: '2px' }}>{reconciliationResult.conflictCount} 笔</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
