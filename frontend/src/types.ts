export type DocumentStatus =
  | 'pending'
  | 'processing'
  | 'ocr_processing'
  | 'indexed'
  | 'error'
  | 'requires_ocr'

export type SourceType = 'pdf' | 'docx'

export interface DocumentOut {
  document_id: string
  filename: string
  source_type: SourceType
  status: DocumentStatus
  used_ocr: boolean
  uploaded_at: string
  page_count: number | null
  chunk_count: number | null
  error_message: string | null
}

export interface UploadResult {
  document_id: string | null
  filename: string
  accepted: boolean
  reason: string | null
}

export interface UploadResponse {
  results: UploadResult[]
}

export interface Citation {
  document_id: string
  filename: string
  page: number
}

export interface ChatApiMessage {
  role: 'user' | 'assistant'
  content: string
}
