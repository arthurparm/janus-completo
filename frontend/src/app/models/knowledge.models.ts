import { Citation } from './chat.models';

// Knowledge Health
export interface KnowledgeHealthResponse {
  status: string;
  neo4j_connected: boolean;
  qdrant_connected: boolean;
  circuit_breaker_open: boolean;
  total_nodes: number;
  total_relationships: number;
}

export interface KnowledgeHealthDetailedResponse {
  timestamp: string;
  overall_status: string;
  basic_health: KnowledgeHealthResponse;
  detailed_status: {
    offline: boolean;
    circuit_breaker_open: boolean;
    metrics: Record<string, unknown>;
  };
  monitoring: Record<string, unknown> | null;
  recommendations: string[];
}

export interface ContextInfo { [key: string]: unknown }
export interface WebSearchResult { [key: string]: unknown }
export interface WebCacheStatus { [key: string]: unknown }

// Documents / RAG
export interface UploadResponse { doc_id: string; chunks: number; status: string; consolidation?: Record<string, unknown> | null }
export interface DocListItem { doc_id: string; file_name?: string; chunks: number; conversation_id?: string; last_index_ts?: number }
export interface DocListResponse { items: DocListItem[] }
export interface DocSearchResultItem {
  id: string;
  score: number;
  doc_id: string;
  file_name?: string;
  index?: number;
  timestamp?: number;
  [key: string]: unknown;
}

export interface DocSearchResponse {
  results: DocSearchResultItem[];
}

export interface KnowledgeSpace {
  knowledge_space_id: string;
  user_id: string;
  name: string;
  source_type: string;
  source_id?: string | null;
  edition_or_version?: string | null;
  language?: string | null;
  parent_collection_id?: string | null;
  description?: string | null;
  consolidation_status: string;
  consolidation_summary?: string | null;
  last_consolidated_at?: string | null;
}

export interface KnowledgeSpaceStatus extends KnowledgeSpace {
  documents_total: number;
  documents_indexed: number;
  documents_processing: number;
  documents_queued: number;
  documents_failed: number;
  chunks_total: number;
  chunks_indexed: number;
  progress: number;
}

export interface KnowledgeSpaceCreateRequest {
  name: string;
  user_id?: string;
  source_type?: string;
  source_id?: string;
  edition_or_version?: string;
  language?: string;
  parent_collection_id?: string;
  description?: string;
}

export interface KnowledgeSpaceListResponse {
  items: KnowledgeSpace[];
}

export interface KnowledgeSpaceAttachRequest {
  user_id?: string;
  source_type?: string;
  source_id?: string;
  edition_or_version?: string;
  language?: string;
  parent_collection_id?: string;
}

export interface KnowledgeSpaceConsolidationResponse {
  message: string;
  stats: {
    status: string;
    task_id?: string;
    status_url?: string;
    [key: string]: unknown;
  };
}

export interface KnowledgeSpaceQueryResponse {
  answer: string;
  mode_used: string;
  base_used: string;
  source_scope: Record<string, unknown>;
  citations: Citation[];
  confidence: number;
  gaps_or_conflicts: string[];
}

export interface RagSearchResponse {
  answer: string;
  citations: Citation[];
}

export interface RagHybridResponse {
  answer: string;
  citations: Citation[];
}

// Knowledge Graph
export interface KnowledgeStats {
  total_nodes: number
  total_relationships: number
  labels: Record<string, number>
}

export interface EntityRelationshipItem {
  related_entity: string
  related_type: string
  relationship: string
  distance: number
}

export interface EntityRelationshipsResponse {
  results: EntityRelationshipItem[]
}

export interface GraphNode {
  data: {
    id: string;
    label: string;
    type?: string;
    color?: string;
  };
}

export interface GraphEdge {
  data: {
    source: string;
    target: string;
    label: string;
  };
}

export interface ContextualGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

