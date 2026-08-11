/**
 * 管理后台 - 邀请推广运营管理页面。
 * 提供邀请活动（Referral Campaign）多版本配置、多阶里程碑奖励规则设置、
 * 严格防作弊规则定义（同设备/同支付身份/风控分）、灰度滚动上线与真实历史版本回退功能。
 * 使用 @tanstack/react-query 进行数据流管理。
 */
import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UserPlus,
  Plus,
  RefreshCw,
  Edit3,
  Send,
  RotateCcw,
  ShieldAlert,
  Award,
  Users,
  AlertCircle,
  Trash2,
  Sliders,
  CheckCircle2,
  Loader2,
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
  ReferralCampaignStatus,
  ReferralMilestoneCode,
  ReferralBeneficiary,
  RewardUnit,
  SalesChannel,
} from '../../api/models';
import type {
  ReferralCampaign,
  ReferralRewardRule,
  ReferralCampaignVersion,
  ReferralCampaignWriteRequest,
  PublishReferralCampaignRequest,
  RollbackReferralCampaignRequest,
} from '../../api/models';

/** 表单默认的初值接口 */
interface FormState {
  campaignCode: string;
  displayName: string;
  description: string;
  region: string;
  salesChannels: SalesChannel[];
  bindingWindowHours: number;
  maxQualifiedInvitesPerInviter: number;
  rewardRules: ReferralRewardRule[];
  antiAbusePolicy: {
    blockSelfReferral: true;
    blockSameDevice: boolean;
    blockSamePaymentIdentity: boolean;
    requireVerifiedPrimaryChannel: boolean;
    riskReviewScore: number;
  };
}

/** 空白新建表单的最小初值配置（不预填任何业务运营值） */
const createEmptyFormState = (): FormState => ({
  campaignCode: '',
  displayName: '',
  description: '',
  region: '',
  salesChannels: [],
  bindingWindowHours: 1,
  maxQualifiedInvitesPerInviter: 1,
  rewardRules: [
    {
      milestoneCode: ReferralMilestoneCode.AccountVerified,
      beneficiary: ReferralBeneficiary.Inviter,
      rewardUnit: RewardUnit.Energy,
      rewardAmount: 1,
      coolingOffHours: 0,
    },
  ],
  antiAbusePolicy: {
    blockSelfReferral: true,
    blockSameDevice: false,
    blockSamePaymentIdentity: false,
    requireVerifiedPrimaryChannel: false,
    riskReviewScore: 0,
  },
});

