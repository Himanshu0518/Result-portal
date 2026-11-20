import { useEffect, useState } from 'react'
import { AlertCircle, Loader2, Search, Upload, Users, X } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { GradeBadge, ResultBadge } from '@/components/GradeBadge'
import Notice from '@/components/Notice'
import Pagination from '@/components/Pagination'
import StateCard from '@/components/StateCard'
import StudentAvatar from '@/components/StudentAvatar'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { useApiQuery } from '@/hooks/useApiQuery'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { fetchStudents, type StudentListItem } from '@/lib/api'
import { formatMark, formatNumber, formatPercent } from '@/lib/format'
import { cn } from '@/lib/utils'

const PAGE_SIZES = [10, 20, 50]

function parsePage(raw: string | null): number {
  const value = Number(raw)
  return Number.isFinite(value) && value >= 1 ? Math.floor(value) : 1
}

function parsePageSize(raw: string | null): number {
  const value = Number(raw)
  return PAGE_SIZES.includes(value) ? value : 20
}

function parseGradeLevel(raw: string | null): number | undefined {
  if (!raw) return undefined
  const value = Number(raw)
  return Number.isInteger(value) && value >= 1 && value <= 12 ? value : undefined
}

export default function StudentsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const q = (searchParams.get('q') ?? '').trim()
  const gradeLevel = parseGradeLevel(searchParams.get('grade_level'))
  const page = parsePage(searchParams.get('page'))
  const pageSize = parsePageSize(searchParams.get('page_size'))

  const [input, setInput] = useState(q)
  const debouncedInput = useDebouncedValue(input, 500)

  const hasFilters = Boolean(q) || gradeLevel !== undefined

  // Keep the box in sync when the URL changes (back button, Clear filters).
  useEffect(() => {
    setInput(previous => (previous === q ? previous : q))
  }, [q])

  // Commit the debounced search term to the URL, resetting to page 1.
  useEffect(() => {
    const nextQuery = debouncedInput.trim()
    if (nextQuery === q) return

    setSearchParams(
      previous => {
        const next = new URLSearchParams(previous)
        if (nextQuery) next.set('q', nextQuery)
        else next.delete('q')
        next.delete('page')
        return next
      },
      { replace: true },
    )
  }, [debouncedInput, q, setSearchParams])

  const { data, meta, loading, error, refetch } = useApiQuery<StudentListItem[]>(
    `students:${q}|${gradeLevel ?? 'all'}|${page}|${pageSize}`,
    signal =>
      fetchStudents({ q: q || undefined, gradeLevel, page, pageSize }, signal),
  )

  const students = data ?? []
  const total = meta?.total ?? 0

  // If the URL points past the last page (deep link, deleted filter), correct it.
  useEffect(() => {
    if (!meta) return
    const totalPages = Math.max(1, Math.ceil(meta.total / pageSize))
    if (page > totalPages) {
      setSearchParams(
        previous => {
          const next = new URLSearchParams(previous)
          next.set('page', String(totalPages))
          return next
        },
        { replace: true },
      )
    }
  }, [meta, page, pageSize, setSearchParams])

  function updateParams(updates: Record<string, string | null>) {
    setSearchParams(previous => {
      const next = new URLSearchParams(previous)
      for (const [key, value] of Object.entries(updates)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      return next
    })
  }

  function clearFilters() {
    setInput('')
    setSearchParams({})
  }

  function clearSearch() {
    setInput('')
    updateParams({ q: null, page: null })
  }

  function goToPage(nextPage: number) {
    updateParams({ page: String(nextPage) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">Directory</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Students</h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Search by name or student ID, filter by class, and open any student to see their full
            report.
          </p>
        </div>

        <Button asChild variant="outline" size="sm">
          <Link to="/import">
            <Upload className="h-3.5 w-3.5" />
            Import CSV
          </Link>
        </Button>
      </div>

      <Card className="mt-6 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <label htmlFor="student-search" className="sr-only">
              Search students by name or ID
            </label>
            <Input
              id="student-search"
              value={input}
              onChange={event => setInput(event.target.value)}
              placeholder="Search by name or student ID…"
              className="pl-9 pr-9"
              autoComplete="off"
            />
            {input && (
              <button
                type="button"
                onClick={clearSearch}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="grade-filter" className="sr-only">
              Filter by class
            </label>
            <Select
              id="grade-filter"
              value={gradeLevel ?? ''}
              onChange={event =>
                updateParams({
                  grade_level: event.target.value || null,
                  page: null,
                })
              }
              className="w-36"
            >
              <option value="">All classes</option>
              {Array.from({ length: 12 }, (_, index) => index + 1).map(grade => (
                <option key={grade} value={grade}>
                  Class {grade}
                </option>
              ))}
            </Select>

            <label htmlFor="page-size" className="sr-only">
              Rows per page
            </label>
            <Select
              id="page-size"
              value={pageSize}
              onChange={event =>
                updateParams({ page_size: event.target.value, page: null })
              }
              className="w-32"
            >
              {PAGE_SIZES.map(size => (
                <option key={size} value={size}>
                  {size} per page
                </option>
              ))}
            </Select>
          </div>
        </div>
      </Card>

      <div id="students-results" className="mt-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {loading && data && (
              <Loader2 className="mr-2 inline h-3.5 w-3.5 animate-spin align-[-2px]" />
            )}
            <span className="font-medium tabular text-foreground">{formatNumber(total)}</span>{' '}
            {total === 1 ? 'student' : 'students'}
            {q ? (
              <>
                {' '}
                matching “<span className="font-medium text-foreground">{q}</span>”
              </>
            ) : null}
            {gradeLevel ? ` in class ${gradeLevel}` : null}
          </p>

          {hasFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-xs font-medium text-primary hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>

        {error && !data ? (
          <Card>
            <StateCard
              icon={AlertCircle}
              tone="danger"
              title="Could not load students"
              description={error.message}
              action={
                <Button type="button" variant="outline" size="sm" onClick={refetch}>
                  Try again
                </Button>
              }
            />
          </Card>
        ) : (
          <>
            {error && data && (
              <Notice
                tone="danger"
                title="These results may be out of date"
                className="mb-3"
                action={
                  <Button type="button" variant="outline" size="sm" onClick={refetch}>
                    Retry
                  </Button>
                }
              >
                {error.message}
              </Notice>
            )}

            <Card className="overflow-hidden">
              {loading && !data ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-sm">
                    <thead className="border-b bg-muted/50">
                      <tr>
                        {['Student', 'Student ID', 'Class', 'Total', 'Percentage', 'Grade', 'Result'].map(
                          column => (
                            <th
                              key={column}
                              className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                            >
                              {column}
                            </th>
                          ),
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {Array.from({ length: 8 }, (_, index) => (
                        <tr key={index}>
                          <td className="px-5 py-3.5">
                            <div className="flex items-center gap-3">
                              <Skeleton className="h-8 w-8 rounded-full" />
                              <div className="space-y-1.5">
                                <Skeleton className="h-3 w-32" />
                                <Skeleton className="h-3 w-40" />
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3.5">
                            <Skeleton className="h-3 w-20" />
                          </td>
                          <td className="px-4 py-3.5">
                            <Skeleton className="h-3 w-12" />
                          </td>
                          <td className="px-4 py-3.5">
                            <Skeleton className="ml-auto h-3 w-10" />
                          </td>
                          <td className="px-4 py-3.5">
                            <Skeleton className="ml-auto h-3 w-12" />
                          </td>
                          <td className="px-4 py-3.5">
                            <Skeleton className="h-5 w-6 rounded-full" />
                          </td>
                          <td className="px-5 py-3.5">
                            <Skeleton className="ml-auto h-5 w-12 rounded-full" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : students.length === 0 ? (
                hasFilters ? (
                  <StateCard
                    icon={Search}
                    title="No students match these filters"
                    description={
                      <>
                        Nothing matched {q ? `“${q}”` : 'your search'}
                        {gradeLevel ? ` in class ${gradeLevel}` : ''}. Try a different name, ID or
                        class.
                      </>
                    }
                    action={
                      <Button type="button" variant="outline" size="sm" onClick={clearFilters}>
                        Clear filters
                      </Button>
                    }
                  />
                ) : (
                  <StateCard
                    icon={Users}
                    title="No students yet"
                    description="Import a CSV of term results to populate the directory."
                    action={
                      <Button asChild size="sm">
                        <Link to="/import">
                          <Upload className="h-3.5 w-3.5" />
                          Import students
                        </Link>
                      </Button>
                    }
                  />
                )
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[720px] text-sm">
                      <caption className="sr-only">
                        Imported students. Select a name to open that student's report.
                      </caption>
                      <thead className="border-b bg-muted/50">
                        <tr>
                          <th className="px-5 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Student
                          </th>
                          <th className="hidden px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground md:table-cell">
                            Student ID
                          </th>
                          <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Class
                          </th>
                          <th className="hidden px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground sm:table-cell">
                            Total
                          </th>
                          <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Percentage
                          </th>
                          <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Grade
                          </th>
                          <th className="px-5 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Result
                          </th>
                        </tr>
                      </thead>
                      <tbody
                        className={cn('divide-y', loading && 'opacity-60 transition-opacity')}
                        aria-busy={loading}
                      >
                        {students.map(student => (
                          <tr
                            key={student.student_id}
                            className="group transition-colors hover:bg-accent/40"
                          >
                            <td className="px-5 py-3.5">
                              <Link
                                to={`/students/${encodeURIComponent(student.student_id)}`}
                                className="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                              >
                                <StudentAvatar name={student.full_name} size="sm" />
                                <span className="min-w-0">
                                  <span className="block truncate font-medium group-hover:text-primary">
                                    {student.full_name}
                                  </span>
                                  <span className="block truncate text-xs text-muted-foreground">
                                    {student.email}
                                  </span>
                                </span>
                              </Link>
                            </td>
                            <td className="hidden px-4 py-3.5 font-mono text-xs text-muted-foreground md:table-cell">
                              {student.student_id}
                            </td>
                            <td className="px-4 py-3.5">
                              <span className="font-medium tabular">{student.grade_level}</span>
                              <span className="text-muted-foreground"> · {student.section}</span>
                            </td>
                            <td className="hidden px-4 py-3.5 text-right tabular sm:table-cell">
                              {formatMark(student.total)}
                            </td>
                            <td className="px-4 py-3.5 text-right font-medium tabular">
                              {formatPercent(student.percentage)}
                            </td>
                            <td className="px-4 py-3.5">
                              <GradeBadge grade={student.grade} />
                            </td>
                            <td className="px-5 py-3.5 text-right">
                              <ResultBadge result={student.pass_fail} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="border-t px-5 py-3">
                    <Pagination
                      page={page}
                      pageSize={pageSize}
                      total={total}
                      onPageChange={goToPage}
                      disabled={loading}
                    />
                  </div>
                </>
              )}
            </Card>
          </>
        )}
      </div>
    </div>
  )
}
