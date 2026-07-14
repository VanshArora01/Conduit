'use client';

import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Skeleton — static pulse (--bg-subtle opacity), no moving shimmer.
 * Calmer and more aligned with Conduit's brand.
 */
export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn('skeleton rounded-lg', className)}
      style={style}
      aria-hidden="true"
    />
  );
}

/** Pre-composed skeleton for document cards */
export function DocumentCardSkeleton() {
  return (
    <div
      className="flex flex-col gap-2 p-3 rounded-xl"
      style={{ border: '1px solid var(--border)' }}
    >
      <div className="flex justify-between">
        <Skeleton className="w-5 h-5" />
        <Skeleton className="w-16 h-3" />
      </div>
      <Skeleton className="w-3/4 h-4 mt-1" />
      <Skeleton className="w-1/2 h-3" />
    </div>
  );
}

/** Pre-composed skeleton for list rows */
export function ListRowSkeleton() {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <Skeleton className="w-5 h-5 rounded" />
      <Skeleton className="w-40 h-4" />
      <Skeleton className="w-20 h-3 ml-auto" />
      <Skeleton className="w-16 h-3" />
    </div>
  );
}

/** Pre-composed skeleton for sidebar chat rows */
export function ChatRowSkeleton() {
  return (
    <div className="flex flex-col gap-1.5 px-3 py-2">
      <Skeleton className="w-32 h-3.5" />
      <Skeleton className="w-16 h-2.5" />
    </div>
  );
}
