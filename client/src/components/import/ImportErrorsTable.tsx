import { useState } from 'react'
import { AlertCircle, CheckCircle2, Download, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import Pagination from '@/components/Pagination'
import StateCard from '@/components/StateCard'
import { useApiQuery } from '@/hooks/useApiQuery'
import { fetchImportErrors, getErrorMessage, type ImportRowError } from '@/lib/api'
import { fieldLabel, formatNumber } from '@/lib/format'

const PAGE_SIZE = 25

function csvCell(value: string | number | null): string {
  let text = value === null ? '' : String(value)
  // Prevent spreadsheet formula injection in exported reports.
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`
  return `"${text.replace(/"/g, '""')}"`
}

function buildErrorCsv(errors: ImportRowError[]): string {
  const rows: (string | number | null)[][] = [['Line', 'Student ID', 'Column', 'Code', 'Problem']]

  for (const error of errors) {
    rows.push([
      error.row_number,
      error.student_id,
      fieldLabel(error.field),
      error.code,
      error.message,
    ])
  }

  return rows.map(row => row.map(csvCell).join(',')).join('\r\n')
}

type ImportErrorsTableProps = {
  importId: number
  rejectedCount: number
  problemCount: number
}

export default function ImportErrorsTable({
  importId,
  rejectedCount,
  problemCount,
}: ImportErrorsTableProps) {
  const [page, setPage] = useState(1)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const { data, meta, loading, error, refetch } = useApiQuery<ImportRowError[]>(
    `import:${importId}:errors:${page}`,
    signal => fetchImportErrors(importId, page, PAGE_SIZE, signal),
  )

  const totalProblems = meta?.total ?? problemCount

  async function downloadReport() {
    setDownloading(true)
    setDownloadError(null)

    try {
      const all: ImportRowError[] = []
      let nextPage = 1
      let total = problemCount

      while (all.length < total && nextPage <= 100) {
        const response = await fetchImportErrors(importId, nextPage, 200)
        all.push(...response.data)
        total = response.meta?.total ?? all.length
        if (response.data.length === 0) break
        nextPage += 1
      }

      const blob = new Blob([`\uFEFF${buildErrorCsv(all)}`], {
        type: 'text/csv;charset=utf-8;',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `import-${importId}-errors.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (downloadFailure) {
      setDownloadError(getErrorMessage(downloadFailure))
    } finally {
      setDownloading(false)
    }
  }

  if (rejectedCount === 0) {
    return (
      <Card className="border-emerald-200 bg-emerald-50/60">
        <div className="flex items-start gap-3 p-5">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
          <div>
            <p className="font-medium text-emerald-900">Every row was usable</p>
            <p className="mt-1 text-sm text-emerald-800/80">
              No problems were found in this file, so there is nothing to review.
            </p>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <section aria-labelledby="import-problems-heading">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="import-problems-heading" className="text-lg font-semibold">
            Rows that need attention
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            <span className="font-medium tabular text-foreground">
              {formatNumber(rejectedCount)}
            </span>{' '}
            {rejectedCount === 1 ? 'row' : 'rows'} rejected ·{' '}
            <span className="font-medium tabular text-foreground">
              {formatNumber(problemCount)}
            </span>{' '}
            {problemCount === 1 ? 'problem' : 'problems'} found
          </p>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={downloadReport}
          disabled={downloading}
        >
          {downloading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          {downloading ? 'Preparing…' : 'Download CSV'}
        </Button>
      </div>

      {downloadError && <p className="mt-2 text-xs text-rose-600">{downloadError}</p>}

      <Card className="mt-3 overflow-hidden">
        {error ? (
          <StateCard
            icon={AlertCircle}
            tone="danger"
            title="Could not load the problem rows"
            description={error.message}
            action={
              <Button type="button" variant="outline" size="sm" onClick={refetch}>
                Try again
              </Button>
            }
          />
        ) : loading && !data ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-sm">
              <thead className="border-b bg-muted/50">
                <tr>
                  {['Line', 'Student ID', 'Column', 'Problem', 'Code'].map(column => (
                    <th
                      key={column}
                      className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {Array.from({ length: 6 }, (_, index) => (
                  <tr key={index}>
                    <td className="px-4 py-3">
                      <Skeleton className="h-3 w-8" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-3 w-20" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-3 w-24" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-3 w-64" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton className="h-3 w-28" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-sm">
                <caption className="sr-only">
                  Rows rejected during this import, with the reason for each.
                </caption>
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="w-16 px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Line
                    </th>
                    <th className="w-32 px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Student ID
                    </th>
                    <th className="w-36 px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Column
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Problem
                    </th>
                    <th className="w-40 px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Code
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {(data ?? []).map(problem => (
                    <tr key={problem.id} className="align-top transition-colors hover:bg-muted/30">
                      <td className="px-4 py-3 font-mono text-xs tabular text-muted-foreground">
                        {problem.row_number}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">
                        {problem.student_id ?? <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {fieldLabel(problem.field)}
                      </td>
                      <td className="px-4 py-3 leading-relaxed">{problem.message}</td>
                      <td className="px-4 py-3">
                        <Badge tone="outline" className="font-mono text-[10px] tracking-tight">
                          {problem.code}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="border-t px-4 py-3">
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={totalProblems}
                onPageChange={setPage}
                disabled={loading}
              />
            </div>
          </>
        )}
      </Card>
    </section>
  )
}
