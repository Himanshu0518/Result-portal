import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

const TONES = {
  info: {
    box: 'border-sky-200 bg-sky-50 text-sky-900',
    icon: Info,
  },
  success: {
    box: 'border-emerald-200 bg-emerald-50 text-emerald-900',
    icon: CheckCircle2,
  },
  warning: {
    box: 'border-amber-200 bg-amber-50 text-amber-900',
    icon: AlertTriangle,
  },
  danger: {
    box: 'border-rose-200 bg-rose-50 text-rose-900',
    icon: AlertCircle,
  },
}

type NoticeProps = {
  tone?: keyof typeof TONES
  title?: string
  children: ReactNode
  action?: ReactNode
  className?: string
}

export default function Notice({ tone = 'info', title, children, action, className }: NoticeProps) {
  const { box, icon: Icon } = TONES[tone]

  return (
    <div className={cn('flex flex-col gap-3 rounded-xl border p-4 sm:flex-row', box, className)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1 text-sm">
        {title && <p className="font-medium">{title}</p>}
        <div className={cn('leading-relaxed', title && 'mt-1 opacity-90')}>{children}</div>
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  )
}
