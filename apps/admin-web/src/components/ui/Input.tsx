/**
 * 输入框组件。
 * 带可选标签的受控 input 封装。
 */
import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Input: React.FC<InputProps> = ({ label, className = '', ...props }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
      {label && <label style={{ fontSize: '13px', fontWeight: 500 }}>{label}</label>}
      <input className={`input ${className}`} {...props} />
    </div>
  );
};
