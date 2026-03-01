import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');

    if (accessToken && refreshToken) {
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
      window.location.href = '/dashboard';
      return;
    }

    navigate('/login');
  }, [navigate, searchParams]);

  return (
    <div className="max-w-md mx-auto mt-8 bg-white p-8 rounded-lg shadow-md text-center">
      <h2 className="text-xl font-semibold text-gray-900">Completing sign in...</h2>
      <p className="mt-2 text-sm text-gray-600">Please wait while we finish your OAuth login.</p>
    </div>
  );
};
