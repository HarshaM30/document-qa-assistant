import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <section>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link to="/workspaces" className="mt-2 inline-block text-indigo-700 underline">
        Go to workspaces
      </Link>
    </section>
  )
}
