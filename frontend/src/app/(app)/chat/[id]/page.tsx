'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '@/lib/api';
import { useChatStream } from '@/hooks/use-chat-stream';
import { MessageBubble } from '@/components/chat/message-bubble';
import { Composer } from '@/components/chat/composer';
import { DevPanel } from '@/components/chat/dev-panel';
import { DocumentPickerModal } from '@/components/document-picker-modal';
import type { Conversation, Message, ConversationDocument } from '@/types';
import { FileText, Database, X, Search, Network, ArrowRight, Plus, Clock, MessageSquare, ChevronRight, AlertCircle, HelpCircle, Terminal } from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

export default function ChatPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const id = params.id as string;

  const [inputVal, setInputVal] = useState('');
  const [docPickerOpen, setDocPickerOpen] = useState(false);
  const [devPanelOpen, setDevPanelOpen] = useState(false);
  const messageListEndRef = useRef<HTMLDivElement>(null);

  const { data: conversation, isLoading: loadingConv } = useQuery<Conversation>({
    queryKey: ['conversation', id],
    queryFn: () => api<Conversation>(`/conversations/${id}`),
  });

  const { data: messages = [], isLoading: loadingMsgs } = useQuery<Message[]>({
    queryKey: ['conversation-messages', id],
    queryFn: async () => {
      const conv = await api<Conversation>(`/conversations/${id}`);
      return conv.messages || [];
    },
  });

  const {
    isStreaming,
    streamStatus,
    heartbeatText,
    streamedAnswer,
    currentSources,
    currentRetrievedChunks,
    debugMetadata,
    lastQuery,
    sendMessage,
    stopStream,
    setStreamStatus,
  } = useChatStream({
    conversationId: id,
    onSuccess: () => {
      setInputVal('');
      scrollToBottom();
    },
  });

  const scrollToBottom = () => {
    messageListEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamedAnswer, isStreaming, streamStatus]);

  const activeMessages = useMemo(() => {
    const list = [...messages];
    if (isStreaming && streamedAnswer) {
      list.push({
        id: 'streaming-assistant',
        role: 'assistant',
        content: streamedAnswer,
        citations: { sources: currentSources },
        created_at: new Date().toISOString(),
      });
    }
    return list;
  }, [messages, isStreaming, streamedAnswer, currentSources]);

  const lastUserMessage = useMemo(() => {
    const userMsgs = activeMessages.filter(m => m.role === 'user');
    return userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].content : undefined;
  }, [activeMessages]);

  if (loadingConv || loadingMsgs) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[var(--background)]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--accent)]" />
          <span className="text-sm font-mono text-[var(--muted-fg)]">Initializing Knowledge Context...</span>
        </div>
      </div>
    );
  }

  if (!conversation) return null;

  const attachedDocs = conversation?.documents || [];
  const existingDocIds = attachedDocs.map((d) => d.document_id);

  const suggestedQuestions = attachedDocs.length > 0 ? [
    `Summarize the key points from ${attachedDocs[0].title.replace(/\.[^/.]+$/, "")}`,
    `What are the main takeaways from the connected sources?`,
    `Explain the concepts discussed in ${attachedDocs[0].title}`
  ] : [
    "What can you help me with?",
    "How do I add knowledge to this thread?"
  ];

  return (
    <div className="flex-1 flex flex-col bg-[var(--background)] overflow-hidden relative">
      
      {/* MAIN LAYOUT: Chat + Sidebar */}
      <div className="flex-1 flex overflow-hidden min-h-0">
      {/* MAIN PANE: Chat Stream */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        
        {/* Sticky Header */}
        <div className="px-6 py-4 border-b border-[var(--border)] flex justify-between items-center bg-[var(--background)]/90 backdrop-blur-md sticky top-0 z-20">
          <h2 className="text-sm font-medium text-[var(--foreground)] truncate">{conversation.title}</h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--muted-fg)]">{attachedDocs.length} Knowledge Sources</span>
            <button onClick={() => setDocPickerOpen(true)} className="p-1.5 hover:bg-[var(--surface-hover)] rounded-md text-[var(--muted-fg)] hover:text-[var(--foreground)] transition-colors cursor-pointer" title="Attach knowledge">
              <Database size={14} />
            </button>
            {debugMetadata && (
              <button
                onClick={() => setDevPanelOpen(!devPanelOpen)}
                className={`p-1.5 rounded-md transition-colors cursor-pointer ${
                  devPanelOpen
                    ? 'bg-[var(--surface-active)] text-[var(--foreground)]'
                    : 'hover:bg-[var(--surface-hover)] text-[var(--muted-fg)] hover:text-[var(--foreground)]'
                }`}
                title="Developer Panel"
              >
                <Terminal size={14} />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 md:px-12 lg:px-24 select-text relative z-10 pb-8 pt-6">
          <div className="max-w-3xl mx-auto flex flex-col gap-6">
            
            {/* Knowledge Timeline Header (Visual Context) */}
            <div className="flex flex-col gap-3 py-6 border-b border-[var(--border)] mb-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-fg)] mb-2">Knowledge Timeline</h3>
              {attachedDocs.length > 0 ? (
                <div className="flex flex-col gap-2 relative before:absolute before:inset-0 before:ml-[5px] before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-[var(--border)] before:to-transparent">
                  {attachedDocs.map((doc, idx) => (
                    <div key={doc.document_id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                      <div className="flex items-center justify-end w-full mx-auto">
                        <div className="w-full md:w-1/2 md:pl-8">
                          <div className="p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-sm flex items-center gap-3 text-sm">
                            <FileText size={16} className="text-[var(--muted-fg)] flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="truncate font-medium text-[var(--foreground)]">{doc.title}</div>
                              <div className="text-xs text-[var(--muted-fg)]">added {formatRelativeTime(doc.attached_at || new Date().toISOString())}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="absolute left-0 w-2.5 h-2.5 bg-[var(--background)] border-2 border-[var(--border-strong)] rounded-full md:left-1/2 md:-translate-x-1/2" />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-[var(--muted-fg)]">No knowledge sources attached yet.</div>
              )}
              <div className="mt-4 flex items-center justify-center">
                <span className="px-3 py-1 bg-[var(--surface-raised)] border border-[var(--border)] rounded-full text-xs text-[var(--muted-fg)] font-mono">
                  Current Context: {attachedDocs.length} Sources
                </span>
              </div>
            </div>

            {activeMessages.length === 0 && streamStatus === 'idle' ? (
              <div className="flex flex-col items-center justify-center min-h-[30vh] text-center max-w-lg mx-auto">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-6 border border-[var(--border)] bg-[var(--surface)] shadow-sm">
                  <Network size={20} className="text-[var(--foreground)]" />
                </div>
                <h2 className="text-lg font-medium mb-6 text-[var(--foreground)]">Knowledge Flow Activated</h2>
                
                <div className="w-full grid gap-3">
                  {suggestedQuestions.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => sendMessage(q)}
                      className="flex items-center justify-between p-3.5 bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--border-strong)] rounded-xl text-left transition-all hover:shadow-sm group cursor-pointer"
                    >
                      <span className="text-sm text-[var(--foreground)]">{q}</span>
                      <ChevronRight size={16} className="text-[var(--muted-fg)] opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {activeMessages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                
                {/* DYNAMIC PIPELINE STATUS BUBBLE */}
                {isStreaming && !streamedAnswer && streamStatus !== 'idle' && streamStatus !== 'error' && streamStatus !== 'action_required' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full flex gap-4 max-w-3xl mx-auto mb-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full border border-[var(--border)] bg-[var(--surface)] flex items-center justify-center mt-1 text-[var(--muted-fg)] shadow-sm">
                      <Network size={14} className="animate-pulse" />
                    </div>
                    <div className="flex-1 px-4 py-3 border border-[var(--border)] bg-[var(--surface)] rounded-2xl rounded-tl-sm text-[var(--foreground)] min-w-[200px] max-w-md flex flex-col gap-1 shadow-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-[var(--foreground)] tracking-wide">
                          {streamStatus === 'planning' && 'Planning...'}
                          {streamStatus === 'retrieving' && 'Searching your knowledge...'}
                          {streamStatus === 'reranking' && 'Optimizing search results...'}
                          {streamStatus === 'building_prompt' && 'Preparing prompt context...'}
                          {streamStatus === 'calling_llm' && 'Generating response...'}
                          {streamStatus === 'generating' && 'Generating response...'}
                        </span>
                        <div className="flex gap-1 mt-0.5">
                          <motion.div className="w-1.5 h-1.5 bg-[var(--muted-fg)] rounded-full" animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }} transition={{ repeat: Infinity, duration: 1.2, delay: 0 }} />
                          <motion.div className="w-1.5 h-1.5 bg-[var(--muted-fg)] rounded-full" animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }} transition={{ repeat: Infinity, duration: 1.2, delay: 0.2 }} />
                          <motion.div className="w-1.5 h-1.5 bg-[var(--muted-fg)] rounded-full" animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }} transition={{ repeat: Infinity, duration: 1.2, delay: 0.4 }} />
                        </div>
                      </div>
                      {heartbeatText && (
                        <span className="text-xs text-[var(--muted-fg)] italic">{heartbeatText}</span>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* PIPELINE ERROR STATE */}
                {streamStatus === 'error' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full flex gap-4 max-w-3xl mx-auto mb-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full border border-[var(--danger)] bg-[var(--surface)] flex items-center justify-center mt-1 text-[var(--danger)] shadow-sm">
                      <AlertCircle size={14} />
                    </div>
                    <div className="flex-1 px-4 py-3 border border-[var(--danger)]/30 bg-[var(--surface)] text-[var(--foreground)] rounded-2xl rounded-tl-sm max-w-md flex flex-col gap-3 shadow-sm">
                      <span className="text-sm font-medium text-[var(--danger)]">Something went wrong</span>
                      <button
                        onClick={() => sendMessage(lastQuery)}
                        className="self-start px-3 py-1 bg-[var(--danger)] hover:bg-[var(--danger)]/90 text-white text-xs font-semibold rounded-md transition-colors cursor-pointer"
                      >
                        Retry
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* PIPELINE ACTION REQUIRED STATE */}
                {streamStatus === 'action_required' && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="w-full flex gap-4 max-w-3xl mx-auto mb-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full border border-[var(--accent)] bg-[var(--surface)] flex items-center justify-center mt-1 text-[var(--accent)] shadow-sm">
                      <HelpCircle size={14} />
                    </div>
                    <div className="flex-1 px-4 py-3 border border-[var(--accent)]/30 bg-[var(--surface)] rounded-2xl rounded-tl-sm max-w-md flex flex-col gap-3 shadow-sm">
                      <span className="text-sm text-[var(--foreground)]">
                        I couldn't find relevant knowledge. Would you like me to answer using general knowledge?
                      </span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => sendMessage(lastQuery, 'GENERAL_ONLY')}
                          className="px-3 py-1 bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white text-xs font-semibold rounded-md transition-colors cursor-pointer"
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => setStreamStatus('idle')}
                          className="px-3 py-1 bg-[var(--surface-hover)] text-[var(--foreground)] border border-[var(--border)] text-xs font-medium rounded-md transition-colors cursor-pointer"
                        >
                          No
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                <div ref={messageListEndRef} />
              </>
            )}
          </div>
        </div>

        {/* Message Input Composer Area */}
        <div className="px-4 md:px-12 lg:px-24 pb-8 z-10 pt-2 bg-gradient-to-t from-[var(--background)] to-transparent">
          <div className="max-w-3xl mx-auto">
            <Composer
              value={inputVal}
              onChange={setInputVal}
              onSubmit={() => {
                sendMessage(inputVal);
                setInputVal('');
              }}
              isStreaming={isStreaming}
              onStop={stopStream}
              lastUserMessage={lastUserMessage}
            />
          </div>
        </div>
      </div>

      {/* RIGHT PANE: Context Sidebar */}
      <div className="hidden md:flex w-[280px] flex-shrink-0 flex-col border-l border-[var(--border)] bg-[var(--surface)] relative z-10 overflow-y-auto">
        <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between sticky top-0 bg-[var(--surface)] z-10">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-fg)]">Knowledge Context</h2>
          <span className="px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-[10px] font-mono">{attachedDocs.length}</span>
        </div>
        
        <div className="flex-1 p-4 flex flex-col gap-3">
          <AnimatePresence>
            {attachedDocs.map((doc, idx) => (
              <motion.div
                key={doc.document_id}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                className="group p-3 rounded-lg border border-[var(--border)] bg-[var(--background)] hover:border-[var(--border-strong)] transition-colors flex flex-col gap-2 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 text-[var(--foreground)] min-w-0">
                    <FileText size={14} className="flex-shrink-0 text-[var(--accent)]" />
                    <span className="text-sm font-medium truncate group-hover:underline cursor-pointer">{doc.title}</span>
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 transition-opacity text-[var(--muted-fg)] hover:text-[var(--danger)] p-0.5 rounded hover:bg-[var(--surface)]">
                    <X size={12} />
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] uppercase font-bold tracking-widest text-[var(--muted-fg)] opacity-60">Type</span>
                    <span className="text-[10px] font-mono">{doc.provider || 'PDF'}</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] uppercase font-bold tracking-widest text-[var(--muted-fg)] opacity-60">Status</span>
                    <span className="text-[10px] font-mono text-[var(--success)]">Indexed</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] uppercase font-bold tracking-widest text-[var(--muted-fg)] opacity-60">Size</span>
                    <span className="text-[10px] font-mono">{(doc as any).chunks_count || 42} Chunks</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[9px] uppercase font-bold tracking-widest text-[var(--muted-fg)] opacity-60">Added</span>
                    <span className="text-[10px] font-mono">Today</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          <button 
            onClick={() => setDocPickerOpen(true)}
            className="mt-2 p-3 rounded-lg border border-dashed border-[var(--border-strong)] flex items-center justify-center gap-2 text-[var(--muted-fg)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] hover:border-[var(--accent)] transition-colors text-sm font-medium cursor-pointer"
          >
            <Plus size={14} /> Add Knowledge
          </button>

        </div>
      </div>
      </div> {/* end flex-1 flex row */}

      {/* Bottom Drawer Developer Panel */}
      <DevPanel
        debugMetadata={debugMetadata}
        isOpen={devPanelOpen}
        onClose={() => setDevPanelOpen(false)}
      />

      <DocumentPickerModal
        open={docPickerOpen}
        onClose={() => {
          setDocPickerOpen(false);
          queryClient.invalidateQueries({ queryKey: ['conversation', id] });
        }}
        conversationId={id}
        existingDocIds={existingDocIds}
      />
    </div>
  );
}
