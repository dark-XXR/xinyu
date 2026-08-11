/**
 * 网站设置页面。
 * 配置网站名称、App名称、公司名称、本地 Logo 图片、客服邮箱、隐私邮箱、默认语言、官网、备案、维护模式及提示。
 * 清楚区分线上已发布版本和当前草稿，保存草稿与线上发布拥有独立确认机制，发布需至少8字中文审计理由。
 */
import React, { useState, useEffect } from 'react';
import {
  Globe,
  Mail,
  Shield,
  AlertOctagon,
  Save,
  Send,
  RefreshCw,
  CheckCircle2,
} from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Badge } from '../../components/ui/Badge';
import { Dialog } from '../../components/ui/Dialog';
import { MediaUpload } from '../../components/ui/MediaUpload';
import { repository } from '../../api/repository';
import type { SystemIdentityConfig } from '../../api/models';
import { MediaPurpose } from '../../api/models';

export const SettingsPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [publishedConfig, setPublishedConfig] = useState<SystemIdentityConfig | null>(null);
  const [hasUnpublishedChanges, setHasUnpublishedChanges] = useState<boolean>(false);
  const [publishedAt, setPublishedAt] = useState<Date | undefined>(undefined);
  const [version, setVersion] = useState<number>(1);
  const [draftResourceVersion, setDraftResourceVersion] = useState<number | undefined>(undefined);
  const [publishedResourceVersion, setPublishedResourceVersion] = useState<number | undefined>(undefined);
  const [resourceVersion, setResourceVersion] = useState<number | undefined>(undefined);

  // 当前草稿表单
  const [form, setForm] = useState<SystemIdentityConfig>({
    websiteName: '',
    appName: '',
    companyName: '',
    logoUrl: null,
    customerServiceEmail: '',
    privacyEmail: '',
    defaultLocale: 'zh-CN',
    officialWebsiteUrl: '',
    filingInformation: '',
    maintenanceMode: false,
    maintenanceMessage: '',
  });

  const [saveLoading, setSaveLoading] = useState<boolean>(false);
  const [logoUploading, setLogoUploading] = useState<boolean>(false);

  // 发布 Modal
  const [publishModalOpen, setPublishModalOpen] = useState<boolean>(false);
  const [publishAuditReason, setPublishAuditReason] = useState<string>('');
  const [publishLoading, setPublishLoading] = useState<boolean>(false);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await repository.getAdminSystemConfig();
      if (res.publishedConfig) {
        setPublishedConfig(res.publishedConfig);
      }
      if (res.draftConfig) {
        setForm(res.draftConfig);
      } else if (res.publishedConfig) {
        setForm(res.publishedConfig);
      }
      setHasUnpublishedChanges(!!res.hasUnpublishedChanges);
      setPublishedAt(res.publishedAt);
      if (res.version) setVersion(res.version);
      setDraftResourceVersion(res.draftResourceVersion);
      setPublishedResourceVersion(res.publishedResourceVersion);
      setResourceVersion(res.resourceVersion);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载网站系统设置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSaveDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (logoUploading) {
      setError('Logo 图片正在上传处理中，请等待上传完成后保存');
      return;
    }
    setSaveLoading(true);
    setError(null);
    try {
      // 传入真实 If-Match 参数：优先使用草稿资源版本、当前资源版本、线上发布版本或主版本号
      const targetVersion = draftResourceVersion ?? resourceVersion ?? publishedResourceVersion ?? version;
      const ifMatchStr = String(targetVersion);

      await repository.updateAdminSystemConfig({
        _configuration: form,
        auditReason: '更新网站与 App 系统品牌基础设置草稿',
      }, ifMatchStr);

      setSuccessMsg('网站配置草稿保存成功');
      await fetchConfig();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存配置草稿失败');
    } finally {
      setSaveLoading(false);
    }
  };

  const openPublishModal = () => {
    setPublishAuditReason('');
    setPublishModalOpen(true);
  };

  const handlePublishSubmit = async () => {
    setPublishLoading(true);
    setError(null);
    try {
      // 发布必须使用草稿的 resourceVersion（如果只有线上版则使用线上 resourceVersion）
      const targetVersion = draftResourceVersion ?? resourceVersion ?? publishedResourceVersion ?? version;
      const ifMatchStr = String(targetVersion);

      await repository.publishAdminSystemConfig(publishAuditReason.trim(), ifMatchStr);
      setSuccessMsg('已成功将当前设置草稿发布至线上生效');
      setPublishModalOpen(false);
      await fetchConfig();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '发布线上设置失败');
    } finally {
      setPublishLoading(false);
    }
  };

  const isPublishReasonValid = publishAuditReason.trim().length >= 8;
  const canSubmitPublish = isPublishReasonValid && !publishLoading;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 头部导航与发布状态 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--color-text-primary)' }}>网站设置与品牌配置</h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            管理官方网站、App 品牌身份、备案法务邮箱及维护模式。区分线上发布版与草稿版。
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {hasUnpublishedChanges ? (
            <Badge variant="warning">有未发布的草稿修改</Badge>
          ) : (
            <Badge variant="success">已发布至最新 (v{version})</Badge>
          )}
          <Button variant="default" onClick={fetchConfig} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> 刷新
          </Button>
          <Button variant="primary" onClick={openPublishModal} disabled={loading || publishLoading || logoUploading}>
            <Send size={14} /> 发布线上配置
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
            <AlertOctagon size={18} />
            <div style={{ flex: 1, fontSize: '13px' }}>{error}</div>
            <Button variant="default" style={{ height: '28px', fontSize: '12px' }} onClick={fetchConfig}>重试</Button>
          </div>
        </Card>
      )}

      {/* 线上已发布对照视口 */}
      {publishedConfig && (
        <Card style={{ background: '#fafafa', borderStyle: 'dashed' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '13px' }}>
              <CheckCircle2 size={16} style={{ color: 'var(--color-success)' }} />
              线上当前生效配置摘要 (v{version})
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
              上次发布于: {publishedAt ? new Date(publishedAt).toLocaleString('zh-CN') : '未记载'}
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
            <div>网站名称: <strong>{publishedConfig.websiteName}</strong></div>
            <div>App 名称: <strong>{publishedConfig.appName}</strong></div>
            <div>公司主体: <strong>{publishedConfig.companyName}</strong></div>
            <div>ICP 备案: <strong>{publishedConfig.filingInformation || '未配置'}</strong></div>
            <div>维护模式: <Badge variant={publishedConfig.maintenanceMode ? 'danger' : 'success'}>{publishedConfig.maintenanceMode ? '开启维护' : '正常运行'}</Badge></div>
          </div>
        </Card>
      )}

      {/* 草稿配置表单 */}
      <form onSubmit={handleSaveDraft}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* 品牌与身份 */}
          <Card>
            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Globe size={16} /> 品牌与系统标识
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>网站名称 *</label>
                <Input
                  placeholder="例如: 爱回复 Web 运营管理后台"
                  value={form.websiteName}
                  onChange={(e) => setForm({ ...form, websiteName: e.target.value })}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>App 名称 *</label>
                <Input
                  placeholder="例如: 爱回复 APP"
                  value={form.appName}
                  onChange={(e) => setForm({ ...form, appName: e.target.value })}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>公司主体 *</label>
                <Input
                  placeholder="例如: 爱回复科技 (北京) 有限公司"
                  value={form.companyName}
                  onChange={(e) => setForm({ ...form, companyName: e.target.value })}
                  required
                />
              </div>
              <div>
                <label htmlFor="system-logo-upload-input" style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
                  网站与 App 品牌 Logo
                </label>
                <MediaUpload
                  id="system-logo-upload-input"
                  value={form.logoUrl ?? null}
                  purpose={MediaPurpose.WebsiteBrand}
                  auditReason="更新网站与 App 系统品牌 Logo 资产上传"
                  onChange={(url) => setForm({ ...form, logoUrl: url ?? null })}
                  onUploadingChange={setLogoUploading}
                  disabled={saveLoading}
                  label="品牌 Logo"
                />
              </div>
            </div>
          </Card>

          {/* 邮箱与备案法务 */}
          <Card>
            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Mail size={16} /> 法务合规与客服支持
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>客服支持邮箱 *</label>
                <Input
                  type="email"
                  placeholder="support@lovereply.app"
                  value={form.customerServiceEmail}
                  onChange={(e) => setForm({ ...form, customerServiceEmail: e.target.value })}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>隐私合规邮箱 *</label>
                <Input
                  type="email"
                  placeholder="privacy@lovereply.app"
                  value={form.privacyEmail}
                  onChange={(e) => setForm({ ...form, privacyEmail: e.target.value })}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>官网链接</label>
                <Input
                  placeholder="https://lovereply.app"
                  value={form.officialWebsiteUrl || ''}
                  onChange={(e) => setForm({ ...form, officialWebsiteUrl: e.target.value })}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>ICP 备案许可号</label>
                <Input
                  placeholder="京ICP备20268888号-1"
                  value={form.filingInformation || ''}
                  onChange={(e) => setForm({ ...form, filingInformation: e.target.value })}
                />
              </div>
            </div>
          </Card>

          {/* 维护模式开关 */}
          <Card style={{ borderColor: form.maintenanceMode ? 'var(--color-danger)' : 'var(--color-border)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px', color: form.maintenanceMode ? 'var(--color-danger)' : 'inherit' }}>
              <Shield size={16} /> 紧急维护与运行控制
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <input
                  type="checkbox"
                  id="maintenanceMode"
                  checked={form.maintenanceMode}
                  onChange={(e) => setForm({ ...form, maintenanceMode: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                <label htmlFor="maintenanceMode" style={{ fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
                  开启全站停机例行维护模式 (开启后普通 API 与 App 请求将返回维护阻断响应)
                </label>
              </div>

              {form.maintenanceMode && (
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px', color: 'var(--color-danger)' }}>
                    维护提示文案 *
                  </label>
                  <Textarea
                    placeholder="请输入面向用户展示的维护提醒文案..."
                    value={form.maintenanceMessage || ''}
                    onChange={(e) => setForm({ ...form, maintenanceMessage: e.target.value })}
                    rows={2}
                  />
                </div>
              )}
            </div>
          </Card>

          {/* 保存草稿提交按钮 */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <Button variant="primary" type="submit" disabled={saveLoading || logoUploading}>
              <Save size={16} /> {saveLoading ? '保存中...' : logoUploading ? 'Logo 上传中...' : '保存为修改草稿'}
            </Button>
          </div>
        </div>
      </form>

      {/* 发布线上对话框 Dialog */}
      <Dialog
        open={publishModalOpen}
        onClose={() => setPublishModalOpen(false)}
        title="发布网站设置至线上"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            您即将把当前修改的配置草稿发布至线上环境。该操作将立即变更网站名称、App 品牌及全局维护模式状态。
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, marginBottom: '4px' }}>
              线上发布审计理由 <span style={{ color: 'var(--color-danger)' }}>*（至少 8 字中文）</span>
            </label>
            <Textarea
              placeholder="请输入发布线上配置的明确审计理由（例如：更新备案号及客服支持邮箱）"
              value={publishAuditReason}
              onChange={(e) => setPublishAuditReason(e.target.value)}
              rows={3}
            />
            <div style={{ fontSize: '11px', textAlign: 'right', marginTop: '2px', color: isPublishReasonValid ? 'var(--color-success)' : 'var(--color-text-tertiary)' }}>
              当前字数: {publishAuditReason.trim().length} / 至少 8 字
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
            <Button variant="default" onClick={() => setPublishModalOpen(false)} disabled={publishLoading}>
              取消
            </Button>
            <Button variant="primary" onClick={handlePublishSubmit} disabled={!canSubmitPublish}>
              {publishLoading ? '发布中...' : '确认发布至线上'}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
