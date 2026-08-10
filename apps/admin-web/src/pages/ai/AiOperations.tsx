/**
 * AI 运行配置管理页面。
 * 负责管理后台 AI 模型映射、场景路由、提示词模板、风控策略以及模型评测与发布操作。
 * 提供首屏统计、Tab 分区、响应式数据表格、JSON Schema 校验及二次确认防护机制。
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Cpu,
  Route,
  FileCode,
  ShieldAlert,
  Plus,
  RefreshCw,
  Send,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Play,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Select } from '../../components/ui/Select';
import { Badge } from '../../components/ui/Badge';
import { Dialog } from '../../components/ui/Dialog';
import { Drawer } from '../../components/ui/Drawer';
import { repository } from '../../api/repository';
import type { AiEditorDefaults } from '../../api/repository';
import {
  AiResourceStatus,
  AiScenario,
  AiModality,
  AiRiskPolicyPromptInjectionActionEnum,
  AiEvaluationRunStatusEnum,
} from '../../api/models';
import type {
  AiModelMapping,
  AiModelMappingWriteRequest,
  AiRoute,
  AiRouteWriteRequest,
  AiPromptTemplate,
  AiPromptWriteRequest,
  AiRiskPolicy,
  AiRiskPolicyWriteRequest,
  AiEvaluationRun,
  AiEvaluationRunRequest,
  AiPublishRequest,
  AiRollbackRequest,
  Provider,
} from '../../api/models';

type TabKey = 'mappings' | 'routes' | 'prompts' | 'policies' | 'evaluations';

/** 将 Date 对象安全格式化为 HTML datetime-local 输入框所需的 YYYY-MM-DDTHH:mm 格式 */
const formatDateToLocalInput = (d: Date): string => {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

/** 将 datetime-local 字符串解析为 Date 对象 */
const parseLocalInputToDate = (str: string): Date => {
  const parsed = new Date(str);
  return isNaN(parsed.getTime()) ? new Date() : parsed;
};

export const AiOperations: React.FC = () => {
  /* ── 核心状态 ── */
  const [activeTab, setActiveTab] = useState<TabKey>('mappings');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  /* ── 列表数据状态 ── */
  const [providers, setProviders] = useState<Provider[]>([]);
  const [mappings, setMappings] = useState<AiModelMapping[]>([]);
  const [routes, setRoutes] = useState<AiRoute[]>([]);
  const [prompts, setPrompts] = useState<AiPromptTemplate[]>([]);
  const [policies, setPolicies] = useState<AiRiskPolicy[]>([]);
  const [latestEvalRun, setLatestEvalRun] = useState<AiEvaluationRun | null>(null);
  const [editorDefaults, setEditorDefaults] = useState<AiEditorDefaults | null>(null);

  /* ── 模态框与抽屉控制状态 ── */
  const [mappingDrawerOpen, setMappingDrawerOpen] = useState<boolean>(false);
  const [editingMappingId, setEditingMappingId] = useState<string | null>(null);
  const [mappingForm, setMappingForm] = useState<AiModelMappingWriteRequest | null>(null);

  const [routeDrawerOpen, setRouteDrawerOpen] = useState<boolean>(false);
  const [editingRouteId, setEditingRouteId] = useState<string | null>(null);
  const [routeForm, setRouteForm] = useState<AiRouteWriteRequest | null>(null);

  const [promptDrawerOpen, setPromptDrawerOpen] = useState<boolean>(false);
  const [editingPromptId, setEditingPromptId] = useState<string | null>(null);
  const [promptForm, setPromptForm] = useState<AiPromptWriteRequest | null>(null);
  const [promptSchemaText, setPromptSchemaText] = useState<string>('{}');
  const [promptSchemaError, setPromptSchemaError] = useState<string | null>(null);
  const [promptInputFieldsText, setPromptInputFieldsText] = useState<string>('');

  const [policyDrawerOpen, setPolicyDrawerOpen] = useState<boolean>(false);
  const [editingPolicyId, setEditingPolicyId] = useState<string | null>(null);
  const [policyForm, setPolicyForm] = useState<AiRiskPolicyWriteRequest | null>(null);
  const [blockedCatText, setBlockedCatText] = useState<string>('');
  const [reviewCatText, setReviewCatText] = useState<string>('');

  const [evalDialogOpen, setEvalDialogOpen] = useState<boolean>(false);
  const [evalForm, setEvalForm] = useState<AiEvaluationRunRequest | null>(null);

  const [publishDialogOpen, setPublishDialogOpen] = useState<boolean>(false);
  const [publishTarget, setPublishTarget] = useState<{ type: 'route' | 'prompt' | 'policy'; id: string; resourceVersion: number } | null>(null);
  const [publishForm, setPublishForm] = useState<AiPublishRequest | null>(null);
  const [isPublishing, setIsPublishing] = useState<boolean>(false);

  const [rollbackDialogOpen, setRollbackDialogOpen] = useState<boolean>(false);
  const [rollbackTarget, setRollbackTarget] = useState<{ type: 'route' | 'prompt' | 'policy'; id: string; resourceVersion: number; codeOrScenario: string } | null>(null);
  const [rollbackAllowedVersions, setRollbackAllowedVersions] = useState<number[]>([]);
  const [rollbackForm, setRollbackForm] = useState<AiRollbackRequest | null>(null);

  /* ── 异步加载全量数据 ── */
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        provRes,
        mapRes,
        routeRes,
        promptRes,
        policyRes,
        defaultsRes,
      ] = await Promise.all([
        repository.getProviders(),
        repository.getAiModelMappings(),
        repository.getAiRoutes(),
        repository.getAiPrompts(),
        repository.getAiRiskPolicies(),
        repository.getAiEditorDefaults(),
      ]);

      setProviders(provRes);
      setMappings(mapRes);
      setRoutes(routeRes);
      setPrompts(promptRes);
      setPolicies(policyRes);
      setEditorDefaults(defaultsRes);

      // 获取最新评测
      if (defaultsRes.publish.evaluationRunId) {
        const evalRun = await repository.getAiEvaluationRun(defaultsRes.publish.evaluationRunId);
        setLatestEvalRun(evalRun);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载 AI 运行配置数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ── 常用统计派生值 ── */
  const enabledModelsCount = mappings.filter((m) => m.enabled).length;
  const activeRoutesCount = routes.filter((r) => r.status === AiResourceStatus.Active).length;
  const activePromptsCount = prompts.filter((p) => p.status === AiResourceStatus.Active).length;
  const draftCandidatesCount =
    routes.filter((r) => r.status === AiResourceStatus.Draft).length +
    prompts.filter((p) => p.status === AiResourceStatus.Draft).length +
    policies.filter((p) => p.status === AiResourceStatus.Draft).length;

  /* ── 逻辑模型 mappings 提取选项 ── */
  const logicalModelOptions = Array.from(new Set(mappings.map((m) => m.logicalModelId)))
    .filter((id) => id.trim().length > 0)
    .map((id) => ({
      label: id,
      value: id,
    }));
  if (logicalModelOptions.length === 0 && editorDefaults?.modelMapping.logicalModelId) {
    logicalModelOptions.push({
      label: editorDefaults.modelMapping.logicalModelId,
      value: editorDefaults.modelMapping.logicalModelId,
    });
  }

  const providerOptions = providers.map((p) => ({
    label: `${p.providerName} (${p.providerId})`,
    value: p.providerId,
  }));
  if (providerOptions.length === 0) {
    providerOptions.push({ label: '请先配置供应商资源', value: '' });
  }

  const safetyPolicyOptions = policies.map((p) => ({
    label: `${p.policyCode} (v${p.version})`,
    value: p.riskPolicyId,
  }));
  if (safetyPolicyOptions.length === 0) {
    safetyPolicyOptions.push({ label: '请先配置风控策略资源', value: '' });
  }

  /* ── 模型映射 编辑与保存 ── */
  const handleOpenNewMapping = () => {
    if (!editorDefaults) return;
    setEditingMappingId(null);
    setMappingForm({ ...editorDefaults.modelMapping });
    setMappingDrawerOpen(true);
  };

  const handleOpenEditMapping = (m: AiModelMapping) => {
    setEditingMappingId(m.modelMappingId);
    setMappingForm({
      logicalModelId: m.logicalModelId,
      providerId: m.providerId,
      providerModelName: m.providerModelName,
      inputModalities: new Set(m.inputModalities),
      outputModalities: new Set(m.outputModalities),
      contextWindowTokens: m.contextWindowTokens,
      maxOutputTokens: m.maxOutputTokens,
      inputCostMicrounitsPerMillionTokens: m.inputCostMicrounitsPerMillionTokens,
      outputCostMicrounitsPerMillionTokens: m.outputCostMicrounitsPerMillionTokens,
      currency: m.currency,
      qualityTier: m.qualityTier ?? undefined,
      dataRegion: m.dataRegion ?? undefined,
      retentionPolicy: m.retentionPolicy ?? undefined,
      enabled: m.enabled,
    });
    setMappingDrawerOpen(true);
  };

  const handleSaveMapping = async () => {
    if (!mappingForm) return;
    setMutationError(null);
    try {
      const existing = mappings.find((m) => m.modelMappingId === editingMappingId);
      await repository.saveAiModelMapping(mappingForm, editingMappingId ?? undefined, existing?.resourceVersion);
      setMappingDrawerOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '保存模型映射失败');
    }
  };

  /* ── 场景路由 Targets 动态操作 ── */
  const handleAddRouteTarget = () => {
    if (!routeForm) return;
    const lastTarget = routeForm.targets[routeForm.targets.length - 1];
    const template = lastTarget ?? editorDefaults?.route.targets[0] ?? {
      modelMappingId: mappings[0]?.modelMappingId ?? '',
      priority: 1,
      timeoutMs: 0,
      retryLimit: 0,
    };
    setRouteForm({
      ...routeForm,
      targets: [
        ...routeForm.targets,
        {
          modelMappingId: template.modelMappingId,
          priority: routeForm.targets.length + 1,
          timeoutMs: template.timeoutMs,
          retryLimit: template.retryLimit,
        },
      ],
    });
  };

  const handleRemoveRouteTarget = (index: number) => {
    // 复杂校验限制：至少保留一个 Target，禁止全删
    if (!routeForm || routeForm.targets.length <= 1) return;
    const updated = routeForm.targets.filter((_, i) => i !== index);
    setRouteForm({ ...routeForm, targets: updated });
  };

  const handleUpdateRouteTarget = (index: number, field: 'modelMappingId' | 'priority' | 'timeoutMs' | 'retryLimit', value: string | number) => {
    if (!routeForm) return;
    const updated = [...routeForm.targets];
    updated[index] = {
      ...updated[index],
      [field]: value,
    };
    setRouteForm({ ...routeForm, targets: updated });
  };

  /* ── 场景路由 编辑与保存 ── */
  const handleOpenNewRoute = () => {
    if (!editorDefaults) return;
    setEditingRouteId(null);
    setRouteForm({ ...editorDefaults.route });
    setRouteDrawerOpen(true);
  };

  const handleOpenEditRoute = (r: AiRoute) => {
    setEditingRouteId(r.routeId);
    setRouteForm({
      scenario: r.scenario,
      logicalModelId: r.logicalModelId,
      targets: r.targets.map((t) => ({ ...t })),
      maxInputTokens: r.maxInputTokens,
      maxOutputTokens: r.maxOutputTokens,
      budgetCeilingMicrounits: r.budgetCeilingMicrounits,
      totalAttemptLimit: r.totalAttemptLimit,
      safetyPolicyId: r.safetyPolicyId,
    });
    setRouteDrawerOpen(true);
  };

  const handleSaveRoute = async () => {
    if (!routeForm) return;
    setMutationError(null);
    try {
      const existing = routes.find((r) => r.routeId === editingRouteId);
      await repository.saveAiRoute(routeForm, editingRouteId ?? undefined, existing?.resourceVersion);
      setRouteDrawerOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '保存场景路由失败');
    }
  };

  /* ── 提示词 编辑与保存 ── */
  const handleOpenNewPrompt = () => {
    if (!editorDefaults) return;
    setEditingPromptId(null);
    const form = { ...editorDefaults.prompt };
    setPromptForm(form);
    setPromptSchemaText(JSON.stringify(form.outputSchema, null, 2));
    setPromptSchemaError(null);
    setPromptInputFieldsText(Array.from(form.allowedInputFields).join(', '));
    setPromptDrawerOpen(true);
  };

  const handleOpenEditPrompt = (p: AiPromptTemplate) => {
    setEditingPromptId(p.promptId);
    setPromptForm({
      promptCode: p.promptCode,
      scenario: p.scenario,
      systemTemplate: p.systemTemplate,
      userTemplate: p.userTemplate,
      allowedInputFields: new Set(p.allowedInputFields),
      outputSchema: p.outputSchema,
      safetyPolicyId: p.safetyPolicyId ?? undefined,
    });
    setPromptSchemaText(JSON.stringify(p.outputSchema, null, 2));
    setPromptSchemaError(null);
    setPromptInputFieldsText(Array.from(p.allowedInputFields).join(', '));
    setPromptDrawerOpen(true);
  };

  const handleSavePrompt = async () => {
    if (!promptForm) return;
    setPromptSchemaError(null);
    setMutationError(null);

    // JSON 严格校验，拒绝静默吞错
    let parsedSchema: object;
    try {
      parsedSchema = JSON.parse(promptSchemaText);
    } catch (err: unknown) {
      setPromptSchemaError(`JSON Schema 格式错误: ${err instanceof Error ? err.message : String(err)}`);
      return;
    }

    const fieldsSet = new Set(
      promptInputFieldsText
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    );

    const payload: AiPromptWriteRequest = {
      ...promptForm,
      allowedInputFields: fieldsSet,
      outputSchema: parsedSchema,
    };

    try {
      const existing = prompts.find((p) => p.promptId === editingPromptId);
      await repository.saveAiPrompt(payload, editingPromptId ?? undefined, existing?.resourceVersion);
      setPromptDrawerOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '保存提示词失败');
    }
  };

  /* ── 风控策略 编辑与保存 ── */
  const handleOpenNewPolicy = () => {
    if (!editorDefaults) return;
    setEditingPolicyId(null);
    const form = { ...editorDefaults.riskPolicy };
    setPolicyForm(form);
    setBlockedCatText(Array.from(form.blockedCategories).join(', '));
    setReviewCatText(Array.from(form.reviewCategories).join(', '));
    setPolicyDrawerOpen(true);
  };

  const handleOpenEditPolicy = (p: AiRiskPolicy) => {
    setEditingPolicyId(p.riskPolicyId);
    setPolicyForm({
      policyCode: p.policyCode,
      blockedCategories: new Set(p.blockedCategories),
      reviewCategories: new Set(p.reviewCategories),
      inputModerationEnabled: p.inputModerationEnabled,
      outputModerationEnabled: p.outputModerationEnabled,
      promptInjectionAction: p.promptInjectionAction,
      minimumSafetyScore: p.minimumSafetyScore,
      allowAppeals: p.allowAppeals,
    });
    setBlockedCatText(Array.from(p.blockedCategories).join(', '));
    setReviewCatText(Array.from(p.reviewCategories).join(', '));
    setPolicyDrawerOpen(true);
  };

  const handleSavePolicy = async () => {
    if (!policyForm) return;
    setMutationError(null);

    const blockedSet = new Set(
      blockedCatText
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    );
    const reviewSet = new Set(
      reviewCatText
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0),
    );

    const payload: AiRiskPolicyWriteRequest = {
      ...policyForm,
      blockedCategories: blockedSet,
      reviewCategories: reviewSet,
    };

    try {
      const existing = policies.find((p) => p.riskPolicyId === editingPolicyId);
      await repository.saveAiRiskPolicy(payload, editingPolicyId ?? undefined, existing?.resourceVersion);
      setPolicyDrawerOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '保存风控策略失败');
    }
  };

  /* ── 运行评测 ── */
  const handleOpenEvalDialog = () => {
    if (!editorDefaults) return;
    setEvalForm({ ...editorDefaults.evaluationRun });
    setEvalDialogOpen(true);
  };

  const handleRunEvaluation = async () => {
    if (!evalForm) return;
    setMutationError(null);
    try {
      const res = await repository.runAiEvaluation(evalForm);
      setLatestEvalRun(res);
      setEvalDialogOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '运行评测失败');
    }
  };

  /* ── 发布操作 (二次确认 & 真实评测门槛校验) ── */
  const handleOpenPublish = (type: 'route' | 'prompt' | 'policy', id: string, rv: number) => {
    if (!editorDefaults) return;
    setPublishTarget({ type, id, resourceVersion: rv });

    // 默认填入最新已加载且完全通过闸门的评测 ID；若无合规评测则默认为空，禁止自动伪造成功评测
    const defaultEvalRunId =
      latestEvalRun &&
      latestEvalRun.status === AiEvaluationRunStatusEnum.Succeeded &&
      latestEvalRun.passed &&
      latestEvalRun.safetyPassed
        ? latestEvalRun.evaluationRunId
        : '';

    setPublishForm({
      rolloutPercentage: editorDefaults.publish.rolloutPercentage,
      effectiveAt: new Date(),
      evaluationRunId: defaultEvalRunId,
      auditReason: editorDefaults.publish.auditReason,
    });
    setPublishDialogOpen(true);
  };

  const handleConfirmPublish = async () => {
    if (!publishTarget || !publishForm) return;
    setMutationError(null);

    // 1. 字段非空与数值合法性本地校验
    const evalId = publishForm.evaluationRunId.trim();
    if (!evalId) {
      setMutationError('发布必须绑定通过的评测运行 ID (evaluationRunId)');
      return;
    }

    if (
      typeof publishForm.rolloutPercentage !== 'number' ||
      isNaN(publishForm.rolloutPercentage) ||
      publishForm.rolloutPercentage < 0 ||
      publishForm.rolloutPercentage > 100
    ) {
      setMutationError('灰度流量比例 (rolloutPercentage) 必须在 0 到 100 之间');
      return;
    }

    if (!publishForm.auditReason.trim()) {
      setMutationError('发布审计原因 (auditReason) 不能为空');
      return;
    }

    if (!(publishForm.effectiveAt instanceof Date) || isNaN(publishForm.effectiveAt.getTime())) {
      setMutationError('生效时间 (effectiveAt) 格式无效');
      return;
    }

    // 2. 从 repository 重新拉取评测记录进行真实防伪校验
    setIsPublishing(true);
    try {
      const evalRun = await repository.getAiEvaluationRun(evalId);
      if (!evalRun) {
        setMutationError(`未找到 ID 为 "${evalId}" 的评测运行记录`);
        return;
      }
      if (evalRun.status !== AiEvaluationRunStatusEnum.Succeeded) {
        setMutationError(`评测尚未成功完成 (当前状态: ${evalRun.status})`);
        return;
      }
      if (!evalRun.passed) {
        setMutationError('该评测未通过质量门槛 (passed=false)，禁止发布');
        return;
      }
      if (!evalRun.safetyPassed) {
        setMutationError('该评测未通过安全检查 (safetyPassed=false)，禁止发布');
        return;
      }

      // 3. 校验全部通过，执行发布动作
      const { type, id, resourceVersion } = publishTarget;
      if (type === 'route') {
        await repository.publishAiRoute(id, resourceVersion, publishForm);
      } else if (type === 'prompt') {
        await repository.publishAiPrompt(id, resourceVersion, publishForm);
      } else if (type === 'policy') {
        await repository.publishAiRiskPolicy(id, resourceVersion, publishForm);
      }
      setPublishDialogOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '发布失败');
    } finally {
      setIsPublishing(false);
    }
  };

  /* ── 回滚操作 (二次确认 & 仅限同资源允许历史版本) ── */
  const handleOpenRollback = (
    type: 'route' | 'prompt' | 'policy',
    id: string,
    rv: number,
    codeOrScenario: string,
    allowedVersions: number[],
  ) => {
    if (!editorDefaults) return;
    setRollbackTarget({ type, id, resourceVersion: rv, codeOrScenario });
    setRollbackAllowedVersions(allowedVersions);

    // 默认选择历史版本列表中最新的版本，禁止默认 version=1 或猜测猜测
    const defaultTargetVersion = allowedVersions[0] ?? 0;

    setRollbackForm({
      targetVersion: defaultTargetVersion,
      auditReason: editorDefaults.rollback.auditReason,
    });
    setRollbackDialogOpen(true);
  };

  const handleConfirmRollback = async () => {
    if (!rollbackTarget || !rollbackForm) return;
    setMutationError(null);

    // 复杂校验：再次二次验证 targetVersion 属于允许的历史版本列表，防止绕过 UI 错误输入
    if (!rollbackAllowedVersions.includes(rollbackForm.targetVersion)) {
      setMutationError('选中的目标回滚版本无效或不存在于允许的历史版本列表中');
      return;
    }

    try {
      const { type, id, resourceVersion } = rollbackTarget;
      if (type === 'route') {
        await repository.rollbackAiRoute(id, resourceVersion, rollbackForm);
      } else if (type === 'prompt') {
        await repository.rollbackAiPrompt(id, resourceVersion, rollbackForm);
      } else if (type === 'policy') {
        await repository.rollbackAiRiskPolicy(id, resourceVersion, rollbackForm);
      }
      setRollbackDialogOpen(false);
      await fetchData();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : '回滚失败');
    }
  };

  /* ── 渲染加载与错误状态 ── */
  if (loading && mappings.length === 0) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '60px 0' }}>
        <RefreshCw className="spin" size={28} style={{ margin: '0 auto 12px', color: 'var(--color-primary)' }} />
        <p style={{ color: 'var(--color-text-secondary)' }}>正在加载 AI 运行配置...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <Card>
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <AlertTriangle size={32} style={{ color: '#ef4444', margin: '0 auto 12px' }} />
            <h3 style={{ marginBottom: '8px' }}>加载发生错误</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '16px' }}>{error}</p>
            <Button variant="primary" onClick={fetchData}>
              重新尝试
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* 标题与同步动作 */}
      <div className="page-title-group" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600 }}>AI 运行配置</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            监控和管理模型映射、场景路由、提示词模板、安全风控策略与质量评测。
          </p>
        </div>
        <Button variant="default" onClick={fetchData} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          刷新数据
        </Button>
      </div>

      {/* Mutation 操作失败通知 */}
      {mutationError && (
        <div style={{ padding: '12px 16px', background: '#fee2e2', color: '#991b1b', borderRadius: '6px', marginBottom: '16px', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>操作失败：{mutationError}</span>
          <button onClick={() => setMutationError(null)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#991b1b', fontWeight: 600 }}>✕</button>
        </div>
      )}

      {/* 首屏 4 项统计卡片 */}
      <div className="metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '10px', background: '#e0f2fe', borderRadius: '8px', color: '#0284c7' }}>
              <Cpu size={20} />
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>启用模型数</div>
              <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '2px' }}>{enabledModelsCount}</div>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '10px', background: '#dcfce7', borderRadius: '8px', color: '#16a34a' }}>
              <Route size={20} />
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>在线路由数</div>
              <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '2px' }}>{activeRoutesCount}</div>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '10px', background: '#fef3c7', borderRadius: '8px', color: '#d97706' }}>
              <FileCode size={20} />
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>在线提示词数</div>
              <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '2px' }}>{activePromptsCount}</div>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '10px', background: '#f3e8ff', borderRadius: '8px', color: '#9333ea' }}>
              <ShieldAlert size={20} />
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>待评测草稿数</div>
              <div style={{ fontSize: '22px', fontWeight: 700, marginTop: '2px' }}>{draftCandidatesCount}</div>
            </div>
          </div>
        </Card>
      </div>

      {/* 5大核心功能页签 */}
      <div className="tabs-header">
        <button className={`tab-button ${activeTab === 'mappings' ? 'active' : ''}`} onClick={() => setActiveTab('mappings')}>
          模型映射 ({mappings.length})
        </button>
        <button className={`tab-button ${activeTab === 'routes' ? 'active' : ''}`} onClick={() => setActiveTab('routes')}>
          场景路由 ({routes.length})
        </button>
        <button className={`tab-button ${activeTab === 'prompts' ? 'active' : ''}`} onClick={() => setActiveTab('prompts')}>
          提示词 ({prompts.length})
        </button>
        <button className={`tab-button ${activeTab === 'policies' ? 'active' : ''}`} onClick={() => setActiveTab('policies')}>
          风控策略 ({policies.length})
        </button>
        <button className={`tab-button ${activeTab === 'evaluations' ? 'active' : ''}`} onClick={() => setActiveTab('evaluations')}>
          评测与发布
        </button>
      </div>

      {/* 页签一：模型映射 */}
      {activeTab === 'mappings' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>逻辑模型至供应商上游映射</h3>
            <Button variant="primary" onClick={handleOpenNewMapping}>
              <Plus size={14} />
              新建模型映射
            </Button>
          </div>

          {mappings.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-secondary)' }}>暂无模型映射数据</div>
          ) : (
            <div className="table-wrapper responsive-table">
              <table>
                <thead>
                  <tr>
                    <th>逻辑模型 ID</th>
                    <th>供应商 ID</th>
                    <th>上游模型名</th>
                    <th>模态</th>
                    <th>上下文/输出 Token</th>
                    <th>输入/输出成本(每百万Token)</th>
                    <th>货币/区域</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {mappings.map((m) => (
                    <tr key={m.modelMappingId}>
                      <td data-label="逻辑模型 ID"><strong>{m.logicalModelId}</strong></td>
                      <td data-label="供应商 ID">{m.providerId}</td>
                      <td data-label="上游模型名"><code>{m.providerModelName}</code></td>
                      <td data-label="模态">
                        {Array.from(m.inputModalities).join(',') || 'TEXT'} &rarr; {Array.from(m.outputModalities).join(',') || 'TEXT'}
                      </td>
                      <td data-label="Token上限">{m.contextWindowTokens.toLocaleString()} / {m.maxOutputTokens.toLocaleString()}</td>
                      <td data-label="成本">{m.inputCostMicrounitsPerMillionTokens.toLocaleString()} / {m.outputCostMicrounitsPerMillionTokens.toLocaleString()} 微单位 {m.currency ? `(${m.currency})` : ''}</td>
                      <td data-label="货币/区域">{m.currency} ({m.dataRegion ?? 'GLOBAL'})</td>
                      <td data-label="状态">
                        <Badge variant={m.enabled ? 'success' : 'default'}>
                          {m.enabled ? '已启用' : '已禁用'}
                        </Badge>
                      </td>
                      <td data-label="操作">
                        <Button variant="default" onClick={() => handleOpenEditMapping(m)}>
                          编辑
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* 页签二：场景路由 */}
      {activeTab === 'routes' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>场景路由配置列表</h3>
            <Button variant="primary" onClick={handleOpenNewRoute}>
              <Plus size={14} />
              新建场景路由
            </Button>
          </div>

          {routes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-secondary)' }}>暂无场景路由</div>
          ) : (
            <div className="table-wrapper responsive-table">
              <table>
                <thead>
                  <tr>
                    <th>场景名称</th>
                    <th>版本</th>
                    <th>逻辑模型</th>
                    <th>Target 映射</th>
                    <th>Token 上限 (In/Out)</th>
                    <th>预算上限/重试</th>
                    <th>状态 / 灰度</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {routes.map((r) => {
                    // 计算同 scenario 且 ID 不同的真实历史版本
                    const history = routes.filter((item) => item.scenario === r.scenario && item.routeId !== r.routeId);
                    const allowedVersions = Array.from(new Set(history.map((item) => item.version))).sort((a, b) => b - a);

                    return (
                      <tr key={r.routeId}>
                        <td data-label="场景名称"><strong>{r.scenario}</strong></td>
                        <td data-label="版本">v{r.version}</td>
                        <td data-label="逻辑模型">{r.logicalModelId}</td>
                        <td data-label="Target 映射">{r.targets.map((t) => `${t.modelMappingId}(P${t.priority})`).join(', ')}</td>
                        <td data-label="Token 上限">{r.maxInputTokens} / {r.maxOutputTokens}</td>
                        <td data-label="预算上限/重试">{r.budgetCeilingMicrounits.toLocaleString()} 微单位 / {r.totalAttemptLimit}次</td>
                        <td data-label="状态 / 灰度">
                          <Badge variant={r.status === AiResourceStatus.Active ? 'success' : r.status === AiResourceStatus.Draft ? 'warning' : 'default'}>
                            {r.status === AiResourceStatus.Active ? `在线 (${r.rolloutPercentage}%)` : r.status === AiResourceStatus.Draft ? '草稿' : '已下线'}
                          </Badge>
                        </td>
                        <td data-label="操作" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <Button variant="default" onClick={() => handleOpenEditRoute(r)}>编辑</Button>
                          {r.status !== AiResourceStatus.Active && (
                            <Button variant="primary" onClick={() => handleOpenPublish('route', r.routeId, r.resourceVersion)}>
                              <Send size={12} /> 发布
                            </Button>
                          )}
                          <Button
                            variant="default"
                            disabled={allowedVersions.length === 0}
                            title={allowedVersions.length === 0 ? '暂无历史版本' : undefined}
                            onClick={() => handleOpenRollback('route', r.routeId, r.resourceVersion, r.scenario, allowedVersions)}
                          >
                            <RotateCcw size={12} /> {allowedVersions.length === 0 ? '暂无历史版本' : '回滚'}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* 页签三：提示词 */}
      {activeTab === 'prompts' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>提示词模板库</h3>
            <Button variant="primary" onClick={handleOpenNewPrompt}>
              <Plus size={14} />
              新建提示词
            </Button>
          </div>

          {prompts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-secondary)' }}>暂无提示词模板</div>
          ) : (
            <div className="table-wrapper responsive-table">
              <table>
                <thead>
                  <tr>
                    <th>Prompt 代码</th>
                    <th>版本</th>
                    <th>场景</th>
                    <th>System 模板预览</th>
                    <th>允许输入字段</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {prompts.map((p) => {
                    const history = prompts.filter((item) => item.promptCode === p.promptCode && item.promptId !== p.promptId);
                    const allowedVersions = Array.from(new Set(history.map((item) => item.version))).sort((a, b) => b - a);

                    return (
                      <tr key={p.promptId}>
                        <td data-label="Prompt 代码"><strong>{p.promptCode}</strong></td>
                        <td data-label="版本">v{p.version}</td>
                        <td data-label="场景">{p.scenario}</td>
                        <td data-label="System 模板预览" style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {p.systemTemplate}
                        </td>
                        <td data-label="允许输入字段">{Array.from(p.allowedInputFields).join(', ') || '-'}</td>
                        <td data-label="状态">
                          <Badge variant={p.status === AiResourceStatus.Active ? 'success' : p.status === AiResourceStatus.Draft ? 'warning' : 'default'}>
                            {p.status === AiResourceStatus.Active ? '在线' : p.status === AiResourceStatus.Draft ? '草稿' : '已归档'}
                          </Badge>
                        </td>
                        <td data-label="操作" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <Button variant="default" onClick={() => handleOpenEditPrompt(p)}>编辑</Button>
                          {p.status !== AiResourceStatus.Active && (
                            <Button variant="primary" onClick={() => handleOpenPublish('prompt', p.promptId, p.resourceVersion)}>
                              <Send size={12} /> 发布
                            </Button>
                          )}
                          <Button
                            variant="default"
                            disabled={allowedVersions.length === 0}
                            title={allowedVersions.length === 0 ? '暂无历史版本' : undefined}
                            onClick={() => handleOpenRollback('prompt', p.promptId, p.resourceVersion, p.promptCode, allowedVersions)}
                          >
                            <RotateCcw size={12} /> {allowedVersions.length === 0 ? '暂无历史版本' : '回滚'}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* 页签四：风控策略 */}
      {activeTab === 'policies' && (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>AI 安全与风控策略</h3>
            <Button variant="primary" onClick={handleOpenNewPolicy}>
              <Plus size={14} />
              新建风控策略
            </Button>
          </div>

          {policies.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-secondary)' }}>暂无风控策略</div>
          ) : (
            <div className="table-wrapper responsive-table">
              <table>
                <thead>
                  <tr>
                    <th>策略编码</th>
                    <th>版本</th>
                    <th>阻断分类</th>
                    <th>注入拦截动作</th>
                    <th>最低安全分</th>
                    <th>申诉</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {policies.map((pol) => {
                    const history = policies.filter((item) => item.policyCode === pol.policyCode && item.riskPolicyId !== pol.riskPolicyId);
                    const allowedVersions = Array.from(new Set(history.map((item) => item.version))).sort((a, b) => b - a);

                    return (
                      <tr key={pol.riskPolicyId}>
                        <td data-label="策略编码"><strong>{pol.policyCode}</strong></td>
                        <td data-label="版本">v{pol.version}</td>
                        <td data-label="阻断分类">{Array.from(pol.blockedCategories).join(', ') || '无'}</td>
                        <td data-label="注入拦截动作"><code>{pol.promptInjectionAction}</code></td>
                        <td data-label="最低安全分">{pol.minimumSafetyScore}分</td>
                        <td data-label="申诉">{pol.allowAppeals ? '允许' : '禁止'}</td>
                        <td data-label="状态">
                          <Badge variant={pol.status === AiResourceStatus.Active ? 'success' : pol.status === AiResourceStatus.Draft ? 'warning' : 'default'}>
                            {pol.status === AiResourceStatus.Active ? '在线' : pol.status === AiResourceStatus.Draft ? '草稿' : '已停用'}
                          </Badge>
                        </td>
                        <td data-label="操作" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                          <Button variant="default" onClick={() => handleOpenEditPolicy(pol)}>编辑</Button>
                          {pol.status !== AiResourceStatus.Active && (
                            <Button variant="primary" onClick={() => handleOpenPublish('policy', pol.riskPolicyId, pol.resourceVersion)}>
                              <Send size={12} /> 发布
                            </Button>
                          )}
                          <Button
                            variant="default"
                            disabled={allowedVersions.length === 0}
                            title={allowedVersions.length === 0 ? '暂无历史版本' : undefined}
                            onClick={() => handleOpenRollback('policy', pol.riskPolicyId, pol.resourceVersion, pol.policyCode, allowedVersions)}
                          >
                            <RotateCcw size={12} /> {allowedVersions.length === 0 ? '暂无历史版本' : '回滚'}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* 页签五：评测与发布 */}
      {activeTab === 'evaluations' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 600 }}>模型评测闸门与历史概览</h3>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                  发布 Prompt 与 Route 必须拥有通过判定 (passed=true) 的评测运行记录。
                </p>
              </div>
              <Button variant="primary" onClick={handleOpenEvalDialog}>
                <Play size={14} />
                发起新评测
              </Button>
            </div>

            {latestEvalRun ? (
              <div style={{ background: 'var(--color-surface-sub)', padding: '16px', borderRadius: '8px', border: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <strong>最新评测记录：{latestEvalRun.evaluationRunId}</strong>
                    <Badge variant={latestEvalRun.status === AiEvaluationRunStatusEnum.Succeeded && latestEvalRun.passed ? 'success' : 'danger'}>
                      {latestEvalRun.status} ({latestEvalRun.passed ? 'GATE PASSED' : 'GATE FAILED'})
                    </Badge>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    更新时间: {new Date(latestEvalRun.updatedAt).toLocaleString()}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>综合得分</span>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: latestEvalRun.passed ? '#16a34a' : '#d97706' }}>
                      {latestEvalRun.score} 分
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>安全检查过闸</span>
                    <div style={{ fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
                      {latestEvalRun.safetyPassed ? <CheckCircle size={16} color="#16a34a" /> : <AlertTriangle size={16} color="#dc2626" />}
                      {latestEvalRun.safetyPassed ? '安全通过' : '安全不达标'}
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>测试案例进度</span>
                    <div style={{ fontSize: '14px', fontWeight: 600, marginTop: '4px' }}>
                      {latestEvalRun.completedCases} / {latestEvalRun.totalCases}
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>产生预估成本</span>
                    <div style={{ fontSize: '14px', fontWeight: 600, marginTop: '4px' }}>
                      {latestEvalRun.costMicrounits.toLocaleString()} 微单位
                    </div>
                  </div>
                </div>

                {latestEvalRun.failureCode && (
                  <div style={{ marginTop: '12px', fontSize: '12px', color: '#dc2626' }}>
                    失败原因码：{latestEvalRun.failureCode}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--color-text-secondary)' }}>
                暂无评测记录，请发起新评测。
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ── 抽屉：模型映射 编辑/新建 ── */}
      <Drawer open={mappingDrawerOpen} title={editingMappingId ? '编辑模型映射' : '新建模型映射'} onClose={() => setMappingDrawerOpen(false)}>
        {mappingForm && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Input
              label="逻辑模型 ID"
              value={mappingForm.logicalModelId}
              onChange={(e) => setMappingForm({ ...mappingForm, logicalModelId: e.target.value })}
            />
            <Select
              label="关联供应商"
              options={providerOptions}
              value={mappingForm.providerId}
              onChange={(e) => setMappingForm({ ...mappingForm, providerId: e.target.value })}
            />
            <Input
              label="供应商上游模型名 (Upstream Model)"
              value={mappingForm.providerModelName}
              onChange={(e) => setMappingForm({ ...mappingForm, providerModelName: e.target.value })}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>支持输入模态</label>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {Object.values(AiModality).map((mod) => (
                  <label key={`in-${mod}`} style={{ fontSize: '13px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <input
                      type="checkbox"
                      checked={mappingForm.inputModalities.has(mod as AiModality)}
                      onChange={(e) => {
                        const updated = new Set(mappingForm.inputModalities);
                        if (e.target.checked) updated.add(mod as AiModality);
                        else updated.delete(mod as AiModality);
                        setMappingForm({ ...mappingForm, inputModalities: updated });
                      }}
                    />
                    {mod}
                  </label>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
              <label style={{ fontSize: '13px', fontWeight: 500 }}>支持输出模态</label>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {Object.values(AiModality).map((mod) => (
                  <label key={`out-${mod}`} style={{ fontSize: '13px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <input
                      type="checkbox"
                      checked={mappingForm.outputModalities.has(mod as AiModality)}
                      onChange={(e) => {
                        const updated = new Set(mappingForm.outputModalities);
                        if (e.target.checked) updated.add(mod as AiModality);
                        else updated.delete(mod as AiModality);
                        setMappingForm({ ...mappingForm, outputModalities: updated });
                      }}
                    />
                    {mod}
                  </label>
                ))}
              </div>
            </div>
            <Input
              label="上下文 Token 窗口上限"
              type="number"
              value={mappingForm.contextWindowTokens}
              onChange={(e) => setMappingForm({ ...mappingForm, contextWindowTokens: Number(e.target.value) })}
            />
            <Input
              label="单次最大输出 Token 限制"
              type="number"
              value={mappingForm.maxOutputTokens}
              onChange={(e) => setMappingForm({ ...mappingForm, maxOutputTokens: Number(e.target.value) })}
            />
            <Input
              label="输入成本 (MicroUnits/百万Token)"
              type="number"
              value={mappingForm.inputCostMicrounitsPerMillionTokens}
              onChange={(e) => setMappingForm({ ...mappingForm, inputCostMicrounitsPerMillionTokens: Number(e.target.value) })}
            />
            <Input
              label="输出成本 (MicroUnits/百万Token)"
              type="number"
              value={mappingForm.outputCostMicrounitsPerMillionTokens}
              onChange={(e) => setMappingForm({ ...mappingForm, outputCostMicrounitsPerMillionTokens: Number(e.target.value) })}
            />
            <Input
              label="计费货币代号"
              value={mappingForm.currency}
              onChange={(e) => setMappingForm({ ...mappingForm, currency: e.target.value })}
            />
            <Input
              label="质量等级 (Quality Tier)"
              value={mappingForm.qualityTier ?? ''}
              onChange={(e) => setMappingForm({ ...mappingForm, qualityTier: e.target.value })}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
              <input
                type="checkbox"
                id="mapping-enabled"
                checked={mappingForm.enabled}
                onChange={(e) => setMappingForm({ ...mappingForm, enabled: e.target.checked })}
              />
              <label htmlFor="mapping-enabled" style={{ fontSize: '13px', cursor: 'pointer' }}>启用该模型映射</label>
            </div>
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <Button variant="default" onClick={() => setMappingDrawerOpen(false)}>取消</Button>
              <Button variant="primary" onClick={handleSaveMapping}>保存修改</Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* ── 抽屉：场景路由 编辑/新建 ── */}
      <Drawer open={routeDrawerOpen} title={editingRouteId ? '编辑场景路由' : '新建场景路由'} onClose={() => setRouteDrawerOpen(false)}>
        {routeForm && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Select
              label="场景名称"
              options={Object.values(AiScenario).map((s) => ({ label: s, value: s }))}
              value={routeForm.scenario}
              onChange={(e) => setRouteForm({ ...routeForm, scenario: e.target.value as AiScenario })}
            />
            <Select
              label="目标逻辑模型"
              options={logicalModelOptions}
              value={routeForm.logicalModelId}
              onChange={(e) => setRouteForm({ ...routeForm, logicalModelId: e.target.value })}
            />
            <Select
              label="绑定安全风控策略"
              options={safetyPolicyOptions}
              value={routeForm.safetyPolicyId}
              onChange={(e) => setRouteForm({ ...routeForm, safetyPolicyId: e.target.value })}
            />

            {/* 动态 Route Targets 多节点管理 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px', marginBottom: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: '13px', fontWeight: 600 }}>Route Target 目标节点映射</label>
                <Button variant="default" type="button" onClick={handleAddRouteTarget} style={{ fontSize: '12px', padding: '2px 8px' }}>
                  <Plus size={12} /> 添加 Target
                </Button>
              </div>
              {routeForm.targets.map((t, idx) => (
                <div key={`target-${idx}`} style={{ background: 'var(--color-surface-sub)', padding: '10px', borderRadius: '6px', border: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600 }}>Target 节点 #{idx + 1}</span>
                    <Button
                      variant="default"
                      type="button"
                      disabled={routeForm.targets.length <= 1}
                      onClick={() => handleRemoveRouteTarget(idx)}
                      style={{ fontSize: '12px', padding: '2px 8px', color: routeForm.targets.length <= 1 ? 'var(--color-text-secondary)' : '#dc2626' }}
                    >
                      删除
                    </Button>
                  </div>
                  <Select
                    label="目标模型映射 (Model Mapping)"
                    options={mappings.length > 0
                      ? mappings.map((m) => ({ label: `${m.logicalModelId} -> ${m.providerModelName} (${m.modelMappingId})`, value: m.modelMappingId }))
                      : [{ label: '请先配置模型映射资源', value: '' }]}
                    value={t.modelMappingId}
                    onChange={(e) => handleUpdateRouteTarget(idx, 'modelMappingId', e.target.value)}
                  />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                    <Input
                      label="优先级"
                      type="number"
                      value={t.priority}
                      onChange={(e) => handleUpdateRouteTarget(idx, 'priority', Number(e.target.value))}
                    />
                    <Input
                      label="超时 (ms)"
                      type="number"
                      value={t.timeoutMs}
                      onChange={(e) => handleUpdateRouteTarget(idx, 'timeoutMs', Number(e.target.value))}
                    />
                    <Input
                      label="重试次数"
                      type="number"
                      value={t.retryLimit}
                      onChange={(e) => handleUpdateRouteTarget(idx, 'retryLimit', Number(e.target.value))}
                    />
                  </div>
                </div>
              ))}
            </div>

            <Input
              label="最大输入 Token"
              type="number"
              value={routeForm.maxInputTokens}
              onChange={(e) => setRouteForm({ ...routeForm, maxInputTokens: Number(e.target.value) })}
            />
            <Input
              label="最大输出 Token"
              type="number"
              value={routeForm.maxOutputTokens}
              onChange={(e) => setRouteForm({ ...routeForm, maxOutputTokens: Number(e.target.value) })}
            />
            <Input
              label="单次请求预算上限 (MicroUnits)"
              type="number"
              value={routeForm.budgetCeilingMicrounits}
              onChange={(e) => setRouteForm({ ...routeForm, budgetCeilingMicrounits: Number(e.target.value) })}
            />
            <Input
              label="总重试上限次数"
              type="number"
              value={routeForm.totalAttemptLimit}
              onChange={(e) => setRouteForm({ ...routeForm, totalAttemptLimit: Number(e.target.value) })}
            />
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <Button variant="default" onClick={() => setRouteDrawerOpen(false)}>取消</Button>
              <Button variant="primary" onClick={handleSaveRoute}>保存修改</Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* ── 抽屉：提示词 编辑/新建 ── */}
      <Drawer open={promptDrawerOpen} title={editingPromptId ? '编辑提示词模板' : '新建提示词模板'} onClose={() => setPromptDrawerOpen(false)}>
        {promptForm && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Input
              label="Prompt Code"
              value={promptForm.promptCode}
              onChange={(e) => setPromptForm({ ...promptForm, promptCode: e.target.value })}
            />
            <Select
              label="适用场景"
              options={Object.values(AiScenario).map((s) => ({ label: s, value: s }))}
              value={promptForm.scenario}
              onChange={(e) => setPromptForm({ ...promptForm, scenario: e.target.value as AiScenario })}
            />
            <Textarea
              label="System Prompt 模板"
              rows={4}
              value={promptForm.systemTemplate}
              onChange={(e) => setPromptForm({ ...promptForm, systemTemplate: e.target.value })}
            />
            <Textarea
              label="User Prompt 模板"
              rows={4}
              value={promptForm.userTemplate}
              onChange={(e) => setPromptForm({ ...promptForm, userTemplate: e.target.value })}
            />
            <Input
              label="允许输入变量字段 (逗号分隔)"
              value={promptInputFieldsText}
              onChange={(e) => setPromptInputFieldsText(e.target.value)}
            />
            <Textarea
              label="Output JSON Schema (必填 JSON)"
              rows={6}
              value={promptSchemaText}
              error={promptSchemaError ?? undefined}
              onChange={(e) => {
                setPromptSchemaText(e.target.value);
                setPromptSchemaError(null);
              }}
            />
            <Select
              label="关联安全风控策略"
              options={safetyPolicyOptions}
              value={promptForm.safetyPolicyId ?? ''}
              onChange={(e) => setPromptForm({ ...promptForm, safetyPolicyId: e.target.value })}
            />
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <Button variant="default" onClick={() => setPromptDrawerOpen(false)}>取消</Button>
              <Button variant="primary" onClick={handleSavePrompt}>保存修改</Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* ── 抽屉：风控策略 编辑/新建 ── */}
      <Drawer open={policyDrawerOpen} title={editingPolicyId ? '编辑风控策略' : '新建风控策略'} onClose={() => setPolicyDrawerOpen(false)}>
        {policyForm && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Input
              label="策略编码 (Policy Code)"
              value={policyForm.policyCode}
              onChange={(e) => setPolicyForm({ ...policyForm, policyCode: e.target.value })}
            />
            <Input
              label="阻断敏感词分类 (逗号分隔)"
              value={blockedCatText}
              onChange={(e) => setBlockedCatText(e.target.value)}
            />
            <Input
              label="需复核分类 (逗号分隔)"
              value={reviewCatText}
              onChange={(e) => setReviewCatText(e.target.value)}
            />
            <Select
              label="提示词注入拦截动作"
              options={Object.values(AiRiskPolicyPromptInjectionActionEnum).map((action) => ({ label: action, value: action }))}
              value={policyForm.promptInjectionAction}
              onChange={(e) => setPolicyForm({ ...policyForm, promptInjectionAction: e.target.value as typeof policyForm.promptInjectionAction })}
            />
            <Input
              label="最低安全得分门槛"
              type="number"
              value={policyForm.minimumSafetyScore}
              onChange={(e) => setPolicyForm({ ...policyForm, minimumSafetyScore: Number(e.target.value) })}
            />
            <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={policyForm.inputModerationEnabled}
                  onChange={(e) => setPolicyForm({ ...policyForm, inputModerationEnabled: e.target.checked })}
                />
                启用输入审核
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={policyForm.outputModerationEnabled}
                  onChange={(e) => setPolicyForm({ ...policyForm, outputModerationEnabled: e.target.checked })}
                />
                启用输出审核
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={policyForm.allowAppeals}
                  onChange={(e) => setPolicyForm({ ...policyForm, allowAppeals: e.target.checked })}
                />
                允许申诉
              </label>
            </div>
            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <Button variant="default" onClick={() => setPolicyDrawerOpen(false)}>取消</Button>
              <Button variant="primary" onClick={handleSavePolicy}>保存修改</Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* ── 对话框：运行评测 二次确认 ── */}
      <Dialog
        open={evalDialogOpen}
        title="发起模型与 Prompt 评测运行"
        onClose={() => setEvalDialogOpen(false)}
        footer={
          <>
            <Button variant="default" onClick={() => setEvalDialogOpen(false)}>取消</Button>
            <Button variant="primary" onClick={handleRunEvaluation}>开始评测</Button>
          </>
        }
      >
        {evalForm && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Select
              label="选择目标 Prompt"
              options={prompts.map((p) => ({ label: `${p.promptCode} (v${p.version})`, value: p.promptId }))}
              value={evalForm.promptId}
              onChange={(e) => setEvalForm({ ...evalForm, promptId: e.target.value })}
            />
            <Select
              label="选择目标场景路由"
              options={routes.map((r) => ({ label: `${r.scenario} (v${r.version})`, value: r.routeId }))}
              value={evalForm.routeId}
              onChange={(e) => setEvalForm({ ...evalForm, routeId: e.target.value })}
            />
            <Select
              label="评估裁判模型"
              options={logicalModelOptions}
              value={evalForm.evaluatorLogicalModelId}
              onChange={(e) => setEvalForm({ ...evalForm, evaluatorLogicalModelId: e.target.value })}
            />
            <Input
              label="最大评测成本预算 (MicroUnits)"
              type="number"
              value={evalForm.maxCostMicrounits}
              onChange={(e) => setEvalForm({ ...evalForm, maxCostMicrounits: Number(e.target.value) })}
            />
          </div>
        )}
      </Dialog>

      {/* ── 对话框：发布二次确认 ── */}
      <Dialog
        open={publishDialogOpen}
        title="确认发布上线"
        onClose={() => setPublishDialogOpen(false)}
        footer={
          <>
            <Button variant="default" onClick={() => setPublishDialogOpen(false)}>取消</Button>
            <Button variant="primary" disabled={isPublishing} onClick={handleConfirmPublish}>
              {isPublishing ? '校验发布中...' : '确认发布'}
            </Button>
          </>
        }
      >
        {publishForm && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              发布操作将使此草稿资源成为生产环境的在线生效版本。发布前将强校验绑定评测运行记录状态。
            </p>
            <Input
              label="绑定评测 Run ID (必须为通过闸门记录)"
              value={publishForm.evaluationRunId}
              onChange={(e) => setPublishForm({ ...publishForm, evaluationRunId: e.target.value })}
            />
            <Input
              label="流量灰度比例 (0 - 100%)"
              type="number"
              value={publishForm.rolloutPercentage}
              onChange={(e) => setPublishForm({ ...publishForm, rolloutPercentage: Number(e.target.value) })}
            />
            <Input
              label="生效时间 (Effective At)"
              type="datetime-local"
              value={formatDateToLocalInput(publishForm.effectiveAt)}
              onChange={(e) => setPublishForm({ ...publishForm, effectiveAt: parseLocalInputToDate(e.target.value) })}
            />
            <Textarea
              label="发布审计原因"
              rows={2}
              value={publishForm.auditReason}
              onChange={(e) => setPublishForm({ ...publishForm, auditReason: e.target.value })}
            />
          </div>
        )}
      </Dialog>

      {/* ── 对话框：回滚二次确认 ── */}
      <Dialog
        open={rollbackDialogOpen}
        title="确认回滚上线资源"
        onClose={() => setRollbackDialogOpen(false)}
        footer={
          <>
            <Button variant="default" onClick={() => setRollbackDialogOpen(false)}>取消</Button>
            <Button variant="danger" onClick={handleConfirmRollback}>确认回滚</Button>
          </>
        }
      >
        {rollbackForm && rollbackTarget && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <p style={{ fontSize: '13px', color: '#b91c1c' }}>
              警告：回滚将立刻使选中的历史版本重新在生产环境上线！请确保选择合规的目标版本。
            </p>
            <Select
              label="目标回滚版本 (Target Version)"
              options={rollbackAllowedVersions.map((v) => ({
                label: `版本 v${v}`,
                value: String(v),
              }))}
              value={String(rollbackForm.targetVersion)}
              onChange={(e) => setRollbackForm({ ...rollbackForm, targetVersion: Number(e.target.value) })}
            />
            <Textarea
              label="回滚审计原因"
              rows={2}
              value={rollbackForm.auditReason}
              onChange={(e) => setRollbackForm({ ...rollbackForm, auditReason: e.target.value })}
            />
          </div>
        )}
      </Dialog>
    </div>
  );
};
