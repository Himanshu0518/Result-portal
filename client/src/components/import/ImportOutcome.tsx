import { CheckCircle2, RotateCcw } from 'lucide-react'
import ImportErrorsTable from '@/components/import/ImportErrorsTable'
import Notice from '@/components/Notice'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import type { ImportResult } from '@/lib/api'
import { formatFileSize, formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'

function StatCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string
  value: string
  hint: string
  accent?: string
}) {
  return (
    <Card className="p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn('mt-2 text-2xl font-semibold tracking-tight tabular', accent)}>{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{hint}</p>
    </Card>
  )
}

type ImportOutcomeProps = {
  result: ImportResult
  onReset: () => void
}

export default function ImportOutcome({ result, onReset }: ImportOutcomeProps) {
  const { summary } = result
  const imported = summary.new_count + summary.updated_count + summary.unchanged_count
  const isReupload =
    summary.new_count === 0 && summary.updated_count === 0 && summary.unchanged_count > 0
  const acceptedRate = summary.rows_read > 0 ? (imported / summary.rows_read) * 100 : 0

  return (
    <div className="animate-fade-up" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <CheckCircle2 className="h-5 w-5" />
            </span>
            <h2 className="text-lg font-semibold">Import complete</h2>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{summary.filename}</span> ·{' '}
            {formatFileSize(summary.size_bytes)} · {formatNumber(summary.rows_read)} rows read
          </p>
        </div>

        <Button type="button" variant="outline" size="sm" onClick={onReset}>
          <RotateCcw className="h-3.5 w-3.5" />
          Import another file
        </Button>
      </div>

      {isReupload && (
        <Notice tone="warning" title="This exact file has been imported before" className="mt-5">
          All {formatNumber(summary.unchanged_count)} valid rows already match the stored records,
          so nothing was added or changed. Re-uploading never deletes students who are missing from
          the new file.
        </Notice>
      )}

      {summary.encoding_note && (
        <Notice tone="info" title="The file encoding was guessed" className="mt-4">
          {summary.encoding_note}. The file was not valid UTF-8, so it was read with a fallback
          encoding. Spot-check a few accented names in the student directory.
        </Notice>
      )}

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Rows read"
          value={formatNumber(summary.rows_read)}
          hint="Blank lines are skipped and not counted."
        />
        <StatCard
          label="Imported"
          value={formatNumber(imported)}
          hint={`${formatNumber(summary.new_count)} new · ${formatNumber(summary.updated_count)} updated · ${formatNumber(summary.unchanged_count)} unchanged`}
          accent="text-emerald-600"
        />
        <StatCard
          label="Rejected"
          value={formatNumber(summary.rejected_count)}
          hint={`${formatNumber(summary.problem_count)} ${summary.problem_count === 1 ? 'problem' : 'problems'} found across these rows.`}
          accent={summary.rejected_count > 0 ? 'text-rose-600' : undefined}
        />
        <StatCard
          label="Accepted"
          value={`${acceptedRate.toFixed(1)}%`}
          hint="Share of the file's rows that were usable."
        />
      </div>

      <p className="mt-4 text-sm text-muted-foreground">
        {summary.rejected_count > 0 ? (
          <>
            <span className="font-medium text-foreground">{formatNumber(imported)}</span> students
            are available in the directory. Fix the rejected rows and upload the file again — valid
            students will be updated, not duplicated.
          </>
        ) : (
          <>
            All <span className="font-medium text-foreground">{formatNumber(imported)}</span>{' '}
            students are now available in the directory.
          </>
        )}
      </p>

      <div className="mt-8">
        <ImportErrorsTable
          importId={summary.id}
          rejectedCount={summary.rejected_count}
          problemCount={summary.problem_count}
        />
      </div>
    </div>
  )
}
