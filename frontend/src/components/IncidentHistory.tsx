import React, { useState, useEffect } from 'react';
import { Clock, AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react';

interface IncidentHistoryProps {
  incidents: Array<{
    id: string;
    timestamp: string;
    type: string;
    sku: string;
    status: 'resolved' | 'failed' | 'in_progress';
    duration?: number;
    cause: string;
  }>;
}

const IncidentHistory: React.FC<IncidentHistoryProps> = ({ incidents }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'resolved':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
        return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-blue-600 animate-spin" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved':
        return 'bg-green-50 border-green-200';
      case 'failed':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center space-x-2 mb-4">
        <TrendingUp className="h-5 w-5 text-gray-600" />
        <h3 className="text-lg font-semibold text-gray-900">Incident History</h3>
      </div>

      {incidents.length === 0 ? (
        <p className="text-gray-500 text-sm">No incidents recorded yet</p>
      ) : (
        <div className="space-y-3">
          {incidents.slice(0, 5).map((incident) => (
            <div
              key={incident.id}
              className={`border rounded-lg p-3 ${getStatusColor(incident.status)}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(incident.status)}
                  <div>
                    <div className="font-medium text-gray-900">
                      {incident.type} - {incident.sku}
                    </div>
                    <div className="text-sm text-gray-600">{incident.cause}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">
                    {new Date(incident.timestamp).toLocaleString()}
                  </div>
                  {incident.duration && (
                    <div className="text-xs text-gray-500">
                      Healed in {incident.duration}s
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default IncidentHistory; 