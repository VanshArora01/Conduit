'use client';

import { cn } from '@/lib/utils';
import { formatRelativeTime, getMimeTypeLabel, getProviderLabel } from '@/lib/utils';
import { StatusChip } from '@/components/ui/status-chip';
import {
  FileText,
  FileType,
  FileCode,
  Table,
  File,
  Check,
  Eye,
} from 'lucide-react';
import type { DocumentListItem, Document } from '@/types';
import { useState, type ReactNode } from 'react';

interface DocumentCardProps {
  document: DocumentListItem | Document;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (id: string) => void;
  onClick?: (id: string) => void;
  showStatus?: boolean;
  className?: string;
}

const iconMap: Record<string, ReactNode> = {
  FileText: <FileText size={18} />,
  FileType: <FileType size={18} />,
  FileCode: <FileCode size={18} />,
  Table: <Table size={18} />,
  File: <File size={18} />,
};

function getIcon(mimeType: string): ReactNode {
  const map: Record<string, string> = {
    'application/pdf': 'FileText',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'FileText',
    'application/msword': 'FileText',
    'text/plain': 'FileType',
    'text/markdown': 'FileCode',
    'text/csv': 'Table',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Table',
    'application/vnd.ms-excel': 'Table',
    'application/vnd.google-apps.document': 'FileText',
    'application/vnd.google-apps.spreadsheet': 'Table',
  };
  const iconName = map[mimeType] || 'File';
  return iconMap[iconName] || <File size={18} />;
}

/**
 * DocumentCard — shared component used identically in:
 * - New Chat document picker (selectable=true)
 * - Knowledge grid view (selectable=false, onClick opens detail)
 *
 * Never fork into two implementations.
 */
export function DocumentCard({
  document: doc,
  selectable = false,
  selected = false,
  onSelect,
  onClick,
  showStatus = false,
  className,
}: DocumentCardProps) {
  const [showPreview, setShowPreview] = useState(false);

  const handleClick = () => {
    if (selectable && onSelect) {
      onSelect(doc.id);
    } else if (onClick) {
      onClick(doc.id);
    }
  };

  const hasContent = 'processed_content' in doc && doc.processed_content;
  const updatedAt = 'updated_at' in doc ? doc.updated_at : undefined;

  return (
    <div
      role={selectable ? 'option' : 'button'}
      aria-selected={selectable ? selected : undefined}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      className={cn(
        'relative flex flex-col gap-2 p-3 rounded-xl cursor-pointer',
        'transition-all duration-150 ease-out',
        'focus-visible:outline-2 focus-visible:outline-offset-2',
        className
      )}
      style={{
        backgroundColor: selected ? 'var(--accent-subtle)' : 'var(--surface)',
        border: selected
          ? '1.5px solid var(--accent)'
          : '1px solid var(--border)',
        outlineColor: 'var(--accent)',
      }}
      onMouseEnter={(e) => {
        if (!selected) {
          e.currentTarget.style.borderColor = 'var(--border-strong)';
          e.currentTarget.style.backgroundColor = 'var(--bg-subtle)';
        }
      }}
      onMouseLeave={(e) => {
        if (!selected) {
          e.currentTarget.style.borderColor = 'var(--border)';
          e.currentTarget.style.backgroundColor = 'var(--surface)';
        }
      }}
    >
      {/* Top row: file icon + provider badge */}
      <div className="flex items-start justify-between">
        <span style={{ color: 'var(--text-secondary)' }}>{getIcon(doc.mime_type)}</span>
        <div className="flex items-center gap-1.5">
          {/* Preview eye icon on hover */}
          {hasContent && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowPreview(!showPreview);
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded"
              style={{ color: 'var(--text-tertiary)' }}
              aria-label="Preview document"
            >
              <Eye size={14} />
            </button>
          )}
          <span className="text-micro" style={{ color: 'var(--text-tertiary)' }}>
            {getProviderLabel(doc.provider)}
          </span>
        </div>
      </div>

      {/* Filename */}
      <p
        className="text-body-medium truncate"
        style={{ color: 'var(--text-primary)' }}
        title={doc.title}
      >
        {doc.title}
      </p>

      {/* Metadata row */}
      <div className="flex items-center gap-2">
        <span className="text-caption" style={{ color: 'var(--text-tertiary)' }}>
          {getMimeTypeLabel(doc.mime_type)}
        </span>
        {updatedAt && (
          <>
            <span style={{ color: 'var(--text-tertiary)' }}>·</span>
            <span className="text-caption" style={{ color: 'var(--text-tertiary)' }}>
              {formatRelativeTime(updatedAt)}
            </span>
          </>
        )}
      </div>

      {/* Status chip (Knowledge grid only) */}
      {showStatus && (
        <div className="mt-auto pt-1">
          <StatusChip status={doc.status} />
        </div>
      )}

      {/* Selection check badge */}
      {selectable && selected && (
        <div
          className="absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center"
          style={{ backgroundColor: 'var(--accent)' }}
        >
          <Check size={12} color="#FFFFFF" strokeWidth={2.5} />
        </div>
      )}

      {/* Content preview popover */}
      {showPreview && hasContent && (
        <div
          className="absolute left-0 right-0 top-full mt-1 z-20 p-3 rounded-lg text-caption max-h-32 overflow-y-auto"
          style={{
            backgroundColor: 'var(--surface-raised)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--surface-raised-shadow)',
            color: 'var(--text-secondary)',
          }}
        >
          {('processed_content' in doc && doc.processed_content || '').slice(0, 300)}
          {('processed_content' in doc && doc.processed_content || '').length > 300 && '…'}
        </div>
      )}
    </div>
  );
}
