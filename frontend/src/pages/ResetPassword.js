import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Lock, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import api from '../api';
import { AuthShell } from '../components/auth/AuthShell';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/reset-password', { token, new_password: newPassword });
      setDone(true);
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not reset password.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthShell
        title="Reset link missing"
        subtitle="No reset token was found in the URL."
        footer={
          <Link to="/forgot-password" className="text-purple-400 hover:text-purple-300">
            Request a new reset link →
          </Link>
        }
      >
        <p className="text-red-200 text-sm" data-testid="reset-no-token">
          The reset link you used is incomplete. Please use the link from your email exactly as
          received, or request a new one.
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Set a new password"
      subtitle="Pick something at least 8 characters long."
      footer={
        <Link to="/login" className="text-purple-400 hover:text-purple-300">
          Back to login
        </Link>
      }
    >
      {done ? (
        <div
          className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 flex items-start gap-3"
          data-testid="reset-password-success"
        >
          <CheckCircle className="h-5 w-5 text-green-300 mt-0.5 flex-shrink-0" />
          <p className="text-green-100 text-sm">
            Password updated. Redirecting you to login…
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" data-testid="reset-password-form">
          <PasswordField
            label="New password"
            value={newPassword}
            onChange={setNewPassword}
            testId="reset-new-password"
          />
          <PasswordField
            label="Confirm new password"
            value={confirm}
            onChange={setConfirm}
            testId="reset-confirm-password"
          />
          {error && (
            <div
              className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-red-200 text-sm flex items-center gap-2"
              data-testid="reset-password-error"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white py-3 rounded-xl font-semibold flex items-center justify-center space-x-2"
            data-testid="reset-submit-btn"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Updating…</span>
              </>
            ) : (
              <span>Update password</span>
            )}
          </button>
        </form>
      )}
    </AuthShell>
  );
}

const PasswordField = ({ label, value, onChange, testId }) => (
  <div>
    <label className="block text-sm font-medium text-gray-300 mb-2">{label}</label>
    <div className="relative">
      <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        minLength={8}
        className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
        placeholder="••••••••"
        data-testid={testId}
      />
    </div>
  </div>
);
