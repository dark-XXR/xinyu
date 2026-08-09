/**
 * 订单管理页面。
 * 展示订单列表、支持按状态/关键词过滤。
 * 抽屉展示订单详情，包含 productSnapshot、paymentAttempts 等细节。
 * 退款流程同步更新订单状态和 refundedAmountMinor。
 * 所有操作使用真实 resourceVersion 作为 ifMatch。
 * 展示 isError/error 中文错误提示。
 */
import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { repository } from '../../api/repository';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { Dialog } from '../../components/ui/Dialog';
import { Input } from '../../components/ui/Input';
import { OrderStatus, RefundStatus } from '../../api/models';
import type { AdminOrder, AdminRefund } from '../../api/models';

export const Orders: React.FC = () => {
  const queryClient = useQueryClient();

  const {
    data: orders = [],
    isLoading: ordersLoading,
    isError: ordersError,
    error: ordersFetchError,
  } = useQuery({
    queryKey: ['orders'],
    queryFn: () => repository.getOrders(),
  });

  const {
    data: refunds = [],
    isLoading: refundsLoading,
    isError: refundsError,
    error: refundsFetchError,
  } = useQuery({
    queryKey: ['refunds'],
    queryFn: () => repository.getRefunds(),
  });

  const [selectedOrder, setSelectedOrder] = useState<AdminOrder | null>(null);
  const [filterKeyword, setFilterKeyword] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [refundToAudit, setRefundToAudit] = useState<{ refund: AdminRefund; action: 'APPROVE' | 'REJECT' } | null>(null);
  const [refundToExecute, setRefundToExecute] = useState<AdminRefund | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const triggerRef = useRef<HTMLElement | null>(null);
  const drawerFocusRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedOrder && drawerFocusRef.current) {
      drawerFocusRef.current.focus();
    }
  }, [selectedOrder]);

  const auditRefundMutation = useMutation({
    mutationFn: (params: { refund: AdminRefund; approved: boolean }) =>
      repository.auditRefund(
        params.refund.refundId ?? '',
        { decision: params.approved ? 'APPROVE' : 'REJECT', auditReason: '管理后台审批' },
        params.refund.resourceVersion,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['refunds'] });
      setRefundToAudit(null);
      setMutationError(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
      setRefundToAudit(null);
    },
  });

  const executeRefundMutation = useMutation({
    mutationFn: (refund: AdminRefund) =>
      repository.executeRefund(
        refund.refundId ?? '',
        { auditReason: '管理后台执行退款' },
        refund.resourceVersion,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['refunds'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      setRefundToExecute(null);
      setMutationError(null);
    },
    onError: (err: unknown) => {
      setMutationError(err instanceof Error ? err.message : String(err));
      setRefundToExecute(null);
    },
  });

  const getOrderStatusBadge = (status?: OrderStatus) => {
    switch (status) {
      case OrderStatus.Paid: return <Badge variant="success">已支付</Badge>;
      case OrderStatus.Created: return <Badge variant="warning">待支付</Badge>;
      case OrderStatus.Failed: return <Badge variant="danger">失败</Badge>;
      case OrderStatus.Cancelled: return <Badge variant="danger">已取消</Badge>;
      case OrderStatus.Refunded: return <Badge variant="default">已退款</Badge>;
      case OrderStatus.PartiallyRefunded: return <Badge variant="warning">部分退款</Badge>;
      default: return <Badge variant="default">{status}</Badge>;
    }
  };

  const getRefundStatusBadge = (status?: RefundStatus) => {
    switch (status) {
      case RefundStatus.Requested: return <Badge variant="warning">待审批</Badge>;
      case RefundStatus.Approved: return <Badge variant="success">已批准</Badge>;
      case RefundStatus.Rejected: return <Badge variant="danger">已驳回</Badge>;
      case RefundStatus.Succeeded: return <Badge variant="success">已退款</Badge>;
      case RefundStatus.Failed: return <Badge variant="danger">退款失败</Badge>;
      default: return <Badge variant="default">{status}</Badge>;
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (filterStatus && o.order.status !== filterStatus) return false;
    if (filterKeyword) {
      const lower = filterKeyword.toLowerCase();
      if (
        !o.order.orderId?.toLowerCase().includes(lower) &&
        !o.userId?.toLowerCase().includes(lower)
      ) {
        return false;
      }
    }
    return true;
  });

  const metrics = {
    total: orders.length,
    paid: orders.filter((o) => o.order.status === OrderStatus.Paid).length,
    pendingRefunds: refunds.filter((r) => r.status === RefundStatus.Requested).length,
  };

  const currentOrderRefunds = selectedOrder
    ? refunds.filter((r) => r.orderId === selectedOrder.order.orderId)
    : [];

  const formatDate = (d: Date | string | undefined) => {
    if (!d) return '-';
    return new Date(d).toLocaleString('zh-CN');
  };

  const formatAmount = (minor: number | undefined, currency: string | undefined) => {
    if (minor === undefined) return '-';
    return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: currency ?? 'CNY' }).format(minor / 100);
  };

  return (
    <div>
      <div className="page-title-group" style={{ marginBottom: '20px' }}>
        <h1 style={{ fontSize: '20px', fontWeight: 600 }}>订单管理</h1>
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>查看和处理所有用户的订单及退款</div>
      </div>
      <div className="toolbar" style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <Input
          placeholder="搜索订单ID / 用户ID"
          value={filterKeyword}
          onChange={(e) => setFilterKeyword(e.target.value)}
          style={{ marginBottom: 0, width: '250px' }}
        />
        <select className="input" style={{ width: 'auto' }} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="">所有状态</option>
          {Object.values(OrderStatus).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {mutationError && (
        <div style={{ background: 'var(--color-danger-bg, #fef2f2)', color: 'var(--color-danger)', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px' }}>
          操作失败：{mutationError}
          <button onClick={() => setMutationError(null)} style={{ marginLeft: '8px', border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', textDecoration: 'underline' }}>关闭</button>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '20px' }}>
        <Card><div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>总订单数</div><div style={{ fontSize: '24px', fontWeight: 600 }}>{metrics.total}</div></Card>
        <Card><div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>已支付/完成</div><div style={{ fontSize: '24px', fontWeight: 600 }}>{metrics.paid}</div></Card>
        <Card><div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>待处理退款</div><div style={{ fontSize: '24px', fontWeight: 600, color: metrics.pendingRefunds > 0 ? 'var(--color-danger)' : 'inherit' }}>{metrics.pendingRefunds}</div></Card>
      </div>

      <Card>
        {(ordersLoading || refundsLoading) && <div style={{ color: 'var(--color-text-tertiary)' }}>加载中...</div>}
        {ordersError && (
          <div style={{ color: 'var(--color-danger)', padding: '12px' }}>
            获取订单列表失败：{ordersFetchError instanceof Error ? ordersFetchError.message : String(ordersFetchError)}
          </div>
        )}
        {refundsError && (
          <div style={{ color: 'var(--color-danger)', padding: '12px' }}>
            获取退款列表失败：{refundsFetchError instanceof Error ? refundsFetchError.message : String(refundsFetchError)}
          </div>
        )}
        {!ordersLoading && !refundsLoading && !ordersError && !refundsError && (
          <div className="table-wrapper">
            <table className="responsive-table">
              <thead>
                <tr>
                  <th>订单ID</th>
                  <th>用户ID</th>
                  <th>商品</th>
                  <th>金额</th>
                  <th>创建时间</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((o) => (
                  <tr key={o.order.orderId}>
                    <td data-label="订单ID">{o.order.orderId}</td>
                    <td data-label="用户ID">{o.userId}</td>
                    <td data-label="商品">{o.order.product?.displayName ?? '-'}</td>
                    <td data-label="金额">{formatAmount(o.order.amountMinor, o.order.currency)}</td>
                    <td data-label="创建时间">{formatDate(o.order.createdAt)}</td>
                    <td data-label="状态">{getOrderStatusBadge(o.order.status)}</td>
                    <td data-label="操作">
                      <Button variant="ghost" onClick={() => { triggerRef.current = document.activeElement as HTMLElement; setSelectedOrder(o); }}>
                        查看详情
                      </Button>
                    </td>
                  </tr>
                ))}
                {filteredOrders.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-tertiary)' }}>
                      未找到订单
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 订单详情抽屉 */}
      <Drawer
        open={!!selectedOrder}
        title="订单详情"
        onClose={() => setSelectedOrder(null)}
      >
        {selectedOrder && (
          <div ref={drawerFocusRef} tabIndex={-1} style={{ display: 'flex', flexDirection: 'column', gap: '16px', outline: 'none' }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>订单ID</div>
              <div>{selectedOrder.order.orderId}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>用户ID</div>
              <div>{selectedOrder.userId}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>状态</div>
              <div>{getOrderStatusBadge(selectedOrder.order.status)}</div>
            </div>

            {/* 商品快照 */}
            {selectedOrder.order.product && (
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px' }}>
                <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>商品快照</div>
                <div style={{ fontSize: '13px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div><span style={{ color: 'var(--color-text-secondary)' }}>代码: </span>{selectedOrder.order.product.productCode}</div>
                  <div><span style={{ color: 'var(--color-text-secondary)' }}>名称: </span>{selectedOrder.order.product.displayName}</div>
                  <div><span style={{ color: 'var(--color-text-secondary)' }}>版本: </span>v{selectedOrder.order.product.version}</div>
                  <div><span style={{ color: 'var(--color-text-secondary)' }}>续费: </span>{selectedOrder.order.product.renewalType}</div>
                  <div><span style={{ color: 'var(--color-text-secondary)' }}>金额: </span>{formatAmount(selectedOrder.order.product.amountMinor, selectedOrder.order.product.currency)}</div>
                </div>
              </div>
            )}

            {/* 金额信息 */}
            <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>金额信息</div>
              <div style={{ fontSize: '13px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div><span style={{ color: 'var(--color-text-secondary)' }}>订单金额: </span>{formatAmount(selectedOrder.order.amountMinor, selectedOrder.order.currency)}</div>
                <div><span style={{ color: 'var(--color-text-secondary)' }}>已支付: </span>{formatAmount(selectedOrder.order.paidAmountMinor, selectedOrder.order.currency)}</div>
                {selectedOrder.order.paidAt && <div><span style={{ color: 'var(--color-text-secondary)' }}>支付时间: </span>{formatDate(selectedOrder.order.paidAt)}</div>}
                <div><span style={{ color: 'var(--color-text-secondary)' }}>权益已发放: </span>{selectedOrder.order.entitlementGranted ? '是' : '否'}</div>
              </div>
            </div>

            {/* 支付尝试 */}
            {selectedOrder.order.paymentAttempts && selectedOrder.order.paymentAttempts.length > 0 && (
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px' }}>
                <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>支付尝试</div>
                {selectedOrder.order.paymentAttempts.map((pa) => (
                  <div key={pa.paymentAttemptId} style={{ fontSize: '13px', background: 'var(--color-surface-hover)', padding: '8px', borderRadius: '4px', marginBottom: '4px' }}>
                    <div>{pa.paymentMethod} - {pa.status} - {formatAmount(pa.amountMinor, selectedOrder.order.currency)}</div>
                    {pa.createdAt && <div style={{ color: 'var(--color-text-tertiary)', fontSize: '12px' }}>{formatDate(pa.createdAt)}</div>}
                  </div>
                ))}
              </div>
            )}

            {/* 关联退款 */}
            <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '16px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>关联退款</h3>
              {currentOrderRefunds.length > 0 ? (
                currentOrderRefunds.map((r) => (
                  <div key={r.refundId} style={{ marginBottom: '12px', padding: '12px', background: 'var(--color-surface-hover)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '13px', marginBottom: '4px' }}>退款ID: {r.refundId}</div>
                    <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                      状态: {getRefundStatusBadge(r.status)}
                    </div>
                    <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                      申请金额: {formatAmount(r.requestedAmountMinor, r.currency)} | 已退: {formatAmount(r.refundedAmountMinor, r.currency)}
                    </div>
                    <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                      原因: {r.reasonCode ?? '-'}
                    </div>

                    {r.status === RefundStatus.Requested && (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <Button variant="primary" onClick={() => setRefundToAudit({ refund: r, action: 'APPROVE' })}>审批同意</Button>
                        <Button variant="danger" onClick={() => setRefundToAudit({ refund: r, action: 'REJECT' })}>驳回</Button>
                      </div>
                    )}
                    {r.status === RefundStatus.Approved && (
                      <Button variant="primary" onClick={() => setRefundToExecute(r)}>执行退款</Button>
                    )}
                  </div>
                ))
              ) : (
                <div style={{ fontSize: '13px', color: 'var(--color-text-tertiary)' }}>暂无退款申请</div>
              )}
            </div>
          </div>
        )}
      </Drawer>

      {/* 审批确认 */}
      <Dialog
        open={!!refundToAudit}
        title={refundToAudit?.action === 'APPROVE' ? '同意退款申请' : '驳回退款申请'}
        onClose={() => setRefundToAudit(null)}
        footer={
          <>
            <Button variant="default" onClick={() => setRefundToAudit(null)}>取消</Button>
            <Button
              variant={refundToAudit?.action === 'APPROVE' ? 'primary' : 'danger'}
              onClick={() => refundToAudit && auditRefundMutation.mutate({ refund: refundToAudit.refund, approved: refundToAudit.action === 'APPROVE' })}
              disabled={auditRefundMutation.isPending}
            >
              {auditRefundMutation.isPending ? '提交中...' : '确认操作'}
            </Button>
          </>
        }
      >
        确定要{refundToAudit?.action === 'APPROVE' ? '同意' : '驳回'}此退款申请吗？
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '8px' }}>
          退款ID: {refundToAudit?.refund.refundId} | 金额: {formatAmount(refundToAudit?.refund.requestedAmountMinor, refundToAudit?.refund.currency)}
        </div>
      </Dialog>

      {/* 执行退款确认 */}
      <Dialog
        open={!!refundToExecute}
        title="执行退款"
        onClose={() => setRefundToExecute(null)}
        footer={
          <>
            <Button variant="default" onClick={() => setRefundToExecute(null)}>取消</Button>
            <Button
              variant="primary"
              onClick={() => refundToExecute && executeRefundMutation.mutate(refundToExecute)}
              disabled={executeRefundMutation.isPending}
            >
              {executeRefundMutation.isPending ? '执行中...' : '确认执行'}
            </Button>
          </>
        }
      >
        执行退款将通过支付渠道原路退回金额，此操作不可逆。是否继续？
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '8px' }}>
          退款ID: {refundToExecute?.refundId} | 金额: {formatAmount(refundToExecute?.requestedAmountMinor, refundToExecute?.currency)}
        </div>
      </Dialog>
    </div>
  );
};
