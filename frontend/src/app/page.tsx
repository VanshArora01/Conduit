'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ArrowRight, Loader2, Database, Network, Search, MessageSquare } from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();
  const [step, setStep] = useState<0 | 1 | 2 | 3 | 4>(0);
  
  // Interactive RAG Demo State
  const handleUpload = () => {
    setStep(1); // Uploading & Chunking
    setTimeout(() => setStep(2), 2000); // Vectorizing
    setTimeout(() => setStep(3), 4000); // Ready for QA
  };

  const handleAsk = () => {
    setStep(4); // Retrieving and Answering
  };

  return (
    <div className="min-h-screen bg-[var(--background)] flex flex-col items-center justify-center p-6 text-[var(--foreground)]">
      {/* Header/Nav */}
      <nav className="fixed top-0 w-full flex justify-between items-center px-8 py-6 z-50">
        <div className="font-mono text-sm tracking-widest font-semibold uppercase">Conduit</div>
        <button 
          onClick={() => router.push('/home')}
          className="text-sm font-medium text-[var(--muted-fg)] hover:text-[var(--foreground)] transition-colors"
        >
          Enter Workspace →
        </button>
      </nav>

      {/* Main Interactive Demo Area */}
      <div className="w-full max-w-3xl flex flex-col items-center">
        
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-medium tracking-tight mb-4">
            Think with your knowledge.
          </h1>
          <p className="text-[var(--muted-fg)] text-lg">
            Experience the RAG pipeline in real-time.
          </p>
        </div>

        {/* Demo Container */}
        <div className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-8 shadow-2xl relative overflow-hidden">
          
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div 
                key="step0"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-12"
              >
                <div 
                  onClick={handleUpload}
                  className="w-64 h-32 border border-dashed border-[var(--border-strong)] rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer hover:bg-[var(--surface-hover)] transition-colors group"
                >
                  <FileText className="w-6 h-6 text-[var(--muted-fg)] group-hover:text-[var(--foreground)] transition-colors" />
                  <span className="text-sm font-medium">Add Knowledge (PDF)</span>
                </div>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div 
                key="step1"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-12 gap-6"
              >
                <div className="flex items-center gap-4 text-sm font-mono text-[var(--muted-fg)]">
                  <FileText className="w-4 h-4" />
                  <span>Parsing document...</span>
                  <Loader2 className="w-3 h-3 animate-spin" />
                </div>
                
                <div className="w-full max-w-md grid grid-cols-4 gap-2">
                  {[...Array(8)].map((_, i) => (
                    <motion.div 
                      key={i} 
                      initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.1 }}
                      className="h-8 bg-[var(--surface-hover)] border border-[var(--border-strong)] rounded flex items-center justify-center"
                    >
                      <span className="text-[10px] font-mono text-[var(--muted-fg)]">Chunk {i+1}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div 
                key="step2"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-12 gap-6"
              >
                <div className="flex items-center gap-4 text-sm font-mono text-[var(--muted-fg)]">
                  <Network className="w-4 h-4" />
                  <span>Generating embeddings...</span>
                  <Loader2 className="w-3 h-3 animate-spin" />
                </div>
                
                <div className="flex items-center gap-6">
                  <div className="flex flex-col gap-1">
                    {[...Array(3)].map((_, i) => (
                      <motion.div key={`vec-${i}`} className="text-[10px] font-mono text-[#3B82F6] opacity-70">
                        [0.{Math.floor(Math.random() * 900) + 100}, 0.{Math.floor(Math.random() * 900) + 100}, ...]
                      </motion.div>
                    ))}
                  </div>
                  <ArrowRight className="w-4 h-4 text-[var(--border-strong)]" />
                  <Database className="w-6 h-6 text-[var(--muted-fg)]" />
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div 
                key="step3"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                className="flex flex-col w-full"
              >
                <div className="mb-6 flex items-center gap-2 text-sm text-[var(--muted-fg)]">
                  <Database className="w-4 h-4" />
                  <span>Knowledge indexed and ready.</span>
                </div>
                
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    defaultValue="What are the key takeaways from this document?"
                    className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-lg px-4 py-3 text-sm outline-none focus:border-[var(--muted-fg)]"
                  />
                  <button 
                    onClick={handleAsk}
                    className="bg-[var(--foreground)] text-[var(--background)] px-6 rounded-lg font-medium text-sm hover:opacity-90 transition-opacity"
                  >
                    Ask
                  </button>
                </div>
              </motion.div>
            )}

            {step === 4 && (
              <motion.div 
                key="step4"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="flex flex-col w-full gap-6"
              >
                {/* Pipeline visualization */}
                <div className="flex justify-between items-center text-xs font-mono text-[var(--muted-fg)] border-b border-[var(--border)] pb-4">
                  <span className="text-[var(--foreground)] flex items-center gap-2"><Search className="w-3 h-3"/> Searching Knowledge...</span>
                  <span className="text-[var(--foreground)] flex items-center gap-2"><Database className="w-3 h-3"/> Retrieving...</span>
                  <span className="text-[var(--foreground)] flex items-center gap-2"><Network className="w-3 h-3"/> Reasoning...</span>
                </div>

                {/* Similarity bars (simulated) */}
                <div className="flex gap-4 mb-4">
                  <div className="flex-1 bg-[var(--background)] border border-[var(--border)] rounded-lg p-3">
                    <div className="text-xs font-mono mb-2 text-[var(--muted-fg)]">Retrieved Chunks</div>
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] w-12 text-right">Chunk 4</span>
                        <div className="h-1 bg-[var(--surface-active)] flex-1 rounded overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: '94%' }} transition={{ duration: 1 }} className="h-full bg-[var(--foreground)]" />
                        </div>
                        <span className="text-[10px] w-8">0.94</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] w-12 text-right">Chunk 1</span>
                        <div className="h-1 bg-[var(--surface-active)] flex-1 rounded overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: '82%' }} transition={{ duration: 1.2 }} className="h-full bg-[var(--muted-fg)]" />
                        </div>
                        <span className="text-[10px] w-8">0.82</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Answer */}
                <motion.div 
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.5 }}
                  className="text-sm leading-relaxed"
                >
                  Based on the retrieved context, the document outlines three primary mechanisms for knowledge synthesis...
                </motion.div>
              </motion.div>
            )}

          </AnimatePresence>

        </div>
      </div>
    </div>
  );
}
