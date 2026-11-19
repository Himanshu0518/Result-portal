import { Badge } from '@/components/ui/badge'

const GRADE_TONES = {
  A: 'success',
  B: 'primary',
  C: 'warning',
  D: 'warning',
  F: 'danger',
} as const

export function GradeBadge({ grade, className }: { grade: string; className?: string }) {
  const tone = GRADE_TONES[grade as keyof typeof GRADE_TONES] ?? 'neutral'
  return (
    <Badge tone={tone} className={className}>
      {grade}
    </Badge>
  )
}

export function ResultBadge({ result, className }: { result: string; className?: string }) {
  const isPass = result.toLowerCase() === 'pass'
  return (
    <Badge tone={isPass ? 'success' : 'danger'} className={className}>
      {isPass ? 'Pass' : 'Fail'}
    </Badge>
  )
}
