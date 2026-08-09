/**
 * 侧边抽屉组件。
 * 实现初始聚焦、Tab 焦点约束、Escape 关闭和关闭后恢复触发点焦点。
 */
import React, { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  /** 关闭后恢复焦点的元素 */
  returnFocusRef?: React.RefObject<HTMLElement | null>;
}

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export const Drawer: React.FC<DrawerProps> = ({ open, title, onClose, children, footer, returnFocusRef }) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement as HTMLElement | null;
      requestAnimationFrame(() => {
        const first = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE);
        first?.focus();
      });
    }
  }, [open]);

  useEffect(() => {
    if (!open) {
      const target = returnFocusRef?.current ?? previousFocusRef.current;
      target?.focus();
    }
  }, [open, returnFocusRef]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key === 'Tab' && panelRef.current) {
        const focusable = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
    [onClose],
  );

  if (!open) return null;

  return (
    <div
      className="overlay"
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      onKeyDown={handleKeyDown}
    >
      <div className="drawer" ref={panelRef} role="dialog" aria-modal="true" aria-label={title}>
        <div className="dialog-header">
          <span>{title}</span>
          <button
            className="dialog-close-btn"
            onClick={onClose}
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>
        <div className="dialog-body" style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
        {footer && <div className="dialog-footer">{footer}</div>}
      </div>
    </div>
  );
};
