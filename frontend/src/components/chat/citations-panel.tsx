'use client';

import { X, HardDrive, FileText, Globe } from 'lucide-react';
import { formatFileSize, getProviderLabel } from '@/lib/utils';
import type { Citation, RetrievedChunk } from '@/types';

interface CitationsPanelProps {
  open: boolean;
  onClose: () => void;
  citations: Citation[];
  chunks: RetrievedChunk[];
  highlightedIndex?: number;
}

export function CitationsPanel({
  open,
  onClose,
  citations,
  chunks,
  highlightedIndex,
}: CitationsPanelProps) {
  if (!open) return null;

  // Render provider icon helper
  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'google_drive':
        return <HardDrive size={16} className="text-blue-500" />;
      case 'local':
        return <FileText size={16} className="text-gray-400" />;
      default:
        return <Globe size={16} className="text-gray-400" />;
    }
  };

  return (
    <div
      className="fixed inset-y-0 right-0 z-40 w-full sm:w-[400px] flex flex-col"
      style={{
        backgroundColor: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        boxShadow: 'var(--surface-raised-shadow)',
      }}
    >
      {/* Panel Header */}
      <div
        className="flex items-center justify-between px-6 h-14 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h3 className="text-heading" style={{ color: 'var(--text-primary)' }}>
          Retrieved Sources
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-lg cursor-pointer transition-colors hover:bg-[var(--bg-subtle)]"
          style={{ color: 'var(--text-tertiary)' }}
          aria-label="Close citations panel"
        >
          <X size={16} />
        </button>
      </div>

      {/* Sources list */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {chunks.length === 0 ? (
          <p className="text-caption text-center pt-8" style={{ color: 'var(--text-tertiary)' }}>
            No sources retrieved for this message.
          </p>
        ) : (
          chunks.map((chunk, index) => {
            const citation = citations[index];
            const isHighlighted = highlightedIndex === index;
            const scorePercent = Math.round(chunk.score * 100);

            return (
              <div
                key={index}
                className="flex flex-col gap-2.5 p-4 rounded-xl transition-all"
                style={{
                  border: isHighlighted
                    ? '1.5px solid var(--accent)'
                    : '1px solid var(--border)',
                  backgroundColor: isHighlighted
                    ? 'var(--accent-subtle)'
                    : 'var(--surface-raised)',
                }}
              >
                {/* Meta details */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    {getProviderIcon(citation?.provider || 'local')}
                    <span
                      className="text-body-medium truncate font-semibold"
                      style={{ color: 'var(--text-primary)' }}
                      title={chunk.document_title}
                    >
                      {chunk.document_title}
                    </span>
                  </div>
                  
                  {/* Similarity score */}
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <div
                      className="w-16 h-1.5 rounded-full overflow-hidden bg-[var(--border)]"
                      aria-hidden="true"
                    >
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${scorePercent}%`,
                          backgroundColor: chunk.score > 0.8 ? 'var(--success)' : 'var(--accent)',
                        }}
                      />
                    </div>
                    <span className="text-micro font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {scorePercent}%
                    </span>
                  </div>
                </div>

                {/* Retrieved snippet content */}
                <div
                  className="text-caption font-mono leading-relaxed p-3 rounded-lg overflow-x-auto select-text"
                  style={{
                    backgroundColor: 'var(--bg)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-secondary)',
                    maxHeight: '200px',
                  }}
                >
                  <p className="whitespace-pre-wrap">{chunk.content}</p>
                </div>

                {/* Subtitle details */}
                <div className="flex items-center justify-between text-micro" style={{ color: 'var(--text-tertiary)' }}>
                  <span>Source: {getProviderLabel(citation?.provider || 'local')}</span>
                  {citation?.chunk_index !== undefined && (
                    <span>Chunk #{citation.chunk_index}</span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
