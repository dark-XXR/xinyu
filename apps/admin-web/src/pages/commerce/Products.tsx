/**
 * 商品与套餐版本页。
 * 支持创建/编辑草稿、发布与回滚、枚举选择器（ProductType/RenewalType/SalesChannel）。
 * 完整传输 AdminProductWriteRequest。
 * 所有操作使用真实 resourceVersion 作为 ifMatch。
 * 展示 isError/error 中文错误提示。
 */
import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { repository } from '../../api/repository';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { Dialog } from '../../components/ui/Dialog';
import { Input } from '../../components/ui/Input';
import {
  ProductType,
  SalesChannel,
  RenewalType,
  ProductPublicationStatus,
} from '../../api/models';
import type {
  AdminProductVersion,
  AdminProductWriteRequest,
  BenefitGrant,
} from '../../api/models';

/* ── 表单 DTO ── */

interface ProductFormDTO {
  productCode: string;
  displayName: string;
  description: string;
  productType: ProductType;
  currency: string;
  amountMinor: number;
  region: string;
  salesChannels: SalesChannel[];
  renewalType: RenewalType;
  termDays: number;
  benefitWindowDays: number;
  textQuota: number;
  visionQuota: number;
  energyAmount: number;
  auditReason: string;
}

function blankProductForm(): ProductFormDTO {
  return {
    productCode: '',
    displayName: '',
    description: '',
    productType: ProductType.Plan,
    currency: 'CNY',
    amountMinor: 0,
    region: 'CN',
    salesChannels: [SalesChannel.Android],
    renewalType: RenewalType.None,
    termDays: 30,
    benefitWindowDays: 30,
    textQuota: 0,
    visionQuota: 0,
    energyAmount: 0,
    auditReason: '',
  };
}

function productToForm(p: AdminProductVersion): ProductFormDTO {
  return {
    productCode: p.productCode ?? '',
    displayName: p.displayName ?? '',
    description: p.description ?? '',
    productType: p.productType ?? ProductType.Plan,
    currency: p.currency ?? 'CNY',
    amountMinor: p.amountMinor ?? 0,
    region: p.region ?? 'CN',
    salesChannels: p.salesChannels ? Array.from(p.salesChannels) : [SalesChannel.Android],
    renewalType: p.renewalType ?? RenewalType.None,
    termDays: p.termDays ?? 30,
    benefitWindowDays: p.benefitWindowDays ?? 30,
    textQuota: p.benefits?.textQuota ?? 0,
    visionQuota: p.benefits?.visionQuota ?? 0,
    energyAmount: p.benefits?.energyAmount ?? 0,
    auditReason: '',
  };
}

/* ── 产品类型中文标签 ── */

function productTypeLabel(t: ProductType): string {
  switch (t) {
    case ProductType.Plan: return '订阅套餐';
    case ProductType.EnergyPack: return '能量包';
    default: return String(t);
  }
}

function renewalTypeLabel(t: RenewalType): string {
  switch (t) {
    case RenewalType.None: return '不自动续费';
    case RenewalType.ProviderMandate: return '第三方授权扣费';
    default: return String(t);
  }
}

/* ── 页面组件 ── */

