import React from 'react';
import { BookOpen, Code } from 'lucide-react';

const ENDPOINTS = [
  'GET /api/ramp-api-health',
  'POST /api/ramp-api-onramp-quote',
  'POST /api/ramp-api-onramp',
  'POST /api/ramp-api-offramp-quote',
  'POST /api/ramp-api-offramp',
];

export const ApiDocs = () => (
  <div className="space-y-6">
    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6">
      <h3 className="text-lg font-semibold text-white flex items-center mb-4">
        <BookOpen className="h-5 w-5 mr-2 text-purple-400" /> Quick Start
      </h3>
      <div className="space-y-4">
        <div>
          <h4 className="text-gray-300 font-medium mb-2">1. HMAC Authentication</h4>
          <p className="text-gray-500 text-sm">All ramp API calls require HMAC-SHA256 signature</p>
        </div>
        <div>
          <h4 className="text-gray-300 font-medium mb-2">2. Required Headers</h4>
          <ul className="text-gray-500 text-sm space-y-1">
            <li>• X-API-KEY</li>
            <li>• X-TIMESTAMP (Unix)</li>
            <li>• X-SIGNATURE</li>
          </ul>
        </div>
        <div>
          <h4 className="text-gray-300 font-medium mb-2">3. Signature Formula</h4>
          <code className="text-xs bg-black/30 px-2 py-1 rounded text-green-400 block">
            HMAC-SHA256(timestamp + body, secret)
          </code>
        </div>
      </div>
    </div>

    <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6">
      <h3 className="text-lg font-semibold text-white flex items-center mb-4">
        <Code className="h-5 w-5 mr-2 text-purple-400" /> API Endpoints
      </h3>
      <div className="space-y-3 text-sm">
        {ENDPOINTS.map((endpoint) => (
          <code key={endpoint} className="text-purple-400 block">{endpoint}</code>
        ))}
      </div>
    </div>
  </div>
);
