import React, { useState } from 'react';
import { CheckCircle, Copy, Eye, EyeOff } from 'lucide-react';

export const CreatedKeyModal = ({ apiKey, onClose }) => {
  const [showSecret, setShowSecret] = useState(false);
  const [copiedField, setCopiedField] = useState('');

  const copy = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(''), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-2xl p-6 max-w-lg w-full" data-testid="created-key-modal">
        <div className="flex items-center space-x-3 mb-6">
          <div className="bg-green-500/20 p-3 rounded-full">
            <CheckCircle className="h-8 w-8 text-green-400" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white">API Key Created!</h3>
            <p className="text-gray-400 text-sm">Save your secret now - it will not be shown again</p>
          </div>
        </div>

        <div className="space-y-4">
          <Field label="API Key">
            <code className="flex-1 bg-black/30 px-4 py-3 rounded-lg text-green-400 text-sm font-mono break-all">
              {apiKey.api_key}
            </code>
            <CopyButton
              copied={copiedField === 'key'}
              onClick={() => copy(apiKey.api_key, 'key')}
              testId="copy-api-key"
            />
          </Field>

          <Field label="API Secret">
            <code className="flex-1 bg-black/30 px-4 py-3 rounded-lg text-yellow-400 text-sm font-mono break-all">
              {showSecret ? apiKey.api_secret : '•'.repeat(64)}
            </code>
            <button
              onClick={() => setShowSecret(!showSecret)}
              className="p-3 bg-white/10 hover:bg-white/20 rounded-lg"
              data-testid="toggle-secret-visibility"
            >
              {showSecret ? <EyeOff className="h-5 w-5 text-gray-400" /> : <Eye className="h-5 w-5 text-gray-400" />}
            </button>
            <CopyButton
              copied={copiedField === 'secret'}
              onClick={() => copy(apiKey.api_secret, 'secret')}
              testId="copy-api-secret"
            />
          </Field>
        </div>

        <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-yellow-200 text-sm">
            ⚠️ <strong>Important:</strong> Copy and save your API secret now. It will not be displayed again.
          </p>
        </div>

        <button
          onClick={onClose}
          className="w-full mt-6 bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-semibold"
          data-testid="close-created-key-modal"
        >
          Done
        </button>
      </div>
    </div>
  );
};

const Field = ({ label, children }) => (
  <div>
    <label className="block text-sm font-medium text-gray-400 mb-1">{label}</label>
    <div className="flex items-center space-x-2">{children}</div>
  </div>
);

const CopyButton = ({ copied, onClick, testId }) => (
  <button
    onClick={onClick}
    className="p-3 bg-white/10 hover:bg-white/20 rounded-lg"
    data-testid={testId}
  >
    {copied ? <CheckCircle className="h-5 w-5 text-green-400" /> : <Copy className="h-5 w-5 text-gray-400" />}
  </button>
);
