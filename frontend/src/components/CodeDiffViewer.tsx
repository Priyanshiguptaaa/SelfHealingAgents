import React from 'react';
import { FileText, Plus, Minus } from 'lucide-react';

interface CodeDiffViewerProps {
  filename: string;
  before: string;
  after: string;
}

const CodeDiffViewer: React.FC<CodeDiffViewerProps> = ({ filename, before, after }) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center space-x-2 mb-4">
        <FileText className="h-5 w-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">Code Diff</h3>
      </div>
      
      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        <div className="text-sm font-mono text-gray-600 mb-2">{filename}</div>
      </div>

      <div className="space-y-2">
        {/* Before (removed line) */}
        <div className="flex items-start space-x-2 bg-red-50 border border-red-200 rounded px-3 py-2">
          <Minus className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
          <code className="text-sm font-mono text-red-800 flex-1">{before}</code>
        </div>

        {/* After (added line) */}
        <div className="flex items-start space-x-2 bg-green-50 border border-green-200 rounded px-3 py-2">
          <Plus className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
          <code className="text-sm font-mono text-green-800 flex-1">{after}</code>
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <span className="text-green-600 font-medium">+1</span> addition,{' '}
        <span className="text-red-600 font-medium">-1</span> deletion
      </div>
    </div>
  );
};

export default CodeDiffViewer; 