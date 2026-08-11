/**
 * 下拉选择框组件。
 * 带可选标签的受控 select 封装，支持从枚举和数组数据派生选项。
 */
import React from 'react';

export interface SelectOption {
  label: string;
  value: string | number;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options?: SelectOption[];
}

export const Select: React.FC<SelectProps> = ({ label, options, children, className = '', ...props }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
      {label && <label style={{ fontSize: '13px', fontWeight: 500 }}>{label}</label>}
      <select className={`input ${className}`} {...props}>
        {options
          ? options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))
          : children}
      </select>
    </div>
  );
};
