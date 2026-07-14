'use client';

import { cn } from '@/lib/utils';
import type { DocumentStatus, IntegrationStatus } from '@/types';

type ChipStatus = DocumentStatus | IntegrationStatus | 'READY' | string;

interface StatusChipProps {
  status: ChipStatus;
  className?: string;
}

const statusConfig: Record<
  string,
  { label: string; color: string; bg: string; pulse?: boolean }
> = {
  INDEXED: { label: 'Indexed', color: 'var(--success)', bg: 'var(--success-subtle)' },
  READY: { label: 'Ready', color: 'var(--success)', bg: 'var(--success-subtle)' },
  CONNECTED: { label: 'Connected', color: 'var(--success)', bg: 'var(--success-subtle)' },
  IMPORTED: { label: 'Imported', color: 'var(--accent)', bg: 'var(--accent-subtle)' },
  PARSING: { label: 'Parsing', color: 'var(--warning)', bg: 'var(--warning-subtle)', pulse: true },
  CHUNKING: { label: 'Chunking', color: 'var(--warning)', bg: 'var(--warning-subtle)', pulse: true },
  EMBEDDING: { label: 'Embedding', color: 'var(--warning)', bg: 'var(--warning-subtle)', pulse: true },
  PROCESSING: { label: 'Processing', color: 'var(--warning)', bg: 'var(--warning-subtle)', pulse: true },
  FAILED: { label: 'Failed', color: 'var(--danger)', bg: 'var(--danger-subtle)' },
  DISCONNECTED: { label: 'Disconnected', color: 'var(--text-tertiary)', bg: 'var(--bg-subtle)' },
  NEEDS_REAUTHORIZATION: { label: 'Needs reauth', color: 'var(--warning)', bg: 'var(--warning-subtle)' },
};

export function StatusChip({ status, className }: StatusChipProps) {
  const config = statusConfig[status] || {
    label: status,
    color: 'var(--text-tertiary)',
    bg: 'var(--bg-subtle)',
  };

  return (
    <span
      role="status"
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-micro whitespace-nowrap',
        config.pulse && 'animate-pulse',
        className
      )}
      style={{
        backgroundColor: config.bg,
        color: config.color,
      }}
    >
      {/* Status dot — always paired with label for accessibility */}
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: config.color }}
        aria-hidden="true"
      />
      {config.label}
    </span>
  );
}
