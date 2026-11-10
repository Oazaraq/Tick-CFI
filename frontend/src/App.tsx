import { Navigate, Route, Routes, useLocation } from 'react-router'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import { useMe } from './hooks'
import ActionsPage from './pages/ActionsPage'
import DashboardPage from './pages/DashboardPage'
import EmailsPage from './pages/EmailsPage'
import LoginPage from './pages/LoginPage'
import ProjectPage from './pages/ProjectPage'
import ChecklistPage from './pages/ChecklistPage'
import ProjectsPage from './pages/ProjectsPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import UsersPage from './pages/UsersPage'

export default function App() {
  const { data: me, isPending } = useMe()
  const { pathname } = useLocation()
  if (pathname === '/reset-password') return <ResetPasswordPage />  // lien d'activation : accessible sans session
  if (isPending) return <Spinner />
  if (!me) return <LoginPage />
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:id" element={<ProjectPage />} />
        <Route path="projects/:id/checklist" element={<ChecklistPage />} />
        <Route path="actions" element={<ActionsPage />} />
        {me.permissions.includes('user_manage') && <Route path="users" element={<UsersPage />} />}
        {me.permissions.includes('email_log_view') && <Route path="emails" element={<EmailsPage />} />}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
