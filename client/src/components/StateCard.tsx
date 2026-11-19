import type { ComponentType, ReactNode } from 'react'
import { cn } from '@/lib/utils'

type StateCardProps = {
  icon?: ComponentType<{ className?: string }>
  title: string
  description?: ReactNode
  action?: ReactNode
  tone?: 'default' | 'danger'
  className?: string
}

export default function StateCard({
  icon: Icon,
  title,
  description,
  action,
  tone = 'default',
  className,
}: StateCardProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-16 text-center',
        className,
      )}
    >
      {Icon && (
        <div
          className={cn(
            'mb-4 flex h-11 w-11 items-center justify-center rounded-full',
            tone === 'danger' ? 'bg-rose-50 text-rose-600' : 'bg-accent text-primary',
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
      )}
      <h3 className="text-base font-semibold">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-5 flex flex-wrap items-center justify-center gap-2">{action}</div>}
    </div>
  )
}
