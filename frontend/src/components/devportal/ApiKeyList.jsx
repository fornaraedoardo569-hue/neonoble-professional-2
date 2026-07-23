import React from 'react';
import { Key, Trash2, Loader2 } from 'lucide-react';

const STATUS_STYLES = {
  ACTIVE: 'bg-green-500/20 text-green-400',
  REVOKED: 'bg-red-500/20 text-red-400',
};

export const ApiKeyList = ({ apiKeys, loading, onRevoke }) => {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
      </div>
    );
  }

  if (apiKeys.length === 0) {
    return (
      <div className="text-center py-12" data-testid="empty-api-keys">
        <Key className="h-12 w-12 text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400">No API keys yet</p>
        <p className="text-gray-500 text-sm">Create your first API key to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {apiKeys.map((key) => (
        <ApiKeyRow key={key.id} apiKey={key} onRevoke={onRevoke} />
      ))}
    </div>
  );
};

const ApiKeyRow = ({ apiKey, onRevoke }) => (
  <div className="bg-white/5 rounded-xl p-4" data-testid={`api-key-${apiKey.id}`}>
    <div className="flex justify-between items-start">
      <div>
        <h4 className="text-white font-semibold">{apiKey.name}</h4>
        {apiKey.description && (
          <p className="text-gray-400 text-sm mt-1">{apiKey.description}</p>
        )}
        <code className="text-purple-400 text-sm font-mono mt-2 block">{apiKey.api_key}</code>
      </div>
      <div className="flex items-center space-x-2">
        <span
          className={`text-xs px-2 py-1 rounded ${
            STATUS_STYLES[apiKey.status] || 'bg-gray-500/20 text-gray-400'
          }`}
        >
          {apiKey.status}
        </span>
        {apiKey.status === 'ACTIVE' && (
          <button
            onClick={() => onRevoke(apiKey.id)}
            className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg"
            data-testid={`revoke-key-${apiKey.id}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
    <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
      <span>Rate: {apiKey.rate_limit}/hr</span>
      <span>Used: {apiKey.usage_count} times</span>
      <span>Created: {new Date(apiKey.created_at).toLocaleDateString()}</span>
    </div>
  </div>
);
