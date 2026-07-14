'use client';

import { cn } from '@/lib/utils';

interface FlowLineProps {
  variant?: 'horizontal' | 'vertical' | 'curved';
  length?: number;
  animated?: boolean;
  className?: string;
}

/**
 * FlowLine — Conduit's signature visual element.
 * A thin, animated SVG path in accent color that represents
 * the controlled channel through which knowledge flows.
 *
 * Usage policy — ONLY in:
 * 1. Landing page hero visual
 * 2. Google Drive scan sequence (onboarding)
 * 3. New Chat creation transition
 * 4. Empty dashboard state
 *
 * Never inside chat messages. Never as generic decoration.
 */
export function FlowLine({
  variant = 'horizontal',
  length = 200,
  animated = true,
  className,
}: FlowLineProps) {
  const pathData = getPathData(variant, length);
  const viewBox = getViewBox(variant, length);

  return (
    <svg
      viewBox={viewBox}
      fill="none"
      className={cn('flow-line-svg', className)}
      aria-hidden="true"
      style={{
        width: variant === 'vertical' ? 24 : length,
        height: variant === 'vertical' ? length : 24,
      }}
    >
      <path
        d={pathData}
        className={animated ? 'flow-line-path' : undefined}
        style={
          animated
            ? undefined
            : {
                stroke: 'var(--accent)',
                strokeWidth: 1.5,
                fill: 'none',
                strokeLinecap: 'round',
                opacity: 0.6,
              }
        }
      />
    </svg>
  );
}

function getPathData(variant: string, length: number): string {
  switch (variant) {
    case 'vertical':
      return `M 12 0 L 12 ${length}`;
    case 'curved':
      return `M 0 12 Q ${length * 0.25} 2, ${length * 0.5} 12 T ${length} 12`;
    case 'horizontal':
    default:
      return `M 0 12 L ${length} 12`;
  }
}

function getViewBox(variant: string, length: number): string {
  switch (variant) {
    case 'vertical':
      return `0 0 24 ${length}`;
    case 'curved':
    case 'horizontal':
    default:
      return `0 0 ${length} 24`;
  }
}
