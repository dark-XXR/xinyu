/**
 * 卡片容器组件。
 * 提供标题和右侧扩展区域的通用数据展示容器。
 */
import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  title?: string;
  extra?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, title, extra, className = '', ...props }) => {
  return (
    <div className={`card ${className}`} {...props}>
      {(title || extra) && (
        <div className="card-header">
          {title && <div className="card-title">{title}</div>}
          {extra && <div>{extra}</div>}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
};
