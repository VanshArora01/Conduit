'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Upload, Cloud, FileText, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

export default function AddKnowledgePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'upload' | 'drive'>('upload');
  const [uploadState, setUploadState] = useState<'idle' | 'importing' | 'success'>('idle');
  const [progressSteps, setProgressSteps] = useState<number>(0);
  
  const [isConnectingDrive, setIsConnectingDrive] = useState(false);
  const [driveSuccess, setDriveSuccess] = useState(false);
  const [driveError, setDriveError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadState('importing');
    setProgressSteps(0);

    try {
      setProgressSteps(1); // Uploaded / Downloaded
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api<{ status: string; document_id: string }>(
        '/documents/upload',
        {
          method: 'POST',
          body: formData,
        }
      );
      
      const documentId = response.document_id;
      let attempts = 0;
      const maxAttempts = 60;
      
      const pollInterval = setInterval(async () => {
        attempts++;
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setUploadState('idle');
          alert('Indexing timed out. Please try again.');
          return;
        }
        
        try {
          const statusRes = await api<{ document_id: string; status: string }>(
            `/documents/${documentId}/status`
          );
          
          const status = statusRes.status;
          
          if (status === 'IMPORTED') {
            setProgressSteps(1);
          } else if (status === 'PARSING') {
            setProgressSteps(2);
          } else if (status === 'CHUNKING') {
            setProgressSteps(4);
          } else if (status === 'EMBEDDING') {
            setProgressSteps(5);
          } else if (status === 'INDEXED') {
            clearInterval(pollInterval);
            setProgressSteps(6);
            setTimeout(() => {
              setUploadState('success');
              setTimeout(() => {
                router.push('/home');
              }, 1500);
            }, 500);
          } else if (status === 'FAILED') {
            clearInterval(pollInterval);
            setUploadState('idle');
            alert('Indexing failed. Please check the file content.');
          }
        } catch (pollErr) {
          console.error('Error polling status:', pollErr);
        }
      }, 1000);
      
    } catch (err: any) {
      console.error(err);
      setUploadState('idle');
      alert(`Upload failed: ${err.message || err}`);
    }
  };

  const handleConnectGoogle = async () => {
    setIsConnectingDrive(true);
    setDriveError(null);
    try {
      const data = await api<{ url: string }>('/integrations/google/connect');
      const popup = window.open(data.url, 'google-oauth', 'width=500,height=600');

      const messageListener = async (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data?.type === 'OAUTH_COMPLETE') {
          window.removeEventListener('message', messageListener);
          setDriveSuccess(true);
          setTimeout(() => router.push('/home'), 1500);
        }
      };

      window.addEventListener('message', messageListener);

      const interval = setInterval(async () => {
        try {
          if (popup?.closed) {
            clearInterval(interval);
            window.removeEventListener('message', messageListener);
            if (!driveSuccess) {
              // Assume if it closed without message it failed or was cancelled
              setDriveError("Authentication window was closed before completion.");
              setIsConnectingDrive(false);
            }
          }
        } catch {
          clearInterval(interval);
        }
      }, 1000);
    } catch (err) {
      console.error(err);
      setDriveError("Failed to initialize Google Drive integration. Please check your connection and try again.");
      setIsConnectingDrive(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto w-full max-w-4xl mx-auto px-8 py-12">
      <div className="mb-10">
        <h1 className="text-2xl font-medium tracking-tight text-[var(--foreground)] mb-1">Add Knowledge</h1>
        <p className="text-sm text-[var(--muted-fg)]">Expand your workspace's intelligence with new documents.</p>
      </div>

      <div className="flex items-center gap-6 mb-8 border-b border-[var(--border)]">
        <button 
          onClick={() => setActiveTab('upload')}
          className={`pb-3 text-sm font-medium transition-colors relative ${activeTab === 'upload' ? 'text-[var(--foreground)]' : 'text-[var(--muted-fg)] hover:text-[var(--foreground)]'}`}
        >
          Upload Local Files
          {activeTab === 'upload' && (
            <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--foreground)]" />
          )}
        </button>
        <button 
          onClick={() => setActiveTab('drive')}
          className={`pb-3 text-sm font-medium transition-colors relative ${activeTab === 'drive' ? 'text-[var(--foreground)]' : 'text-[var(--muted-fg)] hover:text-[var(--foreground)]'}`}
        >
          Google Drive Integration
          {activeTab === 'drive' && (
            <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--foreground)]" />
          )}
        </button>
      </div>

      <div className="flex-1 flex flex-col">
        {activeTab === 'upload' ? (
          <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-[var(--border-strong)] rounded-xl bg-[var(--surface)] hover:bg-[var(--surface-hover)] transition-colors cursor-pointer group p-12 min-h-[400px]">
            {uploadState === 'success' ? (
              <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center text-center">
                <CheckCircle2 size={48} className="text-[#00FF85] mb-4" />
                <h3 className="text-lg font-medium text-[var(--foreground)]">Ready</h3>
                <p className="text-sm text-[var(--muted-fg)] mt-2">Knowledge added successfully.</p>
              </motion.div>
            ) : uploadState === 'importing' ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col text-left w-full max-w-sm">
                <div className="flex items-center gap-3 mb-6 text-sm font-medium text-[var(--foreground)]">
                  <Loader2 size={16} className="animate-spin text-[var(--accent)]" />
                  <span>Importing...</span>
                </div>
                
                <div className="flex flex-col gap-3 text-sm font-mono text-[var(--muted-fg)]">
                  {['Downloaded', 'Parsed', 'Cleaned', 'Chunked', 'Embedded', 'Stored'].map((stepName, idx) => (
                    <div key={stepName} className="flex items-center gap-3">
                      {progressSteps > idx ? (
                        <CheckCircle2 size={14} className="text-[#00FF85]" />
                      ) : progressSteps === idx ? (
                        <Loader2 size={14} className="animate-spin text-[var(--accent)]" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-[var(--border-strong)] opacity-50" />
                      )}
                      <span className={progressSteps > idx ? 'text-[var(--foreground)]' : progressSteps === idx ? 'text-[var(--foreground)] font-medium' : 'opacity-50'}>
                        {stepName}
                      </span>
                    </div>
                  ))}
                </div>
              </motion.div>
            ) : (
              <div className="flex flex-col items-center text-center w-full h-full justify-center" onClick={handleBrowseClick}>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                  accept=".pdf,.docx,.txt,.csv,.md,.xlsx"
                />
                <div className="w-16 h-16 rounded-2xl bg-[var(--background)] border border-[var(--border)] flex items-center justify-center mb-6 group-hover:scale-105 transition-transform shadow-sm">
                  <Upload size={24} className="text-[var(--foreground)]" />
                </div>
                <h3 className="text-lg font-medium text-[var(--foreground)]">Select files to add</h3>
                <p className="text-sm text-[var(--muted-fg)] mt-2 max-w-sm mb-6">
                  PDF, Markdown, Text, or DocX. We automatically extract and vectorize the knowledge.
                </p>
                <div className="flex items-center gap-4 text-xs font-medium text-[var(--muted-fg)] opacity-60">
                  <span className="flex items-center gap-1"><Cloud size={14}/> Drag & Drop</span>
                  <span>•</span>
                  <span className="flex items-center gap-1"><FileText size={14}/> Paste</span>
                  <span>•</span>
                  <span className="flex items-center gap-1"><Upload size={14}/> Browse</span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center text-center pt-16">
            {driveSuccess ? (
              <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center text-center">
                <CheckCircle2 size={48} className="text-[#00FF85] mb-4" />
                <h3 className="text-lg font-medium text-[var(--foreground)]">✓ Google Drive Connected</h3>
                <p className="text-sm text-[var(--muted-fg)] mt-2">Your knowledge base is ready to import.</p>
              </motion.div>
            ) : driveError ? (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center text-center max-w-sm">
                <div className="w-16 h-16 rounded-2xl bg-[var(--danger)]/10 border border-[var(--danger)]/20 flex items-center justify-center mb-6">
                  <Cloud size={24} className="text-[var(--danger)]" />
                </div>
                <h3 className="text-lg font-medium text-[var(--foreground)]">Connection Failed</h3>
                <p className="text-sm text-[var(--muted-fg)] mt-2 mb-6">
                  {driveError}
                </p>
                <div className="flex gap-3 w-full">
                  <button 
                    onClick={() => setDriveError(null)}
                    className="flex-1 py-2.5 bg-[var(--surface-hover)] border border-[var(--border)] text-[var(--foreground)] rounded-md text-sm font-medium transition-colors hover:bg-[var(--surface-raised)]"
                  >
                    View Details
                  </button>
                  <button 
                    onClick={handleConnectGoogle}
                    className="flex-1 py-2.5 bg-[var(--foreground)] text-[var(--background)] rounded-md text-sm font-medium transition-opacity hover:opacity-90 shadow-sm"
                  >
                    Retry Connection
                  </button>
                </div>
              </motion.div>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-[var(--background)] border border-[var(--border)] flex items-center justify-center mb-6 shadow-sm">
                  <Cloud size={24} className="text-[#3B82F6]" />
                </div>
                <h3 className="text-lg font-medium text-[var(--foreground)]">Connect Google Drive</h3>
                <p className="text-sm text-[var(--muted-fg)] mt-2 max-w-sm mb-8">
                  Sync specific folders or files. Conduit stays updated as your knowledge base changes.
                </p>
                <button 
                  onClick={handleConnectGoogle}
                  disabled={isConnectingDrive}
                  className="flex items-center gap-2 px-6 py-3 bg-[var(--foreground)] text-[var(--background)] hover:opacity-90 disabled:opacity-50 rounded-md text-sm font-medium transition-opacity shadow-sm cursor-pointer"
                >
                  {isConnectingDrive ? (
                    <><Loader2 size={16} className="animate-spin" /> Connecting...</>
                  ) : (
                    <>Authenticate with Google <ArrowRight size={16} /></>
                  )}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
