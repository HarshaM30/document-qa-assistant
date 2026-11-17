import { createBrowserRouter, Navigate } from 'react-router'

import { Layout } from './components/Layout'
import { ChatPage } from './pages/ChatPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SignupPage } from './pages/SignupPage'
import { WorkspacesPage } from './pages/WorkspacesPage'

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/workspaces" replace /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'signup', element: <SignupPage /> },
      { path: 'workspaces', element: <WorkspacesPage /> },
      { path: 'workspaces/:workspaceId/documents', element: <DocumentsPage /> },
      { path: 'workspaces/:workspaceId/chat', element: <ChatPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
