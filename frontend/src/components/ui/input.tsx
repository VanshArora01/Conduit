'use client';

import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, className, id, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={id}
            className="text-caption"
            style={{ color: 'var(--text-secondary)' }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={cn(
            'h-10 px-3 rounded-lg text-body outline-none transition-all',
            className
          )}
          style={{
            backgroundColor: 'var(--surface)',
            border: `1px solid ${error ? 'var(--danger)' : 'var(--border)'}`,
            color: 'var(--text-primary)',
          }}
          onFocus={(e) => {
            if (!error) {
              e.currentTarget.style.border = '1px solid var(--accent)';
              e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent-subtle)';
            }
          }}
          onBlur={(e) => {
            if (!error) {
              e.currentTarget.style.border = '1px solid var(--border)';
              e.currentTarget.style.boxShadow = 'none';
            }
          }}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          {...props}
        />
        {error && (
          <span
            id={`${id}-error`}
            className="text-caption"
            style={{ color: 'var(--danger)' }}
            role="alert"
          >
            {error}
          </span>
        )}
        {hint && !error && (
          <span
            id={`${id}-hint`}
            className="text-caption"
            style={{ color: 'var(--text-tertiary)' }}
          >
            {hint}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
