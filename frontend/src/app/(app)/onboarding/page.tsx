'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FlowLine } from '@/components/flow-line';
import { Button } from '@/components/ui/button';
import { StatusChip } from '@/components/ui/status-chip';
import { api } from '@/lib/api';
import {
  HardDrive,
  Github,
  Mail,
  FileText as NotionIcon,
  Cloud,
  MessageCircle,
  Upload,
  Check,
  Loader2,
} from 'lucide-react';

type OnboardingStep = 'welcome' | 'connecting' | 'scanning' | 'done';

interface Connector {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  active: boolean;
}

const connectors: Connector[] = [
  { id: 'google_drive', name: 'Google Drive', icon: <HardDrive size={20} />, description: 'Import documents, spreadsheets, and presentations', active: true },
  { id: 'github', name: 'GitHub', icon: <Github size={20} />, description: 'Import repositories, issues, and documentation', active: false },
  { id: 'gmail', name: 'Gmail', icon: <Mail size={20} />, description: 'Import email threads and attachments', active: false },
  { id: 'notion', name: 'Notion', icon: <NotionIcon size={20} />, description: 'Import pages, databases, and wikis', active: false },
  { id: 'dropbox', name: 'Dropbox', icon: <Cloud size={20} />, description: 'Import files and folders', active: false },
  { id: 'slack', name: 'Slack', icon: <MessageCircle size={20} />, description: 'Import channel messages and threads', active: false },
  { id: 'onedrive', name: 'OneDrive', icon: <Upload size={20} />, description: 'Import files from Microsoft OneDrive', active: false },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<OnboardingStep>('welcome');
  const [fileCount, setFileCount] = useState(0);
  const [animatedCount, setAnimatedCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleConnectGoogle = async () => {
    setStep('connecting');
    try {
      const data = await api<{ url: string }>('/integrations/google/connect');
      const popup = window.open(data.url, 'google-oauth', 'width=500,height=600');

      const messageListener = async (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type === 'OAUTH_COMPLETE') {
          window.removeEventListener('message', messageListener);
          setStep('scanning');
          await scanDrive();
        }
      };

      window.addEventListener('message', messageListener);

      // Fallback polling just in case popup closes without message
      const interval = setInterval(async () => {
        try {
          if (popup?.closed) {
            clearInterval(interval);
            window.removeEventListener('message', messageListener);
            if (step === 'connecting') {
              setStep('scanning');
              await scanDrive();
            }
          }
        } catch {
          clearInterval(interval);
        }
      }, 1000);
    } catch (err) {
      setError('Failed to connect. Please try again.');
      setStep('welcome');
    }
  };

  const scanDrive = async () => {
    try {
      // Fetch file count
      const filesData = await api<{ documents: Array<unknown>; next_page_token: string | null }>('/integrations/google/files');
      const count = filesData.documents.length;
      setFileCount(count);

      // Animate count up
      let current = 0;
      const step = Math.max(1, Math.floor(count / 30));
      const counterInterval = setInterval(() => {
        current = Math.min(current + step, count);
        setAnimatedCount(current);
        if (current >= count) clearInterval(counterInterval);
      }, 30);

      // Import files
      if (count > 0) {
        const fileIds = filesData.documents.map((d: any) => d.external_id);
        await api('/integrations/google/import', {
          method: 'POST',
          body: { file_ids: fileIds },
        });
      }

      setTimeout(() => setStep('done'), 1500);
    } catch {
      setStep('done');
    }
  };

  const handleSkip = () => {
    localStorage.setItem('conduit_onboarded', 'true');
    router.push('/home');
  };

  const handleFinish = () => {
    localStorage.setItem('conduit_onboarded', 'true');
    router.push('/home');
  };

  return (
    <div
      className="flex-1 flex items-center justify-center px-4"
      style={{ backgroundColor: 'var(--bg)' }}
    >
      <div className="w-full max-w-lg">
        {/* Step 1: Welcome */}
        {step === 'welcome' && (
          <div className="flex flex-col items-center text-center">
            <div className="mb-6 opacity-50">
              <FlowLine variant="curved" length={180} animated />
            </div>

            <h1 className="text-display-lg mb-2" style={{ color: 'var(--text-primary)' }}>
              Welcome to Conduit
            </h1>
            <p className="text-body mb-8" style={{ color: 'var(--text-secondary)' }}>
              Connect your knowledge to begin.
            </p>

            {error && (
              <div className="text-body mb-4 px-3 py-2 rounded-lg w-full" style={{ backgroundColor: 'var(--danger-subtle)', color: 'var(--danger)' }}>
                {error}
              </div>
            )}

            <div className="w-full flex flex-col gap-1">
              {connectors.map((connector) => (
                <div
                  key={connector.id}
                  className="flex items-center gap-3 px-4 py-3 rounded-xl transition-colors"
                  style={{
                    backgroundColor: connector.active ? 'var(--surface)' : 'transparent',
                    border: connector.active ? '1px solid var(--border)' : '1px solid transparent',
                    opacity: connector.active ? 1 : 0.5,
                  }}
                >
                  <span style={{ color: connector.active ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>
                    {connector.icon}
                  </span>
                  <div className="flex-1 text-left">
                    <p className="text-body-medium" style={{ color: 'var(--text-primary)' }}>{connector.name}</p>
                    <p className="text-caption" style={{ color: 'var(--text-tertiary)' }}>{connector.description}</p>
                  </div>
                  {connector.active ? (
                    <Button variant="primary" size="compact" onClick={handleConnectGoogle}>
                      Connect
                    </Button>
                  ) : (
                    <span className="text-micro px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--bg-subtle)', color: 'var(--text-tertiary)' }}>
                      Coming soon
                    </span>
                  )}
                </div>
              ))}
            </div>

            <button
              onClick={handleSkip}
              className="mt-6 text-body cursor-pointer transition-colors"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Skip for now
            </button>
          </div>
        )}

        {/* Step 2: Connecting / Scanning */}
        {(step === 'connecting' || step === 'scanning') && (
          <div className="flex flex-col items-center text-center">
            <div className="mb-8">
              <FlowLine variant="vertical" length={60} animated />
            </div>

            <div className="flex flex-col gap-4">
              {/* Line 1 */}
              <div className="flex items-center gap-3">
                {step === 'connecting' ? (
                  <Loader2 size={16} className="animate-spin" style={{ color: 'var(--accent)' }} />
                ) : (
                  <Check size={16} style={{ color: 'var(--success)' }} />
                )}
                <span className="text-body" style={{ color: 'var(--text-primary)' }}>
                  {step === 'connecting' ? 'Connecting to Google Drive...' : 'Connected to Google Drive'}
                </span>
              </div>

              {/* Line 2 */}
              {step === 'scanning' && (
                <div className="flex items-center gap-3">
                  <Loader2 size={16} className="animate-spin" style={{ color: 'var(--accent)' }} />
                  <span className="text-body" style={{ color: 'var(--text-primary)' }}>
                    Found <span className="mono" style={{ color: 'var(--accent)' }}>{animatedCount}</span> files
                  </span>
                </div>
              )}

              {/* Line 3 */}
              {step === 'scanning' && animatedCount >= fileCount && fileCount > 0 && (
                <div className="flex items-center gap-3">
                  <Loader2 size={16} className="animate-spin" style={{ color: 'var(--accent)' }} />
                  <span className="text-body" style={{ color: 'var(--text-primary)' }}>
                    Preparing your knowledge...
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Done */}
        {step === 'done' && (
          <div className="flex flex-col items-center text-center">
            <div className="mb-6">
              <FlowLine variant="curved" length={180} animated={false} />
            </div>

            <div className="w-10 h-10 rounded-full flex items-center justify-center mb-4" style={{ backgroundColor: 'var(--success-subtle)' }}>
              <Check size={20} style={{ color: 'var(--success)' }} />
            </div>

            <h2 className="text-display-sm mb-2" style={{ color: 'var(--text-primary)' }}>
              Your knowledge is ready
            </h2>
            <p className="text-body mb-6" style={{ color: 'var(--text-secondary)' }}>
              {fileCount > 0
                ? `${fileCount} files imported from Google Drive. Create your first conversation to start asking questions.`
                : 'Google Drive connected. Start by creating a conversation.'}
            </p>

            <Button variant="primary" size="large" onClick={handleFinish}>
              Continue to Dashboard
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
