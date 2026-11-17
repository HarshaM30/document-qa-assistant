import { useLogin } from '../api/auth'
import { AuthForm } from '../components/AuthForm'

export function LoginPage() {
  const login = useLogin()
  return <AuthForm mode="login" submit={login.mutateAsync} pending={login.isPending} />
}
