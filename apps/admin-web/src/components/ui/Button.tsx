/**
 * 基础按钮组件。
 * 支持 primary/danger/ghost/default 四种变体和图标前缀。
 */
import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'danger' | 'default' | 'ghost';
  icon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'default', icon, children, className = '', ...props }, ref) => {
    return (
      <button ref={ref} className={`btn btn-${variant} ${className}`} {...props}>
        {icon && <span style={{ display: 'flex', alignItems: 'center' }}>{icon}</span>}
        {children}
      </button>
    );
  },
);
Button.displayName = 'Button';
