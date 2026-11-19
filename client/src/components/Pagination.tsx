import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatNumber } from '@/lib/format'

type PageItem = number | 'gap'

function pageItems(page: number, totalPages: number): PageItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const items: PageItem[] = [1]
  const start = Math.max(2, page - 1)
  const end = Math.min(totalPages - 1, page + 1)

  if (start > 2) items.push('gap')
  for (let number = start; number <= end; number += 1) items.push(number)
  if (end < totalPages - 1) items.push('gap')
  items.push(totalPages)

  return items
}

type PaginationProps = {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  disabled?: boolean
  className?: string
}

export default function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  disabled = false,
  className,
}: PaginationProps) {
  if (total === 0) return null

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const firstRow = (page - 1) * pageSize + 1
  const lastRow = Math.min(page * pageSize, total)
  const items = pageItems(Math.min(page, totalPages), totalPages)

  return (
    <div
      className={cn(
        'flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <p className="text-xs text-muted-foreground" aria-live="polite">
        Showing{' '}
        <span className="font-medium tabular text-foreground">
          {formatNumber(firstRow)}–{formatNumber(lastRow)}
        </span>{' '}
        of <span className="font-medium tabular text-foreground">{formatNumber(total)}</span>
      </p>

      {totalPages > 1 && (
        <nav className="flex items-center gap-1" aria-label="Pagination">
          <button
            type="button"
            onClick={() => onPageChange(page - 1)}
            disabled={disabled || page <= 1}
            aria-label="Previous page"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-input bg-card text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {items.map((item, index) =>
            item === 'gap' ? (
              <span
                key={`gap-${index}`}
                className="flex h-8 w-6 items-center justify-center text-xs text-muted-foreground"
              >
                …
              </span>
            ) : (
              <button
                key={item}
                type="button"
                onClick={() => onPageChange(item)}
                disabled={disabled}
                aria-label={`Go to page ${item}`}
                aria-current={item === page ? 'page' : undefined}
                className={cn(
                  'h-8 min-w-8 rounded-lg px-2 text-xs font-medium tabular transition-colors disabled:pointer-events-none disabled:opacity-40',
                  item === page
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'border border-input bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )}
              >
                {item}
              </button>
            ),
          )}

          <button
            type="button"
            onClick={() => onPageChange(page + 1)}
            disabled={disabled || page >= totalPages}
            aria-label="Next page"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-input bg-card text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground disabled:pointer-events-none disabled:opacity-40"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </nav>
      )}
    </div>
  )
}
