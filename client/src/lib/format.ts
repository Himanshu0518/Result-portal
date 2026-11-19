const numberFormatter = new Intl.NumberFormat('en-US')

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return numberFormatter.format(value)
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export function formatMark(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return iso

  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, day)))
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export const FIELD_LABELS: Record<string, string> = {
  student_id: 'Student ID',
  full_name: 'Full name',
  email: 'Email',
  date_of_birth: 'Date of birth',
  grade_level: 'Grade level',
  section: 'Section',
  maths: 'Maths',
  science: 'Science',
  english: 'English',
  social_studies: 'Social studies',
  second_language: 'Second language',
}

export function fieldLabel(field: string | null): string {
  if (!field) return 'Whole row'
  return FIELD_LABELS[field] ?? field
}

export const SUBJECTS = [
  { key: 'maths', label: 'Maths' },
  { key: 'science', label: 'Science' },
  { key: 'english', label: 'English' },
  { key: 'social_studies', label: 'Social studies' },
  { key: 'second_language', label: 'Second language' },
] as const
