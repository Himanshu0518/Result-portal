/**
 * Typed client for the Result Portal API.
 *
 * Every endpoint answers with the same envelope:
 *   success: { success: true, message?, data, meta? }
 *   failure: { success: false, error: { code, message, details? } }
 */

export type ErrorDetail = { field: string; message: string }

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: ErrorDetail[]

  constructor(message: string, status: number, code: string, details: ErrorDetail[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export type PaginatedMeta = {
  page: number
  page_size: number
  total: number
}

export type Envelope<T> = {
  success: true
  message?: string
  data: T
  meta?: PaginatedMeta
}

type ErrorEnvelope = {
  success?: false
  error?: {
    code?: string
    message?: string
    details?: ErrorDetail[]
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<Envelope<T>> {
  let response: Response

  try {
    response = await fetch(`/api${path}`, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(
      'Could not reach the server. Check your connection and try again.',
      0,
      'NETWORK_ERROR',
    )
  }

  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const error = (payload as ErrorEnvelope | null)?.error
    throw new ApiError(
      error?.message ?? `The request failed (HTTP ${response.status}).`,
      response.status,
      error?.code ?? 'REQUEST_FAILED',
      error?.details ?? [],
    )
  }

  const envelope = payload as Envelope<T> | null
  if (!envelope || envelope.success !== true) {
    throw new ApiError(
      'The server returned an unexpected response. Please try again.',
      response.status,
      'BAD_RESPONSE',
    )
  }

  return envelope
}

/* -------------------------------------------------------------------------- */
/* Imports                                                                    */
/* -------------------------------------------------------------------------- */

export type ImportRowError = {
  id: number
  import_id: number
  row_number: number
  student_id: string | null
  field: string | null
  code: string
  message: string
}

export type ImportSummary = {
  id: number
  filename: string
  file_sha256: string
  size_bytes: number
  rows_read: number
  new_count: number
  updated_count: number
  unchanged_count: number
  rejected_count: number
  problem_count: number
  encoding_note: string | null
  created_at: string
}

export type ImportResult = {
  summary: ImportSummary
  first_errors: ImportRowError[]
}

export function uploadCsv(file: File) {
  const formData = new FormData()
  formData.append('file', file)

  return request<ImportResult>('/imports', {
    method: 'POST',
    body: formData,
  })
}

export function fetchImportErrors(
  importId: number,
  page: number,
  pageSize: number,
  signal?: AbortSignal,
) {
  const search = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })

  return request<ImportRowError[]>(`/imports/${importId}/errors?${search.toString()}`, { signal })
}

/* -------------------------------------------------------------------------- */
/* Students                                                                   */
/* -------------------------------------------------------------------------- */

export type StudentListItem = {
  student_id: string
  full_name: string
  email: string
  grade_level: number
  section: string
  total: number
  percentage: number
  grade: string
  pass_fail: string
}

export type StudentDetail = StudentListItem & {
  date_of_birth: string
  maths: number
  science: number
  english: number
  social_studies: number
  second_language: number
  last_import_id: number | null
  created_at: string
  updated_at: string
}

export type StudentQuery = {
  q?: string
  gradeLevel?: number
  page: number
  pageSize: number
}

export function fetchStudents(params: StudentQuery, signal?: AbortSignal) {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.gradeLevel) search.set('grade_level', String(params.gradeLevel))
  search.set('page', String(params.page))
  search.set('page_size', String(params.pageSize))

  return request<StudentListItem[]>(`/students?${search.toString()}`, { signal })
}

export function fetchStudent(studentId: string, signal?: AbortSignal) {
  return request<StudentDetail>(`/students/${encodeURIComponent(studentId)}`, { signal })
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error && error.message) return error.message
  return 'Something went wrong. Please try again.'
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  return new ApiError(getErrorMessage(error), 0, 'UNKNOWN_ERROR')
}
