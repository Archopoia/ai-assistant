import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link } from 'react-router-dom';
import { OAuthButtons } from './OAuthButtons';
import { authAPI } from '../../services/api';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginForm: React.FC = () => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [email, setEmail] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    setLoading(true);
    try {
      const result = await authAPI.login(data.email, data.password);

      if ('requires_2fa' in result && result.requires_2fa) {
        setRequires2FA(true);
        setEmail(data.email);
        setLoading(false);
        return;
      }

      if ('access_token' in result && 'refresh_token' in result) {
        localStorage.setItem('access_token', result.access_token);
        localStorage.setItem('refresh_token', result.refresh_token);
        window.location.href = '/dashboard';
        return;
      }

      setError('Unexpected login response. Please try again.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (twoFactorCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const tokens = await authAPI.verify2FALogin(email, twoFactorCode);
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      
      // Redirect to dashboard - auth context will be updated on page load
      window.location.href = '/dashboard';
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid 2FA code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (requires2FA) {
    return (
      <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-6 text-center text-gray-900">Two-Factor Authentication</h2>
        
        <p className="mb-4 text-gray-600 text-sm">
          Please enter the 6-digit code from your authenticator app to complete login.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handle2FASubmit} className="space-y-4">
          <div>
            <label htmlFor="2fa-code" className="block text-sm font-medium text-gray-700 mb-2">
              Verification Code
            </label>
            <input
              type="text"
              id="2fa-code"
              value={twoFactorCode}
              onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border text-gray-900 bg-white placeholder-gray-400"
              autoFocus
            />
          </div>

          <button
            type="submit"
            disabled={loading || twoFactorCode.length !== 6}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
          >
            {loading ? 'Verifying...' : 'Verify & Login'}
          </button>

          <button
            type="button"
            onClick={() => {
              setRequires2FA(false);
              setTwoFactorCode('');
              setError(null);
            }}
            className="w-full bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded"
          >
            Back to Login
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-900">Login</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            {...register('email')}
            type="email"
            id="email"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 bg-white placeholder-gray-400"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            {...register('password')}
            type="password"
            id="password"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-gray-900 bg-white placeholder-gray-400"
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        <div className="flex items-center justify-between">
          <Link
            to="/forgot-password"
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <div className="mt-6">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">Or continue with</span>
          </div>
        </div>
        <OAuthButtons />
      </div>

      <p className="mt-6 text-center text-sm text-gray-600">
        Don't have an account?{' '}
        <Link to="/register" className="text-blue-600 hover:text-blue-800">
          Register here
        </Link>
      </p>
    </div>
  );
};