export const ReferralsPage: React.FC = () => {
  const queryClient = useQueryClient();

  // 全局消息与操作提示
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 筛选与搜索
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // 1. React Query 查询邀请活动列表
  const {
    data: campaigns = [],
    isLoading,
    isRefetching,
    error: queryError,
    refetch,
  } = useQuery<ReferralCampaign[], Error>({
    queryKey: ['referralCampaigns'],
    queryFn: () => repository.getAdminReferralCampaigns(),
  });

  // 2. 表单 Modal 状态 (新建/编辑草稿)
  const [formOpen, setFormOpen] = useState<boolean>(false);
  const [editingCampaign, setEditingCampaign] = useState<ReferralCampaign | null>(null);
  const [formState, setFormState] = useState<FormState>(createEmptyFormState());
  const [formError, setFormError] = useState<string | null>(null);

  // 3. 灰度发布 Modal 状态
  const [publishCampaign, setPublishCampaign] = useState<ReferralCampaign | null>(null);
  const [publishState, setPublishState] = useState<{
    rolloutPercentage: number;
    effectiveAtStr: string;
    expiresAtStr: string;
    auditReason: string;
  }>({
    rolloutPercentage: 1,
    effectiveAtStr: '',
    expiresAtStr: '',
    auditReason: '',
  });
  const [publishError, setPublishError] = useState<string | null>(null);

  // 4. 版本回退 Modal 状态
  const [rollbackCampaign, setRollbackCampaign] = useState<ReferralCampaign | null>(null);
  const [rollbackState, setRollbackState] = useState<{
    targetVersion?: number;
    auditReason: string;
  }>({
    targetVersion: undefined,
    auditReason: '',
  });
  const [rollbackError, setRollbackError] = useState<string | null>(null);

  // 查询当前被选中的活动的历史版本列表（仅当 rollbackCampaign 打开时使能）
  const {
    data: campaignVersions = [],
    isLoading: isVersionsLoading,
  } = useQuery<ReferralCampaignVersion[], Error>({
    queryKey: ['referralCampaignVersions', rollbackCampaign?.campaignId],
    queryFn: () => repository.getAdminReferralCampaignVersions(rollbackCampaign!.campaignId),
    enabled: !!rollbackCampaign?.campaignId,
  });

  // 过滤出合法可回退的历史版本：wasPublished 为 true 且版本号严格小于当前版本号
  const validRollbackVersions = useMemo(() => {
    if (!rollbackCampaign) return [];
    return campaignVersions.filter(
      (v) => v.wasPublished === true && v.version < rollbackCampaign.version
    );
  }, [campaignVersions, rollbackCampaign]);

  /* ── Mutations ── */

  // 保存/修改草稿 Mutation
  const saveMutation = useMutation({
    mutationFn: ({
      request,
      campaignId,
      resourceVersion,
    }: {
      request: ReferralCampaignWriteRequest;
      campaignId?: string;
      resourceVersion?: number;
    }) => repository.saveAdminReferralCampaign(request, campaignId, resourceVersion),
    onSuccess: (updatedCampaign) => {
      queryClient.invalidateQueries({ queryKey: ['referralCampaigns'] });
      setFormOpen(false);
      setSuccessMsg(
        editingCampaign
          ? `活动 "${updatedCampaign.displayName}" 草稿已成功更新！`
          : `新活动 "${updatedCampaign.displayName}" 草稿已成功创建！`
      );
    },
    onError: (err: Error) => {
      setFormError(err.message || '保存活动草稿失败');
    },
  });

  // 灰度发布 Mutation
  const publishMutation = useMutation({
    mutationFn: ({
      campaignId,
      resourceVersion,
      request,
    }: {
      campaignId: string;
      resourceVersion: number;
      request: PublishReferralCampaignRequest;
    }) => repository.publishAdminReferralCampaign(campaignId, resourceVersion, request),
    onSuccess: (updatedCampaign) => {
      queryClient.invalidateQueries({ queryKey: ['referralCampaigns'] });
      closePublishModal();
      setSuccessMsg(`活动 "${updatedCampaign.displayName}" 上线发布成功！`);
    },
    onError: (err: Error) => {
      setPublishError(err.message || '发布活动失败');
    },
  });

  // 版本回退 Mutation
  const rollbackMutation = useMutation({
    mutationFn: ({
      campaignId,
      resourceVersion,
      request,
    }: {
      campaignId: string;
      resourceVersion: number;
      request: RollbackReferralCampaignRequest;
    }) => repository.rollbackAdminReferralCampaign(campaignId, resourceVersion, request),
    onSuccess: (updatedCampaign) => {
      queryClient.invalidateQueries({ queryKey: ['referralCampaigns'] });
      queryClient.invalidateQueries({
        queryKey: ['referralCampaignVersions', updatedCampaign.campaignId],
      });
      closeRollbackModal();
      setSuccessMsg(`活动 "${updatedCampaign.displayName}" 已成功回退至版本 v${updatedCampaign.version}！`);
    },
    onError: (err: Error) => {
      setRollbackError(err.message || '版本回退失败');
    },
  });

  /* ── 列表筛选与动态 KPI 统计（完全源自 Query 返回的数据） ── */

  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((c) => {
      if (statusFilter && c.status !== statusFilter) return false;
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchCode = c.campaignCode.toLowerCase().includes(term);
        const matchName = c.displayName.toLowerCase().includes(term);
        return matchCode || matchName;
      }
      return true;
    });
  }, [campaigns, statusFilter, searchTerm]);

  const kpiStats = useMemo(() => {
    const total = campaigns.length;
    const active = campaigns.filter((c) => c.status === ReferralCampaignStatus.Active).length;
    const avgScore = total
      ? Math.round(campaigns.reduce((sum, c) => sum + c.antiAbusePolicy.riskReviewScore, 0) / total)
      : 0;
    const totalRules = campaigns.reduce((sum, c) => sum + c.rewardRules.length, 0);
    return { total, active, avgScore, totalRules };
  }, [campaigns]);

  /* ── Modal 控制与初始化 ── */

  // 打开创建 / 编辑对话框
  const openFormModal = (campaign?: ReferralCampaign) => {
    setFormError(null);
    if (campaign) {
      setEditingCampaign(campaign);
      setFormState({
        campaignCode: campaign.campaignCode,
        displayName: campaign.displayName,
        description: campaign.description,
        region: campaign.region,
        salesChannels: Array.from(campaign.salesChannels),
        bindingWindowHours: campaign.bindingWindowHours,
        maxQualifiedInvitesPerInviter: campaign.maxQualifiedInvitesPerInviter,
        rewardRules: campaign.rewardRules.map((r) => ({ ...r })),
        antiAbusePolicy: { ...campaign.antiAbusePolicy, blockSelfReferral: true },
      });
    } else {
      setEditingCampaign(null);
      setFormState(createEmptyFormState());
    }
    setFormOpen(true);
  };

  const closeFormModal = () => {
    setFormOpen(false);
    setEditingCampaign(null);
    setFormError(null);
  };

  // 打开发布 Modal
  const openPublishModal = (campaign: ReferralCampaign) => {
    setPublishCampaign(campaign);
    setPublishError(null);
    setPublishState({
      rolloutPercentage: 1,
      effectiveAtStr: '',
      expiresAtStr: '',
      auditReason: '',
    });
  };

  const closePublishModal = () => {
    setPublishCampaign(null);
    setPublishError(null);
    setPublishState({
      rolloutPercentage: 1,
      effectiveAtStr: '',
      expiresAtStr: '',
      auditReason: '',
    });
  };

  // 打开回退 Modal
  const openRollbackModal = (campaign: ReferralCampaign) => {
    setRollbackCampaign(campaign);
    setRollbackError(null);
    setRollbackState({
      targetVersion: undefined,
      auditReason: '',
    });
  };

  const closeRollbackModal = () => {
    setRollbackCampaign(null);
    setRollbackError(null);
    setRollbackState({
      targetVersion: undefined,
      auditReason: '',
    });
  };

  /* ── 独立 Validate 校验逻辑 ── */

  /** 严格的草稿表单数据校验 */
  const validateForm = (): string | null => {
    const codeRegex = /^[A-Z][A-Z0-9_]{1,63}$/;
    if (!codeRegex.test(formState.campaignCode)) {
      return '活动编码格式不正确：必须以大写字母开头，只能包含大写字母、数字和下划线，长度为 2 至 64 位。';
    }

    const nameLen = formState.displayName.trim().length;
    if (nameLen < 1 || nameLen > 128) {
      return '活动显示名称不能为空，且长度不能超过 128 个字符。';
    }

    const descLen = formState.description.trim().length;
    if (descLen < 1 || descLen > 500) {
      return '活动描述不能为空，且长度不能超过 500 个字符。';
    }

    const regionLen = formState.region.trim().length;
    if (regionLen < 2 || regionLen > 16) {
      return '适用的国家/地区代码不能为空，且长度须在 2 至 16 个字符之间。';
    }

    if (!formState.salesChannels || formState.salesChannels.length === 0) {
      return '请至少选择一个适用销售渠道。';
    }

    if (formState.bindingWindowHours < 1 || formState.bindingWindowHours > 720) {
      return '绑定关系有效期须在 1 至 720 小时之间。';
    }

    if (
      formState.maxQualifiedInvitesPerInviter < 1 ||
      formState.maxQualifiedInvitesPerInviter > 100000
    ) {
      return '单人最大有效邀请上线须在 1 至 100,000 人之间。';
    }

    if (!formState.rewardRules || formState.rewardRules.length < 1 || formState.rewardRules.length > 20) {
      return '奖励规则数量必须在 1 至 20 条之间。';
    }

    // 校验每条规则的具体要求与唯一性
    const ruleSet = new Set<string>();
    for (let i = 0; i < formState.rewardRules.length; i++) {
      const r: ReferralRewardRule = formState.rewardRules[i];
      if (r.rewardAmount < 1) {
        return `第 ${i + 1} 条奖励规则的发放数量必须大于等于 1。`;
      }
      if (r.coolingOffHours < 0 || r.coolingOffHours > 720) {
        return `第 ${i + 1} 条奖励规则的冷却犹豫期必须在 0 至 720 小时之间。`;
      }
      const key = `${r.milestoneCode}_${r.beneficiary}_${r.rewardUnit}`;
      if (ruleSet.has(key)) {
        return `奖励规则存在重复组合：[${r.milestoneCode} - ${r.beneficiary} - ${r.rewardUnit}]。每个组合只能定义一条规则。`;
      }
      ruleSet.add(key);
    }

    if (formState.antiAbusePolicy.riskReviewScore < 0 || formState.antiAbusePolicy.riskReviewScore > 100) {
      return '风控人工复核分阈值须在 0 至 100 之间。';
    }

    return null;
  };

  /** 提交草稿表单处理 */
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    const err = validateForm();
    if (err) {
      setFormError(err);
      return;
    }

    saveMutation.mutate({
      request: {
        campaignCode: formState.campaignCode,
        displayName: formState.displayName,
        description: formState.description,
        region: formState.region,
        salesChannels: new Set(formState.salesChannels),
        bindingWindowHours: formState.bindingWindowHours,
        maxQualifiedInvitesPerInviter: formState.maxQualifiedInvitesPerInviter,
        rewardRules: formState.rewardRules,
        antiAbusePolicy: formState.antiAbusePolicy,
      },
      campaignId: editingCampaign?.campaignId,
      resourceVersion: editingCampaign?.resourceVersion,
    });
  };

  /** 提交发布处理 */
  const handlePublishSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPublishError(null);
    if (!publishCampaign) return;

    if (publishState.rolloutPercentage < 1 || publishState.rolloutPercentage > 100) {
      setPublishError('灰度发布滚动比例必须在 1% 至 100% 之间。');
      return;
    }

    if (!publishState.effectiveAtStr) {
      setPublishError('生效时间为必填项。');
      return;
    }

    const effectiveDate = new Date(publishState.effectiveAtStr);
    if (isNaN(effectiveDate.getTime())) {
      setPublishError('生效时间输入格式无效。');
      return;
    }

    let expiresDate: Date | undefined = undefined;
    if (publishState.expiresAtStr) {
      expiresDate = new Date(publishState.expiresAtStr);
      if (isNaN(expiresDate.getTime())) {
        setPublishError('失效时间输入格式无效。');
        return;
      }
      if (expiresDate <= effectiveDate) {
        setPublishError('失效时间必须严格晚于生效时间。');
        return;
      }
    }

    if (publishState.auditReason.trim().length < 8) {
      setPublishError('发布审计理由不能为空，且去除空格后至少需要包含 8 个字符。');
      return;
    }

    publishMutation.mutate({
      campaignId: publishCampaign.campaignId,
      resourceVersion: publishCampaign.resourceVersion,
      request: {
        rolloutPercentage: publishState.rolloutPercentage,
        effectiveAt: effectiveDate,
        expiresAt: expiresDate,
        auditReason: publishState.auditReason,
      },
    });
  };

  /** 提交回退处理 */
  const handleRollbackSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setRollbackError(null);
    if (!rollbackCampaign) return;

    if (!rollbackState.targetVersion) {
      setRollbackError('请选择有效的已发布历史目标版本。');
      return;
    }

    if (rollbackState.auditReason.trim().length < 8) {
      setRollbackError('回退审计理由不能为空，且去除空格后至少需要包含 8 个字符。');
      return;
    }

    rollbackMutation.mutate({
      campaignId: rollbackCampaign.campaignId,
      resourceVersion: rollbackCampaign.resourceVersion,
      request: {
        targetVersion: Number(rollbackState.targetVersion),
        auditReason: rollbackState.auditReason,
      },
    });
  };

  /* ── 动态添加/删除/更新奖励规则 ── */

  const addRewardRule = () => {
    if (formState.rewardRules.length >= 20) {
      setFormError('单活动最多只能添加 20 条奖励规则。');
      return;
    }
    setFormState((prev) => ({
      ...prev,
      rewardRules: [
        ...prev.rewardRules,
        {
          milestoneCode: ReferralMilestoneCode.FirstPurchase,
          beneficiary: ReferralBeneficiary.Inviter,
          rewardUnit: RewardUnit.Energy,
          rewardAmount: 1,
          coolingOffHours: 0,
        },
      ],
    }));
  };

  const removeRewardRule = (index: number) => {
    if (formState.rewardRules.length <= 1) {
      setFormError('至少需要保留 1 条奖励规则。');
      return;
    }
    setFormState((prev) => ({
      ...prev,
      rewardRules: prev.rewardRules.filter((_, i) => i !== index),
    }));
  };

  const updateRewardRule = (index: number, field: keyof ReferralRewardRule, val: unknown) => {
    setFormState((prev) => {
      const nextRules = [...prev.rewardRules];
      nextRules[index] = { ...nextRules[index], [field]: val };
      return { ...prev, rewardRules: nextRules };
    });
  };

  const toggleChannel = (channel: SalesChannel) => {
    setFormState((prev) => {
      const exists = prev.salesChannels.includes(channel);
      const nextChannels = exists
        ? prev.salesChannels.filter((c) => c !== channel)
        : [...prev.salesChannels, channel];
      return { ...prev, salesChannels: nextChannels };
    });
  };

  /* ── 状态 Badge 渲染 ── */

  const renderStatusBadge = (status: ReferralCampaignStatus) => {
    switch (status) {
      case ReferralCampaignStatus.Active:
        return <Badge variant="success">运行中 (ACTIVE)</Badge>;
      case ReferralCampaignStatus.Draft:
        return <Badge variant="warning">草稿 (DRAFT)</Badge>;
      case ReferralCampaignStatus.Ready:
        return <Badge variant="default">就绪 (READY)</Badge>;
      case ReferralCampaignStatus.Disabled:
        return <Badge variant="danger">已禁用 (DISABLED)</Badge>;
      case ReferralCampaignStatus.Superseded:
        return <Badge variant="danger">已替代 (SUPERSEDED)</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <div className="referral-page-container" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部标题与控制按钮 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>
            邀请推广管理
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: '4px 0 0 0' }}>
            配置邀请活动规则、多阶段里程碑奖励、严格防作弊拦截策略、灰度发布与真实历史版本回退。
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            variant="default"
            onClick={() => refetch()}
            disabled={isLoading || isRefetching}
            aria-label="刷新列表"
            title="刷新列表"
          >
            <RefreshCw size={14} className={isLoading || isRefetching ? 'spin' : ''} />
            刷新
          </Button>
          <Button
            variant="primary"
            onClick={() => openFormModal()}
            aria-label="新建邀请活动"
            title="新建邀请活动"
          >
            <Plus size={14} />
            新建活动草稿
          </Button>
        </div>
      </div>

      {/* 全局反馈消息Alert */}
      {successMsg && (
        <div
          style={{
            padding: '10px 14px',
            backgroundColor: 'var(--color-success-bg)',
            color: 'var(--color-success)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 'bold' }}
            aria-label="关闭提示"
          >
            ×
          </button>
        </div>
      )}

      {(queryError || errorMsg) && (
        <div
          style={{
            padding: '10px 14px',
            backgroundColor: 'var(--color-danger-bg)',
            color: 'var(--color-danger)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} />
            <span>{queryError ? queryError.message : errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'inherit', fontWeight: 'bold' }}
            aria-label="关闭错误提示"
          >
            ×
          </button>
        </div>
      )}

      {/* 动态 KPI 统计卡片网格（由 Backend Query 数据实时计算） */}
      <div className="referral-kpi-grid">
        <Card style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>活动总数</span>
            <UserPlus size={18} style={{ color: 'var(--color-primary)' }} />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: '8px' }}>{kpiStats.total}</div>
        </Card>
        <Card style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>运行中活动</span>
            <Award size={18} style={{ color: 'var(--color-success)' }} />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: '8px' }}>{kpiStats.active}</div>
        </Card>
        <Card style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>平均风控分阈值</span>
            <ShieldAlert size={18} style={{ color: 'var(--color-warning)' }} />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: '8px' }}>{kpiStats.avgScore} 分</div>
        </Card>
        <Card style={{ padding: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>奖励规则数</span>
            <Users size={18} style={{ color: 'var(--color-primary)' }} />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: '8px' }}>{kpiStats.totalRules}</div>
        </Card>
      </div>

      {/* 列表筛选栏 */}
      <Card style={{ padding: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ width: '200px' }}>
            <Input
              placeholder="搜索活动名称/编码..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              aria-label="搜索活动名称或编码"
            />
          </div>
          <div style={{ width: '160px' }}>
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="按状态筛选"
            >
              <option value="">全部状态</option>
              <option value={ReferralCampaignStatus.Active}>运行中 (ACTIVE)</option>
              <option value={ReferralCampaignStatus.Draft}>草稿 (DRAFT)</option>
              <option value={ReferralCampaignStatus.Ready}>就绪 (READY)</option>
              <option value={ReferralCampaignStatus.Disabled}>已禁用 (DISABLED)</option>
            </Select>
          </div>
          <div style={{ marginLeft: 'auto', fontSize: '13px', color: 'var(--color-text-tertiary)' }}>
            共匹配到 {filteredCampaigns.length} 项
          </div>
        </div>
      </Card>

      {/* 活动列表 */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {isLoading ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
            <Loader2 size={24} className="spin" style={{ margin: '0 auto 8px auto' }} />
            加载活动列表中...
          </div>
        ) : filteredCampaigns.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: '14px' }}>
            暂无匹配的邀请推广活动配置
          </div>
        ) : (
          <div className="referral-table-wrapper responsive-table">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface-sub)' }}>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600 }}>活动名称 / 编码</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600 }}>状态 / 版本</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600 }}>灰度 / 有效期</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600 }}>奖励规则摘要</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600 }}>防作弊规则</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredCampaigns.map((c) => (
                  <tr key={c.campaignId} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td data-label="活动名称 / 编码" style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{c.displayName}</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>
                        {c.campaignCode} ({c.region})
                      </div>
                    </td>
                    <td data-label="状态 / 版本" style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {renderStatusBadge(c.status)}
                        <span style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>v{c.version}</span>
                      </div>
                    </td>
                    <td data-label="灰度 / 有效期" style={{ padding: '12px 16px' }}>
                      <div>{c.rolloutPercentage}% 灰度比例</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
                        {c.effectiveAt ? new Date(c.effectiveAt).toLocaleDateString('zh-CN') : '未生效'}
                        {c.bindingWindowHours ? ` (${c.bindingWindowHours}h绑定)` : ''}
                      </div>
                    </td>
                    <td data-label="奖励规则摘要" style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px' }}>
                        {c.rewardRules.slice(0, 2).map((r: ReferralRewardRule, idx: number) => (
                          <div key={idx} style={{ color: 'var(--color-text-secondary)' }}>
                            [{r.milestoneCode}] {r.beneficiary}: +{r.rewardAmount} {r.rewardUnit}
                          </div>
                        ))}
                        {c.rewardRules.length > 2 && (
                          <div style={{ color: 'var(--color-text-tertiary)' }}>等共 {c.rewardRules.length} 条规则</div>
                        )}
                      </div>
                    </td>
                    <td data-label="防作弊规则" style={{ padding: '12px 16px' }}>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        同设备:{c.antiAbusePolicy.blockSameDevice ? '拦截' : '允许'} | 同支付:
                        {c.antiAbusePolicy.blockSamePaymentIdentity ? '拦截' : '允许'} | 风控:
                        {c.antiAbusePolicy.riskReviewScore}分
                      </div>
                    </td>
                    <td data-label="操作" style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                        <Button
                          variant="ghost"
                          onClick={() => openFormModal(c)}
                          aria-label="编辑活动草稿"
                          title="编辑活动草稿"
                        >
                          <Edit3 size={14} />
                          编辑
                        </Button>

                        {/* 仅 DRAFT 和 READY 显示发布按钮 */}
                        {(c.status === ReferralCampaignStatus.Draft ||
                          c.status === ReferralCampaignStatus.Ready) && (
                          <Button
                            variant="default"
                            onClick={() => openPublishModal(c)}
                            aria-label="发布上线"
                            title="发布上线"
                          >
                            <Send size={14} />
                            发布
                          </Button>
                        )}

                        {/* 版本回退按钮 */}
                        <Button
                          variant="default"
                          onClick={() => openRollbackModal(c)}
                          aria-label="版本回退"
                          title="版本回退"
                        >
                          <RotateCcw size={14} />
                          回退
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* ── 1. 草稿编辑 Modal ── */}
      <Dialog
        open={formOpen}
        onClose={closeFormModal}
        title={editingCampaign ? `编辑活动草稿 - ${editingCampaign.displayName}` : '新建邀请活动草稿'}
      >
        <form onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {formError && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--color-danger-bg)',
                color: 'var(--color-danger)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
              }}
            >
              {formError}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                活动编码 (campaignCode) *
              </label>
              <Input
                value={formState.campaignCode}
                onChange={(e) => setFormState({ ...formState, campaignCode: e.target.value })}
                placeholder="例如: SUMMER_INVITE_2024"
                disabled={!!editingCampaign}
              />
              <span style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                大写字母开头，包含大写字母/数字/下划线 (2..64)
              </span>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                活动显示名称 (displayName) *
              </label>
              <Input
                value={formState.displayName}
                onChange={(e) => setFormState({ ...formState, displayName: e.target.value })}
                placeholder="请输入面向运营与用户的活动名称"
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              活动描述 (description) *
            </label>
            <Textarea
              value={formState.description}
              onChange={(e) => setFormState({ ...formState, description: e.target.value })}
              placeholder="请输入活动的详细运营规则与激励说明 (1..500字符)"
              rows={3}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                适用国家/地区 (region) *
              </label>
              <Input
                value={formState.region}
                onChange={(e) => setFormState({ ...formState, region: e.target.value })}
                placeholder="例如: CN, US"
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                绑定有效期 (小时) *
              </label>
              <Input
                type="number"
                value={formState.bindingWindowHours}
                onChange={(e) =>
                  setFormState({ ...formState, bindingWindowHours: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                单人最大邀请上限 *
              </label>
              <Input
                type="number"
                value={formState.maxQualifiedInvitesPerInviter}
                onChange={(e) =>
                  setFormState({ ...formState, maxQualifiedInvitesPerInviter: Number(e.target.value) })
                }
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              适用销售渠道 (salesChannels) *
            </label>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              {[SalesChannel.Android, SalesChannel.AdminAssisted].map((ch) => (
                <label key={ch} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                  <input
                    type="checkbox"
                    checked={formState.salesChannels.includes(ch)}
                    onChange={() => toggleChannel(ch)}
                  />
                  {ch}
                </label>
              ))}
            </div>
          </div>

          {/* 阶梯奖励规则编辑器 */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <label style={{ fontSize: '13px', fontWeight: 600 }}>里程碑奖励规则设置 (Reward Rules)</label>
              <Button
                type="button"
                variant="default"
                onClick={addRewardRule}
                aria-label="新增奖励规则"
                title="新增奖励规则"
              >
                <Plus size={12} />
                添加规则
              </Button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {formState.rewardRules.map((rule, idx) => (
                <div key={idx} className="reward-rule-grid">
                  <Select
                    value={rule.milestoneCode}
                    onChange={(e) =>
                      updateRewardRule(idx, 'milestoneCode', e.target.value as ReferralMilestoneCode)
                    }
                    aria-label={`第${idx + 1}条里程碑节点`}
                  >
                    <option value={ReferralMilestoneCode.AccountVerified}>账号完成认证</option>
                    <option value={ReferralMilestoneCode.FirstPurchase}>完成首次充值/购买</option>
                    <option value={ReferralMilestoneCode.FirstGeneration}>首次AI生成对话</option>
                  </Select>

                  <Select
                    value={rule.beneficiary}
                    onChange={(e) =>
                      updateRewardRule(idx, 'beneficiary', e.target.value as ReferralBeneficiary)
                    }
                    aria-label={`第${idx + 1}条受益人`}
                  >
                    <option value={ReferralBeneficiary.Inviter}>邀请人 (Inviter)</option>
                    <option value={ReferralBeneficiary.Invitee}>被邀请人 (Invitee)</option>
                  </Select>

                  <Select
                    value={rule.rewardUnit}
                    onChange={(e) =>
                      updateRewardRule(idx, 'rewardUnit', e.target.value as RewardUnit)
                    }
                    aria-label={`第${idx + 1}条奖励单位`}
                  >
                    <option value={RewardUnit.Energy}>算力能量 (Energy)</option>
                    <option value={RewardUnit.TextQuota}>文本额度 (TextQuota)</option>
                    <option value={RewardUnit.VisionQuota}>视觉额度 (VisionQuota)</option>
                    <option value={RewardUnit.PlanDays}>订阅天数 (PlanDays)</option>
                  </Select>

                  <Input
                    type="number"
                    value={rule.rewardAmount}
                    onChange={(e) => updateRewardRule(idx, 'rewardAmount', Number(e.target.value))}
                    placeholder="数量"
                    aria-label={`第${idx + 1}条奖励数量`}
                  />

                  <Input
                    type="number"
                    value={rule.coolingOffHours}
                    onChange={(e) => updateRewardRule(idx, 'coolingOffHours', Number(e.target.value))}
                    placeholder="冷却(小时)"
                    aria-label={`第${idx + 1}条冷却小时数`}
                  />

                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => removeRewardRule(idx)}
                    aria-label="删除奖励规则"
                    title="删除奖励规则"
                    style={{ color: 'var(--color-danger)' }}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* 防作弊拦截策略 */}
          <div
            style={{
              padding: '12px',
              backgroundColor: 'var(--color-surface-sub)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sliders size={16} />
              防作弊拦截策略 (Anti-Abuse Policy)
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <input
                  type="checkbox"
                  checked={formState.antiAbusePolicy.blockSelfReferral}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      antiAbusePolicy: { ...formState.antiAbusePolicy, blockSelfReferral: (e.target.checked ? true : true) as true },
                    })
                  }
                />
                禁止自己邀请自己
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <input
                  type="checkbox"
                  checked={formState.antiAbusePolicy.blockSameDevice}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      antiAbusePolicy: { ...formState.antiAbusePolicy, blockSameDevice: e.target.checked },
                    })
                  }
                />
                拦截同设备多账号
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <input
                  type="checkbox"
                  checked={formState.antiAbusePolicy.blockSamePaymentIdentity}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      antiAbusePolicy: {
                        ...formState.antiAbusePolicy,
                        blockSamePaymentIdentity: e.target.checked,
                      },
                    })
                  }
                />
                拦截同支付身份
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
                <input
                  type="checkbox"
                  checked={formState.antiAbusePolicy.requireVerifiedPrimaryChannel}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      antiAbusePolicy: {
                        ...formState.antiAbusePolicy,
                        requireVerifiedPrimaryChannel: e.target.checked,
                      },
                    })
                  }
                />
                必须完成主渠道验证
              </label>
            </div>

            <div style={{ marginTop: '4px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, marginBottom: '2px' }}>
                风控人工复核分数阈值 (riskReviewScore: 0..100)
              </label>
              <Input
                type="number"
                value={formState.antiAbusePolicy.riskReviewScore}
                onChange={(e) =>
                  setFormState({
                    ...formState,
                    antiAbusePolicy: {
                      ...formState.antiAbusePolicy,
                      riskReviewScore: Number(e.target.value),
                    },
                  })
                }
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
            <Button type="button" variant="default" onClick={closeFormModal}>
              取消
            </Button>
            <Button type="submit" variant="primary" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? '保存中...' : '保存活动草稿'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── 2. 灰度发布 Modal ── */}
      <Dialog
        open={!!publishCampaign}
        onClose={closePublishModal}
        title={publishCampaign ? `灰度发布上线 - ${publishCampaign.displayName}` : '发布活动'}
      >
        <form onSubmit={handlePublishSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {publishError && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--color-danger-bg)',
                color: 'var(--color-danger)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
              }}
            >
              {publishError}
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              灰度滚动比例 (rolloutPercentage: 1..100) *
            </label>
            <Input
              type="number"
              value={publishState.rolloutPercentage}
              onChange={(e) =>
                setPublishState({ ...publishState, rolloutPercentage: Number(e.target.value) })
              }
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                生效时间 (effectiveAt) *
              </label>
              <Input
                type="datetime-local"
                value={publishState.effectiveAtStr}
                onChange={(e) => setPublishState({ ...publishState, effectiveAtStr: e.target.value })}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                失效时间 (expiresAt) (可选)
              </label>
              <Input
                type="datetime-local"
                value={publishState.expiresAtStr}
                onChange={(e) => setPublishState({ ...publishState, expiresAtStr: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              发布上线审计理由 (auditReason: 至少8字符) *
            </label>
            <Textarea
              value={publishState.auditReason}
              onChange={(e) => setPublishState({ ...publishState, auditReason: e.target.value })}
              placeholder="请输入发布上线的合规审计变更原因"
              rows={3}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
            <Button type="button" variant="default" onClick={closePublishModal}>
              取消
            </Button>
            <Button type="submit" variant="primary" disabled={publishMutation.isPending}>
              {publishMutation.isPending ? '发布中...' : '确认上线发布'}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── 3. 真实版本回退 Modal ── */}
      <Dialog
        open={!!rollbackCampaign}
        onClose={closeRollbackModal}
        title={rollbackCampaign ? `真实版本回退 - ${rollbackCampaign.displayName}` : '版本回退'}
      >
        <form onSubmit={handleRollbackSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {rollbackError && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--color-danger-bg)',
                color: 'var(--color-danger)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px',
              }}
            >
              {rollbackError}
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              选择已发布的历史目标版本 *
            </label>

            {isVersionsLoading ? (
              <div style={{ padding: '12px', textAlign: 'center', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                <Loader2 size={16} className="spin" style={{ display: 'inline', marginRight: '6px' }} />
                正在加载历史版本数据...
              </div>
            ) : validRollbackVersions.length === 0 ? (
              <div
                style={{
                  padding: '12px',
                  backgroundColor: 'var(--color-warning-bg)',
                  color: 'var(--color-warning)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '13px',
                }}
              >
                暂无可以回退的已发布历史版本（必须满足 wasPublished=true 且版本号小于当前版本 v
                {rollbackCampaign?.version}）。
              </div>
            ) : (
              <Select
                value={rollbackState.targetVersion ? String(rollbackState.targetVersion) : ''}
                onChange={(e) =>
                  setRollbackState({
                    ...rollbackState,
                    targetVersion: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                aria-label="选择历史回退目标版本"
              >
                <option value="">-- 请选择目标版本 --</option>
                {validRollbackVersions.map((v) => (
                  <option key={v.campaignVersionId} value={v.version}>
                    版本 v{v.version} - {v.displayName} [{v.action}] (
                    {v.createdAt ? new Date(v.createdAt).toLocaleString('zh-CN') : ''})
                  </option>
                ))}
              </Select>
            )}
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              版本回退审计理由 (auditReason: 至少8字符) *
            </label>
            <Textarea
              value={rollbackState.auditReason}
              onChange={(e) => setRollbackState({ ...rollbackState, auditReason: e.target.value })}
              placeholder="请输入紧急版本回退的合规审计原因"
              rows={3}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
            <Button type="button" variant="default" onClick={closeRollbackModal}>
              取消
            </Button>
            <Button
              type="submit"
              variant="danger"
              disabled={
                rollbackMutation.isPending ||
                isVersionsLoading ||
                validRollbackVersions.length === 0 ||
                !rollbackState.targetVersion
              }
            >
              {rollbackMutation.isPending ? '回退中...' : '确认回退此版本'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
};
