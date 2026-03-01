import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams, Link } from 'react-router-dom';
import { authAPI } from '../../services/api';

const requestResetSchema = z.object({
  email: z.string().email('Invalid email address'),
});

const resetPasswordSchema = z.object({
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/\d/, 'Password must contain at least one digit'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type RequestResetFormData = z.infer<typeof requestResetSchema>;
type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export const PasswordReset: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (token) {
    // Reset password form
    const {
      register,
      handleSubmit,
      formState: { errors },
    } = useForm<ResetPasswordFormData>({
      resolver: zodResolver(resetPasswordSchema),
    });

    const onSubmit = async (data: ResetPasswordFormData) => {
      setError(null);
      setLoading(true);
      try {
        await authAPI.resetPassword(token, data.password);
        setSuccess(true);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Password reset failed. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    if (success) {
      return (
        <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
          <h2 className="text-2xl font-bold mb-4 text-center">Password Reset Successful</h2>
          <p className="text-center text-gray-600 mb-6">
            Your password has been reset successfully. You can now login with your new password.
          </p>
          <Link
            to="/login"
            className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Go to Login
          </Link>
        </div>
      );
    }

    return (
      <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-6 text-center">Reset Password</h2>
        
        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              New Password
            </label>
            <input
              {...register('password')}
              type="password"
              id="password"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
              Confirm New Password
            </label>
            <input
              {...register('confirmPassword')}
              type="password"
              id="confirmPassword"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
          >
            {loading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      </div>
    );
  }

  // Request password reset form
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RequestResetFormData>({
    resolver: zodResolver(requestResetSchema),
  });

  const onSubmit = async (data: RequestResetFormData) => {
    setError(null);
    setLoading(true);
    try {
      await authAPI.requestPasswordReset(data.email);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send reset email. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4 text-center">Check Your Email</h2>
        <p className="text-center text-gray-600 mb-6">
          If an account exists with that email, we've sent a password reset link.
        </p>
        <Link
          to="/login"
          className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Back to Login
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center">Forgot Password</h2>
      
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
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Sending...' : 'Send Reset Link'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600">
        Remember your password?{' '}
        <Link to="/login" className="text-blue-600 hover:text-blue-800">
          Login here
        </Link>
      </p>
    </div>
  );
};
