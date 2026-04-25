export type SourceType = "faq" | "rule_doc" | "entity" | "temporal" | "graph";
export type Freshness = "current" | "stale" | "expired";

export interface CitationDetail {
  source_name: string;
  source_type: SourceType;
  source_url?: string | null;
  chunk_text: string;
  edge_fact?: string | null;
  entity_name?: string | null;
  freshness?: Freshness | null;
  source_date?: string | null;
  relevance_score: number;
  image_url?: string | null;
}

export interface TimelineEvent {
  stage: string;
  took_ms: number;
  meta?: Record<string, unknown>;
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  message_id: string;
  citations: CitationDetail[];
  confidence: number;
  thumbnails: string[];
  handoff: boolean;
  timeline: TimelineEvent[];
  rag_version_id: number | null;
  scenario_id: string | null;
}

export interface ChatMessageClient {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CitationDetail[];
  confidence?: number;
  thumbnails?: string[];
  handoff?: boolean;
  timeline?: TimelineEvent[];
  rag_version_id?: number | null;
  isStreaming?: boolean;
}

export interface LLMConfig {
  model:
    | "gemini-2.5-flash-lite"
    | "gemini-2.5-flash"
    | "gemini-3.1-flash-lite"
    | "gemini-3.1-flash";
  temperature: number;
  top_p: number;
  web_search: boolean;
}

export interface ScenarioMeta {
  pit_id: string;
  title: string;
  bucket: number;
  probing_question: string;
  expected_before_substr: string;
  expected_after_substr: string;
  has_graph_seed: boolean;
  has_image_seed: boolean;
  current_state: "before" | "after" | "custom";
}

export interface RagVersion {
  id: number;
  label: string;
  source: string;
  author: string;
  created_at: string;
}

export type LayoutMode = "grid" | "columns" | "tabs" | "focus";
export type PanelId = "chat" | "code" | "qdrant" | "neo4j";
