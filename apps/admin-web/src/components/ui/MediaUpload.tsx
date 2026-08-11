/**
 * 媒体资源上传控件组件。
 * 提供本地单文件选择、格式与大小校验（PNG/JPEG/WebP、5 MiB）、图片预览、
 * 上传状态管理（上传中/失败）、图标化重新选择和移除功能。
 * 不支持也不提供 URL 粘贴；符合 HTML 规范与可访问性设计要求。
 */
import React, { useState, useRef } from 'react';
import { Upload, X, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { MediaPurpose } from '../../api/models';
import { repository } from '../../api/repository';

export interface MediaUploadProps {
  /** input 稳定 ID，用于与外部 label 搭配及 DOM 标识 */
  id?: string;
  /** 当前选定或已有图片的 URL 预览地址 */
  value?: string | null;
  /** 媒体资源用途枚举分类 (USER_AVATAR / WEBSITE_BRAND 等) */
  purpose: MediaPurpose;
  /** 上传操作审计理由 */
  auditReason?: string;
  /** 上传成功或移除时的 URL 变更回调 */
  onChange: (url: string | null) => void;
  /** 上传状态变更回调，告知父组件上传进度 */
  onUploadingChange?: (uploading: boolean) => void;
  /** 是否禁用控件 */
  disabled?: boolean;
  /** 可访问性说明及 alt 标签文案 */
  label?: string;
  /** 允许选择的文件 MIME 类型 */
  accept?: string;
}

/** 客户端校验：最大单文件大小 5 MiB */
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
/** 客户端校验：允许的图片格式列表 */
const ALLOWED_MIME_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

/**
 * 计算用于 <img> 预览的可访问地址。
 * 若 value 为站内相对路径，结合 VITE_API_BASE_URL 转换为绝对 URL 用于预览；
 * 绝对 URL 或 data: 协议图片保持原样。
 */
const getPreviewUrl = (url: string | null | undefined): string => {
  if (!url) return '';
  if (url.startsWith('data:') || url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  const baseUrl = import.meta.env.VITE_API_BASE_URL;
  if (baseUrl) {
    try {
      return new URL(url, baseUrl).href;
    } catch {
      const cleanBase = baseUrl.replace(/\/+$/, '');
      const cleanPath = url.replace(/^\/+/, '');
      return `${cleanBase}/${cleanPath}`;
    }
  }
  return url;
};

export const MediaUpload: React.FC<MediaUploadProps> = ({
  id = 'media-upload-input',
  value,
  purpose,
  auditReason = '',
  onChange,
  onUploadingChange,
  disabled = false,
  label = '上传图片',
  accept = 'image/png,image/jpeg,image/webp',
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /** 更新内部上传状态并透传至外部父组件 */
  const updateUploadingState = (state: boolean) => {
    setUploading(state);
    onUploadingChange?.(state);
  };

  /** 处理本地文件选择事件 */
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 清空 input 缓存以允许连续重新选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    // 1. 校验图片 MIME 类型
    if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
      setErrorMessage('仅支持上传 PNG、JPEG、WebP 格式的图片文件');
      return;
    }

    // 2. 校验文件 5 MiB 容量限制
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setErrorMessage('图片文件大小超出限制（不能超过 5 MiB）');
      return;
    }

    setErrorMessage(null);
    updateUploadingState(true);

    try {
      // 审计理由校验与默认回退（至少8字）
      const cleanReason = auditReason.trim();
      const effectiveAuditReason =
        cleanReason.length >= 8
          ? cleanReason
          : purpose === MediaPurpose.UserAvatar
          ? '编辑用户资料上传头像图片资产'
          : '修改系统设置上传品牌 Logo 资产';

      const mediaAsset = await repository.uploadAdminMediaAsset(file, purpose, effectiveAuditReason);
      // onChange 回传原始 publicUrl (如 /media/mda_xxx)，绝不保存拼接后的绝对 API 地址
      onChange(mediaAsset.publicUrl);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '图片上传失败，请检查网络或稍后重试';
      setErrorMessage(msg);
    } finally {
      updateUploadingState(false);
    }
  };

  /** 点击触发本地文件选择弹窗 */
  const handleTriggerClick = () => {
    if (disabled || uploading) return;
    fileInputRef.current?.click();
  };

  /** 移除当前已选择的图片 */
  const handleRemoveImage = () => {
    if (disabled || uploading) return;
    setErrorMessage(null);
    onChange(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const previewSrc = getPreviewUrl(value);

  return (
    <div className="media-upload-container">
      {/* 隐藏的原生本地文件 Select Input */}
      <input
        type="file"
        id={id}
        ref={fileInputRef}
        accept={accept}
        onChange={handleFileSelect}
        disabled={disabled || uploading}
        style={{ display: 'none' }}
        aria-label={label}
      />

      {/* 存在已有图片时的预览视图 */}
      {value ? (
        <div className="media-upload-preview-box">
          <img
            src={previewSrc}
            alt={`${label}预览`}
            className="media-upload-img-preview"
          />
          <div className="media-upload-preview-info">
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-primary)' }}>
              {uploading ? '图片上传中...' : '已选择图片'}
            </span>
          </div>
          <div className="media-upload-actions">
            <button
              type="button"
              className="btn btn-default media-upload-icon-btn"
              onClick={handleTriggerClick}
              disabled={disabled || uploading}
              title="重新选择图片"
              aria-label="重新选择图片"
            >
              {uploading ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
            </button>
            <button
              type="button"
              className="btn btn-danger media-upload-icon-btn"
              onClick={handleRemoveImage}
              disabled={disabled || uploading}
              title="移除图片"
              aria-label="移除图片"
            >
              <X size={15} />
            </button>
          </div>
        </div>
      ) : (
        /* 未选择图片时的点击上传选择框 */
        <div
          className={`media-upload-dropzone ${disabled || uploading ? 'disabled' : ''}`}
          onClick={handleTriggerClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleTriggerClick();
            }
          }}
          aria-label={`选择本地文件以${label}`}
        >
          {uploading ? (
            <>
              <Loader2 size={16} className="spin" style={{ color: 'var(--color-primary)' }} />
              <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                图片资源上传处理中...
              </span>
            </>
          ) : (
            <>
              <Upload size={16} style={{ color: 'var(--color-text-secondary)' }} />
              <span style={{ fontSize: '13px', color: 'var(--color-text-primary)' }}>
                点击选择本地图片
              </span>
            </>
          )}
        </div>
      )}

      {/* 清晰的中文错误提示 */}
      {errorMessage && (
        <div className="media-upload-error" role="alert">
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
