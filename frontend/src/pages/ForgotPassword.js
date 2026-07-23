import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import api from '../api';
import { AuthShell } from '../components/auth/AuthShell';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not submit request. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Forgot Password?"
      subtitle="We'll email you a link to set a new one."
      footer={
        <p className="text-gray-400">
          Remembered it?{' '}
          <Link to="/login" className="text-purple-400 hover:text-purple-300">
            Back to login
          </Link>
        </p>
      }
    >
      {submitted ? (
        <div
          className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 flex items-start gap-3"
          data-testid="forgot-password-success"
        >
          <CheckCircle className="h-5 w-5 text-green-300 mt-0.5 flex-shrink-0" />
          <p className="text-green-100 text-sm">
            If that email is registered, a reset link is on its way. Check your inbox (and the
            spam folder). The link expires in 24 hours.
          </p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" data-testid="forgot-password-form">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
            <div className="relative">
              <Mail className="h-5 w-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="you@example.com"
                data-testid="forgot-email-input"
              />
            </div>
          </div>
          {error && (
            <div
              className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-red-200 text-sm flex items-center gap-2"
              data-testid="forgot-password-error"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white py-3 rounded-xl font-semibold flex items-center justify-center space-x-2"
            data-testid="forgot-submit-btn"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Sending…</span>
              </>
            ) : (
              <span>Send reset link</span>
            )}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
