'use client';

import { useRef, useEffect, type KeyboardEvent } from 'react';
import { Send, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isStreaming: boolean;
  onStop: () => void;
  placeholder?: string;
  lastUserMessage?: string;
}

export function Composer({
  value,
  onChange,
  onSubmit,
  isStreaming,
  onStop,
  placeholder = 'Ask a question about the attached documents...',
  lastUserMessage,
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [value]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Allow typing ahead while streaming; only block Enter-submit mid-stream
    const isSubmit = (e.key === 'Enter' && !e.shiftKey) || (e.key === 'Enter' && (e.ctrlKey || e.metaKey));

    if (isSubmit) {
      e.preventDefault();
      if (!isStreaming && value.trim()) {
        onSubmit();
      }
      return;
    }

    if (e.key === 'ArrowUp' && !value && lastUserMessage) {
      e.preventDefault();
      onChange(lastUserMessage);
    }
  };

  return (
    <div
      className="p-4 border-t flex flex-col gap-2 relative bg-[var(--bg)]"
      style={{ borderColor: 'var(--border)' }}
    >
      <div
        className="relative flex items-end gap-2 p-2.5 rounded-xl border transition-all focus-within:ring-2 focus-within:ring-[var(--accent-subtle)] focus-within:border-[var(--accent)]"
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'Type ahead while Conduit generates…' : placeholder}
          disabled={false}
          className="flex-1 bg-transparent text-body resize-none max-h-[200px] py-1 px-1.5 outline-none"
          style={{ color: 'var(--text-primary)' }}
        />

        <div className="flex items-center gap-2 flex-shrink-0">
          {isStreaming && (
            <Button
              variant="danger"
              size="compact"
              onClick={onStop}
              icon={<Square size={14} fill="currentColor" />}
              aria-label="Cancel generation"
            >
              Cancel
            </Button>
          )}
          <Button
            variant="primary"
            size="compact"
            disabled={!value.trim() || isStreaming}
            onClick={onSubmit}
            icon={<Send size={14} />}
            aria-label="Send message"
          />
        </div>
      </div>

      <div className="flex justify-between items-center px-1">
        <span className="text-xs text-[var(--muted-fg)]">
          <span className="font-mono bg-[var(--surface-raised)] border border-[var(--border)] px-1 py-0.5 rounded mr-1 text-[10px]">Enter</span> to send
          <span className="font-mono bg-[var(--surface-raised)] border border-[var(--border)] px-1 py-0.5 rounded mx-1 text-[10px]">⇧ Enter</span> for newline
          {isStreaming && (
            <span className="ml-2 text-[var(--danger)] font-medium">Generation in progress — Cancel to abort</span>
          )}
        </span>
      </div>
    </div>
  );
}
