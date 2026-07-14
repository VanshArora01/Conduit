'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { cn, formatRelativeTime, truncate } from '@/lib/utils';
import { useAuth } from '@/contexts/auth-context';
import { DropdownMenu, DropdownItem } from '@/components/ui/dropdown-menu';
import type { Conversation } from '@/types';
import {
  Layers,
  PanelLeftClose,
  Plus,
  Settings,
  LogOut,
  MoreHorizontal,
  Pin,
  PinOff,
  Pencil,
  Trash2,
  FileText,
  Database,
  Search,
  User,
  Sliders,
  Keyboard,
  Palette,
  HardDrive
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onNewChat: () => void;
}

export function Sidebar({ collapsed, onToggle, onNewChat }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => api<Conversation[]>('/conversations'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/conversations/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  });

  const sortedConversations = useMemo(() => {
    return [...conversations].sort((a, b) => {
      if (a.is_pinned && !b.is_pinned) return -1;
      if (!a.is_pinned && b.is_pinned) return 1;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [conversations]);

  if (collapsed) {
    return (
      <aside className="flex flex-col items-center py-4 gap-4 flex-shrink-0 w-16 bg-[var(--surface)] border-r border-[var(--border)] h-screen z-20 transition-all">
        <button onClick={onToggle} className="w-10 h-10 flex items-center justify-center rounded-lg text-[var(--foreground)] hover:bg-[var(--surface-hover)] transition-colors cursor-pointer">
          <Layers size={20} />
        </button>
        <div className="w-8 h-[1px] bg-[var(--border)] my-1" />
        <button
          onClick={onNewChat}
          className="w-10 h-10 flex items-center justify-center rounded-lg bg-[var(--foreground)] text-[var(--background)] hover:opacity-90 transition-opacity cursor-pointer shadow-sm"
        >
          <Plus size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex flex-col flex-shrink-0 w-64 bg-[var(--surface)] border-r border-[var(--border)] h-screen z-20 overflow-hidden text-sm transition-all font-sans">
      
      {/* Header */}
      <div className="flex items-center justify-between p-4 pl-5">
        <Link href="/home" className="flex items-center gap-2.5 select-none group">
          <Layers size={16} className="text-[var(--foreground)]" />
          <span className="font-medium tracking-tight text-[var(--foreground)]">Conduit</span>
        </Link>
        <button onClick={onToggle} className="text-[var(--muted-fg)] hover:text-[var(--foreground)] transition-colors p-1 rounded-md hover:bg-[var(--surface-hover)]">
          <PanelLeftClose size={16} />
        </button>
      </div>

      <div className="px-3 pb-2">
        <button
          onClick={onNewChat}
          className="w-full h-8 flex items-center justify-between px-3 rounded-md bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] font-medium hover:bg-[var(--surface-hover)] transition-colors shadow-sm mb-2"
        >
          <span className="flex items-center gap-2"><Plus size={14} /> New Conversation</span>
          <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded bg-[var(--surface)] px-1.5 font-mono text-[10px] text-[var(--muted-fg)]">N</kbd>
        </button>

        <button
          onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }))}
          className="w-full h-8 flex items-center justify-between px-3 rounded-md bg-transparent border border-transparent text-[var(--muted-fg)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] transition-colors"
        >
          <span className="flex items-center gap-2"><Search size={14} /> Search</span>
          <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded px-1.5 font-mono text-[10px] bg-[var(--surface-raised)]">/</kbd>
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-3 flex flex-col gap-[2px]">
        
        {isLoading ? (
          <div className="px-3 py-4 text-xs text-[var(--muted-fg)]">Loading...</div>
        ) : sortedConversations.length === 0 ? (
          <div className="px-3 py-4 text-xs text-[var(--muted-fg)]">No conversations yet.</div>
        ) : (
          sortedConversations.map((conv) => {
            const isActive = pathname === `/chat/${conv.id}`;
            
            const attachedDocs = conv.documents || [];

            const isDeleting = deleteMutation.isPending && deleteMutation.variables === conv.id;

            return (
              <div key={conv.id} className={`mb-3 transition-opacity duration-200 ${isDeleting ? 'opacity-40 pointer-events-none animate-pulse' : ''}`}>
                <div
                  className={`group flex items-center gap-2 px-2.5 py-1.5 rounded-md cursor-pointer transition-colors ${
                    isActive ? 'bg-[var(--surface-active)] text-[var(--foreground)]' : 'hover:bg-[var(--surface-hover)] text-[var(--muted-fg)] hover:text-[var(--foreground)]'
                  }`}
                >
                  {renamingId === conv.id ? (
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') setRenamingId(null);
                      }}
                      onBlur={() => setRenamingId(null)}
                      className="flex-1 text-sm bg-transparent outline-none text-[var(--foreground)]"
                    />
                  ) : (
                    <Link href={`/chat/${conv.id}`} className="flex-1 min-w-0 flex items-center justify-between">
                      <span className={`truncate font-medium ${isActive ? 'text-[var(--foreground)]' : ''}`}>
                        {truncate(conv.title, 24)}
                      </span>
                    </Link>
                  )}

                    <DropdownMenu
                    align="right"
                    trigger={
                      <button className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-[var(--muted-fg)] hover:text-[var(--foreground)] transition-opacity">
                        <MoreHorizontal size={14} />
                      </button>
                    }
                  >
                    <DropdownItem danger onClick={() => deleteMutation.mutate(conv.id)}>
                      <span className="flex items-center gap-2"><Trash2 size={14} /> Delete</span>
                    </DropdownItem>
                  </DropdownMenu>
                </div>
                
                {/* Knowledge Sources attached to this conversation */}
                <div className="flex flex-col gap-0.5 pl-[22px] pr-2 mt-0.5">
                  {attachedDocs.map(doc => (
                    <div key={doc.document_id} className="flex items-center gap-2 text-[11px] text-[var(--muted-fg)] hover:text-[var(--foreground)] cursor-pointer transition-colors py-0.5">
                      <FileText size={10} />
                      <span className="truncate">{doc.title}</span>
                    </div>
                  ))}
                  <div className="flex items-center gap-2 text-[10px] text-[var(--muted-fg)] opacity-60 mt-1 pl-[14px]">
                    {attachedDocs.length} sources
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Knowledge Usage */}
      <div className="px-4 py-3 border-t border-[var(--border)] flex flex-col gap-2">
        <h3 className="text-xs font-semibold text-[var(--muted-fg)] uppercase tracking-wider mb-1">Knowledge Usage</h3>
        <div className="flex items-center justify-between text-xs text-[var(--muted-fg)]">
          <span className="flex items-center gap-1.5"><FileText size={12} /> Documents</span>
          <span className="font-mono">12</span>
        </div>
        <div className="flex items-center justify-between text-xs text-[var(--muted-fg)]">
          <span className="flex items-center gap-1.5"><Layers size={12} /> Conversations</span>
          <span className="font-mono">{sortedConversations.length}</span>
        </div>
        <div className="flex items-center justify-between text-xs text-[var(--muted-fg)]">
          <span className="flex items-center gap-1.5"><HardDrive size={12} /> Sources</span>
          <span className="font-mono text-[var(--success)]">Connected</span>
        </div>
      </div>

      {/* User Profile & Settings */}
      <div className="p-3 border-t border-[var(--border)] flex items-center justify-between">
        <DropdownMenu
          align="left"
          side="top"
          trigger={
            <button className="w-full flex items-center justify-between p-1.5 rounded-md hover:bg-[var(--surface-hover)] transition-colors group">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-6 h-6 rounded bg-[var(--background)] border border-[var(--border)] flex items-center justify-center text-xs font-medium text-[var(--foreground)] flex-shrink-0">
                  {user?.full_name?.[0]?.toUpperCase() || 'U'}
                </div>
                <span className="text-sm font-medium text-[var(--foreground)] truncate group-hover:text-[var(--accent)] transition-colors">{user?.full_name || 'User'}</span>
              </div>
            </button>
          }
        >
          <DropdownItem onClick={() => router.push('/profile')}>
            <span className="flex items-center gap-2"><User size={14} /> Profile</span>
          </DropdownItem>
          <DropdownItem onClick={() => router.push('/settings')}>
            <span className="flex items-center gap-2"><Sliders size={14} /> Preferences</span>
          </DropdownItem>
          <DropdownItem onClick={() => { /* Open shortcuts modal */ }}>
            <span className="flex items-center justify-between w-full">
              <span className="flex items-center gap-2"><Keyboard size={14} /> Keyboard Shortcuts</span>
            </span>
          </DropdownItem>
          <DropdownItem onClick={() => { /* Toggle theme */ }}>
            <span className="flex items-center gap-2"><Palette size={14} /> Theme</span>
          </DropdownItem>
          <div className="h-px bg-[var(--border)] my-1" />
          <DropdownItem onClick={() => router.push('/knowledge')}>
            <span className="flex items-center gap-2"><HardDrive size={14} /> Connected Sources</span>
          </DropdownItem>
          <DropdownItem onClick={() => router.push('/settings/account')}>
            <span className="flex items-center gap-2"><Settings size={14} /> Account</span>
          </DropdownItem>
          <div className="h-px bg-[var(--border)] my-1" />
          <DropdownItem danger onClick={() => {
            // Clear React Query cache
            queryClient.clear();
            // Assuming logout() clears tokens and redirects with toast
            logout();
          }}>
            <span className="flex items-center gap-2"><LogOut size={14} /> Sign out</span>
          </DropdownItem>
        </DropdownMenu>
      </div>
    </aside>
  );
}
