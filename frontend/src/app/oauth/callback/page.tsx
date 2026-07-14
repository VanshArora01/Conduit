'use client';

import { useEffect } from 'react';

export default function OAuthCallbackPage() {
  useEffect(() => {
    // Notify the parent window that OAuth is complete
    if (window.opener) {
      window.opener.postMessage({ type: 'OAUTH_COMPLETE' }, window.location.origin);
    }
    // Automatically close the popup
    window.close();
  }, []);

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[var(--background)]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--accent)]" />
        <p className="text-sm font-medium text-[var(--foreground)]">Authentication successful. Returning to app...</p>
      </div>
    </div>
  );
}
