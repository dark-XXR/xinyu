/**
 * 合规审计与监管取证页面组件。
 * 提供日志分类检索、哈希防篡改完整性校验、敏感正文两阶段受控审查、法务冻结控制以及加密导出审计包功能。
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  ScrollText,
  AlertTriangle,
  Lock,
  Unlock,
  Download,
  RefreshCw,
  Search,
  Eye,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
} from 'lucide-react';
import { repository } from '../../api/repository';
import type { AuditFilterParams } from '../../api/repository';
import type {
  AuditEvent,
  AuditIntegrityData,
  SensitiveContentData,
  AuditExportData,
  AuditExportContentData,
} from '../../api/models';
import {
  AuditEventCategoryEnum,
  AuditEventOutcomeEnum,
  AuditEventSeverityEnum,
} from '../../api/models';

/** 合规审查与冻结理由最小长度契约要求 */
const MIN_REASON_LENGTH = 8;

export const AuditOperations: React.FC = () => {
  /* ── 列表数据与加载状态 ── */
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  /* ── 筛选条件状态 ── */
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedOutcome, setSelectedOutcome] = useState<string>('ALL');
  const [userIdFilter, setUserIdFilter] = useState('');
  const [adminIdFilter, setAdminIdFilter] = useState('');
  const [orderIdFilter, setOrderIdFilter] = useState('');
  const [generationIdFilter, setGenerationIdFilter] = useState('');
  const [requestIdFilter, setRequestIdFilter] = useState('');
  const [fromDateFilter, setFromDateFilter] = useState('');
  const [toDateFilter, setToDateFilter] = useState('');

  /* ── 详情抽屉状态 ── */
  const [activeDrawerEvent, setActiveDrawerEvent] = useState<AuditEvent | null>(null);
  const [sensitiveContentData, setSensitiveContentData] = useState<SensitiveContentData | null>(null);

  /* ── 敏感正文审查 Dialog ── */
  const [sensitiveDialogOpen, setSensitiveDialogOpen] = useState(false);
  const [sensitiveTargetEventId, setSensitiveTargetEventId] = useState<string | null>(null);
  const [sensitiveReason, setSensitiveReason] = useState('');
  const [sensitiveLoading, setSensitiveLoading] = useState(false);

  /* ── 法务冻结 Dialog ── */
  const [holdDialogOpen, setHoldDialogOpen] = useState(false);
  const [holdTargetEvent, setHoldTargetEvent] = useState<AuditEvent | null>(null);
  const [holdReason, setHoldReason] = useState('');
  const [holdLoading, setHoldLoading] = useState(false);

  /* ── 完整性校验 Dialog ── */
  const [integrityDialogOpen, setIntegrityDialogOpen] = useState(false);
  const [integrityData, setIntegrityData] = useState<AuditIntegrityData | null>(null);
  const [integrityLoading, setIntegrityLoading] = useState(false);

  /* ── 创建合规导出 Dialog ── */
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportIncludeSensitive, setExportIncludeSensitive] = useState(false);
  const [exportReason, setExportReason] = useState('');
  const [exportLoading, setExportLoading] = useState(false);
  const [createdExportData, setCreatedExportData] = useState<AuditExportData | null>(null);

  /* ── 读取导出数据 Dialog ── */
  const [readExportReason, setReadExportReason] = useState('');
  const [readExportLoading, setReadExportLoading] = useState(false);
  const [readExportResult, setReadExportResult] = useState<AuditExportContentData | null>(null);

  /* 消息提示自动清除 */
  useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(null), 4000);
      return () => clearTimeout(t);
    }
  }, [successMsg]);

  useEffect(() => {
    if (errorMsg) {
      const t = setTimeout(() => setErrorMsg(null), 6000);
      return () => clearTimeout(t);
    }
  }, [errorMsg]);

  /* ── 加载事件列表 ── */
  const fetchAuditEvents = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const filter: AuditFilterParams = {
        category: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        outcome: selectedOutcome !== 'ALL' ? selectedOutcome : undefined,
        userId: userIdFilter.trim() || undefined,
        adminId: adminIdFilter.trim() || undefined,
        orderId: orderIdFilter.trim() || undefined,
        generationId: generationIdFilter.trim() || undefined,
        requestId: requestIdFilter.trim() || undefined,
        from: fromDateFilter ? new Date(fromDateFilter) : undefined,
        to: toDateFilter ? new Date(toDateFilter) : undefined,
      };

      const res = await repository.getAuditEvents(filter);
      setEvents(res.events);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : '获取合规审计日志列表失败');
    } finally {
      setLoading(false);
    }
  }, [
    selectedCategory,
    selectedOutcome,
    userIdFilter,
    adminIdFilter,
    orderIdFilter,
    generationIdFilter,
    requestIdFilter,
    fromDateFilter,
    toDateFilter,
  ]);

  useEffect(() => {
    fetchAuditEvents();
  }, [fetchAuditEvents]);

  /* ── 重置筛选 ── */
  const handleResetFilters = () => {
    setSelectedCategory('ALL');
    setSelectedOutcome('ALL');
    setUserIdFilter('');
    setAdminIdFilter('');
    setOrderIdFilter('');
    setGenerationIdFilter('');
    setRequestIdFilter('');
    setFromDateFilter('');
    setToDateFilter('');
  };

  /* ── 完整性检查 ── */
  const handleVerifyIntegrity = async () => {
    setIntegrityLoading(true);
    setIntegrityDialogOpen(true);
    try {
      const res = await repository.verifyAuditIntegrity();
      setIntegrityData(res);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : '哈希防篡改完整性校验失败');
    } finally {
      setIntegrityLoading(false);
    }
  };

  /* ── 关闭抽屉时销毁敏感正文 ── */
  const handleCloseDrawer = () => {
    setActiveDrawerEvent(null);
    setSensitiveContentData(null);
  };

  /* ── 触发表单敏感正文审查对话框 ── */
  const handleOpenSensitiveDialog = (eventId: string) => {
    setSensitiveTargetEventId(eventId);
    setSensitiveReason('');
    setSensitiveDialogOpen(true);
  };

  /* ── 确认提交调取敏感正文 ── */
  const handleConfirmReadSensitive = async () => {
    if (!sensitiveTargetEventId) return;
    if (sensitiveReason.trim().length < MIN_REASON_LENGTH) {
      setErrorMsg(`审查理由不得少于 ${MIN_REASON_LENGTH} 个字符`);
      return;
    }

    setSensitiveLoading(true);
    try {
      const data = await repository.readAuditSensitiveContent(
        sensitiveTargetEventId,
        sensitiveReason.trim(),
      );
      setSensitiveContentData(data);
      setSensitiveDialogOpen(false);
      setSuccessMsg('敏感正文授权获取成功，已在当前安全抽屉中安全展示。');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : '敏感正文审查调取失败');
    } finally {
      setSensitiveLoading(false);
    }
  };

  /* ── 开启/解除法务冻结 对话框 ── */
  const handleOpenHoldDialog = (event: AuditEvent) => {
    setHoldTargetEvent(event);
    setHoldReason('');
    setHoldDialogOpen(true);
  };

  const handleConfirmHoldChange = async () => {
    if (!holdTargetEvent) return;
    if (holdReason.trim().length < MIN_REASON_LENGTH) {
      setErrorMsg(`法务冻结理由不得少于 ${MIN_REASON_LENGTH} 个字符`);
      return;
    }

    setHoldLoading(true);
    try {
      const updated = await repository.changeAuditLegalHold(
        holdTargetEvent.eventId,
        !holdTargetEvent.legalHold,
        holdReason.trim(),
      );

      setEvents((prev) =>
        prev.map((e) => (e.eventId === updated.eventId ? updated : e)),
      );

      if (activeDrawerEvent?.eventId === updated.eventId) {
        setActiveDrawerEvent(updated);
      }

      setHoldDialogOpen(false);
      setSuccessMsg(
        `审计日志 [${updated.eventId}] 法务冻结状态已更新为：${
          updated.legalHold ? '已冻结' : '未冻结'
        }`,
      );
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : '更新法务冻结状态失败');
    } finally {
      setHoldLoading(false);
    }
  };

  /* ── 创建合规导出包 ── */
  const handleCreateExport = async () => {
    if (exportReason.trim().length < MIN_REASON_LENGTH) {
      setErrorMsg(`导出理由不得少于 ${MIN_REASON_LENGTH} 个字符`);
      return;
    }

    setExportLoading(true);
    try {
      const requestData = {
        auditReason: exportReason.trim(),
        includeSensitiveContent: exportIncludeSensitive,
        category: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        outcome: selectedOutcome !== 'ALL' ? selectedOutcome : undefined,
        userId: userIdFilter.trim() || undefined,
        adminId: adminIdFilter.trim() || undefined,
        orderId: orderIdFilter.trim() || undefined,
        generationId: generationIdFilter.trim() || undefined,
        requestId: requestIdFilter.trim() || undefined,
        fromTime: fromDateFilter ? new Date(fromDateFilter) : undefined,
        toTime: toDateFilter ? new Date(toDateFilter) : undefined,
      };

      const res = await repository.createAuditExport(requestData);
      setCreatedExportData(res);
      setReadExportResult(null);
      setSuccessMsg('加密合规审计包创建成功');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : '创建导出包失败');
    } finally {
      setExportLoading(false);
    }
  };

  /* ── 读取解密导出包 ── */
  const handleReadExport = async () => {
    if (!createdExportData) return;
    if (readExportReason.trim().length < MIN_REASON_LENGTH) {
      setErrorMsg(`读取理由不得少于 ${MIN_REASON_LENGTH} 个字符`);
      return;
    }

    setReadExportLoading(true);
    try {
      const res = await repository.readAuditExport(
        createdExportData.exportId,
        readExportReason.trim(),
      );
      setReadExportResult(res);
      setSuccessMsg('导出包解密调取成功');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : '读取导出包数据失败');
    } finally {
      setReadExportLoading(false);
    }
  };

  /* ── 指标计算 (仅针对当前筛选结果统计) ── */
  const currentTotal = events.length;
  const currentFailed = events.filter(
    (e) => e.outcome === AuditEventOutcomeEnum.Failed || e.severity === AuditEventSeverityEnum.Error || e.severity === AuditEventSeverityEnum.Critical,
  ).length;
  const currentSensitive = events.filter((e) => e.containsSensitiveContent).length;
  const currentLegalHold = events.filter((e) => e.legalHold).length;

  /* ── 格式化辅助 ── */
  const formatTime = (d: Date) => {
    try {
      const dateObj = d instanceof Date ? d : new Date(d);
      return dateObj.toLocaleString('zh-CN', { hour12: false });
    } catch {
      return String(d);
    }
  };

  const getCategoryLabel = (cat: string) => {
    switch (cat) {
      case AuditEventCategoryEnum.Auth:
        return '登录认证';
      case AuditEventCategoryEnum.Ai:
        return 'AI 内容';
      case AuditEventCategoryEnum.Payment:
        return '充值支付';
      case AuditEventCategoryEnum.Admin:
        return '管理员配置';
      case AuditEventCategoryEnum.Operations:
        return '网站运行';
      case AuditEventCategoryEnum.Security:
        return '安全审计';
      case AuditEventCategoryEnum.Privacy:
        return '隐私合规';
      default:
        return cat;
    }
  };

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case AuditEventOutcomeEnum.Succeeded:
        return <span className="badge badge-success"><CheckCircle2 size={12} style={{ marginRight: 4 }} />成功</span>;
      case AuditEventOutcomeEnum.Failed:
        return <span className="badge badge-danger"><XCircle size={12} style={{ marginRight: 4 }} />失败</span>;
      case AuditEventOutcomeEnum.Cancelled:
        return <span className="badge badge-default">已取消</span>;
      case AuditEventOutcomeEnum.Pending:
        return <span className="badge badge-warning">处理中</span>;
      default:
        return <span className="badge badge-default">{outcome}</span>;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case AuditEventSeverityEnum.Critical:
        return <span className="badge badge-danger">严重</span>;
      case AuditEventSeverityEnum.High:
        return <span className="badge badge-warning">高风险</span>;
      case AuditEventSeverityEnum.Error:
        return <span className="badge badge-danger">错误</span>;
      case AuditEventSeverityEnum.Warning:
        return <span className="badge badge-warning">警告</span>;
      case AuditEventSeverityEnum.Info:
      default:
        return <span className="badge badge-default">信息</span>;
    }
  };

  return (
    <div className="audit-operations-page" style={{ display: 'flex', flexDirection: 'column', gap: 20, minWidth: 0, width: '100%', maxWidth: '100%' }}>
      {/* 消息提示框 */}
      {errorMsg && (
        <div className="card" style={{ backgroundColor: 'var(--color-danger-bg)', borderColor: 'var(--color-danger)', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, maxWidth: '100%' }}>
          <AlertTriangle size={18} color="var(--color-danger)" />
          <span style={{ color: 'var(--color-danger)', fontWeight: 500, flex: 1, minWidth: 0, wordBreak: 'break-word' }}>{errorMsg}</span>
          <button className="btn btn-ghost" style={{ padding: 4, height: 'auto' }} onClick={() => setErrorMsg(null)}>×</button>
        </div>
      )}
      {successMsg && (
        <div className="card" style={{ backgroundColor: 'var(--color-success-bg)', borderColor: 'var(--color-success)', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, maxWidth: '100%' }}>
          <CheckCircle2 size={18} color="var(--color-success)" />
          <span style={{ color: 'var(--color-success)', fontWeight: 500, flex: 1, minWidth: 0, wordBreak: 'break-word' }}>{successMsg}</span>
          <button className="btn btn-ghost" style={{ padding: 4, height: 'auto' }} onClick={() => setSuccessMsg(null)}>×</button>
        </div>
      )}

      {/* 标题与顶部工具栏 */}
      <div className="page-title-group" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, minWidth: 0, width: '100%', maxWidth: '100%' }}>
        <div style={{ minWidth: 0, maxWidth: '100%' }}>
          <h1 style={{ fontSize: '20px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-text-primary)', flexWrap: 'wrap' }}>
            <ShieldCheck size={24} color="var(--color-primary)" />
            合规审计与监管取证
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: 4 }}>
            全站审计日志覆盖登录认证、AI 输入输出、充值支付、管理员配置修改与网站运行状态。支持加密哈希防篡改链校验与安全二阶段取证。
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', minWidth: 0, maxWidth: '100%' }}>
          <button
            className="btn btn-default"
            onClick={handleVerifyIntegrity}
            disabled={integrityLoading}
          >
            <RefreshCw size={15} className={integrityLoading ? 'spin' : ''} />
            哈希防篡改完整性校验
          </button>
          <button
            className="btn btn-primary"
            onClick={() => {
              setExportReason('');
              setExportIncludeSensitive(false);
              setCreatedExportData(null);
              setReadExportResult(null);
              setExportDialogOpen(true);
            }}
          >
            <Download size={15} />
            创建合规审计包
          </button>
        </div>
      </div>

      {/* 统计指标卡 (明确标注为“当前结果统计”) */}
      <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 16, minWidth: 0, width: '100%', maxWidth: '100%' }}>
        <div className="card" style={{ padding: '16px 20px', minWidth: 0, maxWidth: '100%' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            当前结果事件数
            <ScrollText size={16} color="var(--color-text-tertiary)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: 8, color: 'var(--color-text-primary)' }}>
            {currentTotal}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: 4 }}>仅反映当前筛选条件下的总计</div>
        </div>

        <div className="card" style={{ padding: '16px 20px', minWidth: 0, maxWidth: '100%' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            失败 / 异常事件
            <AlertTriangle size={16} color="var(--color-danger)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: 8, color: 'var(--color-danger)' }}>
            {currentFailed}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: 4 }}>包含校验失败或高风险告警项</div>
        </div>

        <div className="card" style={{ padding: '16px 20px', minWidth: 0, maxWidth: '100%' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            含敏感正文日志
            <Eye size={16} color="var(--color-warning)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: 8, color: 'var(--color-warning)' }}>
            {currentSensitive}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: 4 }}>需要二阶段填理由授权查看</div>
        </div>

        <div className="card" style={{ padding: '16px 20px', minWidth: 0, maxWidth: '100%' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            法务冻结锁定项
            <Lock size={16} color="var(--color-primary)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 600, marginTop: 8, color: 'var(--color-primary)' }}>
            {currentLegalHold}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: 4 }}>已排除自动化策略删除范围</div>
        </div>
      </div>

      {/* 检索与筛选卡片 */}
      <div className="card" style={{ padding: '16px 20px', minWidth: 0, maxWidth: '100%' }}>
        {/* 1. 分类 Tab 切换 */}
        <div className="tabs-header" style={{ marginBottom: 16, minWidth: 0, maxWidth: '100%' }}>
          {[
            { key: 'ALL', label: '全部事件' },
            { key: AuditEventCategoryEnum.Auth, label: '登录认证' },
            { key: AuditEventCategoryEnum.Ai, label: 'AI 内容' },
            { key: AuditEventCategoryEnum.Payment, label: '充值支付' },
            { key: AuditEventCategoryEnum.Admin, label: '管理员配置' },
            { key: AuditEventCategoryEnum.Operations, label: '网站运行' },
          ].map((tab) => (
            <button
              key={tab.key}
              className={`tab-button ${selectedCategory === tab.key ? 'active' : ''}`}
              onClick={() => setSelectedCategory(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 2. 高级过滤表单 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 12, minWidth: 0, maxWidth: '100%' }}>
          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>执行结果</label>
            <select
              className="input"
              value={selectedOutcome}
              onChange={(e) => setSelectedOutcome(e.target.value)}
            >
              <option value="ALL">全部分组结果</option>
              <option value={AuditEventOutcomeEnum.Succeeded}>SUCCEEDED (成功)</option>
              <option value={AuditEventOutcomeEnum.Failed}>FAILED (失败)</option>
              <option value={AuditEventOutcomeEnum.Cancelled}>CANCELLED (已取消)</option>
              <option value={AuditEventOutcomeEnum.Pending}>PENDING (处理中)</option>
            </select>
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>用户 ID</label>
            <input
              type="text"
              className="input"
              placeholder="如 user-001"
              value={userIdFilter}
              onChange={(e) => setUserIdFilter(e.target.value)}
            />
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>管理员 ID</label>
            <input
              type="text"
              className="input"
              placeholder="如 admin-001"
              value={adminIdFilter}
              onChange={(e) => setAdminIdFilter(e.target.value)}
            />
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>订单 ID</label>
            <input
              type="text"
              className="input"
              placeholder="如 ord-20240801-001"
              value={orderIdFilter}
              onChange={(e) => setOrderIdFilter(e.target.value)}
            />
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>生成 ID</label>
            <input
              type="text"
              className="input"
              placeholder="如 gen-20240809-001"
              value={generationIdFilter}
              onChange={(e) => setGenerationIdFilter(e.target.value)}
            />
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>请求 ID</label>
            <input
              type="text"
              className="input"
              placeholder="如 req-ai-1001"
              value={requestIdFilter}
              onChange={(e) => setRequestIdFilter(e.target.value)}
            />
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>开始时间</label>
            <input
              type="datetime-local"
              className="input"
              value={fromDateFilter}
              onChange={(e) => setFromDateFilter(e.target.value)}
            />
          </div>

          <div style={{ minWidth: 0 }}>
            <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: 4 }}>结束时间</label>
            <input
              type="datetime-local"
              className="input"
              value={toDateFilter}
              onChange={(e) => setToDateFilter(e.target.value)}
            />
          </div>
        </div>

        {/* 筛选按钮组 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16, flexWrap: 'wrap', minWidth: 0, maxWidth: '100%' }}>
          <button className="btn btn-default" onClick={handleResetFilters}>
            重置筛选
          </button>
          <button className="btn btn-primary" onClick={fetchAuditEvents} disabled={loading}>
            <Search size={15} />
            {loading ? '检索中...' : '查询日志'}
          </button>
        </div>
      </div>

      {/* 审计日志列表 (响应式：桌面表格 / 手机 390px 卡片) */}
      <div className="table-wrapper responsive-table" style={{ minWidth: 0, maxWidth: '100%' }}>
        <table>
          <thead>
            <tr>
              <th>发生时间</th>
              <th>分类 / 事件类型</th>
              <th>摘要</th>
              <th>结果 / 严重度</th>
              <th>关联对象</th>
              <th>合规标记</th>
              <th style={{ textAlign: 'right' }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '32px 0', color: 'var(--color-text-secondary)' }}>
                  数据加载中...
                </td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '32px 0', color: 'var(--color-text-secondary)' }}>
                  未查找到符合条件的合规审计日志记录
                </td>
              </tr>
            ) : (
              events.map((evt) => (
                <tr key={evt.eventId}>
                  <td data-label="发生时间" style={{ whiteSpace: 'nowrap', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={13} color="var(--color-text-tertiary)" />
                      {formatTime(evt.occurredAt)}
                    </div>
                  </td>
                  <td data-label="分类 / 事件类型">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
                      <span style={{ fontWeight: 600, fontSize: '13px' }}>{getCategoryLabel(evt.category)}</span>
                      <code style={{ fontSize: '11px', color: 'var(--color-text-secondary)', background: 'var(--color-surface-sub)', padding: '1px 4px', borderRadius: 2, display: 'inline-block', maxWidth: '100%', wordBreak: 'break-all' }}>
                        {evt.eventType}
                      </code>
                    </div>
                  </td>
                  <td data-label="摘要" style={{ maxWidth: 280, minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                    <div style={{ fontSize: '13px', color: 'var(--color-text-primary)', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                      {evt.summary}
                    </div>
                  </td>
                  <td data-label="结果 / 严重度">
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', minWidth: 0 }}>
                      {getOutcomeBadge(evt.outcome)}
                      {getSeverityBadge(evt.severity)}
                    </div>
                  </td>
                  <td data-label="关联对象" style={{ fontSize: '12px', minWidth: 0, wordBreak: 'break-all' }}>
                    {evt.userId && <div>用户: <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{evt.userId}</code></div>}
                    {evt.adminId && <div>管理员: <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{evt.adminId}</code></div>}
                    {evt.orderId && <div>订单: <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{evt.orderId}</code></div>}
                    {evt.generationId && <div>生成: <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{evt.generationId}</code></div>}
                    {evt.requestId && <div>请求: <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{evt.requestId}</code></div>}
                    {!evt.userId && !evt.adminId && !evt.orderId && !evt.generationId && !evt.requestId && (
                      <span style={{ color: 'var(--color-text-tertiary)' }}>系统全局</span>
                    )}
                  </td>
                  <td data-label="合规标记">
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', minWidth: 0 }}>
                      {evt.containsSensitiveContent && (
                        <span className="badge badge-warning" title="包含敏感业务正文">敏感正文</span>
                      )}
                      {evt.legalHold ? (
                        <span className="badge badge-danger" style={{ display: 'inline-flex', alignItems: 'center', gap: 2 }}>
                          <Lock size={10} /> 法务冻结
                        </span>
                      ) : (
                        <span className="badge badge-default">常规保留</span>
                      )}
                    </div>
                  </td>
                  <td data-label="操作" style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      <button
                        className="btn btn-default"
                        style={{ height: 28, padding: '0 8px', fontSize: '12px' }}
                        onClick={() => {
                          setActiveDrawerEvent(evt);
                          setSensitiveContentData(null);
                        }}
                      >
                        <Eye size={13} />
                        详情
                      </button>
                      <button
                        className={evt.legalHold ? 'btn btn-default' : 'btn btn-ghost'}
                        style={{ height: 28, padding: '0 8px', fontSize: '12px', color: evt.legalHold ? 'var(--color-danger)' : undefined }}
                        onClick={() => handleOpenHoldDialog(evt)}
                      >
                        {evt.legalHold ? <Unlock size={13} /> : <Lock size={13} />}
                        {evt.legalHold ? '解冻' : '冻结'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Drawer: 审计事件详情抽屉 ── */}
      {activeDrawerEvent && (
        <div className="overlay" onClick={handleCloseDrawer}>
          <div className="drawer" onClick={(e) => e.stopPropagation()} style={{ overflowY: 'auto', minWidth: 0, maxWidth: '100%' }}>
            <div className="dialog-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ScrollText size={18} color="var(--color-primary)" />
                <span>合规审计事件详情</span>
              </div>
              <button className="btn btn-ghost" style={{ padding: '0 8px' }} onClick={handleCloseDrawer}>×</button>
            </div>

            <div className="dialog-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* 基本属性卡片 */}
              <div style={{ background: 'var(--color-surface-sub)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: 8, color: 'var(--color-text-primary)', wordBreak: 'break-word' }}>
                  {activeDrawerEvent.summary}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))', gap: '8px 12px', fontSize: '12px', minWidth: 0 }}>
                  <div><strong>事件 ID:</strong> <code style={{ wordBreak: 'break-all' }}>{activeDrawerEvent.eventId}</code></div>
                  <div><strong>发生时间:</strong> {formatTime(activeDrawerEvent.occurredAt)}</div>
                  <div><strong>业务分类:</strong> {getCategoryLabel(activeDrawerEvent.category)}</div>
                  <div><strong>事件类型:</strong> <code style={{ wordBreak: 'break-all' }}>{activeDrawerEvent.eventType}</code></div>
                  <div><strong>执行结果:</strong> {getOutcomeBadge(activeDrawerEvent.outcome)}</div>
                  <div><strong>严重程度:</strong> {getSeverityBadge(activeDrawerEvent.severity)}</div>
                  <div><strong>主体类型:</strong> {activeDrawerEvent.actorType}</div>
                  <div><strong>主体 ID:</strong> {activeDrawerEvent.actorId || '-'}</div>
                  <div><strong>保留截止:</strong> {formatTime(activeDrawerEvent.retentionUntil)}</div>
                  <div><strong>法务冻结:</strong> {activeDrawerEvent.legalHold ? '已锁定 (HOLD)' : '未锁定'}</div>
                </div>
              </div>

              {/* 资源标识区 */}
              <div style={{ minWidth: 0 }}>
                <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: 6, color: 'var(--color-text-secondary)' }}>关联标识与关联号</h4>
                <div style={{ background: 'var(--color-surface-main)', padding: 10, borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0, wordBreak: 'break-all', overflowWrap: 'anywhere' }}>
                  <div>请求 ID (requestId): <code>{activeDrawerEvent.requestId || '-'}</code></div>
                  <div>会话 ID (sessionId): <code>{activeDrawerEvent.sessionId || '-'}</code></div>
                  <div>用户 ID (userId): <code>{activeDrawerEvent.userId || '-'}</code></div>
                  <div>管理员 ID (adminId): <code>{activeDrawerEvent.adminId || '-'}</code></div>
                  <div>订单 ID (orderId): <code>{activeDrawerEvent.orderId || '-'}</code></div>
                  <div>生成 ID (generationId): <code>{activeDrawerEvent.generationId || '-'}</code></div>
                  <div>资源类型/ID: <code>{activeDrawerEvent.resourceType || '-'}:{activeDrawerEvent.resourceId || '-'}</code></div>
                </div>
              </div>

              {/* 哈希与防篡改签名 */}
              <div style={{ minWidth: 0 }}>
                <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: 6, color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Shield size={14} color="var(--color-primary)" />
                  密码学哈希签名链 (防篡改审计)
                </h4>
                <div style={{ background: '#1e293b', color: '#e2e8f0', padding: 10, borderRadius: 'var(--radius-sm)', fontSize: '11px', fontFamily: 'monospace', wordBreak: 'break-all', overflowWrap: 'anywhere', display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0, maxWidth: '100%' }}>
                  <div><span style={{ color: '#94a3b8' }}>Event Hash:</span><br />{activeDrawerEvent.eventHash}</div>
                  <div><span style={{ color: '#94a3b8' }}>Previous Event Hash:</span><br />{activeDrawerEvent.previousEventHash}</div>
                  {activeDrawerEvent.sensitivePayloadDigest && (
                    <div><span style={{ color: '#94a3b8' }}>Sensitive Payload Digest:</span><br />{activeDrawerEvent.sensitivePayloadDigest}</div>
                  )}
                </div>
              </div>

              {/* 结构化元数据 Metadata */}
              <div style={{ minWidth: 0 }}>
                <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: 6, color: 'var(--color-text-secondary)' }}>扩展元数据 (Metadata)</h4>
                <pre style={{ background: 'var(--color-surface-sub)', padding: 10, borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', fontSize: '11px', overflowX: 'auto', minWidth: 0, maxWidth: '100%', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(activeDrawerEvent.metadata, null, 2)}
                </pre>
              </div>

              {/* 敏感正文审查区域 (受控显示) */}
              {activeDrawerEvent.containsSensitiveContent && (
                <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 16, minWidth: 0 }}>
                  <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: 8, color: 'var(--color-warning)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertTriangle size={15} />
                    敏感业务正文审查区
                  </h4>

                  {!sensitiveContentData ? (
                    <div style={{ background: 'var(--color-warning-bg)', border: '1px solid var(--color-warning)', padding: 12, borderRadius: 'var(--radius-sm)', fontSize: '12px', color: '#92400e', minWidth: 0 }}>
                      <p style={{ marginBottom: 8 }}>
                        根据安全合规与隐私防护规程，敏感业务正文（如 AI 上下文提示词、审核原始明文）默认脱敏隐蔽。调取需输入至少 8 字的调取审查理由。
                      </p>
                      <button
                        className="btn btn-primary"
                        style={{ height: 30, fontSize: '12px' }}
                        onClick={() => handleOpenSensitiveDialog(activeDrawerEvent.eventId)}
                      >
                        <Eye size={13} />
                        审查敏感正文 (需授权填理由)
                      </button>
                    </div>
                  ) : (
                    <div style={{ background: '#fef2f2', border: '1px dotted var(--color-danger)', padding: 12, borderRadius: 'var(--radius-sm)', minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-danger)' }}>
                          已完成二次安全验证授权正文：
                        </span>
                        <button
                          className="btn btn-ghost"
                          style={{ height: 24, padding: '0 6px', fontSize: '11px' }}
                          onClick={() => setSensitiveContentData(null)}
                        >
                          隐藏正文
                        </button>
                      </div>
                      <pre style={{ background: '#ffffff', padding: 10, borderRadius: 'var(--radius-sm)', border: '1px solid #fca5a5', fontSize: '11px', color: '#991b1b', overflowX: 'auto', maxHeight: 200, minWidth: 0, maxWidth: '100%', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(sensitiveContentData.content, null, 2)}
                      </pre>
                      <p style={{ fontSize: '11px', color: 'var(--color-danger)', marginTop: 6 }}>
                        ⚠️ 提示：敏感正文仅在此抽屉生命周期内展示，关闭此抽屉后会自动从内存抹除销毁。
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="dialog-footer">
              <button className="btn btn-default" onClick={handleCloseDrawer}>关闭详情</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog 1: 敏感正文审查理由二次确认框 ── */}
      {sensitiveDialogOpen && (
        <div className="overlay" onClick={() => setSensitiveDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()} style={{ minWidth: 0 }}>
            <div className="dialog-header">
              <span>审查敏感正文 - 调取授权确认</span>
              <button className="btn btn-ghost" onClick={() => setSensitiveDialogOpen(false)}>×</button>
            </div>
            <div className="dialog-body" style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
              <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                调取合规敏感正文将被审计日志永久记录。请填写调取理由（不少于 {MIN_REASON_LENGTH} 字）：
              </div>
              <textarea
                className="input"
                style={{ height: 80, padding: 8, resize: 'vertical' }}
                placeholder="例如：接到法务安全复核工单 [TICKET-99201]，针对高风险提示词注入攻击做人工审查"
                value={sensitiveReason}
                onChange={(e) => setSensitiveReason(e.target.value)}
              />
              <div style={{ fontSize: '11px', color: sensitiveReason.trim().length < MIN_REASON_LENGTH ? 'var(--color-danger)' : 'var(--color-success)' }}>
                已输入 {sensitiveReason.trim().length} / 最小 {MIN_REASON_LENGTH} 字
              </div>
            </div>
            <div className="dialog-footer">
              <button className="btn btn-default" onClick={() => setSensitiveDialogOpen(false)}>取消</button>
              <button
                className="btn btn-primary"
                onClick={handleConfirmReadSensitive}
                disabled={sensitiveLoading || sensitiveReason.trim().length < MIN_REASON_LENGTH}
              >
                {sensitiveLoading ? '调取中...' : '确认调取正文'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog 2: 法务冻结控制确认框 ── */}
      {holdDialogOpen && holdTargetEvent && (
        <div className="overlay" onClick={() => setHoldDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()} style={{ minWidth: 0 }}>
            <div className="dialog-header">
              <span>{holdTargetEvent.legalHold ? '解除法务冻结' : '开启法务冻结'}</span>
              <button className="btn btn-ghost" onClick={() => setHoldDialogOpen(false)}>×</button>
            </div>
            <div className="dialog-body" style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', wordBreak: 'break-word' }}>
                {holdTargetEvent.legalHold
                  ? `您正在解除日志 [${holdTargetEvent.eventId}] 的法务冻结锁定。解除后将恢复标准保存策略。`
                  : `您正在将日志 [${holdTargetEvent.eventId}] 标记为法务冻结。锁定后将排除自动化归档清理，防篡改保留。`}
              </p>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 500, display: 'block', marginBottom: 4 }}>
                  操作理由（不少于 {MIN_REASON_LENGTH} 字）:
                </label>
                <textarea
                  className="input"
                  style={{ height: 80, padding: 8, resize: 'vertical' }}
                  placeholder="例如：应司法监管部门执法协助函 [2026] 0809 号要求锁定涉及涉案订单的交易日志"
                  value={holdReason}
                  onChange={(e) => setHoldReason(e.target.value)}
                />
                <div style={{ fontSize: '11px', marginTop: 4, color: holdReason.trim().length < MIN_REASON_LENGTH ? 'var(--color-danger)' : 'var(--color-success)' }}>
                  已输入 {holdReason.trim().length} / 最小 {MIN_REASON_LENGTH} 字
                </div>
              </div>
            </div>
            <div className="dialog-footer">
              <button className="btn btn-default" onClick={() => setHoldDialogOpen(false)}>取消</button>
              <button
                className={holdTargetEvent.legalHold ? 'btn btn-default' : 'btn btn-danger'}
                onClick={handleConfirmHoldChange}
                disabled={holdLoading || holdReason.trim().length < MIN_REASON_LENGTH}
              >
                {holdLoading ? '处理中...' : holdTargetEvent.legalHold ? '确认解除冻结' : '确认开启冻结'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog 3: 哈希防篡改完整性校验结果 ── */}
      {integrityDialogOpen && (
        <div className="overlay" onClick={() => setIntegrityDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()} style={{ width: 460, maxWidth: 'calc(100vw - 32px)', minWidth: 0 }}>
            <div className="dialog-header">
              <span>哈希防篡改链完整性校验</span>
              <button className="btn btn-ghost" onClick={() => setIntegrityDialogOpen(false)}>×</button>
            </div>
            <div className="dialog-body" style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
              {integrityLoading ? (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-text-secondary)' }}>
                  正在递归校验日志链加密 SHA-256 签名与前序哈希...
                </div>
              ) : integrityData ? (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, padding: 12, borderRadius: 'var(--radius-sm)', background: integrityData.valid ? 'var(--color-success-bg)' : 'var(--color-danger-bg)' }}>
                    {integrityData.valid ? (
                      <CheckCircle2 size={24} color="var(--color-success)" />
                    ) : (
                      <AlertTriangle size={24} color="var(--color-danger)" />
                    )}
                    <div>
                      <div style={{ fontWeight: 600, color: integrityData.valid ? 'var(--color-success)' : 'var(--color-danger)' }}>
                        {integrityData.valid ? '完整性校验通过 (Hash Chain Valid)' : '发现哈希链异常/修改'}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        已成功比对连续 {integrityData.checkedCount} 条日志的前序与当前签名节点
                      </div>
                    </div>
                  </div>

                  {!integrityData.valid && (
                    <div style={{ fontSize: '12px', color: 'var(--color-danger)', wordBreak: 'break-all' }}>
                      首次发现断链异常事件 ID: <code>{integrityData.firstInvalidEventId || '未知'}</code>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ color: 'var(--color-text-tertiary)' }}>无校验数据</div>
              )}
            </div>
            <div className="dialog-footer">
              <button className="btn btn-primary" onClick={() => setIntegrityDialogOpen(false)}>确定</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog 4: 创建与读取加密合规导出包 ── */}
      {exportDialogOpen && (
        <div className="overlay" onClick={() => setExportDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()} style={{ width: 520, maxWidth: 'calc(100vw - 32px)', minWidth: 0 }}>
            <div className="dialog-header">
              <span>创建与阅读加密合规审计包</span>
              <button className="btn btn-ghost" onClick={() => setExportDialogOpen(false)}>×</button>
            </div>
            <div className="dialog-body" style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>
              {!createdExportData ? (
                /* 阶段 A: 填写导出请求参数 */
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
                  <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    按当前页面检索条件打包生成具有防篡改数字签名的加密审计导出包。
                  </p>

                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '13px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={exportIncludeSensitive}
                      onChange={(e) => setExportIncludeSensitive(e.target.checked)}
                    />
                    包含敏感业务正文 (根据合规要求需额外授权)
                  </label>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 500, display: 'block', marginBottom: 4 }}>
                      导出申请具体理由（不少于 {MIN_REASON_LENGTH} 字）:
                    </label>
                    <textarea
                      className="input"
                      style={{ height: 80, padding: 8, resize: 'vertical' }}
                      placeholder="例如：向数据保护合规监管部门提交 2026 年三季度例行合规留存审计凭证"
                      value={exportReason}
                      onChange={(e) => setExportReason(e.target.value)}
                    />
                    <div style={{ fontSize: '11px', marginTop: 4, color: exportReason.trim().length < MIN_REASON_LENGTH ? 'var(--color-danger)' : 'var(--color-success)' }}>
                      已输入 {exportReason.trim().length} / 最小 {MIN_REASON_LENGTH} 字
                    </div>
                  </div>

                  <button
                    className="btn btn-primary"
                    onClick={handleCreateExport}
                    disabled={exportLoading || exportReason.trim().length < MIN_REASON_LENGTH}
                  >
                    {exportLoading ? '打包生成中...' : '生成加密导出包'}
                  </button>
                </div>
              ) : (
                /* 阶段 B: 展示导出包元数据与在线二阶段调取解密数据 */
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
                  <div style={{ background: 'var(--color-success-bg)', padding: 12, borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-success)', fontSize: '12px', minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: 'var(--color-success)', marginBottom: 4 }}>
                      加密合规审计包生成完成
                    </div>
                    <div><strong>导出 ID:</strong> <code style={{ wordBreak: 'break-all' }}>{createdExportData.exportId}</code></div>
                    <div><strong>事件条数:</strong> {createdExportData.eventCount}</div>
                    <div><strong>哈希摘要:</strong> <code style={{ fontSize: '11px', wordBreak: 'break-all' }}>{createdExportData.bundleDigest}</code></div>
                    <div><strong>包失效时间:</strong> {formatTime(createdExportData.expiresAt)}</div>
                  </div>

                  {!readExportResult ? (
                    <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>调取解密数据包内容预览 (需填二次读取理由)</span>
                      <textarea
                        className="input"
                        style={{ height: 60, padding: 6, fontSize: '12px' }}
                        placeholder="请输入读取该合规导出包内容的二次核验理由（不少于 8 字）"
                        value={readExportReason}
                        onChange={(e) => setReadExportReason(e.target.value)}
                      />
                      <button
                        className="btn btn-default"
                        onClick={handleReadExport}
                        disabled={readExportLoading || readExportReason.trim().length < MIN_REASON_LENGTH}
                      >
                        {readExportLoading ? '解密调取中...' : '调取解密包数据'}
                      </button>
                    </div>
                  ) : (
                    <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 12, minWidth: 0 }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary)', marginBottom: 4 }}>
                        解密数据 Bundle 结构预览:
                      </div>
                      <pre style={{ background: '#1e293b', color: '#38bdf8', padding: 10, borderRadius: 'var(--radius-sm)', fontSize: '11px', overflowX: 'auto', maxHeight: 200, minWidth: 0, maxWidth: '100%', wordBreak: 'break-all', whiteSpace: 'pre-wrap' }}>
                        {JSON.stringify(readExportResult.bundle, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="dialog-footer">
              <button className="btn btn-default" onClick={() => setExportDialogOpen(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
