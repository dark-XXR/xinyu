/**
 * 用户管理页面组件。
 * 提供脱敏用户检索、账号状态变更（冻结/解冻）、用户资料编辑、登录安全重置（会话撤销）、
 * 关联设备列表及设备撤销、余额/额度手动调整（以增减量记账）以及套餐在线分配（快照叠加）功能。
 *
 * 遵从合规安全约束：高风险写操作均需要填写至少 8 字中文审计理由并进行完整 ID 二次确认。
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
  Edit,
  Lock,
  ShieldX,
  Gift,
  User,
  Globe,
  Clock,
  CheckCircle,
  Sliders,
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
  AdminProductVersion,
} from '../../api/models';
import {
  AccountStatus,
  EntitlementAdjustmentRequestUnitEnum,
  ProductType,
  ProductPublicationStatus,
} from '../../api/models';

/**
 * 获取指定货币代码的 minor-unit 小数位数
 */
const getCurrencyMinorUnitDigits = (currency: string = 'CNY'): number => {
  const upper = currency.toUpperCase();
  if (['JPY', 'KRW', 'VND', 'CLP', 'PYG', 'UGX', 'RWF', 'BIF', 'DJF', 'GNF', 'KMF', 'MGA', 'XAF', 'XOF', 'XPF'].includes(upper)) {
    return 0;
  }
  if (['BHD', 'JOD', 'KWD', 'OMR', 'TND'].includes(upper)) {
    return 3;
  }
  return 2;
};

/**
 * 根据产品 currency 格式化 amountMinor 金额
 */
const formatAmountMinor = (amountMinor: number, currency: string = 'CNY'): string => {
  const digits = getCurrencyMinorUnitDigits(currency);
  const majorAmount = amountMinor / Math.pow(10, digits);
  try {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: currency.toUpperCase(),
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(majorAmount);
  } catch {
    return `${currency.toUpperCase()} ${majorAmount.toFixed(digits)}`;
  }
};

/**
 * 原因代码格式校验正则：必须以大写字母开头，且只包含大写字母、数字及下划线
 */
const REASON_CODE_REGEX = /^[A-Z][A-Z0-9_]*$/;
const isReasonCodeValid = (code: string) => REASON_CODE_REGEX.test(code.trim());

