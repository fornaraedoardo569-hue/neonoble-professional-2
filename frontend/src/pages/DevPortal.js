import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useApiKeys } from '../hooks/useApiKeys';
import { devApi } from '../api';
import { Coins, Plus, LogOut, AlertCircle, CheckCircle } from 'lucide-react';
import { StatsBar } from '../components/devportal/StatsBar';
import { CreateKeyForm } from '../components/devportal/CreateKeyForm';
import { CreatedKeyModal } from '../components/devportal/CreatedKeyModal';
import { ApiKeyList } from '../components/devportal/ApiKeyList';
import { ApiDocs } from '../components/devportal/ApiDocs';
import { TransakSandboxCard } from '../components/devportal/TransakSandboxCard';
import { AssistantWidget } from '../components/assistant/AssistantWidget';

export default function DevPortal() {
  const { user, logout, isAuthenticated, isDeveloper } = useAuth();
  const navigate = useNavigate();
  const { apiKeys, stats, loading, error, setError, refresh } = useApiKeys();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState(null);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/dev/login');
      return;
    }
    if (!isDeveloper) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, isDeveloper, navigate]);

  if (!isAuthenticated || !isDeveloper) return null;

  const handleCreateKey = async ({ name, description, rateLimit }) => {
    setError('');
    setCreating(true);
    try {
      const key = await devApi.createApiKey(name, description, rateLimit);
      setCreatedKey(key);
      setShowCreateForm(false);
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId) => {
    if (!window.confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
      return;
    }
    try {
      await devApi.revokeApiKey(keyId);
      setSuccess('API key revoked successfully');
      refresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke API key');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900" data-testid="dev-portal">
      <header className="border-b border-white/10 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-2">
              <Coins className="h-8 w-8 text-purple-400" />
              <span className="text-xl font-bold text-white">NeoNoble</span>
              <span className="bg-purple-600 text-white text-xs px-2 py-1 rounded">Dev Portal</span>
            </Link>
            <div className="flex items-center space-x-4">
              <Link to="/dashboard" className="text-gray-300 hover:text-white px-3 py-2 text-sm">
                User Dashboard
              </Link>
              <span className="text-gray-400 text-sm">{user?.email}</span>
              <button
                onClick={handleLogout}
                className="text-gray-400 hover:text-white p-2"
                data-testid="logout-btn"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <StatsBar stats={stats} />

        {error && (
          <Banner kind="error" message={error} onClose={() => setError('')} testId="dev-error" />
        )}
        {success && (
          <Banner kind="success" message={success} onClose={() => setSuccess('')} testId="dev-success" />
        )}

        {createdKey && (
          <CreatedKeyModal apiKey={createdKey} onClose={() => setCreatedKey(null)} />
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <TransakSandboxCard />

            <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white">API Keys</h2>
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-medium flex items-center space-x-2"
                  data-testid="create-key-btn"
                >
                  <Plus className="h-5 w-5" />
                  <span>Create Key</span>
                </button>
              </div>

              {showCreateForm && (
                <CreateKeyForm
                  onSubmit={handleCreateKey}
                  onCancel={() => setShowCreateForm(false)}
                  creating={creating}
                />
              )}

              <ApiKeyList apiKeys={apiKeys} loading={loading} onRevoke={handleRevoke} />
            </div>
          </div>

          <ApiDocs />
        </div>
      </div>
      <AssistantWidget context="devportal" />
    </div>
  );
}

const Banner = ({ kind, message, onClose, testId }) => {
  const isError = kind === 'error';
  const Icon = isError ? AlertCircle : CheckCircle;
  const styles = isError
    ? 'bg-red-500/20 border-red-500/50 text-red-200'
    : 'bg-green-500/20 border-green-500/50 text-green-200';
  return (
    <div
      className={`mb-6 p-4 border rounded-lg flex items-center space-x-2 ${styles}`}
      data-testid={testId}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      <span>{message}</span>
      <button onClick={onClose} className="ml-auto">×</button>
    </div>
  );
};
