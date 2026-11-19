import { Compass } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent text-primary">
        <Compass className="h-7 w-7" />
      </div>
      <p className="mt-5 text-xs font-semibold uppercase tracking-widest text-primary">404</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
        The page you’re looking for doesn’t exist or may have moved.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
        <Button asChild size="sm">
          <Link to="/students">Go to students</Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to="/import">Import a CSV</Link>
        </Button>
      </div>
    </div>
  )
}
