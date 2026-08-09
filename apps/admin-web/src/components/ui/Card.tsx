/**
 * 卡片容器组件。
 * 提供标题和右侧扩展区域的通用数据展示容器。
 */
import React from 'react';

export const Card: React.FC<{ children: React.ReactNode; title?: string; extra?: React.ReactNode }> = (
  { children, title, extra },
) => {
  return (
    <div className="card">
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
