import React, { useState } from 'react';
import { authAPI } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';

export const TwoFactorAuth: React.FC = () => {
  const { user } = useAuth();
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [step, setStep] = useState<'idle' | 'setup' | 'verifying'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleEnable = async () => {
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const result = await authAPI.enable2FA();
      setQrCode(result.qr_code);
      setStep('setup');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to enable 2FA');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await authAPI.verify2FA(verificationCode);
      setSuccess('2FA enabled successfully!');
      setStep('idle');
      setQrCode(null);
      setVerificationCode('');
      // Refresh user data
      window.location.reload();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid verification code');
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    if (!confirm('Are you sure you want to disable 2FA? This will make your account less secure.')) {
      return;
    }

    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      await authAPI.disable2FA();
      setSuccess('2FA disabled successfully');
      window.location.reload();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to disable 2FA');
    } finally {
      setLoading(false);
    }
  };

  if (user?.two_factor_enabled && step === 'idle') {
    return (
      <div className="max-w-2xl mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Two-Factor Authentication</h2>
        
        <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
          <p className="font-semibold">✓ 2FA is enabled</p>
          <p className="text-sm mt-1">Your account is protected with two-factor authentication.</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
            {success}
          </div>
        )}

        <button
          onClick={handleDisable}
          disabled={loading}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? 'Disabling...' : 'Disable 2FA'}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-gray-900">Two-Factor Authentication</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
          {success}
        </div>
      )}

      {step === 'idle' && (
        <div>
          <p className="mb-4 text-gray-600">
            Two-factor authentication adds an extra layer of security to your account.
            You'll need to enter a code from your authenticator app when logging in.
          </p>
          <button
            onClick={handleEnable}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
          >
            {loading ? 'Setting up...' : 'Enable 2FA'}
          </button>
        </div>
      )}

      {step === 'setup' && qrCode && (
        <div>
          <p className="mb-4 text-gray-600">
            Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.):
          </p>
          <div className="mb-4 flex justify-center">
            <img src={qrCode} alt="2FA QR Code" className="border border-gray-300 rounded" />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter the 6-digit code from your app:
            </label>
            <input
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              className="block w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border text-gray-900 bg-white placeholder-gray-400"
            />
          </div>
          <div className="flex space-x-4">
            <button
              onClick={handleVerify}
              disabled={loading || verificationCode.length !== 6}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify & Enable'}
            </button>
            <button
              onClick={() => {
                setStep('idle');
                setQrCode(null);
                setVerificationCode('');
              }}
              className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
