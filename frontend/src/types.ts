export type DocumentStatus =
  | 'pending'
  | 'processing'
  | 'indexed'
  | 'error'
  | 'requires_ocr'

export interface DocumentOut {
  document_id: string
  filename: string
  status: DocumentStatus
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
