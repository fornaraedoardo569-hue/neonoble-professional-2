import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lock, Loader2, CheckCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import api from '../api';
import { AuthShell } from '../components/auth/AuthShell';
import { useAuth } from '../context/AuthContext';

export default function ChangePassword() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  if (!isAuthenticated) {
    navigate('/login?redirect=/change-password');
    return null;
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (next.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    if (next !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/change-password', {
        current_password: current,
        new_password: next,
      });
      setDone(true);
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not change password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Change password"
      subtitle="Update your password for this account."
      footer={
        <>
          <Link
            to="/dashboard"
            className="text-purple-400 hover:text-purple-300 inline-flex items-center gap-1"
          >
            <ArrowLeft className="h-4 w-4" /> Back to dashboard
          </Link>
          <p className="text-gray-500 text-sm mt-3">
            Don't remember your current password?{' '}
            <Link to="/forgot-password" className="text-purple-400 hover:text-purple-300">
              Reset it via email
            </Link>
          </p>
        </>
      }
    >
      {done && (
        <div
          className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 mb-4 flex items-start gap-3"
          data-testid="change-password-success"
        >
          <CheckCircle className="h-5 w-5 text-green-300 mt-0.5 flex-shrink-0" />
          <p className="text-green-100 text-sm">Password changed successfully.</p>
        </div>
      )}
      <form onSubmit={onSubmit} className="space-y-4" data-testid="change-password-form">
        <Field label="Current password" value={current} onChange={setCurrent} testId="change-current" />
        <Field label="New password" value={next} onChange={setNext} testId="change-new" />
        <Field label="Confirm new password" value={confirm} onChange={setConfirm} testId="change-confirm" />
        {error && (
          <div
            className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-red-200 text-sm flex items-center gap-2"
            data-testid="change-password-error"
          >
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white py-3 rounded-xl font-semibold flex items-center justify-center space-x-2"
          data-testid="change-submit-btn"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Updating…</span>
            </>
          ) : (
            <span>Change password</span>
          )}
        </button>
      </form>
    </AuthShell>
  );
}

const Field = ({ label, value, onChange, testId }) => (
  <div>
    <label className="block text-sm font-medium text-gray-300 mb-2">{label}</label>
    <div className="relative">
      <Lock className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
        placeholder="••••••••"
        data-testid={testId}
      />
    </div>
  </div>
);
