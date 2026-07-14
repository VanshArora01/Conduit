'use client';

import { useState, useRef, useEffect, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface DropdownMenuProps {
  trigger: ReactNode;
  children: ReactNode;
  align?: 'left' | 'right';
  side?: 'top' | 'bottom';
  className?: string;
}

interface DropdownItemProps {
  onClick?: () => void;
  children: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  className?: string;
}

export function DropdownMenu({ trigger, children, align = 'right', side = 'bottom', className }: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Keyboard navigation
  useEffect(() => {
    if (!open || !itemsRef.current) return;

    const items = itemsRef.current.querySelectorAll<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])');
    let focusIndex = -1;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        focusIndex = Math.min(focusIndex + 1, items.length - 1);
        items[focusIndex]?.focus();
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        focusIndex = Math.max(focusIndex - 1, 0);
        items[focusIndex]?.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  return (
    <div ref={menuRef} className={cn('relative inline-flex', className)}>
      <div onClick={() => setOpen(!open)}>{trigger}</div>
      {open && (
        <div
          ref={itemsRef}
          role="menu"
          className={cn(
            "absolute z-50 min-w-[160px] p-1 rounded-xl",
            side === 'top' ? "bottom-full mb-1" : "top-full mt-1"
          )}
          style={{
            backgroundColor: 'var(--surface-raised)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--surface-raised-shadow)',
            ...(align === 'right' ? { right: 0 } : { left: 0 }),
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export function DropdownItem({ onClick, children, danger, disabled, className }: DropdownItemProps) {
  return (
    <button
      role="menuitem"
      disabled={disabled}
      aria-disabled={disabled}
      onClick={() => {
        if (!disabled && onClick) onClick();
      }}
      className={cn(
        'w-full text-left px-3 py-1.5 rounded-lg text-body transition-colors cursor-pointer',
        'hover:bg-[var(--bg-subtle)]',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        className
      )}
      style={{
        color: danger ? 'var(--danger)' : 'var(--text-primary)',
      }}
    >
      {children}
    </button>
  );
}
