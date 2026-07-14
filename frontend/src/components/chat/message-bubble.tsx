'use client';

import { FileText, Layers, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Citation, Message } from '@/types';

interface MessageBubbleProps {
  message: Message;
  onCitationClick?: (index: number) => void;
}

/** Group citations by document for the minimal Sources Used list. */
function groupSources(sources: Citation[]): { title: string; sections: number }[] {
  const map = new Map<string, number>();
  for (const src of sources) {
    const title = (src as any).title || src.document_title || 'Unknown Document';
    map.set(title, (map.get(title) || 0) + 1);
  }
  return Array.from(map.entries()).map(([title, sections]) => ({ title, sections }));
}

export function MessageBubble({ message, onCitationClick }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const renderContent = (content: string) => {
    if (isUser) return <p className="whitespace-pre-wrap">{content}</p>;

    const regex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
      const matchIndex = match.index;
      const citationNumber = parseInt(match[1], 10);

      if (matchIndex > lastIndex) {
        parts.push(content.substring(lastIndex, matchIndex));
      }

      parts.push(
        <button
          key={matchIndex}
          onClick={() => onCitationClick?.(citationNumber - 1)}
          className="mx-[2px] inline-flex items-center justify-center font-mono text-[10px] font-medium rounded-sm px-1 py-0.5 cursor-pointer transition-colors hover:bg-[var(--foreground)] hover:text-[var(--background)] bg-[var(--surface-hover)] text-[var(--muted-fg)] border border-[var(--border)]"
          title={`View Source ${citationNumber}`}
        >
          {citationNumber}
        </button>
      );

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return (
      <div className="whitespace-pre-wrap space-y-4 text-sm leading-relaxed text-[var(--foreground)]">
        {parts.length > 0 ? parts : content}
      </div>
    );
  };

  const sources = message.citations?.sources || [];
  const showSources = !isUser && sources.length > 0 && message.id !== 'streaming-assistant';
  const grouped = showSources ? groupSources(sources) : [];

  return (
    <div className="w-full flex gap-4 my-2 select-text group">
      <div className="flex-shrink-0 pt-1">
        {isUser ? (
          <div className="w-6 h-6 rounded bg-[var(--surface-hover)] border border-[var(--border)] flex items-center justify-center text-[var(--muted-fg)]">
            <User size={12} />
          </div>
        ) : (
          <div className="w-6 h-6 rounded bg-[var(--foreground)] flex items-center justify-center text-[var(--background)] shadow-sm">
            <Layers size={12} />
          </div>
        )}
      </div>

      <div className="flex-1 flex flex-col min-w-0 pb-6 border-b border-[var(--border)]/50 group-last:border-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-[var(--foreground)]">
            {isUser ? 'You' : 'Conduit'}
          </span>
          <span className="text-[10px] text-[var(--muted-fg)] font-mono">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div className={cn('text-sm text-[var(--foreground)]', isUser ? 'opacity-90' : '')}>
          {renderContent(message.content)}
        </div>

        {/* Minimal Sources Used — detailed chunks live only in Developer Panel */}
        {showSources && (
          <div className="mt-4 pt-3 border-t border-[var(--border)]/60">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-fg)] mb-2">
              Sources Used
            </div>
            <ul className="flex flex-col gap-2">
              {grouped.map((g, i) => (
                <li key={i} className="flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={() => onCitationClick?.(i)}
                    className="inline-flex items-center gap-1.5 text-left text-xs text-[var(--foreground)] hover:underline cursor-pointer"
                  >
                    <FileText size={12} className="text-[var(--muted-fg)] flex-shrink-0" />
                    <span className="truncate">{g.title}</span>
                  </button>
                  <span className="text-[11px] text-[var(--muted-fg)] pl-5">
                    • {g.sections} section{g.sections === 1 ? '' : 's'} referenced
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
