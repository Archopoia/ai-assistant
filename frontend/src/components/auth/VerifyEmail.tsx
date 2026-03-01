import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { authAPI } from '../../services/api';

export const VerifyEmail: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying your email...');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setMessage('Verification token is missing.');
      return;
    }

    const verify = async () => {
      try {
        await authAPI.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been verified. You can now log in.');
      } catch (err: any) {
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Verification link is invalid or expired.');
      }
    };

    verify();
  }, [searchParams]);

  return (
    <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4 text-center text-gray-900">Email Verification</h2>
      <p
        className={`mb-6 text-center ${
          status === 'success' ? 'text-green-700' : status === 'error' ? 'text-red-700' : 'text-gray-600'
        }`}
      >
        {message}
      </p>
      <Link
        to="/login"
        className="block text-center bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
      >
        Go to Login
      </Link>
    </div>
  );
};
