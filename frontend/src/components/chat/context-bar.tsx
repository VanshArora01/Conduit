'use client';

import { HardDrive, FileText, X, Plus } from 'lucide-react';
import { getFileTypeIcon, truncate } from '@/lib/utils';
import type { ConversationDocument } from '@/types';

interface ContextBarProps {
  documents: ConversationDocument[];
  onDetach: (docId: string) => void;
  onAddFiles: () => void;
}

export function ContextBar({ documents, onDetach, onAddFiles }: ContextBarProps) {
  // Render document icon based on attached metadata
  const getDocIcon = (mimeType?: string) => {
    switch (mimeType) {
      case 'application/pdf':
        return <FileText size={14} />;
      default:
        return <FileText size={14} />;
    }
  };

  return (
    <div
      className="flex items-center gap-2 px-6 py-3 overflow-x-auto flex-nowrap select-none bg-[var(--bg-subtle)]"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      <span className="text-micro font-bold uppercase tracking-wider whitespace-nowrap mr-2" style={{ color: 'var(--text-tertiary)' }}>
        Knowing:
      </span>

      {documents.map((doc) => (
        <div
          key={doc.document_id}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-caption border transition-all"
          style={{
            backgroundColor: 'var(--surface)',
            borderColor: 'var(--border)',
            color: 'var(--text-secondary)',
          }}
        >
          <span style={{ color: 'var(--text-tertiary)' }}>
            {doc.provider === 'google_drive' ? <HardDrive size={14} /> : getDocIcon(doc.mime_type)}
          </span>
          <span className="truncate max-w-[120px]" title={doc.title}>
            {doc.title}
          </span>
          <button
            onClick={() => onDetach(doc.document_id)}
            className="p-0.5 rounded-full cursor-pointer hover:bg-[var(--border)]"
            style={{ color: 'var(--text-tertiary)' }}
            aria-label={`Detach ${doc.title}`}
          >
            <X size={10} />
          </button>
        </div>
      ))}

      <button
        onClick={onAddFiles}
        className="flex items-center gap-1 px-3 py-1 rounded-full text-caption border border-dashed cursor-pointer transition-colors"
        style={{
          borderColor: 'var(--border-strong)',
          color: 'var(--accent)',
          backgroundColor: 'transparent',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--accent-subtle)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
      >
        <Plus size={12} />
        Add Files
      </button>
    </div>
  );
}
