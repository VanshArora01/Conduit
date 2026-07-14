'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import { Sidebar } from '@/components/layout/sidebar';
import { CommandPalette } from '@/components/command-palette';
import { ToastContainer } from '@/components/ui/toast';
import { DocumentPickerModal } from '@/components/document-picker-modal';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [documentPickerOpen, setDocumentPickerOpen] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input, textarea, or contenteditable
      const target = e.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
      
      // ⌘N / Ctrl+N new chat
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        setDocumentPickerOpen(true);
      }

      if (!isInput) {
        // 'n' for New Conversation
        if (e.key === 'n' && !e.metaKey && !e.ctrlKey) {
          e.preventDefault();
          setDocumentPickerOpen(true);
        }
        
        // '/' for Search / Command Palette
        if (e.key === '/') {
          e.preventDefault();
          setCommandPaletteOpen(true);
        }
      }

      // Esc to close overlays
      if (e.key === 'Escape') {
        if (commandPaletteOpen) setCommandPaletteOpen(false);
        if (documentPickerOpen) setDocumentPickerOpen(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [commandPaletteOpen, documentPickerOpen]);

  // Responsive: auto-collapse sidebar on tablet
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 1279px)');
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      setSidebarCollapsed(e.matches);
    };
    handler(mql);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  if (isLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: 'var(--bg)' }}
      >
        <div className="flex gap-1">
          <span className="thinking-dot" />
          <span className="thinking-dot" />
          <span className="thinking-dot" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg)' }}>
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        onNewChat={() => setDocumentPickerOpen(true)}
      />

      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        {children}
      </main>

      {/* Global overlays */}
      <CommandPalette
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onNewChat={() => {
          setCommandPaletteOpen(false);
          setDocumentPickerOpen(true);
        }}
      />

      <DocumentPickerModal
        open={documentPickerOpen}
        onClose={() => setDocumentPickerOpen(false)}
      />

      <ToastContainer />
    </div>
  );
}
