import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'

import type { Credentials } from '../api/auth'
import { errorMessage } from '../api/client'
import { Button, ErrorText, inputClass } from './ui'

const MIN_PASSWORD_LENGTH = 8
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface Props {
  mode: 'login' | 'signup'
  submit: (body: Credentials) => Promise<unknown>
  pending: boolean
}

export function AuthForm({ mode, submit, pending }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [serverError, setServerError] = useState<string | null>(null)
  const signup = mode === 'signup'

  function validate(): Record<string, string> {
    const errors: Record<string, string> = {}
    if (!EMAIL.test(email.trim())) errors.email = 'Enter a valid email address.'
    if (!password) errors.password = 'Enter your password.'
    else if (signup && password.length < MIN_PASSWORD_LENGTH)
      errors.password = `Use at least ${MIN_PASSWORD_LENGTH} characters.`
    if (signup && confirm !== password) errors.confirm = 'Passwords do not match.'
    return errors
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const errors = validate()
    setFieldErrors(errors)
    setServerError(null)
    if (Object.keys(errors).length) return
    try {
      await submit({ email: email.trim(), password })
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' && from !== '/signup' ? from : '/workspaces', {
        replace: true,
      })
    } catch (error) {
      setServerError(errorMessage(error))
    }
  }

  return (
    <section className="mx-auto max-w-sm">
      <h1 className="text-2xl font-semibold">{signup ? 'Create an account' : 'Log in'}</h1>
      <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
        <Field label="Email" error={fieldErrors.email}>
          <input
            type="email"
            name="email"
            autoComplete="email"
            className={inputClass}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label="Password" error={fieldErrors.password}>
          <input
            type="password"
            name="password"
            autoComplete={signup ? 'new-password' : 'current-password'}
            className={inputClass}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {signup ? (
          <Field label="Confirm password" error={fieldErrors.confirm}>
            <input
              type="password"
              name="confirm"
              autoComplete="new-password"
              className={inputClass}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
        ) : null}
        <ErrorText>{serverError}</ErrorText>
        <Button type="submit" className="w-full py-2" disabled={pending}>
          {pending ? 'Please wait…' : signup ? 'Sign up' : 'Log in'}
        </Button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        {signup ? 'Already have an account? ' : 'New here? '}
        <Link
          to={signup ? '/login' : '/signup'}
          state={location.state}
          className="text-indigo-700 underline"
        >
          {signup ? 'Log in' : 'Create an account'}
        </Link>
      </p>
    </section>
  )
}

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
      {error ? <span className="block text-xs text-red-700">{error}</span> : null}
    </label>
  )
}
