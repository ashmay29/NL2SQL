export interface HealthResponse {
  status: string;
  timestamp: string;
  services: Record<string, string>;
}

export interface SchemaInfo {
  database: string;
  tables: Record<string, any>;
  relationships: any[];
  version: string;
  extracted_at: string;
}

export interface NL2IRRequest {
  query_text: string;
  conversation_id?: string;
  database_id?: string;
}

export interface NL2IRResponse {
  ir: Record<string, any>;
  confidence: number;
  ambiguities: any[];
  questions: string[];
  conversation_id: string;
}

export interface IR2SQLRequest {
  ir: Record<string, any>;
}

export interface IR2SQLResponse {
  sql: string;
  params: Record<string, any>;
}

export interface NL2SQLRequest {
  query_text: string;
  conversation_id?: string;
  database_id?: string;
  use_cache?: boolean;
}

export interface NL2SQLResponse {
  original_question: string;
  resolved_question: string;
  sql: string;
  ir?: Record<string, any>;
  confidence: number;
  ambiguities: any[];
  explanations: string[];
  suggested_fixes: string[];
  cache_hit: boolean;
  execution_time: number;
}

export interface EmbeddingUploadPayload {
  schema_fingerprint: string;
  dim: number;
  nodes: Array<{ id: string; vec: number[] }>;
}

export interface EmbeddingUploadResponse {
  schema_fingerprint: string;
  nodes_count: number;
  dim: number;
  message: string;
}
