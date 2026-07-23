import React from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';

export const AlertBanner = ({ kind, message, testId }) => {
  if (!message) return null;
  const isError = kind === 'error';
  const Icon = isError ? AlertCircle : CheckCircle;
  const styles = isError
    ? 'bg-red-500/20 border-red-500/50 text-red-200'
    : 'bg-green-500/20 border-green-500/50 text-green-200';
  return (
    <div
      className={`mb-4 p-4 border rounded-lg flex items-center space-x-2 ${styles}`}
      data-testid={testId}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      <span>{message}</span>
    </div>
  );
};
