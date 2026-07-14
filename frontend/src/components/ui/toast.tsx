'use client';

import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface ToastItem {
  id: string;
  message: string;
  type?: 'success' | 'error' | 'info';
}

interface ToastContextValue {
  toast: (message: string, type?: ToastItem['type']) => void;
}

// Singleton toast state (avoids deep context nesting)
let toastListeners: Array<(items: ToastItem[]) => void> = [];
let toastItems: ToastItem[] = [];
let toastCounter = 0;

function notifyListeners() {
  toastListeners.forEach((l) => l([...toastItems]));
}

export function toast(message: string, type: ToastItem['type'] = 'info') {
  const id = `toast-${++toastCounter}`;
  toastItems.push({ id, message, type });
  notifyListeners();

  // Auto-dismiss after 3 seconds
  setTimeout(() => {
    toastItems = toastItems.filter((t) => t.id !== id);
    notifyListeners();
  }, 3000);
}

/**
 * ToastContainer — render at root level. Bottom-right, async confirmations only.
 */
export function ToastContainer() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    toastListeners.push(setItems);
    return () => {
      toastListeners = toastListeners.filter((l) => l !== setItems);
    };
  }, []);

  if (items.length === 0) return null;

  const typeStyles: Record<string, React.CSSProperties> = {
    success: { borderLeft: '3px solid var(--success)' },
    error: { borderLeft: '3px solid var(--danger)' },
    info: { borderLeft: '3px solid var(--accent)' },
  };

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 max-w-sm">
      {items.map((item) => (
        <div
          key={item.id}
          className="px-4 py-3 rounded-lg text-body shadow-sm"
          style={{
            backgroundColor: 'var(--surface-raised)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            ...typeStyles[item.type || 'info'],
          }}
          role="status"
          aria-live="polite"
        >
          {item.message}
        </div>
      ))}
    </div>
  );
}
