import { initials } from '@/lib/format'
import { cn } from '@/lib/utils'

const PALETTE = [
  'bg-indigo-100 text-indigo-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
  'bg-sky-100 text-sky-700',
  'bg-violet-100 text-violet-700',
]

const SIZES = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-16 w-16 text-xl',
}

type StudentAvatarProps = {
  name: string
  size?: keyof typeof SIZES
  className?: string
}

export default function StudentAvatar({ name, size = 'md', className }: StudentAvatarProps) {
  const colorIndex = Array.from(name).reduce((total, char) => total + char.codePointAt(0)!, 0) %
    PALETTE.length

  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full font-semibold tracking-tight',
        PALETTE[colorIndex],
        SIZES[size],
        className,
      )}
    >
      {initials(name)}
    </span>
  )
}
