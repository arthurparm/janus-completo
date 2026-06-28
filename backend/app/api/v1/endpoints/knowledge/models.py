from typing import Any

from pydantic import BaseModel


class IndexResponse(BaseModel):
    message: str
    summary: str


class KnowledgeQueryRequest(BaseModel):
    query: str
    limit: int | None = 10


class KnowledgeQueryResponse(BaseModel):
    answer: str


class CodeCitation(BaseModel):
    type: str
    name: str
    file_path: str
    line: int
    full_name: str
    relevance: int


class CodeQuestionRequest(BaseModel):
    question: str
    limit: int | None = 10
    citation_limit: int | None = 8


class CodeQuestionResponse(BaseModel):
    answer: str
    citations: list[CodeCitation]


class RelatedConceptsRequest(BaseModel):
    concept: str
    max_depth: int = 2
    limit: int = 10
    skip: int = 0


class RelatedConceptItem(BaseModel):
    concept: str
    relationship: str
    distance: int


class RelatedConceptsResponse(BaseModel):
    results: list[RelatedConceptItem]


class ReindexRequest(BaseModel):
    batch_size: int = 50
    labels: list[str] | None = None


class ReindexResponse(BaseModel):
    status: str
    updated_count: int


class EntityRelationshipsItem(BaseModel):
    related_entity: str
    related_type: str
    relationship: str
    distance: int


class EntityRelationshipsResponse(BaseModel):
    results: list[EntityRelationshipsItem]


class ClearGraphResponse(BaseModel):
    status: str
    message: str
    remaining_nodes: int


class NodeTypesResponse(BaseModel):
    types: list[str]


class KnowledgeHealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    qdrant_connected: bool
    circuit_breaker_open: bool
    total_nodes: int
    total_relationships: int


class ExperimentalKnowledgeHealthResponse(BaseModel):
    active_backend: str
    shadow_backend: str | None = None
    experimental_collection_suffix: str | None = None
    experimental_index_enabled: bool
    experimental_index_version: str
    experimental_write_dual: bool
    compare_on_read: bool
    promotion_allowed: bool
    last_build: dict[str, Any] | None = None


class ExperimentalIndexBuildRequest(BaseModel):
    domain: str
    user_id: str | None = None
    knowledge_space_id: str | None = None
    doc_id: str | None = None
    rebuild_full: bool = False
    since_ts: int | None = None
    dry_run: bool = False


class ExperimentalIndexBuildResponse(BaseModel):
    dry_run: bool
    output_dir: str
    manifest: dict[str, Any]


class ExperimentalCompareRequest(BaseModel):
    operation: str
    query: str
    limit: int = 5
    min_score: float | None = None
    session_id: str | None = None
    role: str | None = None
    memory_type: str | None = None
    origin: str | None = None
    doc_id: str | None = None
    knowledge_space_id: str | None = None
    start_ts: int | None = None
    end_ts: int | None = None
    exclude_duplicate: bool = False


class ConsolidationRequest(BaseModel):
    mode: str = "batch"
    limit: int = 10
    min_score: float = 0.0
    experience_id: str | None = None
    experience_content: str | None = None
    metadata: dict[str, Any] | None = None


class ConsolidationResponse(BaseModel):
    message: str
    stats: dict[str, Any]


class DocConsolidationRequest(BaseModel):
    doc_id: str
    limit: int = 50


class RegisterRelTypeRequest(BaseModel):
    name: str


class RegisterRelTypeResponse(BaseModel):
    status: str
    name: str


class QuarantineItem(BaseModel):
    reason: str | None
    type: str | None
    from_name: str | None
    to_name: str | None
    experience_id: str | None
    timestamp: str | None


class QuarantineListResponse(BaseModel):
    items: list[QuarantineItem]


class PromoteQuarantineRequest(BaseModel):
    from_name: str
    to_name: str
    type: str
    source_experience: str


class PromoteQuarantineResponse(BaseModel):
    status: str
    from_name: str
    to_name: str
    type: str


class KnowledgeSpaceCreateRequest(BaseModel):
    name: str
    source_type: str = "documentation"
    source_id: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None
    description: str | None = None


class KnowledgeSpaceResponse(BaseModel):
    knowledge_space_id: str
    name: str
    source_type: str
    source_id: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None
    description: str | None = None
    consolidation_status: str
    consolidation_summary: str | None = None
    last_consolidated_at: str | None = None
    sections_total: int = 0
    sections_indexed: int = 0
    sections_skipped_as_noise: int = 0
    canonical_frames_total: int = 0
    consolidation_quality_score: float = 0.0


class KnowledgeSpaceStatusResponse(KnowledgeSpaceResponse):
    documents_total: int = 0
    documents_indexed: int = 0
    documents_processing: int = 0
    documents_queued: int = 0
    documents_failed: int = 0
    chunks_total: int = 0
    chunks_indexed: int = 0
    progress: float = 0.0


class KnowledgeSpaceListResponse(BaseModel):
    items: list[KnowledgeSpaceResponse]


class AttachDocumentRequest(BaseModel):
    source_type: str | None = None
    source_id: str | None = None
    doc_role: str | None = None
    edition_or_version: str | None = None
    language: str | None = None
    parent_collection_id: str | None = None


class KnowledgeSpaceConsolidationRequest(BaseModel):
    limit_docs: int = 20


class KnowledgeSpaceQueryRequest(BaseModel):
    question: str
    mode: str = "auto"
    limit: int = 5


class KnowledgeSpaceQueryResponse(BaseModel):
    answer: str
    mode_used: str
    base_used: str
    answer_strategy: str = "scope"
    estimated_wait_seconds: int = 0
    estimated_wait_range_seconds: list[int] = []
    processing_profile: str | None = None
    processing_notice: str | None = None
    evidence_count: int = 0
    source_roles_used: list[str] = []
    source_scope: dict[str, Any]
    citations: list[dict[str, Any]]
    confidence: float
    gaps_or_conflicts: list[str]
