// TypeScript interfaces mirroring all backend schemas

export interface User {
  id: string;
  email: string;
  username: string | null;
  full_name: string;
  avatar_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  password: string;
  username?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type DocumentStatus =
  | 'IMPORTED'
  | 'PARSING'
  | 'CHUNKING'
  | 'EMBEDDING'
  | 'INDEXED'
  | 'FAILED';

export type DocumentProvider = 'google_drive' | 'local' | string;

export interface Document {
  id: string;
  title: string;
  provider: DocumentProvider;
  status: DocumentStatus;
  mime_type: string;
  external_id: string | null;
  user_id: string;
  integration_id: string | null;
  storage_path: string | null;
  file_size: number | null;
  checksum: string | null;
  processed_content: string | null;
  metadata_: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends Document {
  chunk_count?: number;
  embedding_status?: string;
  embedding_model?: string;
  index_status?: string;
  last_indexed_at?: string;
  conversation_count?: number;
  pipeline_stages?: PipelineStage[];
}

export interface PipelineStage {
  name: string;
  status: 'completed' | 'active' | 'pending' | 'failed';
  completed_at?: string;
  error?: string;
}

export interface DocumentListItem {
  id: string;
  title: string;
  provider: DocumentProvider;
  status: DocumentStatus;
  mime_type: string;
  created_at: string;
}

export interface NormalizedDocument {
  id: string | null;
  external_id: string;
  title: string;
  provider: string;
  mime_type: string;
  modified_at: string;
  size: number | null;
  web_view_link: string;
  is_folder: boolean;
}

export interface DocumentListResponse {
  documents: NormalizedDocument[];
  next_page_token: string | null;
}

export interface DocumentImportRequest {
  file_ids: string[];
}

export interface DocumentImportResponse {
  imported: number;
  failed: number;
  errors: Array<Record<string, string>>;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  document_count?: number;
  last_message?: string | null;
  is_pinned?: boolean;
  messages?: Message[];
  documents?: ConversationDocument[];
}

export interface ConversationCreate {
  title: string;
}

export interface ConversationUpdate {
  title?: string;
  is_pinned?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: {
    sources?: Citation[];
  };
  created_at: string;
}

export interface ConversationDocument {
  document_id: string;
  title: string;
  provider: DocumentProvider;
  status: DocumentStatus;
  attached_at: string;
  mime_type?: string;
}

export interface Citation {
  document_title: string;
  provider: string;
  chunk_index: number;
  score: number;
}

export interface RetrievedChunk {
  score: number;
  document_title: string;
  content: string;
}

export interface ChatQueryRequest {
  query: string;
  top_k?: number;
  provider?: string;
  mime_type?: string;
}

export interface ChatQueryResponse {
  answer: string;
  sources: Citation[];
  retrieved_chunks: RetrievedChunk[];
}

export interface SearchResponse {
  chunks: RetrievedChunk[];
}

export interface SSEEvent {
  event: string;
  data: string;
}

export interface StreamMetadata {
  sources: Citation[];
  retrieved_chunks: RetrievedChunk[];
}

export interface StreamChunk {
  text: string;
}

export type IntegrationStatus = 'CONNECTED' | 'DISCONNECTED' | 'NEEDS_REAUTHORIZATION';

export interface Integration {
  id: string;
  provider: string;
  display_name: string;
  status: IntegrationStatus;
  created_at?: string;
  updated_at?: string;
}

export interface IntegrationStatusResponse {
  status: IntegrationStatus;
  integration_id?: string;
  display_name?: string;
}

// UI-level types

export type ThemeMode = 'light' | 'dark' | 'system';

export interface CommandPaletteItem {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  category: 'conversation' | 'document' | 'action' | 'navigation' | 'setting';
  action: () => void;
}
