/**
 * 公告运营页面。
 * 提供公告列表展示、类型与平台筛选、草稿表单新建/编辑。
 * 支持公告发布与撤回操作，要求填写至少8字中文审计理由。
 */
import React, { useState, useEffect } from 'react';
import {
  Plus,
  RefreshCw,
  Edit3,
  Send,
  AlertCircle,
  XCircle,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Textarea } from '../../components/ui/Textarea';
import { Badge } from '../../components/ui/Badge';
import { Dialog } from '../../components/ui/Dialog';
import { repository } from '../../api/repository';
import {
  NoticeWriteRequestNoticeTypeEnum,
  NoticeWriteRequestTargetPlatformsEnum,
  NoticeWriteRequestDisplayFrequencyEnum,
} from '../../api/models';
import type { NoticeVersion, NoticeWriteRequest } from '../../api/models';

export const NoticesPage: React.FC = () => {
  const [notices, setNotices] = useState<NoticeVersion[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 筛选器
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  // 表单 Dialog（新建或编辑草稿）
  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [editingNotice, setEditingNotice] = useState<NoticeVersion | null>(null);
  const [formData, setFormData] = useState<{
    title: string;
    body: string;
    noticeType: string;
    targetPlatforms: string[];
    targetLocales: string[];
    minClientVersion: string;
    maxClientVersion: string;
    displayFrequency: string;
    startsAt: string;
    endsAt: string;
    auditReason: string;
  }>({
    title: '',
    body: '',
    noticeType: 'GENERAL',
    targetPlatforms: ['ADMIN_WEB', 'ANDROID'],
    targetLocales: ['zh-CN'],
    minClientVersion: '',
    maxClientVersion: '',
    displayFrequency: 'ONCE',
    startsAt: new Date().toISOString().slice(0, 16),
    endsAt: '',
    auditReason: '公告运营管理更新草稿',
  });
  const [formSaving, setFormSaving] = useState<boolean>(false);

  // 发布 / 撤回 Dialog
  const [actionNotice, setActionNotice] = useState<NoticeVersion | null>(null);
  const [actionType, setActionType] = useState<'PUBLISH' | 'REVOKE'>('PUBLISH');
  const [actionAuditReason, setActionAuditReason] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const fetchNotices = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await repository.getAdminNotices({
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      });
      setNotices(res.notices);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载公告列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotices();
  }, [statusFilter, typeFilter]);

  const openFormModal = (notice?: NoticeVersion) => {
    if (notice) {
      setEditingNotice(notice);
      setFormData({
        title: notice.title,
        body: notice.body,
        noticeType: notice.noticeType,
        targetPlatforms: notice.targetPlatforms || ['ANDROID'],
        targetLocales: notice.targetLocales || ['zh-CN'],
        minClientVersion: notice.minClientVersion || '',
        maxClientVersion: notice.maxClientVersion || '',
        displayFrequency: notice.displayFrequency || 'ONCE',
        startsAt: notice.startsAt ? new Date(notice.startsAt).toISOString().slice(0, 16) : new Date().toISOString().slice(0, 16),
        endsAt: notice.endsAt ? new Date(notice.endsAt).toISOString().slice(0, 16) : '',
        auditReason: '编辑公告草稿明细内容',
      });
    } else {
      setEditingNotice(null);
      setFormData({
        title: '',
        body: '',
        noticeType: 'GENERAL',
        targetPlatforms: ['ADMIN_WEB', 'ANDROID'],
        targetLocales: ['zh-CN'],
        minClientVersion: '',
        maxClientVersion: '',
        displayFrequency: 'ONCE',
        startsAt: new Date().toISOString().slice(0, 16),
        endsAt: '',
        auditReason: '新建系统公告运营草稿',
      });
    }
    setFormOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSaving(true);
    setError(null);

    const writeReq: NoticeWriteRequest = {
      title: formData.title,
      body: formData.body,
      noticeType: formData.noticeType as unknown as NoticeWriteRequestNoticeTypeEnum,
      targetPlatforms: new Set(formData.targetPlatforms as NoticeWriteRequestTargetPlatformsEnum[]),
      targetLocales: new Set(formData.targetLocales),
      minClientVersion: formData.minClientVersion || undefined,
      maxClientVersion: formData.maxClientVersion || undefined,
      displayFrequency: formData.displayFrequency as NoticeWriteRequestDisplayFrequencyEnum,
      startsAt: new Date(formData.startsAt),
      endsAt: formData.endsAt ? new Date(formData.endsAt) : undefined,
      auditReason: formData.auditReason,
    };

    try {
      if (editingNotice) {
        await repository.updateAdminNotice(editingNotice.noticeId, writeReq);
        setSuccessMsg(`公告草稿 "${formData.title}" 保存更新成功`);
      } else {
        await repository.createAdminNotice(writeReq);
        setSuccessMsg(`公告草稿 "${formData.title}" 新建成功`);
      }
      setFormOpen(false);
      fetchNotices();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存草稿失败');
    } finally {
      setFormSaving(false);
    }
  };

  const openActionModal = (notice: NoticeVersion, act: 'PUBLISH' | 'REVOKE') => {
    setActionNotice(notice);
    setActionType(act);
    setActionAuditReason('');
  };

  const handleActionSubmit = async () => {
    if (!actionNotice) return;
    setActionLoading(true);
    try {
      if (actionType === 'PUBLISH') {
        await repository.publishAdminNotice(actionNotice.noticeId, actionAuditReason.trim());
        setSuccessMsg(`公告 "${actionNotice.title}" 已成功发布`);
      } else {
        await repository.revokeAdminNotice(actionNotice.noticeId, actionAuditReason.trim());
        setSuccessMsg(`公告 "${actionNotice.title}" 已撤回`);
      }
      setActionNotice(null);
      fetchNotices();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '变更公告状态失败');
    } finally {
      setActionLoading(false);
    }
  };

  const isFormReasonValid = formData.auditReason.trim().length >= 8;
  const isFormValid = formData.title.trim() && formData.body.trim() && isFormReasonValid && !formSaving;

  const isActionReasonValid = actionAuditReason.trim().length >= 8;
  const canSubmitAction = isActionReasonValid && !actionLoading;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部区域 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)' }}>公告运营</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            管理全端客户端公告、系统升级通知、营销活动与弹窗策略。
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button variant="default" onClick={fetchNotices} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> 刷新
          </Button>
          <Button variant="primary" onClick={() => openFormModal()}>
            <Plus size={14} /> 新建公告草稿
          </Button>
        </div>
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
            <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={fetchNotices}>重试</Button>
          </div>
        </Card>
      )}

      {/* 状态与类型过滤器 */}
      <Card>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ width: '180px' }}>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">全部公告状态</option>
              <option value="DRAFT">草稿 (DRAFT)</option>
              <option value="PUBLISHED">已发布 (PUBLISHED)</option>
              <option value="REVOKED">已撤回 (REVOKED)</option>
            </Select>
          </div>
          <div style={{ width: '180px' }}>
            <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">全部公告类型</option>
              <option value="GENERAL">常规升级 (GENERAL)</option>
              <option value="MAINTENANCE">例行维护 (MAINTENANCE)</option>
              <option value="PROMOTION">营销活动 (PROMOTION)</option>
              <option value="SECURITY">安全告警 (SECURITY)</option>
            </Select>
          </div>
        </div>
      </Card>

      {/* 公告列表 */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '13px' }}>加载公告列表中...</div>
        ) : notices.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>暂无符合条件的公告</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="responsive-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-sub)', borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>标题与正文</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>类型</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>状态</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>定向平台 / 语言</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>频次 / 版本范围</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>生效起止时间</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {notices.map((n) => (
                  <tr key={n.noticeId} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td data-label="标题与正文" style={{ padding: '12px 16px', maxWidth: '300px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{n.title}</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                        {n.body}
                      </div>
                    </td>
                    <td data-label="类型" style={{ padding: '12px 16px' }}>
                      <Badge variant="default">{n.noticeType}</Badge>
                    </td>
                    <td data-label="状态" style={{ padding: '12px 16px' }}>
                      {n.status === 'PUBLISHED' ? (
                        <Badge variant="success">已发布</Badge>
                      ) : n.status === 'DRAFT' ? (
                        <Badge variant="warning">草稿</Badge>
                      ) : (
                        <Badge variant="danger">已撤回</Badge>
                      )}
                    </td>
                    <td data-label="定向平台 / 语言" style={{ padding: '12px 16px', fontSize: '12px' }}>
                      <div>平台: {n.targetPlatforms?.join(', ') || '全端'}</div>
                      <div style={{ color: 'var(--color-text-tertiary)' }}>语言: {n.targetLocales?.join(', ') || 'zh-CN'}</div>
                    </td>
                    <td data-label="频次 / 版本范围" style={{ padding: '12px 16px', fontSize: '12px' }}>
                      <div>频次: {n.displayFrequency}</div>
                      <div style={{ color: 'var(--color-text-tertiary)' }}>
                        版本: {n.minClientVersion || '*'} ~ {n.maxClientVersion || '*'}
                      </div>
                    </td>
                    <td data-label="生效起止时间" style={{ padding: '12px 16px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      <div>开始: {new Date(n.startsAt).toLocaleString('zh-CN')}</div>
                      <div>结束: {n.endsAt ? new Date(n.endsAt).toLocaleString('zh-CN') : '长期生效'}</div>
                    </td>
                    <td data-label="操作" style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        {n.status === 'DRAFT' && (
                          <>
                            <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openFormModal(n)}>
                              <Edit3 size={14} /> 编辑
                            </Button>
                            <Button variant="primary" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openActionModal(n, 'PUBLISH')}>
                              <Send size={14} /> 发布
                            </Button>
                          </>
                        )}
                        {n.status === 'PUBLISHED' && (
                          <Button variant="danger" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openActionModal(n, 'REVOKE')}>
                            <XCircle size={14} /> 撤回
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 创建 / 编辑草稿 Dialog */}
      <Dialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editingNotice ? '编辑公告草稿' : '新建公告草稿'}
      >
        <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>公告标题 *</label>
            <Input
              placeholder="请输入清晰的公告标题"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>公告正文 *</label>
            <Textarea
              placeholder="请输入公告详细正文内容..."
              value={formData.body}
              onChange={(e) => setFormData({ ...formData, body: e.target.value })}
              rows={4}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>公告类型</label>
              <Select
                value={formData.noticeType}
                onChange={(e) => setFormData({ ...formData, noticeType: e.target.value })}
              >
                <option value="GENERAL">常规升级 (GENERAL)</option>
                <option value="MAINTENANCE">系统维护 (MAINTENANCE)</option>
                <option value="PROMOTION">营销活动 (PROMOTION)</option>
                <option value="SECURITY">安全告警 (SECURITY)</option>
              </Select>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>展示频次</label>
              <Select
                value={formData.displayFrequency}
                onChange={(e) => setFormData({ ...formData, displayFrequency: e.target.value })}
              >
                <option value="ONCE">仅展示一次 (ONCE)</option>
                <option value="ONCE_PER_VERSION">每个版本一次 (ONCE_PER_VERSION)</option>
                <option value="EVERY_LAUNCH">每次启动展示 (EVERY_LAUNCH)</option>
              </Select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>最小客户端版本</label>
              <Input
                placeholder="例如: 2.0.0"
                value={formData.minClientVersion}
                onChange={(e) => setFormData({ ...formData, minClientVersion: e.target.value })}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>最大客户端版本</label>
              <Input
                placeholder="例如: 2.4.0"
                value={formData.maxClientVersion}
                onChange={(e) => setFormData({ ...formData, maxClientVersion: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>生效开始时间 *</label>
              <Input
                type="datetime-local"
                value={formData.startsAt}
                onChange={(e) => setFormData({ ...formData, startsAt: e.target.value })}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>生效结束时间（可选）</label>
              <Input
                type="datetime-local"
                value={formData.endsAt}
                onChange={(e) => setFormData({ ...formData, endsAt: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
            </label>
            <Textarea
              placeholder="请输入保存草稿的明确业务背景说明"
              value={formData.auditReason}
              onChange={(e) => setFormData({ ...formData, auditReason: e.target.value })}
              rows={2}
            />
            <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isFormReasonValid ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
              当前字数: {formData.auditReason.trim().length} / 至少 8 字
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
            <Button variant="default" type="button" onClick={() => setFormOpen(false)} disabled={formSaving}>
              取消
            </Button>
            <Button variant="primary" type="submit" disabled={!isFormValid}>
              {formSaving ? '保存中...' : '保存草稿'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* 发布 / 撤回 确认 Dialog */}
      <Dialog
        open={!!actionNotice}
        onClose={() => setActionNotice(null)}
        title={actionType === 'PUBLISH' ? '发布公告' : '撤回公告'}
      >
        {actionNotice && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              确定对公告 <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>"{actionNotice.title}"</span> 执行 {actionType === 'PUBLISH' ? '线上发布' : '下架撤回'} 操作？
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                操作审计理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请输入详细的发布或撤回审计理由"
                value={actionAuditReason}
                onChange={(e) => setActionAuditReason(e.target.value)}
                rows={3}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isActionReasonValid ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {actionAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <Button variant="default" onClick={() => setActionNotice(null)} disabled={actionLoading}>
                取消
              </Button>
              <Button
                variant={actionType === 'PUBLISH' ? 'primary' : 'danger'}
                onClick={handleActionSubmit}
                disabled={!canSubmitAction}
              >
                {actionLoading ? '提交中...' : actionType === 'PUBLISH' ? '确认发布' : '确认撤回'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
