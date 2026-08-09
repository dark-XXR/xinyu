/**
 * 徽章组件。
 * 用于展示状态标签的轻量级视觉元素。
 */
import React from 'react';

interface BadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'default';
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({ variant = 'default', children }) => {
  return <span className={`badge badge-${variant}`}>{children}</span>;
};