export const UsersPage: React.FC = () => {
  // 全局列表与状态
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
  const [userDevices, setUserDevices] = useState<(Device & { revokedAt?: Date | null })[]>([]);
  const [userEntitlements, setUserEntitlements] = useState<Entitlement[]>([]);
  const [userWalletEntries, setUserWalletEntries] = useState<WalletLedgerEntry[]>([]);
  const [drawerLoading, setDrawerLoading] = useState<boolean>(false);
  const [drawerTab, setDrawerTab] = useState<'devices' | 'entitlements' | 'ledger'>('devices');

  // 1. 状态变更 Dialog (冻结/恢复)
  const [statusDialogOpen, setStatusDialogOpen] = useState<boolean>(false);
  const [actionUser, setActionUser] = useState<AdminUserSummary | null>(null);
  const [targetStatus, setTargetStatus] = useState<AccountStatus>(AccountStatus.Suspended);
  const [statusAuditReason, setStatusAuditReason] = useState<string>('');
  const [statusConfirmUserId, setStatusConfirmUserId] = useState<string>('');
  const [statusSubmitting, setStatusSubmitting] = useState<boolean>(false);

  // 2. 资料编辑 Dialog
  const [profileDialogOpen, setProfileDialogOpen] = useState<boolean>(false);
  const [profileUser, setProfileUser] = useState<AdminUserSummary | null>(null);
  const [editNickname, setEditNickname] = useState<string>('');
  const [editAvatarUrl, setEditAvatarUrl] = useState<string>('');
  const [editLocale, setEditLocale] = useState<string>('zh-CN');
  const [editTimeZone, setEditTimeZone] = useState<string>('Asia/Shanghai');
  const [profileResourceVersion, setProfileResourceVersion] = useState<number>(1);
  const [profileAuditReason, setProfileAuditReason] = useState<string>('');
  const [profileConfirmUserId, setProfileConfirmUserId] = useState<string>('');
  const [profileSubmitting, setProfileSubmitting] = useState<boolean>(false);

  // 3. 登录安全重置 Dialog
  const [resetDialogOpen, setResetDialogOpen] = useState<boolean>(false);
  const [resetUser, setResetUser] = useState<AdminUserSummary | null>(null);
  const [resetAuditReason, setResetAuditReason] = useState<string>('');
  const [resetConfirmUserId, setResetConfirmUserId] = useState<string>('');
  const [resetSubmitting, setResetSubmitting] = useState<boolean>(false);

  // 4. 设备撤销 Dialog
  const [revokeDeviceDialogOpen, setRevokeDeviceDialogOpen] = useState<boolean>(false);
  const [revokeUser, setRevokeUser] = useState<AdminUserSummary | null>(null);
  const [targetDevice, setTargetDevice] = useState<(Device & { revokedAt?: Date | null }) | null>(null);
  const [deviceAuditReason, setDeviceAuditReason] = useState<string>('');
  const [deviceConfirmId, setDeviceConfirmId] = useState<string>('');
  const [deviceSubmitting, setDeviceSubmitting] = useState<boolean>(false);

  // 5. 余额/额度调整 Dialog
  const [adjustDialogOpen, setAdjustDialogOpen] = useState<boolean>(false);
  const [adjustUser, setAdjustUser] = useState<AdminUserSummary | null>(null);
  const [adjustDetail, setAdjustDetail] = useState<AdminUserDetail | null>(null);
  const [adjustUnit, setAdjustUnit] = useState<EntitlementAdjustmentRequestUnitEnum | 'ENERGY' | 'TEXT_QUOTA' | 'VISION_QUOTA' | 'PLAN_DAYS'>(EntitlementAdjustmentRequestUnitEnum.Energy);
  const [adjustDelta, setAdjustDelta] = useState<number>(0);
  const [adjustReasonCode, setAdjustReasonCode] = useState<string>('');
  const [adjustAuditReason, setAdjustAuditReason] = useState<string>('');
  const [adjustConfirmUserId, setAdjustConfirmUserId] = useState<string>('');
  const [adjustSubmitting, setAdjustSubmitting] = useState<boolean>(false);

  // 6. 套餐分配 Dialog
  const [grantPlanDialogOpen, setGrantPlanDialogOpen] = useState<boolean>(false);
  const [grantUser, setGrantUser] = useState<AdminUserSummary | null>(null);
  const [grantEntitlementVersion, setGrantEntitlementVersion] = useState<number>(1);
  const [activePlanProducts, setActivePlanProducts] = useState<AdminProductVersion[]>([]);
  const [selectedProductVersionId, setSelectedProductVersionId] = useState<string>('');
  const [grantAuditReason, setGrantAuditReason] = useState<string>('');
  const [grantConfirmUserId, setGrantConfirmUserId] = useState<string>('');
  const [grantLoadingProducts, setGrantLoadingProducts] = useState<boolean>(false);
  const [grantSubmitting, setGrantSubmitting] = useState<boolean>(false);

  /**
   * 加载脱敏用户列表
   */
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

  /**
   * 打开并加载指定用户的详情抽屉
   */
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

  /**
   * 刷新当前已打开抽屉的用户详情
   */
  const refreshCurrentDrawer = async (userId: string) => {
    try {
      const data = await repository.getAdminUserDetail(userId);
      setUserDetail(data.detail);
      setUserDevices(data.devices);
      setUserEntitlements(data.entitlements);
      setUserWalletEntries(data.walletEntries);
    } catch (err: unknown) {
      console.error('刷新用户详情失败', err);
    }
  };

  const closeUserDrawer = () => {
    setDrawerUser(null);
    setUserDetail(null);
  };

  /* ------------------- 1. 冻结 / 恢复 逻辑 ------------------- */
  const openStatusDialog = (user: AdminUserSummary, newStatus: AccountStatus) => {
    setActionUser(user);
    setTargetStatus(newStatus);
    setStatusAuditReason('');
    setStatusConfirmUserId('');
    setStatusDialogOpen(true);
  };

  const closeStatusDialog = () => {
    setStatusDialogOpen(false);
    setActionUser(null);
  };

  const handleStatusSubmit = async () => {
    if (!actionUser) return;
    setStatusSubmitting(true);
    try {
      await repository.changeAdminUserStatus(actionUser.userId, targetStatus, statusAuditReason.trim(), String(actionUser.resourceVersion || 1));
      setSuccessMsg(`已成功将用户 ${actionUser.userId} 状态变更`);
      closeStatusDialog();
      fetchUsers();
      if (drawerUser && drawerUser.userId === actionUser.userId) {
        refreshCurrentDrawer(actionUser.userId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '变更用户状态失败');
    } finally {
      setStatusSubmitting(false);
    }
  };

  /* ------------------- 2. 编辑资料 逻辑 ------------------- */
  const openProfileDialog = async (user: AdminUserSummary) => {
    setProfileUser(user);
    setProfileAuditReason('');
    setProfileConfirmUserId('');
    setProfileDialogOpen(true);
    try {
      const data = await repository.getAdminUserDetail(user.userId);
      setEditNickname(data.detail.nickname || '');
      setEditAvatarUrl(data.detail.avatarUrl || '');
      setEditLocale(data.detail.locale || 'zh-CN');
      setEditTimeZone(data.detail.timeZone || 'Asia/Shanghai');
      setProfileResourceVersion(data.detail.resourceVersion || 1);
    } catch {
      setEditNickname(user.nickname || '');
      setEditAvatarUrl('');
      setEditLocale('zh-CN');
      setEditTimeZone('Asia/Shanghai');
      setProfileResourceVersion(user.resourceVersion || 1);
    }
  };

  const closeProfileDialog = () => {
    setProfileDialogOpen(false);
    setProfileUser(null);
  };

  const handleProfileSubmit = async () => {
    if (!profileUser) return;
    setProfileSubmitting(true);
    try {
      await repository.updateAdminUserProfile(
        profileUser.userId,
        {
          nickname: editNickname.trim() || null,
          avatarUrl: editAvatarUrl.trim() || null,
          locale: editLocale,
          timeZone: editTimeZone,
          auditReason: profileAuditReason.trim(),
          confirmationUserId: profileConfirmUserId.trim(),
        },
        String(profileResourceVersion),
      );
      setSuccessMsg(`已成功更新用户 ${profileUser.userId} 资料`);
      closeProfileDialog();
      fetchUsers();
      if (drawerUser && drawerUser.userId === profileUser.userId) {
        refreshCurrentDrawer(profileUser.userId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '更新用户资料失败');
    } finally {
      setProfileSubmitting(false);
    }
  };

  /* ------------------- 3. 登录安全重置 逻辑 ------------------- */
  const openResetDialog = (user: AdminUserSummary) => {
    setResetUser(user);
    setResetAuditReason('');
    setResetConfirmUserId('');
    setResetDialogOpen(true);
  };

  const closeResetDialog = () => {
    setResetDialogOpen(false);
    setResetUser(null);
  };

  const handleResetSubmit = async () => {
    if (!resetUser) return;
    setResetSubmitting(true);
    try {
      await repository.resetAdminUserLoginState(resetUser.userId, resetAuditReason.trim());
      setSuccessMsg(`已成功重置用户 ${resetUser.userId} 的登录安全状态并撤销会话`);
      closeResetDialog();
      fetchUsers();
      if (drawerUser && drawerUser.userId === resetUser.userId) {
        refreshCurrentDrawer(resetUser.userId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '重置登录状态失败');
    } finally {
      setResetSubmitting(false);
    }
  };

  /* ------------------- 4. 设备撤销 逻辑 ------------------- */
  const openRevokeDeviceDialog = (user: AdminUserSummary, device: Device & { revokedAt?: Date | null }) => {
    setRevokeUser(user);
    setTargetDevice(device);
    setDeviceAuditReason('');
    setDeviceConfirmId('');
    setRevokeDeviceDialogOpen(true);
  };

  const closeRevokeDeviceDialog = () => {
    setRevokeDeviceDialogOpen(false);
    setRevokeUser(null);
    setTargetDevice(null);
  };

  const handleDeviceRevokeSubmit = async () => {
    if (!revokeUser || !targetDevice) return;
    setDeviceSubmitting(true);
    try {
      await repository.revokeAdminUserDevice(revokeUser.userId, targetDevice.deviceId, deviceAuditReason.trim());
      setSuccessMsg(`已成功撤销设备 ${targetDevice.deviceId}`);
      closeRevokeDeviceDialog();
      if (drawerUser && drawerUser.userId === revokeUser.userId) {
        refreshCurrentDrawer(revokeUser.userId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '撤销设备失败');
    } finally {
      setDeviceSubmitting(false);
    }
  };

  /* ------------------- 5. 余额 / 额度调整 逻辑 ------------------- */
  const openAdjustDialog = async (user: AdminUserSummary) => {
    setAdjustUser(user);
    setAdjustUnit(EntitlementAdjustmentRequestUnitEnum.Energy);
    setAdjustDelta(0);
    setAdjustReasonCode('');
    setAdjustAuditReason('');
    setAdjustConfirmUserId('');
    setAdjustDialogOpen(true);
    try {
      const data = await repository.getAdminUserDetail(user.userId);
      setAdjustDetail(data.detail);
    } catch {
      setAdjustDetail(null);
    }
  };

  const closeAdjustDialog = () => {
    setAdjustDialogOpen(false);
    setAdjustUser(null);
    setAdjustDetail(null);
  };

  const handleAdjustSubmit = async () => {
    if (!adjustUser) return;
    setAdjustSubmitting(true);
    try {
      const cleanReasonCode = adjustReasonCode.trim();
      await repository.adjustAdminUserEntitlement(
        adjustUser.userId,
        adjustUnit,
        adjustDelta,
        cleanReasonCode,
        adjustAuditReason.trim(),
      );
      setSuccessMsg(`已成功提交用户 ${adjustUser.userId} 的 ${adjustUnit} 记账变动`);
      closeAdjustDialog();
      fetchUsers();
      if (drawerUser && drawerUser.userId === adjustUser.userId) {
        refreshCurrentDrawer(adjustUser.userId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '调整余额额度失败');
    } finally {
      setAdjustSubmitting(false);
    }
  };

  /* ------------------- 6. 套餐分配 逻辑 ------------------- */
  const openGrantPlanDialog = async (user: AdminUserSummary) => {
    setGrantUser(user);
    setSelectedProductVersionId('');
    setGrantAuditReason('');
    setGrantConfirmUserId('');
    setGrantPlanDialogOpen(true);
    setGrantLoadingProducts(true);

    try {
      const [allProducts, detailData] = await Promise.all([
        repository.getProducts(),
        repository.getAdminUserDetail(user.userId).catch(() => null),
      ]);
      // 只保留 productType=PLAN 且 status=ACTIVE 的发布套餐
      const activePlans = allProducts.filter(
        (p) => p.productType === ProductType.Plan && p.status === ProductPublicationStatus.Active,
      );
      setActivePlanProducts(activePlans);
      if (activePlans.length > 0) {
        setSelectedProductVersionId(activePlans[0].productVersionId);
      }
      if (detailData && detailData.entitlements.length > 0) {
        setGrantEntitlementVersion(detailData.entitlements[0].resourceVersion || 1);
      } else {
        setGrantEntitlementVersion(1);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '获取可分配套餐失败');
    } finally {
      setGrantLoadingProducts(false);
    }
  };

  const closeGrantPlanDialog = () => {
    setGrantPlanDialogOpen(false);
    setGrantUser(null);
  };

  const handleGrantPlanSubmit = async () => {
    if (!grantUser || !selectedProductVersionId) return;
    setGrantSubmitting(true);
    try {
      await repository.grantAdminUserPlan(
        grantUser.userId,
        selectedProductVersionId,
        grantAuditReason.trim(),
        grantEntitlementVersion,
      );
      setSuccessMsg(`已成功为用户 ${grantUser.userId} 分配套餐并叠加权益`);
      closeGrantPlanDialog();
      fetchUsers();
      if (drawerUser && drawerUser.userId === grantUser.userId) {
        refreshCurrentDrawer(grantUser.userId);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '分配套餐失败');
    } finally {
      setGrantSubmitting(false);
    }
  };

  /* ------------------- 确认逻辑校验计算 ------------------- */
  const isReasonValid = (reason: string) => reason.trim().length >= 8;
  const isIdConfirmed = (input: string, expected: string) => input.trim() === expected;

  const canSubmitStatus = isReasonValid(statusAuditReason) && actionUser && isIdConfirmed(statusConfirmUserId, actionUser.userId) && !statusSubmitting;
  const canSubmitProfile = isReasonValid(profileAuditReason) && profileUser && isIdConfirmed(profileConfirmUserId, profileUser.userId) && !profileSubmitting;
  const canSubmitReset = isReasonValid(resetAuditReason) && resetUser && isIdConfirmed(resetConfirmUserId, resetUser.userId) && !resetSubmitting;
  const canSubmitDeviceRevoke = isReasonValid(deviceAuditReason) && targetDevice && isIdConfirmed(deviceConfirmId, targetDevice.deviceId) && !deviceSubmitting;
  const canSubmitAdjust = isReasonValid(adjustAuditReason) && adjustUser && isIdConfirmed(adjustConfirmUserId, adjustUser.userId) && adjustDelta !== 0 && isReasonCodeValid(adjustReasonCode) && !adjustSubmitting;
  const canSubmitGrant = isReasonValid(grantAuditReason) && grantUser && isIdConfirmed(grantConfirmUserId, grantUser.userId) && selectedProductVersionId !== '' && !grantSubmitting;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部标题与广播反馈 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)' }}>用户管理</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            检索全局脱敏用户、管理账户状态与资料、控制验证码登录安全与设备、手动记账增减配额与分配套餐。
          </p>
        </div>
        <Button variant="default" onClick={fetchUsers} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> 刷新
        </Button>
      </div>

      {successMsg && (
        <div style={{ padding: '12px 16px', background: 'var(--color-success-bg)', color: 'var(--color-success)', borderRadius: 'var(--radius-sm)', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle size={16} />
            <span>{successMsg}</span>
          </div>
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
            未搜索到符合条件的脱敏用户信息
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="responsive-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-sub)', borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>用户 ID / 昵称</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>脱敏标识</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>状态</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>套餐与到期时间</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>余额与余量摘要</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>注册 / 更新</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>管理操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSuspended = u.status === AccountStatus.Suspended;
                  return (
                    <tr key={u.userId} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td data-label="用户 ID / 昵称" style={{ padding: '12px 16px' }}>
                        <div style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--color-text-primary)' }}>{u.userId}</div>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>{u.nickname || '未设置昵称'}</div>
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
                      <td data-label="套餐与到期时间" style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 500 }}>{u.planCode || '免费版'}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                          到期: {u.planExpiresAt ? new Date(u.planExpiresAt).toLocaleDateString('zh-CN') : '未生效/永久'}
                        </div>
                      </td>
                      <td data-label="余额与余量摘要" style={{ padding: '12px 16px' }}>
                        <div>文本: {u.textRemaining ?? 0} 次 | 视觉: {u.visionRemaining ?? 0} 次</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                          代币余额: {(u.energyBalance ?? 0).toLocaleString()}
                        </div>
                      </td>
                      <td data-label="注册 / 更新" style={{ padding: '12px 16px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        <div>注册: {new Date(u.createdAt).toLocaleDateString('zh-CN')}</div>
                        <div>更新: {new Date(u.updatedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</div>
                      </td>
                      <td data-label="管理操作" style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                          <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openUserDrawer(u)}>
                            详情
                          </Button>
                          <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openProfileDialog(u)}>
                            <Edit size={13} /> 资料
                          </Button>
                          <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openAdjustDialog(u)}>
                            <Sliders size={13} /> 调额
                          </Button>
                          <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openGrantPlanDialog(u)}>
                            <Gift size={13} /> 套餐
                          </Button>
                          <Button variant="default" style={{ height: '28px', padding: '0 8px', fontSize: '12px' }} onClick={() => openResetDialog(u)}>
                            <Lock size={13} /> 登录安全
                          </Button>
                          {isSuspended ? (
                            <Button
                              variant="default"
                              style={{ height: '28px', padding: '0 8px', fontSize: '12px', color: 'var(--color-success)' }}
                              onClick={() => openStatusDialog(u, AccountStatus.Active)}
                            >
                              <UserCheck size={13} /> 解冻
                            </Button>
                          ) : (
                            <Button
                              variant="danger"
                              style={{ height: '28px', padding: '0 8px', fontSize: '12px' }}
                              onClick={() => openStatusDialog(u, AccountStatus.Suspended)}
                            >
                              <UserX size={13} /> 冻结
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
        title={drawerUser ? `用户详情管理 - ${drawerUser.userId}` : '用户详情'}
      >
        {drawerLoading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>加载详情数据中...</div>
        ) : userDetail && drawerUser ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* 抽屉顶部：用户综合头图 Banner 结构 (无嵌套 Card) */}
            <div style={{ padding: '16px', background: 'var(--color-surface-sub)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                {userDetail.avatarUrl ? (
                  <img
                    src={userDetail.avatarUrl}
                    alt="头像"
                    style={{ width: '48px', height: '48px', borderRadius: '50%', objectFit: 'cover', border: '1px solid var(--color-border)' }}
                  />
                ) : (
                  <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'var(--color-surface-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-secondary)' }}>
                    <User size={24} />
                  </div>
                )}
                <div style={{ flex: 1, minWidth: '160px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{userDetail.nickname || '未设置昵称'}</span>
                    <Badge variant={userDetail.status === AccountStatus.Active ? 'success' : 'danger'}>
                      {userDetail.status}
                    </Badge>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)', marginTop: '2px', fontFamily: 'monospace' }}>
                    ID: {userDetail.userId}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={() => openProfileDialog(drawerUser)}>
                    <Edit size={12} /> 编辑资料
                  </Button>
                  <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={() => openAdjustDialog(drawerUser)}>
                    <Sliders size={12} /> 调整额度
                  </Button>
                  <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={() => openGrantPlanDialog(drawerUser)}>
                    <Gift size={12} /> 分配套餐
                  </Button>
                </div>
              </div>

              {/* 关键属性仪表格 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', fontSize: '12px', borderTop: '1px solid var(--color-border)', paddingTop: '10px' }}>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', display: 'block' }}>认证方式</span>
                  <span style={{ fontWeight: 500, wordBreak: 'break-all' }}><Lock size={11} style={{ display: 'inline', marginRight: '2px' }} />邮件/短信验证码（无密码）</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', display: 'block' }}>语言 / 时区</span>
                  <span style={{ fontWeight: 500 }}><Globe size={11} style={{ display: 'inline', marginRight: '2px' }} />{userDetail.locale} ({userDetail.timeZone})</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', display: 'block' }}>等级 / 套餐</span>
                  <span style={{ fontWeight: 600, color: 'var(--color-primary)' }}>{userDetail.planCode || '免费版'}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', display: 'block' }}>套餐到期时间</span>
                  <span><Clock size={11} style={{ display: 'inline', marginRight: '2px' }} />{userDetail.planExpiresAt ? new Date(userDetail.planExpiresAt).toLocaleDateString('zh-CN') : '永久有效'}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', display: 'block' }}>代币余额 (Energy)</span>
                  <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{(userDetail.energyBalance ?? 0).toLocaleString()}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--color-text-tertiary)', display: 'block' }}>文本 / 视觉余量</span>
                  <span>{userDetail.textRemaining ?? 0} 次 / {userDetail.visionRemaining ?? 0} 次</span>
                </div>
              </div>
            </div>

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

            {/* Tab 内容区 - 不嵌套 Card 结构 */}
            {drawerTab === 'devices' && (
              <div>
                {userDevices.length === 0 ? (
                  <div style={{ padding: '20px', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>暂无绑定的关联设备</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {userDevices.map((d) => {
                      const isRevoked = !!d.revokedAt;
                      return (
                        <div key={d.deviceId} style={{ padding: '12px', background: 'var(--color-surface-sub)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
                              <span style={{ fontWeight: 600 }}>{d.model || d.deviceId}</span>
                              <span style={{ color: 'var(--color-text-tertiary)', fontSize: '11px' }}>({d.platform})</span>
                              {d.current && !isRevoked && <Badge variant="success">在线</Badge>}
                              {isRevoked && <Badge variant="danger">已撤销</Badge>}
                            </div>
                            <div style={{ display: 'flex', gap: '16px', marginTop: '6px', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                              <div>设备 ID: {d.deviceId}</div>
                              <div>最近上线: {new Date(d.lastSeenAt).toLocaleString('zh-CN')}</div>
                              {isRevoked && <div style={{ color: 'var(--color-danger)' }}>撤销时间: {new Date(d.revokedAt!).toLocaleString('zh-CN')}</div>}
                            </div>
                          </div>
                          <div>
                            {isRevoked ? (
                              <Button variant="default" disabled style={{ height: '26px', padding: '0 8px', fontSize: '11px' }}>
                                已撤销不可重复操作
                              </Button>
                            ) : (
                              <Button
                                variant="danger"
                                style={{ height: '26px', padding: '0 8px', fontSize: '11px' }}
                                onClick={() => openRevokeDeviceDialog(drawerUser, d)}
                              >
                                <ShieldX size={12} /> 撤销设备
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
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
                      <div key={idx} style={{ padding: '12px', background: 'var(--color-surface-sub)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
                          <span style={{ fontWeight: 600 }}>套餐代码: {e.planCode}</span>
                          <Badge variant="default">已生效 (v{e.resourceVersion || 1})</Badge>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '6px' }}>
                          文本对话余量: {e.benefits?.textRemaining ?? '不限'} 次 | 视觉生成余量: {e.benefits?.visionRemaining ?? '不限'} 次
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '4px' }}>
                          到期时间: {e.planExpiresAt ? new Date(e.planExpiresAt).toLocaleDateString('zh-CN') : '永久有效'} | 钱包余额: {e.wallet?.energyBalance?.toLocaleString() ?? 0}
                        </div>
                      </div>
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
                      <div key={w.ledgerEntryId} style={{ padding: '10px 12px', background: 'var(--color-surface-sub)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
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

      {/* ------------------- 1. 冻结 / 恢复 对话框 ------------------- */}
      <Dialog
        open={statusDialogOpen}
        onClose={closeStatusDialog}
        title={targetStatus === AccountStatus.Suspended ? '高风险操作：冻结用户账号' : '解冻用户账号'}
      >
        {actionUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {targetStatus === AccountStatus.Suspended && (
              <div style={{ padding: '12px 16px', background: 'var(--color-danger-bg)', color: 'var(--color-danger)', borderRadius: 'var(--radius-sm)', fontSize: '13px', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                <ShieldAlert size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600 }}>高风险警告：即刻撤销活跃会话 (Session)</div>
                  <div style={{ fontSize: '12px', marginTop: '2px' }}>
                    冻结账号将立刻使其客户端下线并撤销所有已颁发的令牌，用户必须重新验证身份后方可恢复。
                  </div>
                </div>
              </div>
            )}

            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{actionUser.userId}</code>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请详细输入变更理由（例如：收到风控违规举报，暂时冻结核查）"
                value={statusAuditReason}
                onChange={(e) => setStatusAuditReason(e.target.value)}
                rows={3}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '4px', color: isReasonValid(statusAuditReason) ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {statusAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
                二次确认：请输入完整用户 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${actionUser.userId}" 确认`}
                value={statusConfirmUserId}
                onChange={(e) => setStatusConfirmUserId(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
              <Button variant="default" onClick={closeStatusDialog} disabled={statusSubmitting}>
                取消
              </Button>
              <Button
                variant={targetStatus === AccountStatus.Suspended ? 'danger' : 'primary'}
                onClick={handleStatusSubmit}
                disabled={!canSubmitStatus}
              >
                {statusSubmitting ? '提交中...' : targetStatus === AccountStatus.Suspended ? '确认冻结账号' : '确认解冻账号'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* ------------------- 2. 资料编辑 对话框 ------------------- */}
      <Dialog
        open={profileDialogOpen}
        onClose={closeProfileDialog}
        title="编辑用户非凭据基础资料"
      >
        {profileUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{profileUser.userId}</code>
              （当前资源版本 v{profileResourceVersion}）
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>用户昵称</label>
              <Input placeholder="输入新昵称" value={editNickname} onChange={(e) => setEditNickname(e.target.value)} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>头像图片 URL</label>
              <Input placeholder="https://example.com/avatar.jpg" value={editAvatarUrl} onChange={(e) => setEditAvatarUrl(e.target.value)} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>首选语言 (Locale)</label>
                <Input value={editLocale} onChange={(e) => setEditLocale(e.target.value)} placeholder="zh-CN" />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>首选时区 (TimeZone)</label>
                <Input value={editTimeZone} onChange={(e) => setEditTimeZone(e.target.value)} placeholder="Asia/Shanghai" />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请输入资料变更审计理由（例如：用户申请人工更正展示昵称）"
                value={profileAuditReason}
                onChange={(e) => setProfileAuditReason(e.target.value)}
                rows={2}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid(profileAuditReason) ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {profileAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                二次确认：请输入完整用户 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${profileUser.userId}" 确认`}
                value={profileConfirmUserId}
                onChange={(e) => setProfileConfirmUserId(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '6px' }}>
              <Button variant="default" onClick={closeProfileDialog} disabled={profileSubmitting}>取消</Button>
              <Button variant="primary" onClick={handleProfileSubmit} disabled={!canSubmitProfile}>
                {profileSubmitting ? '保存中...' : '保存修改'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* ------------------- 3. 登录安全重置 对话框 ------------------- */}
      <Dialog
        open={resetDialogOpen}
        onClose={closeResetDialog}
        title="登录安全控制（撤销全部登录状态）"
      >
        {resetUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ padding: '12px', background: 'var(--color-surface-sub)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Lock size={14} /> 验证码登录安全机制说明
              </div>
              本系统普通用户严格采用<strong>邮件 / 短信验证码</strong>无密码登录，后端没有普通用户密码字段，不存在可查看或修改的普通用户密码。
              <div style={{ marginTop: '6px', color: 'var(--color-danger)' }}>
                管理员可以执行的是<strong>撤销全部登录状态</strong>，包括强制注销全部在线会话 (Session) 与失效未使用的验证码。
              </div>
            </div>

            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{resetUser.userId}</code>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请输入安全重置理由（例如：用户反馈手机丢失请求紧急冻结并注销登录）"
                value={resetAuditReason}
                onChange={(e) => setResetAuditReason(e.target.value)}
                rows={2}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid(resetAuditReason) ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {resetAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                二次确认：请输入完整用户 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${resetUser.userId}" 确认`}
                value={resetConfirmUserId}
                onChange={(e) => setResetConfirmUserId(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '6px' }}>
              <Button variant="default" onClick={closeResetDialog} disabled={resetSubmitting}>取消</Button>
              <Button variant="danger" onClick={handleResetSubmit} disabled={!canSubmitReset}>
                {resetSubmitting ? '撤销中...' : '撤销全部登录状态'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* ------------------- 4. 设备撤销 对话框 ------------------- */}
      <Dialog
        open={revokeDeviceDialogOpen}
        onClose={closeRevokeDeviceDialog}
        title="撤销关联设备令牌"
      >
        {revokeUser && targetDevice && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{revokeUser.userId}</code>
            </div>

            <div style={{ padding: '10px 12px', background: 'var(--color-surface-sub)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
              <div>设备名称/型号: <strong>{targetDevice.model || targetDevice.deviceId}</strong></div>
              <div style={{ marginTop: '2px', color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>设备 ID: {targetDevice.deviceId}</div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                审计撤销理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请输入设备撤销理由（例如：用户报失该手机设备请求关停）"
                value={deviceAuditReason}
                onChange={(e) => setDeviceAuditReason(e.target.value)}
                rows={2}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid(deviceAuditReason) ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {deviceAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                二次确认：请输入完整设备 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${targetDevice.deviceId}" 确认`}
                value={deviceConfirmId}
                onChange={(e) => setDeviceConfirmId(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '6px' }}>
              <Button variant="default" onClick={closeRevokeDeviceDialog} disabled={deviceSubmitting}>取消</Button>
              <Button variant="danger" onClick={handleDeviceRevokeSubmit} disabled={!canSubmitDeviceRevoke}>
                {deviceSubmitting ? '撤销中...' : '确认撤销该设备'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* ------------------- 5. 余额 / 额度手动调整 对话框 ------------------- */}
      <Dialog
        open={adjustDialogOpen}
        onClose={closeAdjustDialog}
        title="手工双向增减余额与配额"
      >
        {adjustUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* 提示信息说明 */}
            <div style={{ padding: '10px 12px', background: 'var(--color-surface-sub)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              <div style={{ fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: '4px' }}>
                记账规则：以增减量 (Delta) 增量记账，不直接覆写已有绝对值
              </div>
              {adjustDetail && (
                <div>
                  当前参考值 — 余额: <strong>{(adjustDetail.energyBalance ?? 0).toLocaleString()}</strong> | 文本: <strong>{adjustDetail.textRemaining ?? 0}</strong> 次 | 视觉: <strong>{adjustDetail.visionRemaining ?? 0}</strong> 次
                </div>
              )}
            </div>

            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{adjustUser.userId}</code>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>调整单位 Unit</label>
                <Select
                  value={adjustUnit}
                  onChange={(e) => setAdjustUnit(e.target.value as any)}
                >
                  <option value={EntitlementAdjustmentRequestUnitEnum.Energy}>代币余额 (ENERGY)</option>
                  <option value={EntitlementAdjustmentRequestUnitEnum.TextQuota}>文本余量 (TEXT_QUOTA)</option>
                  <option value={EntitlementAdjustmentRequestUnitEnum.VisionQuota}>视觉余量 (VISION_QUOTA)</option>
                  <option value={EntitlementAdjustmentRequestUnitEnum.PlanDays}>套餐天数 (PLAN_DAYS)</option>
                </Select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>变动增减量 Delta (正增负减) <span style={{ color: 'var(--color-danger)' }}>*</span></label>
                <Input
                  type="number"
                  value={adjustDelta}
                  onChange={(e) => setAdjustDelta(Number(e.target.value) || 0)}
                  placeholder="例如: 100 或 -50"
                />
                {adjustDelta === 0 && (
                  <div style={{ fontSize: '11px', color: 'var(--color-danger)', marginTop: '2px' }}>
                    变动增减量 Delta 必须为非零数值（正数增加，负数扣减）
                  </div>
                )}
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                记账原因代码 ReasonCode <span style={{ color: 'var(--color-danger)' }}>*</span> <span style={{ color: 'var(--color-text-tertiary)', fontSize: '11px' }}>(匹配 ^[A-Z][A-Z0-9_]*$)</span>
              </label>
              <Input
                placeholder="例如: ADMIN_MANUAL_ADJUSTMENT, REFUND_COMPENSATION"
                value={adjustReasonCode}
                onChange={(e) => setAdjustReasonCode(e.target.value)}
              />
              {adjustReasonCode.trim().length > 0 && !isReasonCodeValid(adjustReasonCode) && (
                <div style={{ fontSize: '11px', color: 'var(--color-danger)', marginTop: '2px' }}>
                  原因代码格式无效！必须以大写英文字母开头，且仅包含大写字母、数字及下划线（无需包含空格）。
                </div>
              )}
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请输入调额审计理由（例如：用户活动补发 100 文本额度）"
                value={adjustAuditReason}
                onChange={(e) => setAdjustAuditReason(e.target.value)}
                rows={2}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid(adjustAuditReason) ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {adjustAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                二次确认：请输入完整用户 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${adjustUser.userId}" 确认`}
                value={adjustConfirmUserId}
                onChange={(e) => setAdjustConfirmUserId(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '6px' }}>
              <Button variant="default" onClick={closeAdjustDialog} disabled={adjustSubmitting}>取消</Button>
              <Button variant="primary" onClick={handleAdjustSubmit} disabled={!canSubmitAdjust}>
                {adjustSubmitting ? '提交记账中...' : '确认提交变动'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>

      {/* ------------------- 6. 套餐分配 对话框 ------------------- */}
      <Dialog
        open={grantPlanDialogOpen}
        onClose={closeGrantPlanDialog}
        title="在线分配已发布套餐"
      >
        {grantUser && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ padding: '10px 12px', background: 'var(--color-surface-sub)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-sm)', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              直接分配将按该套餐在系统中发布的快照叠加权益，若已有未到期套餐，到期时间将在现有基础顺延。
            </div>

            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              目标用户 ID：<code style={{ background: 'var(--color-surface-hover)', padding: '2px 6px', borderRadius: '4px' }}>{grantUser.userId}</code>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>选择活跃发布套餐 (PLAN / ACTIVE)</label>
              {grantLoadingProducts ? (
                <div style={{ padding: '12px', fontSize: '12px', color: 'var(--color-text-tertiary)' }}>加载已发布套餐数据中...</div>
              ) : activePlanProducts.length === 0 ? (
                <div style={{ padding: '12px', fontSize: '12px', color: 'var(--color-danger)' }}>暂无符合条件的 active PLAN 发布套餐</div>
              ) : (
                <Select
                  value={selectedProductVersionId}
                  onChange={(e) => setSelectedProductVersionId(e.target.value)}
                >
                  {activePlanProducts.map((p) => (
                    <option key={p.productVersionId} value={p.productVersionId}>
                      {p.displayName} ({p.productCode} v{p.version}) - {formatAmountMinor(p.amountMinor, p.currency)}
                    </option>
                  ))}
                </Select>
              )}
            </div>

            {/* 所选套餐数据明细预览 - 全部读取动态字段 */}
            {selectedProductVersionId && (() => {
              const selectedProduct = activePlanProducts.find((p) => p.productVersionId === selectedProductVersionId);
              if (!selectedProduct) return null;
              return (
                <div style={{ padding: '10px 12px', background: 'var(--color-surface-sub)', border: '1px dotted var(--color-border)', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
                  <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{selectedProduct.displayName} (代码: {selectedProduct.productCode})</div>
                  <div style={{ marginTop: '4px', color: 'var(--color-text-secondary)' }}>
                    价格: <strong>{formatAmountMinor(selectedProduct.amountMinor, selectedProduct.currency)}</strong> | 有效期: <strong>{selectedProduct.termDays ? `${selectedProduct.termDays} 天` : '未指定/报错'}</strong>
                  </div>
                  <div style={{ marginTop: '2px', color: 'var(--color-text-secondary)' }}>
                    包含额度 — 文本: <strong>{selectedProduct.benefits?.textQuota ?? 0}</strong> 次 | 视觉: <strong>{selectedProduct.benefits?.visionQuota ?? 0}</strong> 次
                  </div>
                </div>
              );
            })()}

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                审计变更理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
              </label>
              <Textarea
                placeholder="请输入分配套餐审计理由（例如：管理员手动赠送月度套餐）"
                value={grantAuditReason}
                onChange={(e) => setGrantAuditReason(e.target.value)}
                rows={2}
              />
              <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isReasonValid(grantAuditReason) ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
                当前字数: {grantAuditReason.trim().length} / 至少 8 字
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                二次确认：请输入完整用户 ID <span style={{ color: 'var(--color-danger)' }}>*</span>
              </label>
              <Input
                placeholder={`请输入 "${grantUser.userId}" 确认`}
                value={grantConfirmUserId}
                onChange={(e) => setGrantConfirmUserId(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '6px' }}>
              <Button variant="default" onClick={closeGrantPlanDialog} disabled={grantSubmitting}>取消</Button>
              <Button variant="primary" onClick={handleGrantPlanSubmit} disabled={!canSubmitGrant}>
                {grantSubmitting ? '分配中...' : '确认分配该套餐'}
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
};
