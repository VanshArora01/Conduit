'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Command } from 'cmdk';
import { Search, MessageSquare, FileText, Plus, Database, Settings, Cloud } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function CommandPalette({ open, onClose, onNewChat }: { open: boolean; onClose: () => void; onNewChat: () => void }) {
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        if (open) onClose();
        else {
          // Open logic needs to be handled by the parent
        }
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/40 backdrop-blur-sm" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <Command 
        className="w-full max-w-[640px] overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--background)] shadow-2xl"
        label="Global Command Menu"
      >
        <div className="flex items-center border-b border-[var(--border)] px-3 py-3" cmdk-input-wrapper="">
          <Search className="mr-2 h-4 w-4 shrink-0 opacity-50 text-[var(--muted-fg)]" />
          <Command.Input 
            className="flex h-6 w-full rounded-md bg-transparent text-sm outline-none placeholder:text-[var(--muted-fg)] disabled:cursor-not-allowed disabled:opacity-50 text-[var(--foreground)]"
            placeholder="Search knowledge, conversations, or actions..." 
            autoFocus 
          />
          <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 font-mono text-[10px] font-medium text-[var(--muted-fg)] opacity-100">
            ESC
          </kbd>
        </div>

        <Command.List className="max-h-[400px] overflow-y-auto overflow-x-hidden">
          <Command.Empty className="py-6 text-center text-sm text-[var(--muted-fg)]">No results found.</Command.Empty>
          
          <Command.Group heading="Actions" className="overflow-hidden p-1 text-[var(--foreground)] [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-[var(--muted-fg)]">
            <Command.Item 
              onSelect={() => { onNewChat(); onClose(); }}
              className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-[var(--surface-hover)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Plus className="mr-2 h-4 w-4 text-[var(--muted-fg)]" />
              <span>New Conversation</span>
              <kbd className="ml-auto inline-flex h-5 items-center gap-1 rounded border border-[var(--border-strong)] px-1.5 font-mono text-[10px] font-medium text-[var(--muted-fg)]">⌘ N</kbd>
            </Command.Item>
            
            <Command.Item 
              onSelect={() => { router.push('/knowledge'); onClose(); }}
              className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-[var(--surface-hover)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Database className="mr-2 h-4 w-4 text-[var(--muted-fg)]" />
              <span>Add Knowledge</span>
            </Command.Item>
            
            <Command.Item 
              onSelect={() => { router.push('/onboarding'); onClose(); }}
              className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-[var(--surface-hover)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Cloud className="mr-2 h-4 w-4 text-[var(--muted-fg)]" />
              <span>Connect Google Drive</span>
            </Command.Item>
          </Command.Group>

          <Command.Separator className="h-px bg-[var(--border)]" />

          <Command.Group heading="Navigation" className="overflow-hidden p-1 text-[var(--foreground)] [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-[var(--muted-fg)]">
            <Command.Item 
              onSelect={() => { router.push('/home'); onClose(); }}
              className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-[var(--surface-hover)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <MessageSquare className="mr-2 h-4 w-4 text-[var(--muted-fg)]" />
              <span>Conversation Home</span>
            </Command.Item>
            
            <Command.Item 
              onSelect={() => { router.push('/settings'); onClose(); }}
              className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-[var(--surface-hover)] data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
            >
              <Settings className="mr-2 h-4 w-4 text-[var(--muted-fg)]" />
              <span>Settings</span>
            </Command.Item>
          </Command.Group>

        </Command.List>
      </Command>
    </div>
  );
}
