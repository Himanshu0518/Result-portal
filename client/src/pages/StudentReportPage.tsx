import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  CalendarDays,
  GraduationCap,
  Mail,
  Printer,
  SearchX,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import Notice from '@/components/Notice'
import StateCard from '@/components/StateCard'
import StudentAvatar from '@/components/StudentAvatar'
import { ResultBadge } from '@/components/GradeBadge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchStudent, toApiError } from '@/lib/api'
import { formatDate, formatMark, formatPercent, SUBJECTS } from '@/lib/format'
import { cn } from '@/lib/utils'

function barColor(mark: number): string {
  if (mark >= 80) return 'bg-emerald-500'
  if (mark >= 60) return 'bg-primary'
  if (mark >= 50) return 'bg-amber-500'
  if (mark >= 40) return 'bg-orange-500'
  return 'bg-rose-500'
}

function ReportSkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-card p-6 shadow-sm">
        <div className="flex items-center gap-4">
          <Skeleton className="h-16 w-16 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-64" />
          </div>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl lg:col-span-2" />
      </div>
    </div>
  )
}

export default function StudentReportPage() {
  const { studentId } = useParams<{ studentId: string }>()
  const id = (studentId ?? '').trim().toUpperCase()

  const {
    data,
    isPending,
    error: queryError,
    refetch,
  } = useQuery({
    queryKey: ['students', 'detail', id],
    queryFn: ({ signal }) => fetchStudent(id, signal),
    enabled: Boolean(id),
  })

  const student = data?.data ?? null
  const loading = Boolean(id) && isPending
  const error = queryError ? toApiError(queryError) : null

  return (
    <div>
      <div className="print-hidden mb-5 flex items-center justify-between gap-3">
        <Link
          to="/students"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          All students
        </Link>

        {student && (
          <Button type="button" variant="outline" size="sm" onClick={() => window.print()}>
            <Printer className="h-3.5 w-3.5" />
            Print report
          </Button>
        )}
      </div>

      {error?.status === 404 ? (
        <Card>
          <StateCard
            icon={SearchX}
            title="Student not found"
            description={
              <>
                We couldn’t find a student with ID{' '}
                <span className="font-mono text-foreground">{id || '—'}</span>. Check the ID, or
                browse the full directory.
              </>
            }
            action={
              <Button asChild size="sm">
                <Link to="/students">Back to students</Link>
              </Button>
            }
          />
        </Card>
      ) : error ? (
        <Notice
          tone="danger"
          title="Could not load this report"
          action={
            <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
              Try again
            </Button>
          }
        >
          {error.message}
        </Notice>
      ) : loading && !student ? (
        <ReportSkeleton />
      ) : student ? (
        <div className="animate-fade-up">
          <Card className="print-plain overflow-hidden">
            <div className="h-1.5 w-full bg-gradient-to-r from-primary via-violet-400 to-sky-400" />
            <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center">
              <StudentAvatar name={student.full_name} size="lg" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-2xl font-semibold tracking-tight">{student.full_name}</h1>
                  <ResultBadge result={student.pass_fail} />
                </div>
                <p className="mt-1 font-mono text-xs tracking-wide text-muted-foreground">
                  {student.student_id}
                </p>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <GraduationCap className="h-4 w-4" />
                    Class {student.grade_level}, Section {student.section}
                  </span>
                  <a
                    href={`mailto:${student.email}`}
                    className="inline-flex items-center gap-1.5 hover:text-foreground"
                  >
                    <Mail className="h-4 w-4" />
                    {student.email}
                  </a>
                  <span className="inline-flex items-center gap-1.5">
                    <CalendarDays className="h-4 w-4" />
                    Born {formatDate(student.date_of_birth)}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card className="print-plain p-6">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Overall result
              </p>

              <div className="mt-4 flex items-start justify-between gap-4">
                <div>
                  <p className="text-4xl font-semibold tracking-tight tabular">
                    {formatPercent(student.percentage)}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    <span className="font-medium tabular text-foreground">
                      {formatMark(student.total)}
                    </span>{' '}
                    out of 500
                  </p>
                </div>
                <div className="flex h-16 w-16 flex-col items-center justify-center rounded-xl bg-accent">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-accent-foreground/70">
                    Grade
                  </span>
                  <span className="text-2xl font-bold leading-tight text-accent-foreground">
                    {student.grade}
                  </span>
                </div>
              </div>

              <div
                className="mt-5 h-2 overflow-hidden rounded-full bg-muted"
                role="img"
                aria-label={`${formatPercent(student.percentage)} of the total marks`}
              >
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-violet-400"
                  style={{ width: `${Math.min(100, Math.max(0, student.percentage))}%` }}
                />
              </div>

              <div className="mt-4 flex items-center justify-between rounded-lg bg-muted/60 px-3 py-2.5">
                <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Outcome
                </span>
                <span
                  className={cn(
                    'text-xs font-semibold',
                    student.pass_fail.toLowerCase() === 'pass'
                      ? 'text-emerald-700'
                      : 'text-rose-700',
                  )}
                >
                  {student.pass_fail.toLowerCase() === 'pass' ? 'Passed' : 'Did not pass'}
                </span>
              </div>

              <p className="mt-3 text-xs text-muted-foreground">
                Pass mark is 40% overall.
              </p>
            </Card>

            <Card className="print-plain p-6 lg:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Subject marks
                </p>
                <p className="text-xs text-muted-foreground">Each subject is out of 100</p>
              </div>

              <table className="mt-4 w-full">
                <caption className="sr-only">Marks by subject for {student.full_name}</caption>
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th className="w-32 pb-2 font-medium sm:w-40">Subject</th>
                    <th className="pb-2 font-medium">
                      <span className="sr-only">Performance bar</span>
                    </th>
                    <th className="w-14 pb-2 text-right font-medium">Mark</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {SUBJECTS.map(subject => {
                    const mark = student[subject.key]
                    return (
                      <tr key={subject.key}>
                        <td className="py-3 pr-3 text-sm font-medium">{subject.label}</td>
                        <td className="py-3 pr-3">
                          <div className="h-2 overflow-hidden rounded-full bg-muted">
                            <div
                              className={cn('h-full rounded-full', barColor(mark))}
                              style={{ width: `${Math.min(100, Math.max(0, mark))}%` }}
                            />
                          </div>
                        </td>
                        <td className="py-3 text-right text-sm font-medium tabular">
                          {formatMark(mark)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </Card>
          </div>

          <div className="print-plain mt-4 rounded-xl border border-dashed bg-card px-5 py-4 text-xs leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">Grading scale</span> — A 80% and above · B
            60–79.9% · C 50–59.9% · D 40–49.9% · F below 40%. Grades are decided on the unrounded
            percentage, then shown to one decimal place.
          </div>

          <p className="print-hidden mt-3 text-[11px] text-muted-foreground">
            Record last updated {formatDate(student.updated_at)}.
          </p>
        </div>
      ) : null}
    </div>
  )
}
