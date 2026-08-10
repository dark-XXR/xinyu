/**
 * 首页仪表盘页面。
 * 展示系统健康状态、待处理订单/退款数、快捷操作入口。
 * 使用 useQuery 获取数据，展示 isError 错误提示。
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { repository } from '../api/repository';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const { data: health, isLoading: healthLoading, isError: healthError, error: healthErr } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: () => repository.getSystemHealth(),
  });

  const { data: providers = [], isLoading: providersLoading } = useQuery({
    queryKey: ['providers'],
    queryFn: () => repository.getProviders(),
  });

  const { data: products = [], isLoading: productsLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => repository.getProducts(),
  });

  const { data: orders = [], isLoading: ordersLoading, isError: ordersError, error: ordersErr } = useQuery({
    queryKey: ['orders'],
    queryFn: () => repository.getOrders(),
  });

  const { data: refunds = [], isLoading: refundsLoading, isError: refundsError, error: refundsErr } = useQuery({
    queryKey: ['refunds'],
    queryFn: () => repository.getRefunds(),
  });

  const pendingOrders = orders.filter((o) => o.order.status === 'CREATED').length;
  const pendingRefunds = refunds.filter((r) => r.status === 'REQUESTED').length;
  const activeProducts = products.filter((p) => p.status === 'ACTIVE').length;

  /** 渲染错误提示 */
  const renderError = (label: string, err: unknown) => (
    <div style={{ color: 'var(--color-danger)', fontSize: '13px', padding: '8px 0' }}>
      {label}：{err instanceof Error ? err.message : String(err)}
    </div>
  );

  // 合并最近活动
  const activities = [
    ...providers.map(p => ({ id: p.providerId, type: '供应商', name: p.providerName, status: p.status, time: p.updatedAt || p.createdAt })),
    ...products.map(p => ({ id: p.productVersionId, type: '商品', name: p.displayName, status: p.status, time: p.updatedAt || p.createdAt })),
    ...orders.map(o => ({ id: o.order.orderId, type: '订单', name: o.order.orderId, status: o.order.status, time: o.order.updatedAt || o.order.createdAt })),
    ...refunds.map(r => ({ id: r.refundId, type: '退款', name: r.refundId, status: r.status, time: r.updatedAt || r.createdAt })),
  ].filter(a => a.time).sort((a, b) => new Date(b.time as Date).getTime() - new Date(a.time as Date).getTime()).slice(0, 6);

  const formatDate = (d: Date | string | undefined) => {
    if (!d) return '-';
    return new Date(d).toLocaleString('zh-CN');
  };

  return (
    <div>
      <div className="page-title-group" style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600 }}>工作台</h1>
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>查看系统核心指标与最新动态</div>
      </div>

      <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        {/* 系统健康 */}
        <Card title="系统状态">
          {healthLoading && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
          {healthError && renderError('获取系统状态失败', healthErr)}
          {!healthLoading && !healthError && health && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Badge variant={health.status === 'healthy' ? 'success' : 'warning'}>
                  {health.status === 'healthy' ? '正常' : '注意'}
                </Badge>
              </div>
              {health.issues.length > 0 && (
                <ul style={{ fontSize: '13px', color: 'var(--color-text-secondary)', paddingLeft: '16px', margin: '4px 0' }}>
                  {health.issues.map((issue, idx) => (
                    <li key={idx}>{issue}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Card>

        {/* 待处理订单 */}
        <Card title="待处理订单">
          {ordersLoading && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
          {ordersError && renderError('获取订单数失败', ordersErr)}
          {!ordersLoading && !ordersError && (
            <div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: pendingOrders > 0 ? 'var(--color-warning)' : 'var(--color-text-primary)' }}>
                {pendingOrders}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--color-text-tertiary)' }}>笔待支付订单</div>
            </div>
          )}
        </Card>

        {/* 待处理退款 */}
        <Card title="待处理退款">
          {refundsLoading && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
          {refundsError && renderError('获取退款数失败', refundsErr)}
          {!refundsLoading && !refundsError && (
            <div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: pendingRefunds > 0 ? 'var(--color-danger)' : 'var(--color-text-primary)' }}>
                {pendingRefunds}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--color-text-tertiary)' }}>笔待审退款</div>
            </div>
          )}
        </Card>

        {/* 已发布商品 */}
        <Card title="已发布商品">
          {productsLoading && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
          {!productsLoading && (
            <div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                {activeProducts}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--color-text-tertiary)' }}>款在线商品</div>
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
        <Card title="最近活动">
          {(providersLoading || productsLoading || ordersLoading || refundsLoading) && (
            <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>
          )}
          <div className="activity-list">
            {activities.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {activities.map((a, i) => (
                  <li key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: i === activities.length - 1 ? 'none' : '1px solid var(--color-surface-sub)' }}>
                    <div>
                      <span style={{ fontWeight: 500, marginRight: '8px' }}>[{a.type}]</span>
                      {a.name}
                      <span style={{ marginLeft: '8px', color: 'var(--color-text-secondary)', fontSize: '12px' }}>({a.status})</span>
                    </div>
                    <div style={{ color: 'var(--color-text-tertiary)', fontSize: '13px' }}>
                      {formatDate(a.time)}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div style={{ color: 'var(--color-text-tertiary)', padding: '20px 0', textAlign: 'center' }}>暂无最近活动</div>
            )}
          </div>
        </Card>

        {/* 快捷操作 */}
        <Card title="快捷操作">
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <Button variant="primary" onClick={() => navigate('/providers')}>
              管理供应商
            </Button>
            <Button variant="primary" onClick={() => navigate('/commerce/products')}>
              管理商品
            </Button>
            <Button variant="primary" onClick={() => navigate('/commerce/orders')}>
              管理订单
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};
