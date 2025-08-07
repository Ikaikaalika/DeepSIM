import React, { useState } from 'react';
import { BarChart3, Activity, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { SimulationResults } from '../types';

interface ResultsPanelProps {
  results: SimulationResults | null;
  isSimulating: boolean;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ results, isSimulating }) => {
  const [activeTab, setActiveTab] = useState<'units' | 'streams' | 'convergence'>('units');

  const renderUnitsResults = () => {
    if (!results?.units) return null;

    return (
      <div className="space-y-3">
        {Object.entries(results.units).map(([unitId, data]) => (
          <div key={unitId} className="p-3 bg-gray-50 rounded-md">
            <h4 className="font-medium text-sm text-gray-900 mb-2">{unitId}</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {Object.entries(data as Record<string, any>).map(([key, value]) => (
                <div key={key}>
                  <span className="text-gray-600">{key}:</span>
                  <span className="ml-1 font-mono">
                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderStreamsResults = () => {
    if (!results?.streams) return null;

    return (
      <div className="space-y-3">
        {Object.entries(results.streams).map(([streamId, data]) => (
          <div key={streamId} className="p-3 bg-blue-50 rounded-md">
            <h4 className="font-medium text-sm text-gray-900 mb-2">{streamId}</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {Object.entries(data as Record<string, any>).map(([key, value]) => {
                if (key === 'composition' && typeof value === 'object') {
                  return (
                    <div key={key} className="col-span-2">
                      <span className="text-gray-600">composition:</span>
                      <div className="ml-2 mt-1">
                        {Object.entries(value).map(([comp, fraction]) => (
                          <div key={comp} className="flex justify-between">
                            <span>{comp}:</span>
                            <span className="font-mono">{(fraction as number).toFixed(3)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }
                return (
                  <div key={key}>
                    <span className="text-gray-600">{key}:</span>
                    <span className="ml-1 font-mono">
                      {typeof value === 'number' ? value.toFixed(2) : String(value)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderConvergenceResults = () => {
    if (!results?.convergence) return null;

    return (
      <div className="p-3 bg-green-50 rounded-md">
        <h4 className="font-medium text-sm text-gray-900 mb-2">Convergence Info</h4>
        <div className="space-y-2 text-xs">
          {Object.entries(results.convergence).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-gray-600">{key.replace(/_/g, ' ')}:</span>
              <span className="font-mono">
                {typeof value === 'number' ? 
                  (value < 0.001 ? value.toExponential(2) : value.toFixed(3)) : 
                  String(value)
                }
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="h-96 bg-white border-t border-gray-200">
      <div className="flex items-center gap-2 p-4 border-b border-gray-200">
        <BarChart3 size={20} className="text-gray-700" />
        <h3 className="text-lg font-medium text-gray-900">Results</h3>
        {isSimulating && (
          <Loader size={16} className="animate-spin text-blue-500" />
        )}
        {results && (
          <div className="ml-auto">
            {results.status === 'completed' ? (
              <CheckCircle size={16} className="text-green-500" />
            ) : results.status === 'failed' ? (
              <AlertCircle size={16} className="text-red-500" />
            ) : (
              <Activity size={16} className="text-yellow-500" />
            )}
          </div>
        )}
      </div>

      {isSimulating ? (
        <div className="flex items-center justify-center h-32">
          <div className="text-center">
            <Loader size={32} className="animate-spin text-blue-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600">Running simulation...</p>
          </div>
        </div>
      ) : !results ? (
        <div className="flex items-center justify-center h-32">
          <div className="text-center text-gray-500">
            <BarChart3 size={48} className="mx-auto mb-4 text-gray-300" />
            <p>Run simulation to see results</p>
          </div>
        </div>
      ) : results.status === 'failed' ? (
        <div className="p-4">
          <div className="flex items-center gap-2 text-red-600 mb-2">
            <AlertCircle size={16} />
            <span className="font-medium">Simulation Failed</span>
          </div>
          <p className="text-sm text-red-700 bg-red-50 p-3 rounded-md">
            {results.error || 'Unknown error occurred'}
          </p>
        </div>
      ) : (
        <div className="flex flex-col h-full">
          <div className="flex border-b border-gray-200">
            {[
              { key: 'units', label: 'Units', icon: Activity },
              { key: 'streams', label: 'Streams', icon: BarChart3 },
              { key: 'convergence', label: 'Convergence', icon: CheckCircle },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as any)}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium border-b-2 ${
                  activeTab === key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>

          <div className="flex-1 p-4 overflow-y-auto">
            {activeTab === 'units' && renderUnitsResults()}
            {activeTab === 'streams' && renderStreamsResults()}
            {activeTab === 'convergence' && renderConvergenceResults()}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultsPanel;