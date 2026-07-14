'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api, apiUpload } from '@/lib/api';
import { toast } from '@/components/ui/toast';
import { Modal } from '@/components/ui/modal';
import { Button } from '@/components/ui/button';
import type { DocumentListItem, Conversation } from '@/types';
import { Search, FileText, ArrowRight, Database, Check, Clock, Upload, Loader2, X } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

interface DocumentPickerModalProps {
  open: boolean;
  onClose: () => void;
  conversationId?: string;
  existingDocIds?: string[];
}

export function DocumentPickerModal({
  open,
  onClose,
  conversationId,
  existingDocIds = [],
}: DocumentPickerModalProps) {
  const router = useRouter();

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(existingDocIds));
  const [searchQuery, setSearchQuery] = useState('');
  const [chatTitle, setChatTitle] = useState('');
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const [isLocalSubmitting, setIsLocalSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', 'picker'],
    queryFn: () => api<DocumentListItem[]>('/documents?limit=100'),
    enabled: open,
  });

  const uploadDocument = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      
      return apiUpload('/documents/upload', formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', 'picker'] });
      toast('File uploaded successfully', 'success');
    },
    onError: (error: any) => {
      toast(error.message || 'Failed to upload file', 'error');
    }
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadDocument.mutate(e.target.files[0]);
    }
  };

  const createConversation = useMutation({
    mutationFn: async () => {
      const title = chatTitle || generateTitle(documents, selectedIds);
      const conv = await api<Conversation>('/conversations', {
        method: 'POST',
        body: { title },
      });

      const newDocIds = [...selectedIds].filter((id) => !existingDocIds.includes(id));
      await Promise.all(
        newDocIds.map((docId) =>
          api(`/conversations/${conv.id}/documents?document_id=${docId}`, {
            method: 'POST',
          })
        )
      );

      return conv;
    },
    onSuccess: (conv) => {
      setIsLocalSubmitting(false);
      onClose();
      toast('Workspace initialized', 'success');
      router.push(`/chat/${conv.id}`);
    },
    onError: (error: any) => {
      setIsLocalSubmitting(false);
      toast(error.message || 'Failed to initialize workspace', 'error');
    },
  });

  const extendConversation = useMutation({
    mutationFn: async () => {
      const newDocIds = [...selectedIds].filter((id) => !existingDocIds.includes(id));
      await Promise.all(
        newDocIds.map((docId) =>
          api(`/conversations/${conversationId}/documents?document_id=${docId}`, {
            method: 'POST',
          })
        )
      );
    },
    onSuccess: () => {
      setIsLocalSubmitting(false);
      onClose();
      toast('Knowledge sources added', 'success');
    },
    onError: (error: any) => {
      setIsLocalSubmitting(false);
      toast(error.message || 'Failed to extend conversation', 'error');
    },
  });

  const filteredDocs = useMemo(() => {
    let result = documents;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter((d) => d.title.toLowerCase().includes(q));
    }
    return result;
  }, [documents, searchQuery]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const totalSelected = selectedIds.size;
  const newSelectionCount = [...selectedIds].filter((id) => !existingDocIds.includes(id)).length;

  const autoTitle = useMemo(() => {
    if (totalSelected === 0) return '';
    return generateTitle(documents, selectedIds);
  }, [totalSelected, documents, selectedIds]);

  const handleContinue = () => {
    setIsLocalSubmitting(true);
    if (conversationId) {
      extendConversation.mutate();
    } else {
      createConversation.mutate();
    }
  };

  const isExtendMode = !!conversationId;
  const isSubmitting = createConversation.isPending || extendConversation.isPending || isLocalSubmitting;

  const previewDoc = useMemo(() => documents.find(d => d.id === previewDocId), [documents, previewDocId]);

  return (
    <Modal
      open={open}
      onClose={isSubmitting ? () => {} : onClose}
      width={previewDocId ? "1000px" : "800px"}
      footer={
        <div className="flex justify-between items-center w-full">
          <div className="text-xs text-[var(--muted-fg)] flex items-center gap-2">
            <Database size={14} />
            {totalSelected} bound to context
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose} disabled={isSubmitting} className="rounded-md px-4">
              Cancel
            </Button>
            <button
              disabled={isExtendMode ? newSelectionCount === 0 : (totalSelected === 0 || isSubmitting)}
              onClick={handleContinue}
              className="h-9 px-4 rounded-md inline-flex items-center justify-center gap-2 transition-all text-sm font-medium bg-[var(--foreground)] text-[var(--background)] disabled:opacity-50 hover:opacity-90 shadow-sm"
            >
              {isSubmitting ? (
                <><Loader2 size={14} className="animate-spin" /> Building Context...</>
              ) : isExtendMode ? (
                `Add ${newSelectionCount}`
              ) : (
                <>Initialize Knowledge <ArrowRight size={14} /></>
              )}
            </button>
          </div>
        </div>
      }
    >
      <div className="flex h-[60vh] max-h-[600px] overflow-hidden bg-[var(--surface)] text-[var(--foreground)] rounded-xl relative">
        
        {/* Main Content Area */}
        <div className="flex-1 flex flex-col relative z-10 min-w-0">
          {/* Header */}
          <div className="p-4 border-b border-[var(--border)] flex flex-col gap-4">
            {!isExtendMode && (
              <input
                type="text"
                placeholder={autoTitle || 'Conversation Name...'}
                value={chatTitle}
                onChange={(e) => setChatTitle(e.target.value)}
                className="w-full text-lg font-medium bg-transparent outline-none placeholder:text-[var(--muted-fg)]"
              />
            )}

            <div className="flex items-center gap-3">
              <div className="relative flex-1 flex items-center bg-[var(--background)] border border-[var(--border)] rounded-md px-3 py-1.5 focus-within:border-[var(--border-strong)] transition-colors">
                <Search size={14} className="text-[var(--muted-fg)] mr-2" />
                <input
                  type="text"
                  placeholder="Search repository..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 bg-transparent border-none outline-none text-sm"
                />
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
                accept=".txt,.md,.pdf,.docx"
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadDocument.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--surface-hover)] rounded-md transition-colors text-[var(--muted-fg)] hover:text-[var(--foreground)] disabled:opacity-50"
              >
                {uploadDocument.isPending ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} 
                {uploadDocument.isPending ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>

          {/* Document List */}
          <div className="flex-1 overflow-y-auto p-2 select-none">
            {isLoading ? (
              <div className="flex flex-col gap-1">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-12 rounded-md bg-[var(--background)] border border-[var(--border)] animate-pulse" />
                ))}
              </div>
            ) : filteredDocs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <FileText size={24} className="text-[var(--muted-fg)] mb-3 opacity-50" />
                <p className="text-sm font-medium mb-1 text-[var(--foreground)]">No matches found</p>
                <p className="text-xs text-[var(--muted-fg)]">Try adjusting your search query.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-1">
                {filteredDocs.map((doc) => {
                  const isSelected = selectedIds.has(doc.id);
                  const isExisting = existingDocIds.includes(doc.id);
                  
                  return (
                    <div
                      key={doc.id}
                      className={`group w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-sm transition-all cursor-pointer ${
                        isSelected 
                          ? 'border-[var(--accent)] bg-[var(--surface-active)] shadow-sm' 
                          : 'border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)]'
                      }`}
                      onClick={() => !isExisting && toggleSelect(doc.id)}
                    >
                      <div className="flex items-center justify-center w-8 h-8 rounded bg-[var(--background)] border border-[var(--border)] flex-shrink-0 group-hover:border-[var(--accent)] transition-colors">
                        <FileText size={16} className={isSelected ? "text-[var(--accent)]" : "text-[var(--muted-fg)]"} />
                      </div>
                      
                      <div className="flex items-center gap-2 min-w-0" onClick={(e) => { e.stopPropagation(); setPreviewDocId(doc.id); }}>
                        <span className="font-medium truncate text-[var(--foreground)] group-hover:underline">{doc.title}</span>
                      </div>
                      
                      <div className="flex-1" />
                      
                      <div className="hidden sm:flex items-center gap-3 text-xs text-[var(--muted-fg)] font-mono mr-2">
                        <span className="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)]">{doc.provider}</span>
                        {doc.status === 'INDEXED' && <span className="text-[var(--success)]">Indexed</span>}
                        <span className="opacity-50">{formatRelativeTime(doc.created_at)}</span>
                      </div>

                      <div className="flex-shrink-0 w-5 h-5 border-2 rounded-full flex items-center justify-center bg-[var(--background)] transition-colors"
                           style={{ borderColor: isSelected ? 'var(--accent)' : 'var(--border)' }}>
                        {isSelected && <Check size={12} strokeWidth={3} className="text-[var(--accent)]" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Document Preview Drawer */}
        {previewDocId && previewDoc && (
          <motion.div 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 320, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="border-l border-[var(--border)] bg-[var(--background)] flex flex-col flex-shrink-0"
          >
            <div className="p-3 border-b border-[var(--border)] flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-fg)]">Document Inspector</h3>
              <button onClick={() => setPreviewDocId(null)} className="p-1 rounded hover:bg-[var(--surface)] text-[var(--muted-fg)]">
                <X size={14} />
              </button>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="mb-6 flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-[var(--surface)] border border-[var(--border)] rounded-lg flex items-center justify-center mb-3">
                  <FileText size={24} className="text-[var(--foreground)]" />
                </div>
                <h2 className="text-sm font-medium break-all">{previewDoc.title}</h2>
                <div className="text-xs font-mono text-[var(--success)] mt-1">{previewDoc.status}</div>
              </div>

              <div className="flex flex-col gap-3 text-xs">
                <div className="flex justify-between border-b border-[var(--border)] pb-2">
                  <span className="text-[var(--muted-fg)]">Provider</span>
                  <span className="font-medium">{previewDoc.provider}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border)] pb-2">
                  <span className="text-[var(--muted-fg)]">Size</span>
                  <span className="font-medium">245 KB</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border)] pb-2">
                  <span className="text-[var(--muted-fg)]">Chunks</span>
                  <span className="font-medium">42 Chunks</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border)] pb-2">
                  <span className="text-[var(--muted-fg)]">Indexed</span>
                  <span className="font-medium">{formatRelativeTime(previewDoc.created_at)}</span>
                </div>
              </div>

              <div className="mt-6 border border-[var(--border)] rounded-md bg-[var(--surface)] overflow-hidden flex flex-col h-full">
                <div className="p-2 border-b border-[var(--border)] text-[10px] font-mono text-[var(--muted-fg)] uppercase">Content Preview</div>
                <div className="p-3 text-xs text-[var(--muted-fg)] leading-relaxed flex-1 min-h-[8rem] overflow-hidden relative">
                  {(previewDoc as any).processed_content ? (
                    (previewDoc as any).processed_content.substring(0, 800) + '...'
                  ) : (
                    'No content preview available.'
                  )}
                  <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-[var(--surface)] to-transparent" />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </Modal>
  );
}

function generateTitle(documents: DocumentListItem[], selectedIds: Set<string>): string {
  if (selectedIds.size === 0) return '';
  const selectedDocs = documents.filter(d => selectedIds.has(d.id));
  
  if (selectedDocs.length === 0) {
    return 'New Conversation';
  }
  
  if (selectedIds.size === 1) {
    const title = selectedDocs[0].title.replace(/\.[^/.]+$/, ""); // remove extension
    return `${title} Discussion`;
  }
  
  // Try to find common patterns or just use the first document's name + others
  const firstTitle = selectedDocs[0].title.replace(/\.[^/.]+$/, "");
  return `${firstTitle} & ${selectedIds.size - 1} others`;
}
