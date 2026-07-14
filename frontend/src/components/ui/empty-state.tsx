'use client';

import { type ReactNode } from 'react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

/**
 * EmptyState — used across every empty view in the app.
 * Always explains WHY it's empty and WHAT to do next.
 * Never just an icon and a noun.
 */
export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center py-16 px-4 ${className || ''}`}
    >
      {icon && (
        <div
          className="mb-4 w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: 'var(--bg-subtle)', color: 'var(--text-tertiary)' }}
        >
          {icon}
        </div>
      )}
      <h3
        className="text-heading mb-2"
        style={{ color: 'var(--text-primary)' }}
      >
        {title}
      </h3>
      <p
        className="text-body max-w-sm mb-6"
        style={{ color: 'var(--text-secondary)' }}
      >
        {description}
      </p>
      {actionLabel && onAction && (
        <Button variant="primary" size="default" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
