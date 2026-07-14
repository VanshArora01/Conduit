'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Cloud, Database, Plus, MessageSquare, Clock, FileText, ChevronRight, HardDrive } from 'lucide-react';
import type { Conversation, DocumentListItem } from '@/types';
import { formatRelativeTime } from '@/lib/utils';
import { motion } from 'framer-motion';

export default function HomePage() {
  const router = useRouter();

  const { data: conversations = [], isLoading: loadingConvs } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api<Conversation[]>('/conversations'),
  });

  const { data: documents = [], isLoading: loadingDocs } = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => api<DocumentListItem[]>('/documents?limit=5'),
  });

  if (loadingConvs || loadingDocs) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center h-full">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--accent)]" />
      </div>
    );
  }

  const hasContent = conversations.length > 0 || documents.length > 0;

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto px-8 md:px-12 lg:px-16 py-12 w-full">
      <div className="flex flex-col gap-2 mb-12 items-center text-center max-w-2xl mx-auto pt-8">
        <h1 className="text-4xl font-semibold tracking-tight text-[var(--foreground)] mb-2">
          {hasContent ? 'Welcome back' : 'Welcome to Conduit'}
        </h1>
        <p className="text-base text-[var(--muted-fg)]">
          {hasContent ? 'Pick up where you left off or start a new thread.' : 'Connect your knowledge to begin building your intelligent workspace.'}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Main Column */}
        <div className="col-span-1 lg:col-span-2 flex flex-col gap-8">
          
          {/* Quick Actions (Always visible, prominently for new users) */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-fg)] mb-4">Quick Actions</h2>
            <div className="grid grid-cols-1 sm:grid-cols-1 gap-6">
              <button 
                onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'n', bubbles: true }))}
                className="flex flex-col gap-4 p-5 bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] hover:shadow-sm rounded-xl transition-all hover:bg-[var(--surface-hover)] group text-left max-w-sm"
              >
                <div className="w-10 h-10 rounded-xl bg-[var(--background)] flex items-center justify-center border border-[var(--border)] group-hover:border-[var(--accent)] group-hover:bg-[var(--accent)] group-hover:text-[var(--background)] transition-all">
                  <Plus size={16} className="text-[var(--foreground)]" />
                </div>
                <div>
                  <div className="text-sm font-medium text-[var(--foreground)] mb-1">New Conversation</div>
                  <div className="text-xs text-[var(--muted-fg)]">Start a new knowledge thread</div>
                </div>
              </button>
            </div>
          </section>

          {/* Continue Working / Recent Conversations */}
          {conversations.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-fg)] mb-4">Continue Working</h2>
              <div className="flex flex-col gap-3">
                {conversations.slice(0, 5).map((conv, i) => (
                  <motion.div 
                    key={conv.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => router.push(`/chat/${conv.id}`)}
                    className="group flex items-center justify-between p-4 bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--border-strong)] rounded-xl cursor-pointer transition-all hover:shadow-sm"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-[var(--background)] border border-[var(--border)] flex items-center justify-center">
                        <MessageSquare size={16} className="text-[var(--muted-fg)] group-hover:text-[var(--foreground)] transition-colors" />
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors">
                          {conv.title}
                        </h3>
                        <div className="flex items-center gap-2 mt-1">
                          <Clock size={12} className="text-[var(--muted-fg)]" />
                          <span className="text-xs text-[var(--muted-fg)]">{formatRelativeTime(conv.updated_at)}</span>
                          <span className="text-[var(--muted-fg)] text-[10px]">•</span>
                          <span className="text-xs text-[var(--muted-fg)]">{(conv.documents || []).length} sources attached</span>
                        </div>
                      </div>
                    </div>
                    <ChevronRight size={16} className="text-[var(--muted-fg)] opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1" />
                  </motion.div>
                ))}
              </div>
            </section>
          )}

        </div>

        {/* Sidebar Column */}
        <div className="col-span-1 flex flex-col gap-8">
          
          {/* Recent Knowledge / Imports */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-fg)] mb-4">Recent Imports</h2>
            {documents.length > 0 ? (
              <div className="flex flex-col gap-2">
                {documents.slice(0, 5).map((doc, i) => (
                  <motion.div 
                    key={doc.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-3 p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg hover:border-[var(--border-strong)] transition-colors cursor-pointer"
                  >
                    <div className="w-8 h-8 flex-shrink-0 rounded bg-[var(--background)] flex items-center justify-center border border-[var(--border)]">
                      <FileText size={14} className="text-[var(--muted-fg)]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium text-[var(--foreground)] truncate">{doc.title}</div>
                      <div className="flex justify-between items-center mt-0.5">
                        <span className="text-[10px] uppercase font-mono tracking-wider text-[var(--success)]">{doc.status}</span>
                        <span className="text-xs text-[var(--muted-fg)]">{formatRelativeTime(doc.created_at)}</span>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="p-6 bg-[var(--surface)] border border-dashed border-[var(--border-strong)] rounded-xl flex flex-col items-center text-center">
                <FileText size={24} className="text-[var(--muted-fg)] mb-2" />
                <div className="text-sm text-[var(--foreground)] font-medium">No documents yet</div>
                <div className="text-xs text-[var(--muted-fg)] mt-1">Upload files to build your context</div>
              </div>
            )}
          </section>

          {/* Connected Sources Summary */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted-fg)] mb-4">Knowledge Sources</h2>
            <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[var(--background)] border border-[var(--border)] flex items-center justify-center">
                  <HardDrive size={18} className="text-[#3B82F6]" />
                </div>
                <div>
                  <div className="text-sm font-medium text-[var(--foreground)]">Google Drive</div>
                  <div className="text-xs text-[var(--success)]">Connected & Syncing</div>
                </div>
              </div>
              <div className="text-xs font-mono text-[var(--muted-fg)]">
                {documents.length} docs
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
