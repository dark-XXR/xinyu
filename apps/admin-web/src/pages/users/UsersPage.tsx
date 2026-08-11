/**
 * 用户管理页面。
 * 包含搜索筛选、脱敏用户列表、状态/套餐/设备摘要展示、详情抽屉（设备/授权/权益/钱包流水）。
 * 冻结与恢复账号需填写至少8字审计理由并输入完整用户ID二次确认，同时提示会话撤销风险。
 */
import React, { useState, useEffect } from 'react';
import {
  Search,
  RefreshCw,
  UserCheck,
  UserX,
  AlertTriangle,
  Smartphone,
  ShieldAlert,
  CreditCard,
  History,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { Badge } from '../../components/ui/Badge';
import { Dialog } from '../../components/ui/Dialog';
import { Drawer } from '../../components/ui/Drawer';
import { Textarea } from '../../components/ui/Textarea';
import { repository } from '../../api/repository';
import type {
  AdminUserSummary,
  AdminUserDetail,
  Device,
  Entitlement,
  WalletLedgerEntry,
} from '../../api/models';
import { AccountStatus } from '../../api/models';

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 筛选与搜索
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // 详情抽屉 Drawer
  const [drawerUser, setDrawerUser] = useState<AdminUserSummary | null>(null);
  const [userDetail, setUserDetail] = useState<AdminUserDetail | null>(null);
  const [userDevices, setUserDevices] = useState<Device[]>([]);
  const [userEntitlements, setUserEntitlements] = useState<Entitlement[]>([]);
  const [userWalletEntries, setUserWalletEntries] = useState<WalletLedgerEntry[]>([]);
  const [drawerLoading, setDrawerLoading] = useState<boolean>(false);
  const [drawerTab, setDrawerTab] = useState<'devices' | 'entitlements' | 'ledger'>('devices');

  // 状态变更 Dialog
  const [actionUser, setActionUser] = useState<AdminUserSummary | null>(null);
  const [targetStatus, setTargetStatus] = useState<AccountStatus>(AccountStatus.Suspended);
  const [auditReason, setAuditReason] = useState<string>('');
  const [confirmUserId, setConfirmUserId] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await repository.getAdminUsers({
        search: search.trim() || undefined,
        status: statusFilter || undefined,
      });
      setUsers(res.users);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchUsers();
  };

  const openUserDrawer = async (user: AdminUserSummary) => {
    setDrawerUser(user);
    setDrawerLoading(true);
    setDrawerTab('devices');
    try {
      const data = await repository.getAdminUserDetail(user.userId);
      setUserDetail(data.detail);
      setUserDevices(data.devices);
      setUserEntitlements(data.entitlements);
      setUserWalletEntries(data.walletEntries);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '读取用户详情失败');
    } finally {
      setDrawerLoading(false);
    }
  };

  const closeUserDrawer = () => {
    setDrawerUser(null);
    setUserDetail(null);
  };

  const openStatusDialog = (user: AdminUserSummary, newStatus: AccountStatus) => {
    setActionUser(user);
    setTargetStatus(newStatus);
    setAuditReason('');
    setConfirmUserId('');
  };

  const closeStatusDialog = () => {
    setActionUser(null);
  };

  const handleStatusSubmit = async () => {
    if (!actionUser) return;
    setActionLoading(true);
    try {
      await repository.changeAdminUserStatus(actionUser.userId, targetStatus, auditReason.trim());
      setSuccessMsg(`已成功将用户 ${actionUser.userId} 状态变更`);
      closeStatusDialog();
      fetchUsers();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '变更用户状态失败');
    } finally {
      setActionLoading(false);
    }
  };

  // 高风险二次确认逻辑：理由至少 8 字，且确认 ID 完全匹配
  const isReasonValid = auditReason.trim().length >= 8;
  const isIdConfirmed = actionUser ? confirmUserId.trim() === actionUser.userId : false;
  const canSubmitAction = isReasonValid && isIdConfirmed && !actionLoading;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部标题与广播反馈 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)' }}>用户管理</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            检索全局脱敏用户、管理账户状态、审计关联设备与授权流水。
          </p>
        </div>
        <Button variant="default" onClick={fetchUsers} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> 刷新
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
            <AlertTriangle size={18} />
            <div style={{ flex: 1, fontSize: '13px' }}>{error}</div>
            <Button variant="default" onClick={fetchUsers} style={{ height: '28px', fontSize: '12px' }}>重试</Button>
          </div>
        </Card>
      )}

      {/* 搜索过滤控制栏 */}
      <Card>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: '1 1 240px', minWidth: '200px' }}>
            <Input
              placeholder="搜索用户ID / 手机号 / 邮箱 / 昵称"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ width: '160px' }}>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">全部账户状态</option>
              <option value={AccountStatus.Active}>正常 (ACTIVE)</option>
              <option value={AccountStatus.Suspended}>冻结 (SUSPENDED)</option>
              <option value={AccountStatus.DeletionPending}>待销户 (DELETION)</option>
            </Select>
          </div>
          <Button type="submit" variant="primary" disabled={loading}>
            <Search size={14} /> 查询
          </Button>
        </form>
      </Card>

      {/* 脱敏用户数据列表 */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
            数据加载中...
          </div>
        ) : users.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>
            未搜索到符合条件脱敏用户信息
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="responsive-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-sub)', borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>用户 ID</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>脱敏标识</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>状态</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>套餐与权益</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>余量摘要</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>注册 / 活跃时间</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSuspended = u.status === AccountStatus.Suspended;
                  return (
                    <tr key={u.userId} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td data-label="用户 ID" style={{ padding: '12px 16px', fontFamily: 'monospace', fontWeight: 500 }}>
                        {u.userId}
                      </td>
                      <td data-label="脱敏标识" style={{ padding: '12px 16px' }}>
                        <div>{u.maskedPhone || '未绑定手机'}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>{u.maskedEmail || '未绑定邮箱'}</div>
                      </td>
                      <td data-label="状态" style={{ padding: '12px 16px' }}>
                        {isSuspended ? (
                          <Badge variant="danger">已冻结</Badge>
                        ) : u.status === AccountStatus.Active ? (
                          <Badge variant="success">正常</Badge>
                        ) : (
                          <Badge variant="warning">待销户</Badge>
                        )}
                      </td>
                      <td data-label="套餐与权益" style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 500 }}>{u.planCode || '免费版'}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                          关联设备: {u.deviceCount} 台
                        </div>
                      </td>
                      <td data-label="余量摘要" style={{ padding: '12px 16px' }}>
                        <div>文本: {u.textRemaining} 次 | 视觉: {u.visionRemaining} 次</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                          代币余额: {u.energyBalance?.toLocaleString()}
                        </div>
                      </td>
                      <td data-label="注册 / 活跃时间" style={{ padding: '12px 16px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        <div>注册: {new Date(u.createdAt).toLocaleDateString('zh-CN')}</div>
                        <div>更新: {new Date(u.updatedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</div>
                      </td>
                      <td data-label="操作" style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '8px' }}>
                          <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openUserDrawer(u)}>
                            详情
                          </Button>
                          {isSuspended ? (
                            <Button
                              variant="default"
                              style={{ height: '28px', padding: '0 8px', fontSize: '12px', color: 'var(--color-success)' }}
                              onClick={() => openStatusDialog(u, AccountStatus.Active)}
                            >
                              <UserCheck size={14} /> 恢复
                            </Button>
                          ) : (
                            <Button
                              variant="danger"
                              style={{ height: '28px', padding: '0 8px', fontSize: '12px' }}
                              onClick={() => openStatusDialog(u, AccountStatus.Suspended)}
                            >
                              <UserX size={14} /> 冻结
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 用户详情 Drawer */}
      <Drawer
        open={!!drawerUser}
        onClose={closeUserDrawer}
        title={drawerUser ? `用户详情 - ${drawerUser.userId}` : '用户详情'}
      >
        {drawerLoading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>加载详情数据中...</div>
        ) : userDetail ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* 用户基本卡片 */}
            <Card style={{ background: 'var(--color-surface-sub)', padding: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', fontSize: '13px' }}>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>手机脱敏：</span>
                  <span style={{ fontWeight: 500 }}>{userDetail.maskedPhone || '未绑定'}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>邮箱脱敏：</span>
                  <span style={{ fontWeight: 500 }}>{userDetail.maskedEmail || '未绑定'}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>语言 / 时区：</span>
                  <span>{userDetail.locale} ({userDetail.timeZone})</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)' }}>当前状态：</span>
                  <Badge variant={userDetail.status === AccountStatus.Active ? 'success' : 'danger'}>
                    {userDetail.status}
                  </Badge>
                </div>
              </div>
            </Card>

            {/* Tab 切换页签 */}
            <div className="tabs-header">
              <button
                className={`tab-button ${drawerTab === 'devices' ? 'active' : ''}`}
                onClick={() => setDrawerTab('devices')}
              >
                <Smartphone size={14} style={{ display: 'inline', marginRight: '4px' }} /> 关联设备 ({userDevices.length})
              </button>
              <button
                className={`tab-button ${drawerTab === 'entitlements' ? 'active' : ''}`}
                onClick={() => setDrawerTab('entitlements')}
              >
                <CreditCard size={14} style={{ display: 'inline', marginRight: '4px' }} /> 授权与权益 ({userEntitlements.length})
              </button>
              <button
                className={`tab-button ${drawerTab === 'ledger' ? 'active' : ''}`}
                onClick={() => setDrawerTab('ledger')}
              >
                <History size={14} style={{ display: 'inline', marginRight: '4px' }} /> 钱包流水 ({userWalletEntries.length})
              </button>
            </div>

            {/* Tab 内容区 */}
            {drawerTab === 'devices' && (
              <div>
                {userDevices.length === 0 ? (
                  <div style={{ padding: '20px', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>暂无绑定的关联设备</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {userDevices.map((d) => (
                      <Card key={d.deviceId} style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
                          <div>
                            <span style={{ fontWeight: 600 }}>{d.model || d.deviceId}</span>
                            <span style={{ marginLeft: '8px', color: 'var(--color-text-tertiary)', fontSize: '11px' }}>({d.platform})</span>
                          </div>
                          {d.current && <Badge variant="success">当前在线</Badge>}
                        </div>
                        <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                          <div>设备 ID: {d.deviceId}</div>
                          <div>最近上线: {new Date(d.lastSeenAt).toLocaleString('zh-CN')}</div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}

            {drawerTab === 'entitlements' && (
              <div>
                {userEntitlements.length === 0 ? (
                  <div style={{ padding: '20px', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>暂无活跃授权与专属权益</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {userEntitlements.map((e, idx) => (
                      <Card key={idx} style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
                          <span style={{ fontWeight: 600 }}>套餐代码: {e.planCode}</span>
                          <Badge variant="default">已生效</Badge>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '6px' }}>
                          文本对话余量: {e.benefits?.textRemaining ?? '不限'} 次 | 视觉生成余量: {e.benefits?.visionRemaining ?? '不限'} 次
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '4px' }}>
                          到期时间: {e.planExpiresAt ? new Date(e.planExpiresAt).toLocaleDateString('zh-CN') : '永久有效'}
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}

            {drawerTab === 'ledger' && (
              <div>
                {userWalletEntries.length === 0 ? (
                  <div style={{ padding: '20px', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>暂无钱包交易流水记录</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {userWalletEntries.map((w) => (
                      <div key={w.ledgerEntryId} style={{ padding: '10px 12px', background: 'var(--color-surface-sub)', borderRadius: 'var(--radius-sm)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
                        <div>
                          <div style={{ fontWeight: 500 }}>{w.entryType} ({w.reasonCode || '系统记账'})</div>
                          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>{new Date(w.createdAt).toLocaleString('zh-CN')}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontWeight: 600, color: w.energyDelta > 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                            {w.energyDelta > 0 ? `+${w.energyDelta.toLocaleString()}` : w.energyDelta.toLocaleString()} 代币
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>结余: {w.balanceAfter.toLocaleString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </Drawer>

      {/* 冻结 / 恢复 账号高风险二次确认对话框 Dialog */}
      <Dialog
        open={!!actionUser}
        onClose={closeStatusDialog}
        title={targetStatus === AccountStatus.Suspended ? '高风险操作：冻结用户账号' : '恢复用户账号'}
      >
        {actionUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* 风险提示 Banner */}
            {targetStatus === AccountStatus.Suspended && (
              <div style={{ padding: '12px 16px', background: 'var(--color-danger-bg)', color: 'var(--color-danger)', borderRadius: 'var(--radius-sm)', fontSize: '13px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                <ShieldAlert size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600 }}>高风险警告：即刻撤销活跃会话 (Session)</div>
                  <div style={{ fontSize: '12px', marginTop: '2px' }}>
                    冻结账号将立刻使其客户端下线并撤销所有已颁发的令牌，用户必须重新登录方可恢复。
                  </div>
                </div>
              </div>
            )}

            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{actionUser.userId}</code>
            </div>

            {/* 至少 8 字中文理由 */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请详细输入变更理由（例如：收到风控违规举报，暂时冻结核查）"
                value={auditReason}
                onChange={(e) => setAuditReason(e.target.value)}
                rows={3}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '4px', color: isReasonValid ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {auditReason.trim().length} / 至少 8 字
              </div>
            </div>

            {/* 确认用户 ID 输入框 */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                二次确认：请输入完整用户 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${actionUser.userId}" 确认`}
                value={confirmUserId}
                onChange={(e) => setConfirmUserId(e.target.value)}
              />
            </div>

            {/* 操作按钮组 */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <Button variant="default" onClick={closeStatusDialog} disabled={actionLoading}>
                取消
              </Button>
              <Button
                variant={targetStatus === AccountStatus.Suspended ? 'danger' : 'primary'}
                onClick={handleStatusSubmit}
                disabled={!canSubmitAction}
              >
                {actionLoading ? '提交中...' : targetStatus === AccountStatus.Suspended ? '确认冻结账号' : '确认解冻账号'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
