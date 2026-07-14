'use client';

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'compact' | 'default' | 'large';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
}

const sizeMap: Record<ButtonSize, string> = {
  compact: 'h-8 px-3 text-[13px]',
  default: 'h-9 px-4 text-[14px]',
  large: 'h-10 px-5 text-[14px]',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'default',
      loading = false,
      icon,
      children,
      className,
      disabled,
      style,
      ...props
    },
    ref
  ) => {
    const isIconOnly = icon && !children;

    const variantStyles: Record<ButtonVariant, React.CSSProperties> = {
      primary: {
        backgroundColor: 'var(--accent)',
        color: '#FFFFFF',
        border: 'none',
      },
      secondary: {
        backgroundColor: 'transparent',
        color: 'var(--text-primary)',
        border: '1px solid var(--border)',
      },
      ghost: {
        backgroundColor: 'transparent',
        color: 'var(--text-primary)',
        border: 'none',
      },
      danger: {
        backgroundColor: 'var(--danger)',
        color: '#FFFFFF',
        border: 'none',
      },
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-lg font-medium',
          'transition-all duration-150 ease-out cursor-pointer',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'hover:opacity-90',
          sizeMap[size],
          isIconOnly && 'px-0 aspect-square',
          className
        )}
        style={{
          ...variantStyles[variant],
          ...style,
        }}
        {...props}
      >
        {loading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : icon ? (
          icon
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
