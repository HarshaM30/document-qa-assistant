// Response shapes from the backend (mirrors backend/src/docqa/schemas).

export interface User {
  id: string
  email: string
  created_at: string
}

export interface Workspace {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export type DocumentStatus = 'queued' | 'processing' | 'ready' | 'failed'
export type JobStatus = 'queued' | 'running' | 'retrying' | 'done' | 'failed'
export type JobStage = 'queued' | 'parsing' | 'chunking' | 'embedding' | 'indexing' | 'done'

export interface IngestionJob {
  id: string
  status: JobStatus
  stage: JobStage
  progress: number
  attempts: number
  max_attempts: number
  error: string | null
  stage_seconds: Record<string, number>
  pages_per_minute: number | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface DocumentInfo {
  id: string
  title: string
  filename: string
  source_type: string
  status: DocumentStatus
  is_library: boolean
  size_bytes: number
  page_count: number | null
  ticker: string | null
  company_name: string | null
  fiscal_year: number | null
  created_at: string
  job: IngestionJob | null
}

export interface Citation {
  marker: number
  chunk_id: string
  document_id: string
  document_title: string
  section_title: string
  item_code: string | null
  page_start: number | null
  page_end: number | null
}

export interface Passage {
  chunk_id: string
  document_id: string
  document_title: string
  section_title: string
  item_code: string | null
  page_start: number | null
  page_end: number | null
  is_table: boolean
  text: string
}

export type StoredAnswerStatus = 'complete' | 'stopped' | 'failed'

export interface StoredAnswer {
  id: string
  text: string
  status: StoredAnswerStatus
  refused: boolean
  citations: Citation[]
  latency_ms: number | null
  created_at: string
}

/** A question saved on the server, with its answer (null if none was saved). */
export interface StoredTurn {
  question_id: string
  question: string
  asked_at: string
  answer: StoredAnswer | null
}
