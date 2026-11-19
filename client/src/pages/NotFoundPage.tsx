import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h1 className="text-5xl font-bold text-muted-foreground">404</h1>
      <p className="text-lg">Page not found.</p>
      <Link to="/students" className="text-primary underline underline-offset-4">
        Back to Students
      </Link>
    </div>
  )
}
