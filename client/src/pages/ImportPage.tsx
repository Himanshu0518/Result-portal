import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { FileText, Loader2, RotateCcw, Upload, X } from 'lucide-react'
import ImportOutcome from '@/components/import/ImportOutcome'
import Notice from '@/components/Notice'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  ApiError,
  fetchImportJob,
  getErrorMessage,
  uploadCsv,
  type ImportJob,
  type ImportResult,
} from '@/lib/api'
import { formatFileSize, formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'

const POLL_INTERVAL_MS = 900

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    return 'Please choose a .csv file. Other file types cannot be imported.'
  }
  if (file.size === 0) {
    return 'That file is empty. Choose a CSV that contains student rows.'
  }
  return null
}

export default function ImportPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [job, setJob] = useState<ImportJob | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [pollWarning, setPollWarning] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)

  const processing = job !== null && job.status !== 'completed' && job.status !== 'failed'
  const busy = uploading || processing

  function chooseFile(picked: File | null) {
    if (!picked || busy) return

    const problem = validateFile(picked)
    if (problem) {
      setFile(null)
      setClientError(problem)
      setUploadError(null)
      return
    }

    setFile(picked)
    setClientError(null)
    setUploadError(null)
    setPollWarning(null)
    setResult(null)
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    chooseFile(event.target.files?.[0] ?? null)
    event.target.value = ''
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    if (busy) return
    chooseFile(event.dataTransfer.files?.[0] ?? null)
  }

  function openPicker() {
    if (!busy) fileInputRef.current?.click()
  }

  async function handleUpload() {
    if (!file || busy) return

    setUploading(true)
    setUploadError(null)
    setPollWarning(null)

    try {
      const response = await uploadCsv(file)
      setJob(response.data)
    } catch (error) {
      setUploadError(getErrorMessage(error))
    } finally {
      setUploading(false)
    }
  }

  // Poll the background job until it is completed or failed. The effect stops
  // scheduling timers as soon as a terminal status arrives.
  const jobId = job?.job_id
  const jobStatus = job?.status

  useEffect(() => {
    if (!jobId || jobStatus === 'completed' || jobStatus === 'failed') return

    let cancelled = false
    let timer: number | undefined
    let failures = 0

    async function poll() {
      try {
        const response = await fetchImportJob(jobId!)
        if (cancelled) return

        failures = 0
        setPollWarning(null)
        const next = response.data
        setJob(next)

        if (next.status === 'completed') {
          if (!next.summary) {
            setUploadError('The import finished without a summary. Please try again.')
            setJob(null)
            return
          }
          setPollWarning(null)
          setResult({ summary: next.summary, first_errors: [] })
          setFile(null)
          setJob(null)
          window.scrollTo({ top: 0, behavior: 'smooth' })
        } else if (next.status === 'failed') {
          setPollWarning(null)
          setUploadError(next.error ?? 'The import could not be completed. Please try again.')
          setJob(null)
        } else {
          timer = window.setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (error) {
        if (cancelled) return
        failures += 1

        // A missing job can never recover; keep polling through a blip.
        if (error instanceof ApiError && error.status === 404) {
          setPollWarning(null)
          setUploadError(getErrorMessage(error))
          setJob(null)
          return
        }
        if (failures >= 3) {
          setPollWarning(
            'Lost contact with the server. Still trying to reconnect — the import continues in the background.',
          )
        }
        timer = window.setTimeout(poll, POLL_INTERVAL_MS * 2)
      }
    }

    timer = window.setTimeout(poll, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [jobId, jobStatus])

  function reset() {
    setFile(null)
    setJob(null)
    setResult(null)
    setClientError(null)
    setUploadError(null)
    setPollWarning(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">Data intake</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Import students</h1>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Upload a term results CSV. Good rows go straight into the directory; problem rows are
          listed with a plain-English reason so they can be fixed and re-uploaded.
        </p>
      </div>

      {result ? (
        <div className="mt-8">
          <ImportOutcome result={result} onReset={reset} />
        </div>
      ) : (
        <div className="mt-6 grid gap-5 lg:grid-cols-3">
          <Card className="p-6 lg:col-span-2">
            {uploadError && (
              <Notice
                tone="danger"
                title="The file could not be imported"
                className="mb-5"
                action={
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleUpload}
                    disabled={uploading}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Retry
                  </Button>
                }
              >
                {uploadError}
              </Notice>
            )}

            {file ? (
              <div>
                <div className="rounded-xl border bg-muted/30 p-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border bg-card text-primary">
                      <FileText className="h-5 w-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)} · ready to import
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setFile(null)
                        setUploadError(null)
                      }}
                      disabled={busy}
                      aria-label="Remove selected file"
                      className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  {(uploading || job) && (
                    <div className="mt-4" aria-live="polite">
                      <div className="flex items-center justify-between gap-3 text-xs">
                        <span className="font-medium text-foreground">
                          {uploading
                            ? 'Uploading file…'
                            : job?.stage === 'queued'
                              ? 'Queued for processing…'
                              : job?.stage === 'saving'
                                ? 'Saving students…'
                                : 'Validating rows…'}
                        </span>
                        {job && (
                          <span className="tabular text-muted-foreground">{job.progress}%</span>
                        )}
                      </div>
                      <div
                        role="progressbar"
                        aria-label="Import progress"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={uploading ? undefined : job?.progress}
                        aria-valuetext={
                          uploading ? 'Uploading file' : job ? `${job.progress}% complete` : undefined
                        }
                        className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"
                      >
                        <div
                          className={cn(
                            'h-full rounded-full bg-primary transition-[width] duration-500 ease-out',
                            uploading && 'w-1/2 animate-pulse',
                          )}
                          style={uploading ? undefined : { width: `${job?.progress ?? 0}%` }}
                        />
                      </div>
                      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                        {uploading
                          ? 'Sending the file to the server.'
                          : job?.stage === 'saving'
                            ? 'Rows are validated. Saving students to the directory — keep this page open.'
                            : job && job.total_rows
                              ? `${formatNumber(job.processed_rows)} of ${formatNumber(job.total_rows)} rows checked. Keep this page open — it updates automatically.`
                              : 'Preparing the file for validation. Keep this page open.'}
                      </p>
                    </div>
                  )}

                  {pollWarning && (
                    <p className="mt-2 text-xs leading-relaxed text-amber-600">{pollWarning}</p>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Button type="button" onClick={handleUpload} disabled={busy}>
                    {uploading || processing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    {uploading ? 'Uploading…' : processing ? 'Import in progress…' : 'Upload and import'}
                  </Button>
                  <button
                    type="button"
                    onClick={openPicker}
                    disabled={busy}
                    className="text-xs font-medium text-muted-foreground hover:text-foreground disabled:opacity-40"
                  >
                    Choose a different file
                  </button>
                </div>

                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                  Large files are validated and saved in batches in the background. Bad rows never
                  stop the good ones from being imported.
                </p>
              </div>
            ) : (
              <div
                role="button"
                tabIndex={0}
                aria-label="Choose a CSV file"
                onClick={openPicker}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    openPicker()
                  }
                }}
                onDragOver={event => {
                  event.preventDefault()
                  if (!uploading) setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                className={cn(
                  'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-14 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  dragging
                    ? 'border-primary bg-accent/60'
                    : 'border-border hover:border-primary/40 hover:bg-accent/30',
                )}
              >
                <span
                  className={cn(
                    'flex h-12 w-12 items-center justify-center rounded-full transition-colors',
                    dragging ? 'bg-primary text-primary-foreground' : 'bg-accent text-primary',
                  )}
                >
                  <Upload className="h-5 w-5" />
                </span>
                <p className="mt-4 text-sm font-medium">
                  Drop your CSV here, or{' '}
                  <span className="text-primary underline underline-offset-2">browse</span>
                </p>
                <p className="mt-1 text-xs text-muted-foreground">CSV only · large files supported</p>
              </div>
            )}

            {clientError && (
              <Notice tone="danger" className="mt-4">
                {clientError}
              </Notice>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleInputChange}
              className="hidden"
              tabIndex={-1}
            />
          </Card>

          <Card className="h-fit p-5">
            <h2 className="text-sm font-semibold">Before you upload</h2>
            <ul className="mt-3 space-y-2.5 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                CSV saved as UTF-8, or an Excel export
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Large files are processed in batches
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Dates as YYYY-MM-DD or DD/MM/YYYY
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Marks between 0 and 100, decimals allowed
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                Re-uploading updates existing students — it never deletes them
              </li>
            </ul>

            <div className="mt-4 rounded-lg bg-muted/60 p-3">
              <p className="text-xs font-medium">Required columns</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                student_id, full_name, email, date_of_birth, grade_level, section, maths, science,
                english, social_studies, second_language
              </p>
            </div>

            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              The header can be in any order and any case. Extra columns, such as parent_phone, are
              ignored.
            </p>
          </Card>
        </div>
      )}
    </div>
  )
}
