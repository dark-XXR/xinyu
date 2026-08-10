/**
 * 多行文本输入框组件。
 * 支持带可选标签的受控 textarea 封装，适用于 Prompt 模版与 JSON Schema 编辑。
 */
import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea: React.FC<TextareaProps> = ({ label, error, className = '', ...props }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
      {label && <label style={{ fontSize: '13px', fontWeight: 500 }}>{label}</label>}
      <textarea className={`input ${className}`} style={{ minHeight: '80px', fontFamily: 'inherit', resize: 'vertical' }} {...props} />
      {error && <span style={{ color: '#ef4444', fontSize: '12px', marginTop: '2px' }}>{error}</span>}
    </div>
  );
};
