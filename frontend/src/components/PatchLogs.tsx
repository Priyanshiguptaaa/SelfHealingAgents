import React from 'react';

interface PatchLogsProps {
  logs: string[];
  isVisible: boolean;
}

const PatchLogs: React.FC<PatchLogsProps> = ({ logs, isVisible }) => {
  if (!isVisible || logs.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-green-300">
          🔧 Patch Generation Logs
        </h3>
        <span className="text-xs text-gray-400">
          {logs.length} log entries
        </span>
      </div>
      
      <div className="space-y-2">
        {logs.map((log, index) => (
          <div key={index} className="border-l-2 border-green-500 pl-3">
            <span className="text-green-300">{log}</span>
          </div>
        ))}
      </div>
      
      {logs.length === 0 && (
        <div className="text-gray-500 italic">
          No patch generation logs yet...
        </div>
      )}
    </div>
  );
};

export default PatchLogs; 