export const Products: React.FC = () => {
  const queryClient = useQueryClient();

  const {
    data: products = [],
    isLoading,
    isError,
    error: fetchError,
  } = useQuery({
    queryKey: ['products'],
    queryFn: () => repository.getProducts(),
  });

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<AdminProductVersion | null>(null);
  const [form, setForm] = useState<ProductFormDTO>(blankProductForm());
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [confirmPublish, setConfirmPublish] = useState<AdminProductVersion | null>(null);
  const [confirmRollback, setConfirmRollback] = useState<AdminProductVersion | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const drawerFocusRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (drawerOpen && drawerFocusRef.current) {
      const first = drawerFocusRef.current.querySelector<HTMLElement>('input, select');
      first?.focus();
    }
  }, [drawerOpen]);

  const saveMutation = useMutation({
    mutationFn: (params: { req: AdminProductWriteRequest; id?: string; rv?: number }) =>
      repository.saveProductDraft(params.req, params.id, params.rv),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setDrawerOpen(false);
      setMutationError(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
    },
  });

  const publishMutation = useMutation({
    mutationFn: (p: AdminProductVersion) =>
      repository.publishProduct(p.productVersionId, p.resourceVersion),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setConfirmPublish(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
      setConfirmPublish(null);
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (p: AdminProductVersion) => {
      const historyVersion = products
        .filter(item => item.productCode === p.productCode && (item.version ?? 1) < (p.version ?? 1))
        .sort((a, b) => (b.version ?? 1) - (a.version ?? 1))[0];
      if (!historyVersion || !historyVersion.productVersionId) {
        throw new Error('没有可用的历史版本进行回滚');
      }
      return repository.rollbackProduct(p.productCode ?? '', p.resourceVersion, historyVersion.productVersionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setConfirmRollback(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
      setConfirmRollback(null);
    },
  });

  const handleCreate = () => {
    setEditingProduct(null);
    setForm(blankProductForm());
    setMutationError(null);
    setDrawerOpen(true);
  };

  const handleEdit = (p: AdminProductVersion) => {
    setEditingProduct(p);
    setForm(productToForm(p));
    setMutationError(null);
    setDrawerOpen(true);
  };

  const handleSave = () => {
    if (!form.productCode.trim() || !form.displayName.trim()) {
      setMutationError('产品代码和名称不能为空');
      return;
    }
    const benefits: BenefitGrant = {
      textQuota: form.textQuota,
      visionQuota: form.visionQuota,
      energyAmount: form.energyAmount,
      allowedModelIds: new Set<string>(),
      allowedStyleIds: new Set<string>(),
      deepAnalysisEnabled: false,
    };
    const req: AdminProductWriteRequest = {
      productCode: form.productCode,
      displayName: form.displayName,
      description: form.description || undefined,
      productType: form.productType,
      currency: form.currency,
      amountMinor: form.amountMinor,
      benefits,
      region: form.region,
      salesChannels: new Set<SalesChannel>(form.salesChannels),
      renewalType: form.renewalType,
      termDays: form.termDays,
      benefitWindowDays: form.benefitWindowDays,
      auditReason: form.auditReason || '管理后台编辑',
    };
    saveMutation.mutate({
      req,
      id: editingProduct?.productVersionId,
      rv: editingProduct?.resourceVersion,
    });
  };

  const getStatusBadge = (status?: ProductPublicationStatus) => {
    switch (status) {
      case ProductPublicationStatus.Active: return <Badge variant="success">已发布</Badge>;
      case ProductPublicationStatus.Draft: return <Badge variant="warning">草稿</Badge>;
      case ProductPublicationStatus.Retired: return <Badge variant="default">已下架</Badge>;
      default: return <Badge variant="default">{status}</Badge>;
    }
  };

  const filteredProducts = products.filter((p) => {
    if (filterStatus && p.status !== filterStatus) return false;
    return true;
  });

  const formatAmount = (minor: number, currency: string) =>
    new Intl.NumberFormat('zh-CN', { style: 'currency', currency }).format(minor / 100);

  const handleChannelToggle = (ch: SalesChannel) => {
    setForm((prev) => {
      const has = prev.salesChannels.includes(ch);
      return {
        ...prev,
        salesChannels: has
          ? prev.salesChannels.filter((c) => c !== ch)
          : [...prev.salesChannels, ch],
      };
    });
  };

  return (
    <div>
      <div className="page-title-group" style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600 }}>商品与套餐</h1>
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>管理所有的付费计划与能量包</div>
      </div>
      <div className="toolbar" style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <select className="input" style={{ width: '200px' }} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">所有状态</option>
          <option value={ProductPublicationStatus.Active}>已发布</option>
          <option value={ProductPublicationStatus.Draft}>草稿</option>
          <option value={ProductPublicationStatus.Retired}>已下架</option>
        </select>
        <div style={{ flex: 1 }}></div>
        <Button ref={triggerRef} variant="primary" onClick={handleCreate}>
          新增商品
        </Button>
      </div>

      {mutationError && (
        <div style={{ background: 'var(--color-danger-bg, #fef2f2)', color: 'var(--color-danger)', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px' }}>
          操作失败：{mutationError}
          <button onClick={() => setMutationError(null)} style={{ marginLeft: '8px', border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', textDecoration: 'underline' }}>关闭</button>
        </div>
      )}

      <Card>
        {isLoading && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
        {isError && (
          <div style={{ color: 'var(--color-danger)', padding: '12px' }}>
            获取商品列表失败：{fetchError instanceof Error ? fetchError.message : String(fetchError)}
          </div>
        )}
        {!isLoading && !isError && (
          <div className="table-wrapper">
            <table className="responsive-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>商品名称</th>
                  <th>类型</th>
                  <th>价格</th>
                  <th>状态</th>
                  <th>版本</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((p) => {
                  const hasHistory = products.some(item => item.productCode === p.productCode && (item.version ?? 1) < (p.version ?? 1));
                  return (
                  <tr key={p.productVersionId}>
                    <td data-label="代码">{p.productCode}</td>
                    <td data-label="名称">{p.displayName}</td>
                    <td data-label="类型">{productTypeLabel(p.productType ?? ProductType.Plan)}</td>
                    <td data-label="价格">{formatAmount(p.amountMinor ?? 0, p.currency ?? 'CNY')}</td>
                    <td data-label="状态">{getStatusBadge(p.status)}</td>
                    <td data-label="版本">v{p.version ?? 1}</td>
                    <td data-label="操作">
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <Button variant="ghost" onClick={() => handleEdit(p)}>编辑</Button>
                        {p.status === ProductPublicationStatus.Draft && (
                          <Button variant="primary" onClick={() => setConfirmPublish(p)}>发布</Button>
                        )}
                        {p.status === ProductPublicationStatus.Active && (p.version ?? 1) > 1 && (
                          <Button variant="danger" onClick={() => setConfirmRollback(p)} disabled={!hasHistory} title={hasHistory ? '' : '没有可用的历史版本进行回滚'}>回滚</Button>
                        )}
                      </div>
                    </td>
                  </tr>
                )})}
                {filteredProducts.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-tertiary)' }}>
                      暂无数据
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
        title={editingProduct ? '编辑商品' : '新增商品'}
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
            label="产品代码"
            value={form.productCode}
            onChange={(e) => setForm((prev) => ({ ...prev, productCode: e.target.value }))}
            disabled={!!editingProduct}
          />
          <Input
            label="商品名称"
            value={form.displayName}
            onChange={(e) => setForm((prev) => ({ ...prev, displayName: e.target.value }))}
          />
          <Input
            label="描述 (可选)"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
          />

          {/* 产品类型枚举选择器 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
            <label style={{ fontSize: '13px', fontWeight: 500 }}>产品类型</label>
            <select className="input" value={form.productType} onChange={(e) => setForm((prev) => ({ ...prev, productType: e.target.value as ProductType }))}>
              {Object.values(ProductType).map((t) => (
                <option key={t} value={t}>{productTypeLabel(t)}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <div style={{ flex: 1 }}>
              <Input label="价格 (分)" type="number" value={form.amountMinor} onChange={(e) => setForm((prev) => ({ ...prev, amountMinor: parseInt(e.target.value, 10) || 0 }))} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
                <label style={{ fontSize: '13px', fontWeight: 500 }}>货币</label>
                <select className="input" value={form.currency} onChange={(e) => setForm((prev) => ({ ...prev, currency: e.target.value }))}>
                  <option value="CNY">CNY</option>
                  <option value="USD">USD</option>
                </select>
              </div>
            </div>
          </div>

          {/* 续费类型枚举选择器 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
            <label style={{ fontSize: '13px', fontWeight: 500 }}>续费类型</label>
            <select className="input" value={form.renewalType} onChange={(e) => setForm((prev) => ({ ...prev, renewalType: e.target.value as RenewalType }))}>
              {Object.values(RenewalType).map((t) => (
                <option key={t} value={t}>{renewalTypeLabel(t)}</option>
              ))}
            </select>
          </div>

          {/* 销售渠道多选 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
            <label style={{ fontSize: '13px', fontWeight: 500 }}>销售渠道</label>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {Object.values(SalesChannel).map((ch) => (
                <label key={ch} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.salesChannels.includes(ch)} onChange={() => handleChannelToggle(ch)} />
                  {ch}
                </label>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <div style={{ flex: 1 }}>
              <Input label="有效天数" type="number" value={form.termDays} onChange={(e) => setForm((prev) => ({ ...prev, termDays: parseInt(e.target.value, 10) || 30 }))} />
            </div>
            <div style={{ flex: 1 }}>
              <Input label="权益窗口天数" type="number" value={form.benefitWindowDays} onChange={(e) => setForm((prev) => ({ ...prev, benefitWindowDays: parseInt(e.target.value, 10) || 30 }))} />
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px', marginTop: '4px' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>权益配置</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ flex: 1 }}>
                <Input label="文本额度" type="number" value={form.textQuota} onChange={(e) => setForm((prev) => ({ ...prev, textQuota: parseInt(e.target.value, 10) || 0 }))} />
              </div>
              <div style={{ flex: 1 }}>
                <Input label="视觉额度" type="number" value={form.visionQuota} onChange={(e) => setForm((prev) => ({ ...prev, visionQuota: parseInt(e.target.value, 10) || 0 }))} />
              </div>
              <div style={{ flex: 1 }}>
                <Input label="能量" type="number" value={form.energyAmount} onChange={(e) => setForm((prev) => ({ ...prev, energyAmount: parseInt(e.target.value, 10) || 0 }))} />
              </div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px', marginTop: '12px' }}>
            <Input label="审计原因 (可选)" value={form.auditReason} onChange={(e) => setForm((prev) => ({ ...prev, auditReason: e.target.value }))} />
          </div>

          {mutationError && (
            <div style={{ color: 'var(--color-danger)', fontSize: '13px', marginTop: '8px' }}>{mutationError}</div>
          )}
        </div>
      </Drawer>

      {/* 发布确认 */}
      <Dialog
        open={!!confirmPublish}
        title="确认发布"
        onClose={() => setConfirmPublish(null)}
        footer={
          <>
            <Button variant="default" onClick={() => setConfirmPublish(null)}>取消</Button>
            <Button variant="primary" onClick={() => confirmPublish && publishMutation.mutate(confirmPublish)} disabled={publishMutation.isPending}>
              {publishMutation.isPending ? '发布中...' : '确认发布'}
            </Button>
          </>
        }
      >
        确定要发布「{confirmPublish?.displayName}」(v{confirmPublish?.version}) 吗？发布后此套餐的新版本将对用户可见。
      </Dialog>

      {/* 回滚确认 */}
      <Dialog
        open={!!confirmRollback}
        title="确认回滚"
        onClose={() => setConfirmRollback(null)}
        footer={
          <>
            <Button variant="default" onClick={() => setConfirmRollback(null)}>取消</Button>
            <Button variant="danger" onClick={() => confirmRollback && rollbackMutation.mutate(confirmRollback)} disabled={rollbackMutation.isPending}>
              {rollbackMutation.isPending ? '回滚中...' : '确认回滚'}
            </Button>
          </>
        }
      >
        确定要回滚「{confirmRollback?.displayName}」至上一版本 (v{(confirmRollback?.version ?? 1) - 1}) 吗？
      </Dialog>
    </div>
  );
};
