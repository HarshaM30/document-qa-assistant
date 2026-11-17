import { useSignup } from '../api/auth'
import { AuthForm } from '../components/AuthForm'

export function SignupPage() {
  const signup = useSignup()
  return <AuthForm mode="signup" submit={signup.mutateAsync} pending={signup.isPending} />
}
