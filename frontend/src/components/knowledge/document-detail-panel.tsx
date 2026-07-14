'use client';

import { X, Play, RefreshCw, Trash2, HardDrive, FileText, CheckCircle2, Circle, AlertCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn, formatFileSize, formatRelativeTime, getProviderLabel } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { StatusChip } from '@/components/ui/status-chip';
import { toast } from '@/components/ui/toast';
import { Skeleton } from '@/components/ui/skeleton';
import type { DocumentDetail, Conversation } from '@/types';

interface DocumentDetailPanelProps {
  documentId: string | null;
  onClose: () => void;
  onDeleted?: () => void;
}

type PipelineStageName = 'Parsed' | 'Cleaned' | 'Classified' | 'Chunked' | 'Embedded' | 'Indexed';

interface StepperStage {
  name: PipelineStageName;
  status: 'completed' | 'active' | 'pending' | 'failed';
}

export function DocumentDetailPanel({ documentId, onClose, onDeleted }: DocumentDetailPanelProps) {
  const queryClient = useQueryClient();

  // Fetch document details
  const { data: doc, isLoading } = useQuery<DocumentDetail>({
    queryKey: ['document-detail', documentId],
    queryFn: () => api<DocumentDetail>(`/documents/${documentId}`),
    enabled: !!documentId,
  });

  // Re-index mutation
  const reindexMutation = useMutation({
    mutationFn: () => api(`/documents/${documentId}/index`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-detail', documentId] });
      toast('Indexing pipeline started in the background.', 'info');
    },
    onError: (err: any) => {
      toast(err.message || 'Failed to trigger re-indexing', 'error');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => api(`/documents/${documentId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast('Document removed successfully.', 'success');
      onClose();
      if (onDeleted) onDeleted();
    },
    onError: (err: any) => {
      toast(err.message || 'Failed to delete document', 'error');
    },
  });

  // Shortcut to start chat
  const startChatMutation = useMutation({
    mutationFn: async () => {
      if (!doc) return;
      // 1. Create a conversation
      const conv = await api<Conversation>('/conversations', {
        method: 'POST',
        body: { title: `Chat with ${doc.title}` },
      });
      // 2. Attach document
      await api(`/conversations/${conv.id}/documents`, {
        method: 'POST',
        body: doc.id,
      });
      return conv;
    },
    onSuccess: (conv) => {
      if (conv) {
        onClose();
        window.location.href = `/chat/${conv.id}`;
      }
    },
    onError: (err: any) => {
      toast(err.message || 'Failed to start chat with document', 'error');
    },
  });

  if (!documentId) return null;

  // Determine status of pipeline stages based on current document status
  const getPipelineStages = (status: string): StepperStage[] => {
    const stages: StepperStage[] = [
      { name: 'Parsed', status: 'pending' },
      { name: 'Cleaned', status: 'pending' },
      { name: 'Classified', status: 'pending' },
      { name: 'Chunked', status: 'pending' },
      { name: 'Embedded', status: 'pending' },
      { name: 'Indexed', status: 'pending' },
    ];

    if (status === 'FAILED') {
      // Find where it failed based on metadata or mock it to fail at embeddings
      return stages.map((s, i) => ({
        ...s,
        status: i < 4 ? 'completed' : i === 4 ? 'failed' : 'pending',
      }));
    }

    const completedUpTo = {
      IMPORTED: -1,
      PARSING: 0,
      CHUNKING: 3,
      EMBEDDING: 4,
      INDEXED: 6,
    }[status] ?? -1;

    return stages.map((s, idx) => {
      if (idx < completedUpTo) return { ...s, status: 'completed' };
      if (idx === completedUpTo) return { ...s, status: 'active' };
      return s;
    });
  };

  const pipelineStages = doc ? getPipelineStages(doc.status) : [];

  return (
    <div
      className="fixed inset-y-0 right-0 z-40 w-full sm:w-[460px] flex flex-col"
      style={{
        backgroundColor: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        boxShadow: 'var(--surface-raised-shadow)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-6 h-14 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h3 className="text-heading" style={{ color: 'var(--text-primary)' }}>
          Document Details
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-lg cursor-pointer transition-colors hover:bg-[var(--bg-subtle)]"
          style={{ color: 'var(--text-tertiary)' }}
          aria-label="Close detail panel"
        >
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="w-full h-8" />
            <Skeleton className="w-3/4 h-5" />
            <Skeleton className="w-1/2 h-5" />
            <Skeleton className="w-full h-24" />
          </div>
        ) : !doc ? (
          <p className="text-body text-center" style={{ color: 'var(--text-secondary)' }}>
            Failed to load document details.
          </p>
        ) : (
          <>
            {/* Title / Provider */}
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <h4 className="text-display-sm" style={{ color: 'var(--text-primary)' }}>
                  {doc.title}
                </h4>
                <StatusChip status={doc.status} />
              </div>
              <div className="flex items-center gap-2 text-caption" style={{ color: 'var(--text-secondary)' }}>
                {doc.provider === 'google_drive' ? <HardDrive size={14} /> : <FileText size={14} />}
                <span>Source: {getProviderLabel(doc.provider)}</span>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant="primary"
                size="compact"
                icon={<Play size={14} />}
                onClick={() => startChatMutation.mutate()}
                loading={startChatMutation.isPending}
              >
                Chat with Document
              </Button>
              <Button
                variant="secondary"
                size="compact"
                icon={<RefreshCw size={14} />}
                onClick={() => reindexMutation.mutate()}
                loading={reindexMutation.isPending}
              >
                Re-index
              </Button>
              <Button
                variant="danger"
                size="compact"
                icon={<Trash2 size={14} />}
                onClick={() => {
                  if (confirm('Permanently remove this document from Conduit? This cannot be undone.')) {
                    deleteMutation.mutate();
                  }
                }}
                loading={deleteMutation.isPending}
              >
                Delete
              </Button>
            </div>

            {/* Pipeline Stepper */}
            <div className="space-y-3">
              <h5 className="text-body-medium font-semibold" style={{ color: 'var(--text-primary)' }}>
                Processing Pipeline
              </h5>
              <div className="flex items-center justify-between border rounded-xl p-4 gap-2 flex-wrap sm:flex-nowrap" style={{ borderColor: 'var(--border)' }}>
                {pipelineStages.map((stage) => {
                  const stageIcons = {
                    completed: <CheckCircle2 size={16} className="text-emerald-500" />,
                    active: <Circle size={16} className="text-blue-500 animate-pulse" />,
                    pending: <Circle size={16} className="text-gray-300 dark:text-gray-700" />,
                    failed: <AlertCircle size={16} className="text-red-500" />,
                  };
                  return (
                    <div key={stage.name} className="flex flex-col items-center gap-1.5 flex-1 min-w-[60px] text-center">
                      {stageIcons[stage.status]}
                      <span className="text-micro font-mono" style={{ color: stage.status === 'completed' || stage.status === 'active' ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>
                        {stage.name}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Metadata attributes list */}
            <div className="space-y-3">
              <h5 className="text-body-medium font-semibold" style={{ color: 'var(--text-primary)' }}>
                Attributes
              </h5>
              <div className="divide-y rounded-xl border px-4" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface-raised)' }}>
                <MetaRow label="File Size" value={formatFileSize(doc.file_size)} />
                <MetaRow label="Mime Type" value={doc.mime_type} />
                <MetaRow label="Storage Path" value={doc.storage_path || 'Not stored physically'} />
                <MetaRow label="Checksum" value={doc.checksum ? `${doc.checksum.slice(0, 8)}...` : 'None'} />
                <MetaRow label="Chunk Count" value={doc.chunk_count?.toString() || '0'} />
                <MetaRow label="Conversations" value={doc.conversation_count?.toString() || '0'} />
                <MetaRow label="Created" value={doc.created_at ? formatRelativeTime(doc.created_at) : 'Unknown'} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-caption" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </span>
      <span className="text-caption font-mono truncate max-w-[200px]" style={{ color: 'var(--text-primary)' }} title={value}>
        {value}
      </span>
    </div>
  );
}
