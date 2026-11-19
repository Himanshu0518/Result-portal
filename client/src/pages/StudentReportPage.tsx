import { useParams } from 'react-router-dom'

export default function StudentReportPage() {
  const { studentId } = useParams<{ studentId: string }>()
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">Student Report</h1>
      <p className="text-muted-foreground mt-1">Viewing report for <code>{studentId}</code>.</p>
    </div>
  )
}
