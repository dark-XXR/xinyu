/**
 * 客服工单运营页面。
 * 队列状态筛选、分类/优先级/负责人管理。
 * 详情会话界面（支持公开回复与内部备注 internal 切换）。
 * 状态、优先级与回复更替提交均需至少8字中文审计理由。
 */
import React, { useState, useEffect } from 'react';
import {
  Search,
  RefreshCw,
  MessageSquare,
  Lock,
  Send,
  AlertCircle,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Badge } from '../../components/ui/Badge';
import { Drawer } from '../../components/ui/Drawer';
import { Textarea } from '../../components/ui/Textarea';
import { repository } from '../../api/repository';
import type { SupportTicket, SupportMessage } from '../../api/models';
import { SupportTicketStatusEnum, SupportTicketPriorityEnum } from '../../api/models';

export const SupportPage: React.FC = () => {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 筛选器
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [search, setSearch] = useState<string>('');

  // 详情与回复 Drawer
  const [activeTicket, setActiveTicket] = useState<SupportTicket | null>(null);
  const [messages, setMessages] = useState<SupportMessage[]>([]);
  const [drawerLoading, setDrawerLoading] = useState<boolean>(false);

  // 回复与更替表单
  const [replyContent, setReplyContent] = useState<string>('');
  const [isInternalNote, setIsInternalNote] = useState<boolean>(false);
  const [newStatus, setNewStatus] = useState<string>('');
  const [newPriority, setNewPriority] = useState<string>('');
  const [auditReason, setAuditReason] = useState<string>('客服工单更替与消息处理');
  const [submitting, setSubmitting] = useState<boolean>(false);

  const fetchTickets = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await repository.getAdminSupportTickets({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        search: search.trim() || undefined,
      });
      setTickets(res.tickets);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载客服工单失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [statusFilter, priorityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTickets();
  };

  const openTicketDrawer = async (ticket: SupportTicket) => {
    setActiveTicket(ticket);
    setDrawerLoading(true);
    setReplyContent('');
    setIsInternalNote(false);
    setNewStatus(ticket.status);
    setNewPriority(ticket.priority);
    setAuditReason('客服响应跟进与状态更替');

    try {
      const data = await repository.getAdminSupportTicketDetail(ticket.ticketId);
      setMessages(data.messages);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '获取工单会话失败');
    } finally {
      setDrawerLoading(false);
    }
  };

  const closeTicketDrawer = () => {
    setActiveTicket(null);
    setMessages([]);
  };

  const handleUpdateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTicket) return;
    setSubmitting(true);
    setError(null);

    try {
      await repository.updateAdminSupportTicket(activeTicket.ticketId, {
        status: newStatus,
        priority: newPriority,
        replyContent: replyContent.trim() || undefined,
        isInternalNote,
        auditReason: auditReason.trim(),
      });

      setSuccessMsg(`工单 ${activeTicket.ticketId} 处理保存成功`);

      // 重新加载当前工单会话
      const data = await repository.getAdminSupportTicketDetail(activeTicket.ticketId);
      setActiveTicket(data.ticket);
      setMessages(data.messages);
      setReplyContent('');

      fetchTickets();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '更新工单失败');
    } finally {
      setSubmitting(false);
    }
  };

  const isReasonValid = auditReason.trim().length >= 8;
  const canSubmit = isReasonValid && !submitting;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)' }}>客服工单运营</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            响应用户客服诉求、内部转办追踪、记录工单处理轨迹与公开/私密回复。
          </p>
        </div>
        <Button variant="default" onClick={fetchTickets} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> 刷新工单队列
        </Button>
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', background: 'var(--color-success-bg)', color: 'var(--color-success)', borderRadius: 'var(--radius-sm)', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>
      )}

      {error && (
        <Card style={{ borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--color-danger)' }}>
            <AlertCircle size={18} />
            <div style={{ flex: 1, fontSize: '13px' }}>{error}</div>
            <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={fetchTickets}>重试</Button>
          </div>
        </Card>
      )}

      {/* 筛选与搜索 */}
      <Card>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: '1 1 240px', minWidth: '200px' }}>
            <Input
              placeholder="搜索工单 ID / 主题 / 分类"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ width: '160px' }}>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">全部工单状态</option>
              <option value={SupportTicketStatusEnum.Open}>待处理 (OPEN)</option>
              <option value={SupportTicketStatusEnum.WaitingSupport}>客服待回复</option>
              <option value={SupportTicketStatusEnum.WaitingUser}>等待用户反馈</option>
              <option value={SupportTicketStatusEnum.Resolved}>已解决 (RESOLVED)</option>
              <option value={SupportTicketStatusEnum.Closed}>已关闭 (CLOSED)</option>
            </Select>
          </div>
          <div style={{ width: '150px' }}>
            <Select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
              <option value="">全部优先级</option>
              <option value={SupportTicketPriorityEnum.Urgent}>紧急 (URGENT)</option>
              <option value={SupportTicketPriorityEnum.High}>高 (HIGH)</option>
              <option value={SupportTicketPriorityEnum.Normal}>普通 (NORMAL)</option>
              <option value={SupportTicketPriorityEnum.Low}>低 (LOW)</option>
            </Select>
          </div>
          <Button type="submit" variant="primary" disabled={loading}>
            <Search size={14} /> 查询
          </Button>
        </form>
      </Card>

      {/* 工单列表 */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '13px' }}>加载工单数据中...</div>
        ) : tickets.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>暂无符合条件的客服工单</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="responsive-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-sub)', borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>工单 ID</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>分类与主题</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>优先级</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>状态</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>提交用户 / 负责人</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>更新时间</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.ticketId} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td data-label="工单 ID" style={{ padding: '12px 16px', fontFamily: 'monospace', fontWeight: 500 }}>
                      {t.ticketId}
                    </td>
                    <td data-label="分类与主题" style={{ padding: '12px 16px', maxWidth: '300px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{t.subject}</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>分类: {t.category}</div>
                    </td>
                    <td data-label="优先级" style={{ padding: '12px 16px' }}>
                      {t.priority === SupportTicketPriorityEnum.Urgent ? (
                        <Badge variant="danger">紧急</Badge>
                      ) : t.priority === SupportTicketPriorityEnum.High ? (
                        <Badge variant="warning">高</Badge>
                      ) : (
                        <Badge variant="default">{t.priority}</Badge>
                      )}
                    </td>
                    <td data-label="状态" style={{ padding: '12px 16px' }}>
                      {t.status === SupportTicketStatusEnum.Resolved ? (
                        <Badge variant="success">已解决</Badge>
                      ) : t.status === SupportTicketStatusEnum.WaitingSupport ? (
                        <Badge variant="warning">待客服回复</Badge>
                      ) : (
                        <Badge variant="default">{t.status}</Badge>
                      )}
                    </td>
                    <td data-label="提交用户 / 负责人" style={{ padding: '12px 16px', fontSize: '12px' }}>
                      <div>用户: {t.userId}</div>
                      <div style={{ color: 'var(--color-text-tertiary)' }}>处理人: {t.assignedAdminId || '未分派'}</div>
                    </td>
                    <td data-label="更新时间" style={{ padding: '12px 16px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      {new Date(t.updatedAt).toLocaleString('zh-CN')}
                    </td>
                    <td data-label="操作" style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openTicketDrawer(t)}>
                        <MessageSquare size={14} /> 处理与回复
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 工单详情与处理 Drawer */}
      <Drawer
        open={!!activeTicket}
        onClose={closeTicketDrawer}
        title={activeTicket ? `处理工单 - ${activeTicket.ticketId}` : '处理工单'}
      >
        {drawerLoading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>加载工单会话中...</div>
        ) : activeTicket ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* 工单基本信息 Header */}
            <Card style={{ background: 'var(--color-surface-sub)', padding: '12px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '8px' }}>{activeTicket.subject}</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                <div>用户: <strong>{activeTicket.userId}</strong></div>
                <div>分类: <strong>{activeTicket.category}</strong></div>
                <div>优先级: <Badge variant="default">{activeTicket.priority}</Badge></div>
                <div>当前状态: <Badge variant="success">{activeTicket.status}</Badge></div>
              </div>
            </Card>

            {/* 消息流水 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '350px', overflowY: 'auto', padding: '8px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', background: 'var(--color-surface-sub)' }}>
              {messages.map((m) => {
                const isAdmin = m.senderType === 'ADMIN';
                const isInternal = m.internal;
                return (
                  <div
                    key={m.messageId}
                    style={{
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-sm)',
                      background: isInternal ? '#fef3c7' : isAdmin ? '#ffedd5' : '#ffffff',
                      border: isInternal ? '1px dashed #f59e0b' : '1px solid var(--color-border)',
                      alignSelf: isAdmin ? 'flex-end' : 'flex-start',
                      maxWidth: '88%',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', fontSize: '11px', color: 'var(--color-text-tertiary)', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, color: isInternal ? '#b45309' : isAdmin ? 'var(--color-primary)' : 'var(--color-text-primary)' }}>
                        {isInternal ? '【内部团队备注】' : isAdmin ? '客服管理员' : `用户 (${m.senderId})`}
                      </span>
                      <span>{new Date(m.createdAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <div style={{ fontSize: '13px', whiteSpace: 'pre-wrap', color: 'var(--color-text-primary)' }}>
                      {m.body}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 回复与状态跟进表单 */}
            <form onSubmit={handleUpdateTicket} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>更新工单状态</label>
                  <Select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                    <option value={SupportTicketStatusEnum.Open}>待处理 (OPEN)</option>
                    <option value={SupportTicketStatusEnum.WaitingSupport}>客服待回复</option>
                    <option value={SupportTicketStatusEnum.WaitingUser}>等待用户反馈</option>
                    <option value={SupportTicketStatusEnum.Resolved}>标记为已解决</option>
                    <option value={SupportTicketStatusEnum.Closed}>直接关闭</option>
                  </Select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>更新优先级</label>
                  <Select value={newPriority} onChange={(e) => setNewPriority(e.target.value)}>
                    <option value={SupportTicketPriorityEnum.Urgent}>紧急 (URGENT)</option>
                    <option value={SupportTicketPriorityEnum.High}>高 (HIGH)</option>
                    <option value={SupportTicketPriorityEnum.Normal}>普通 (NORMAL)</option>
                    <option value={SupportTicketPriorityEnum.Low}>低 (LOW)</option>
                  </Select>
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label style={{ fontSize: '13px', fontWeight: 500 }}>回复 / 备注内容</label>
                  <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: isInternalNote ? 'var(--color-warning)' : 'var(--color-text-secondary)' }}>
                    <input
                      type="checkbox"
                      checked={isInternalNote}
                      onChange={(e) => setIsInternalNote(e.target.checked)}
                    />
                    <Lock size={12} /> 标记为仅团队内部可见的私密备注
                  </label>
                </div>
                <Textarea
                  placeholder={isInternalNote ? '请输入内部备注记录（用户不可见）...' : '请输入发送给用户的公开回复内容...'}
                  value={replyContent}
                  onChange={(e) => setReplyContent(e.target.value)}
                  rows={3}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                  审计处理理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
                </label>
                <Textarea
                  placeholder="请输入变更工单状态或回复的明确操作理由"
                  value={auditReason}
                  onChange={(e) => setAuditReason(e.target.value)}
                  rows={2}
                />
                <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                  当前字数: {auditReason.trim().length} / 至少 8 字
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '4px' }}>
                <Button variant="default" type="button" onClick={closeTicketDrawer} disabled={submitting}>
                  取消
                </Button>
                <Button variant="primary" type="submit" disabled={!canSubmit}>
                  <Send size={14} /> {submitting ? '提交中...' : '保存更新与提交回复'}
                </Button>
              </div>
            </form>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
};
