import React, { useState } from 'react';
import { Plus, Loader2 } from 'lucide-react';

export const CreateKeyForm = ({ onSubmit, onCancel, creating }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [rateLimit, setRateLimit] = useState(1000);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ name, description, rateLimit });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 p-4 bg-white/5 rounded-xl"
      data-testid="create-key-form"
    >
      <h3 className="text-lg font-semibold text-white mb-4">Create New API Key</h3>
      <div className="space-y-4">
        <FormField label="Name *">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="My API Key"
            required
            data-testid="input-key-name"
          />
        </FormField>
        <FormField label="Description">
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="For my trading bot"
            data-testid="input-key-description"
          />
        </FormField>
        <FormField label="Rate Limit (requests/hour)">
          <input
            type="number"
            value={rateLimit}
            onChange={(e) => setRateLimit(parseInt(e.target.value, 10))}
            className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
            min="1"
            max="100000"
            data-testid="input-key-rate-limit"
          />
        </FormField>
      </div>
      <div className="flex space-x-3 mt-4">
        <button
          type="submit"
          disabled={creating}
          className="bg-green-600 hover:bg-green-700 disabled:bg-green-600/50 text-white px-4 py-2 rounded-lg font-medium flex items-center space-x-2"
          data-testid="submit-create-key"
        >
          {creating ? <Loader2 className="h-5 w-5 animate-spin" /> : <Plus className="h-5 w-5" />}
          <span>Create</span>
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-gray-400 hover:text-white px-4 py-2"
          data-testid="cancel-create-key"
        >
          Cancel
        </button>
      </div>
    </form>
  );
};

const FormField = ({ label, children }) => (
  <div>
    <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
    {children}
  </div>
);
