'use client';

import { useState, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiStream } from '@/lib/api';
import type { Message, Citation, RetrievedChunk } from '@/types';
import { toast } from '@/components/ui/toast';

interface UseChatStreamOptions {
  conversationId: string;
  onSuccess?: () => void;
}

export type StreamStatus = 
  | 'idle' 
  | 'planning' 
  | 'retrieving' 
  | 'reranking' 
  | 'building_prompt' 
  | 'calling_llm' 
  | 'generating' 
  | 'error' 
  | 'action_required';

export function useChatStream({ conversationId, onSuccess }: UseChatStreamOptions) {
  const queryClient = useQueryClient();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('idle');
  const [heartbeatText, setHeartbeatText] = useState('');
  const [currentSources, setCurrentSources] = useState<Citation[]>([]);
  const [currentRetrievedChunks, setCurrentRetrievedChunks] = useState<RetrievedChunk[]>([]);
  const [streamedAnswer, setStreamedAnswer] = useState('');
  const [debugMetadata, setDebugMetadata] = useState<any | null>(null);
  const [lastQuery, setLastQuery] = useState('');
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setStreamStatus('idle');
      setHeartbeatText('');
      setStreamedAnswer('');
      toast('Generation cancelled', 'info');
    }
  }, []);

  const sendMessage = useCallback(async (queryText: string, responseMode: string = 'AUTO') => {
    if (!queryText.trim()) return;

    // Stop any existing stream first
    stopStream();

    setIsStreaming(true);
    setStreamStatus('planning');
    setHeartbeatText('');
    setStreamedAnswer('');
    setCurrentSources([]);
    setCurrentRetrievedChunks([]);
    setDebugMetadata(null);
    setLastQuery(queryText);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Optimistically update React Query messages by adding the user's message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: queryText,
      citations: {},
      created_at: new Date().toISOString(),
    };

    queryClient.setQueryData(['conversation-messages', conversationId], (old: Message[] | undefined) => {
      return [...(old || []), userMessage];
    });

    try {
      const stream = apiStream(
        `/conversations/${conversationId}/stream`,
        { query: queryText, response_mode: responseMode },
        abortController.signal
      );

      for await (const chunk of stream) {
        if (chunk.event === 'planning') {
          setStreamStatus('planning');
          setHeartbeatText('');
        } else if (chunk.event === 'retrieving') {
          setStreamStatus('retrieving');
          setHeartbeatText('');
        } else if (chunk.event === 'reranking') {
          setStreamStatus('reranking');
          setHeartbeatText('');
        } else if (chunk.event === 'building_prompt') {
          setStreamStatus('building_prompt');
          setHeartbeatText('');
        } else if (chunk.event === 'calling_llm') {
          setStreamStatus('calling_llm');
          setHeartbeatText('');
        } else if (chunk.event === 'streaming') {
              setStreamStatus('generating');
              setHeartbeatText('');
            } else if (chunk.event === 'stage') {
              // Backward-compatible stage events: stage:planning, etc.
              try {
                const payload = JSON.parse(chunk.data);
                const stage = (payload.stage || '').replace(/^stage:/, '');
                if (stage === 'planning') setStreamStatus('planning');
                else if (stage === 'retrieving') setStreamStatus('retrieving');
                else if (stage === 'generating') setStreamStatus('generating');
                else if (stage === 'building_prompt') setStreamStatus('building_prompt');
              } catch {
                /* ignore */
              }
            } else if (chunk.event === 'heartbeat') {
          try {
            const payload = JSON.parse(chunk.data);
            setHeartbeatText(payload.status || 'Processing...');
          } catch (e) {
            console.error('Failed to parse heartbeat:', e);
          }
        } else if (chunk.event === 'metadata') {
          try {
            const meta = JSON.parse(chunk.data);
            if (meta.sources) setCurrentSources(meta.sources);
            if (meta.retrieved_chunks) setCurrentRetrievedChunks(meta.retrieved_chunks);
          } catch (e) {
            console.error('Failed to parse stream metadata:', e);
          }
        } else if (chunk.event === 'chunk') {
          setStreamStatus('generating');
          try {
            const payload = JSON.parse(chunk.data);
            if (payload.text) {
              setStreamedAnswer((prev) => prev + payload.text);
            }
          } catch (e) {
            console.error('Failed to parse stream chunk:', e);
          }
        } else if (chunk.event === 'error') {
          setStreamStatus('error');
          try {
            const payload = JSON.parse(chunk.data);
            throw new Error(payload.detail || 'Stream error');
          } catch (e: any) {
            throw new Error(e.message || 'Stream error');
          }
        } else if (chunk.event === 'action_required') {
          setStreamStatus('action_required');
          return; // Stop stream reading loop, status is action_required
        } else if (chunk.event === 'done') {
          setStreamStatus('idle');
          setHeartbeatText('');
          try {
            const payload = JSON.parse(chunk.data);
            if (payload.debug_metadata) {
              setDebugMetadata(payload.debug_metadata);
            }
          } catch (e) {
            console.error('Failed to parse stream done data:', e);
          }
          break;
        }
      }

      // Stream completed successfully. Invalidate key query to load saved messages from backend.
      await queryClient.invalidateQueries({ queryKey: ['conversation-messages', conversationId] });
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });
      
      setStreamedAnswer('');
      setCurrentSources([]);
      setCurrentRetrievedChunks([]);
      setIsStreaming(false);
      setStreamStatus('idle');
      abortControllerRef.current = null;
      
      if (onSuccess) onSuccess();
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return;
      }
      console.error('Streaming error:', err);
      toast(err.message || 'An error occurred while getting response.', 'error');
      setStreamStatus('error');
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [conversationId, queryClient, stopStream, onSuccess]);

  return {
    isStreaming,
    streamStatus,
    heartbeatText,
    streamedAnswer,
    currentSources,
    currentRetrievedChunks,
    debugMetadata,
    lastQuery,
    sendMessage,
    stopStream,
    setStreamStatus,
  };
}
