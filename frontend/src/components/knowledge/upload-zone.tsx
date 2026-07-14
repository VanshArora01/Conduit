'use client';

import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiUpload } from '@/lib/api';
import { cn } from '@/lib/utils';
import { UploadCloud, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from '@/components/ui/toast';

interface UploadZoneProps {
  onUploadSuccess?: () => void;
}

interface UploadStatus {
  fileName: string;
  progress: 'uploading' | 'processing' | 'success' | 'error';
  errorDetail?: string;
}

export function UploadZone({ onUploadSuccess }: UploadZoneProps) {
  const queryClient = useQueryClient();
  const [isDragOver, setIsDragOver] = useState(false);
  const [activeUploads, setActiveUploads] = useState<Record<string, UploadStatus>>({});

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiUpload<{ status: string; document_id: string; message: string }>(
        '/documents/upload',
        formData
      );
    },
    onMutate: (file) => {
      setActiveUploads((prev) => ({
        ...prev,
        [file.name]: { fileName: file.name, progress: 'uploading' },
      }));
    },
    onSuccess: (data, file) => {
      setActiveUploads((prev) => ({
        ...prev,
        [file.name]: { fileName: file.name, progress: 'processing' },
      }));

      // Invalidate query to refresh document lists
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast(`Uploaded ${file.name} successfully. Indexing started.`, 'success');

      // Poll status for indexing completion
      let attempts = 0;
      const interval = setInterval(async () => {
        try {
          const statusRes = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/documents/${data.document_id}/status`,
            {
              headers: {
                Authorization: `Bearer ${localStorage.getItem('conduit_access_token')}`,
              },
            }
          );
          if (!statusRes.ok) throw new Error();
          const statusData = await statusRes.json();

          if (statusData.status === 'INDEXED') {
            clearInterval(interval);
            setActiveUploads((prev) => ({
              ...prev,
              [file.name]: { fileName: file.name, progress: 'success' },
            }));
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            if (onUploadSuccess) onUploadSuccess();
          } else if (statusData.status === 'FAILED') {
            clearInterval(interval);
            setActiveUploads((prev) => ({
              ...prev,
              [file.name]: {
                fileName: file.name,
                progress: 'error',
                errorDetail: 'Document extraction or indexing failed.',
              },
            }));
            queryClient.invalidateQueries({ queryKey: ['documents'] });
          }
        } catch {
          clearInterval(interval);
        }

        attempts++;
        if (attempts > 30) {
          // stop polling after 30 seconds
          clearInterval(interval);
        }
      }, 2000);
    },
    onError: (err: any, file) => {
      setActiveUploads((prev) => ({
        ...prev,
        [file.name]: {
          fileName: file.name,
          progress: 'error',
          errorDetail: err.message || 'File upload failed.',
        },
      }));
      toast(`Failed to upload ${file.name}`, 'error');
    },
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    files.forEach((file) => uploadMutation.mutate(file));
  }, [uploadMutation]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      files.forEach((file) => uploadMutation.mutate(file));
    }
  }, [uploadMutation]);

  return (
    <div className="flex flex-col gap-4 w-full select-none">
      {/* Upload Drag & Drop Area */}
      <label
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 cursor-pointer transition-all',
          isDragOver
            ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
            : 'border-[var(--border-strong)] bg-[var(--surface)] hover:bg-[var(--bg-subtle)]'
        )}
      >
        <input
          type="file"
          multiple
          className="hidden"
          onChange={handleFileChange}
          accept=".pdf,.docx,.txt,.md,.csv,.xlsx"
        />

        <UploadCloud
          size={32}
          className="mb-2"
          style={{ color: isDragOver ? 'var(--accent)' : 'var(--text-tertiary)' }}
        />
        <p className="text-body-medium" style={{ color: 'var(--text-primary)' }}>
          Drag & drop files here, or click to browse
        </p>
        <p className="text-caption mt-1" style={{ color: 'var(--text-tertiary)' }}>
          Supports PDF, DOCX, TXT, MD, CSV, XLSX up to 50MB
        </p>
      </label>

      {/* Active uploads list */}
      {Object.keys(activeUploads).length > 0 && (
        <div
          className="p-4 rounded-xl space-y-3"
          style={{
            backgroundColor: 'var(--surface-raised)',
            border: '1px solid var(--border)',
          }}
        >
          <h4 className="text-heading" style={{ color: 'var(--text-primary)' }}>
            Processing Queue
          </h4>
          <div className="divide-y divide-[var(--border)] max-h-40 overflow-y-auto">
            {Object.values(activeUploads).map((upload) => (
              <div key={upload.fileName} className="flex items-center justify-between py-2 gap-3">
                <span className="text-body truncate" style={{ color: 'var(--text-primary)' }}>
                  {upload.fileName}
                </span>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {upload.progress === 'uploading' && (
                    <>
                      <Loader2 size={14} className="animate-spin text-blue-500" />
                      <span className="text-micro" style={{ color: 'var(--text-tertiary)' }}>
                        Uploading
                      </span>
                    </>
                  )}
                  {upload.progress === 'processing' && (
                    <>
                      <Loader2 size={14} className="animate-spin text-amber-500" />
                      <span className="text-micro" style={{ color: 'var(--text-tertiary)' }}>
                        Parsing & Indexing
                      </span>
                    </>
                  )}
                  {upload.progress === 'success' && (
                    <>
                      <CheckCircle size={14} style={{ color: 'var(--success)' }} />
                      <span className="text-micro" style={{ color: 'var(--success)' }}>
                        Indexed
                      </span>
                    </>
                  )}
                  {upload.progress === 'error' && (
                    <>
                      <AlertCircle size={14} style={{ color: 'var(--danger)' }} />
                      <span className="text-micro" style={{ color: 'var(--danger)' }} title={upload.errorDetail}>
                        Failed
                      </span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
