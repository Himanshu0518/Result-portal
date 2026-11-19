import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/Layout'
import ImportPage from '@/pages/ImportPage'
import NotFoundPage from '@/pages/NotFoundPage'
import StudentReportPage from '@/pages/StudentReportPage'
import StudentsPage from '@/pages/StudentsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Redirect root to /students */}
        <Route index element={<Navigate to="/students" replace />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="students" element={<StudentsPage />} />
        <Route path="students/:studentId" element={<StudentReportPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
