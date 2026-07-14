'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/auth-context';
import { Layers, Loader2, AlertCircle } from 'lucide-react';

const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
  });

  async function onSubmit(data: LoginForm) {
    setServerError(null);
    try {
      await login(data);
      router.push('/home');
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Login failed. Please try again.';
      setServerError(message);
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ backgroundColor: 'var(--bg)' }}
    >
      {/* Container Card */}
      <div
        className="w-full max-w-[400px] p-8 rounded-2xl border"
        style={{
          backgroundColor: 'var(--surface-raised)',
          borderColor: 'var(--border)',
          boxShadow: 'var(--surface-raised-shadow)',
        }}
      >
        {/* Header: Logo mark + "Conduit" */}
        <div className="flex items-center gap-2 mb-6">
          <Layers size={18} style={{ color: 'var(--accent)' }} />
          <span className="text-heading font-semibold" style={{ color: 'var(--text-primary)' }}>
            Conduit
          </span>
        </div>

        {/* Page Title */}
        <h1 className="text-display-sm mb-1" style={{ color: 'var(--text-primary)' }}>
          Sign in
        </h1>
        <p className="text-body mb-6" style={{ color: 'var(--text-secondary)' }}>
          Enter your credentials to access your workspace.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="email"
              className="text-body-medium text-[12px] font-medium"
              style={{ color: 'var(--text-secondary)' }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="h-10 px-3 rounded-lg text-body outline-none transition-all focus:border-[var(--accent)] focus:shadow-[0_0_0_2px_var(--accent-subtle)]"
              style={{
                backgroundColor: 'var(--surface)',
                border: `1px solid ${errors.email ? 'var(--danger)' : 'var(--border)'}`,
                color: 'var(--text-primary)',
                borderRadius: '8px',
              }}
              {...register('email')}
            />
            {errors.email && (
              <span className="text-caption" style={{ color: 'var(--danger)' }}>
                {errors.email.message}
              </span>
            )}
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="password"
              className="text-body-medium text-[12px] font-medium"
              style={{ color: 'var(--text-secondary)' }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="h-10 px-3 rounded-lg text-body outline-none transition-all focus:border-[var(--accent)] focus:shadow-[0_0_0_2px_var(--accent-subtle)]"
              style={{
                backgroundColor: 'var(--surface)',
                border: `1px solid ${errors.password ? 'var(--danger)' : 'var(--border)'}`,
                color: 'var(--text-primary)',
                borderRadius: '8px',
              }}
              {...register('password')}
            />
            {errors.password && (
              <span className="text-caption" style={{ color: 'var(--danger)' }}>
                {errors.password.message}
              </span>
            )}
          </div>

          {/* Compact Inline Error State */}
          {serverError && (
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px]"
              style={{
                backgroundColor: 'var(--danger-subtle)',
                color: 'var(--danger)',
              }}
            >
              <AlertCircle size={14} className="flex-shrink-0" />
              <span>{serverError}</span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="h-10 rounded-lg text-body-medium w-full flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed font-medium"
            style={{
              backgroundColor: 'var(--accent)',
              color: '#FFFFFF',
              borderRadius: '8px',
            }}
          >
            {isSubmitting && <Loader2 size={16} className="animate-spin" />}
            Sign in
          </button>
        </form>

        <p
          className="text-body mt-6 text-center"
          style={{ color: 'var(--text-secondary)' }}
        >
          Don&apos;t have an account?{' '}
          <Link
            href="/signup"
            className="font-medium transition-colors hover:opacity-90"
            style={{ color: 'var(--accent)' }}
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
