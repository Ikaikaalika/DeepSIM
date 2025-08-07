import React, { useState, useCallback } from 'react';
import { 
  Play, 
  Save, 
  FolderOpen, 
  Download, 
  FileText, 
  Settings, 
  Loader 
} from 'lucide-react';
import { apiService } from '../services/api';

interface ToolbarProps {
  flowsheetId: string | null;
  onSimulationStart: () => void;
  onSimulationComplete: (results: any) => void;
  isSimulating: boolean;
}

const Toolbar: React.FC<ToolbarProps> = ({
  flowsheetId,
  onSimulationStart,
  onSimulationComplete,
  isSimulating,
}) => {
  const [showLoadModal, setShowLoadModal] = useState(false);
  const [availableFlowsheets, setAvailableFlowsheets] = useState<any[]>([]);

  const runSimulation = useCallback(async () => {
    if (!flowsheetId || isSimulating) return;

    onSimulationStart();
    
    try {
      const results = await apiService.runSimulation(flowsheetId);
      onSimulationComplete(results);
    } catch (error) {
      console.error('Simulation failed:', error);
      onSimulationComplete({
        simulation_id: 'error',
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
        units: {},
        streams: {},
      });
    }
  }, [flowsheetId, isSimulating, onSimulationStart, onSimulationComplete]);

  const saveFlowsheet = useCallback(async () => {
    if (!flowsheetId) return;
    
    try {
      console.log('Flowsheet saved');
    } catch (error) {
      console.error('Save failed:', error);
    }
  }, [flowsheetId]);

  const loadFlowsheets = useCallback(async () => {
    try {
      const response = await apiService.listFlowsheets();
      setAvailableFlowsheets(response.flowsheets);
      setShowLoadModal(true);
    } catch (error) {
      console.error('Failed to load flowsheets:', error);
    }
  }, []);

  const exportFlowsheet = useCallback(async (format: string) => {
    if (!flowsheetId) return;
    
    try {
      if (format === 'svg' || format === 'png') {
        // Export diagram as SVG/PNG
        const flowElement = document.querySelector('.react-flow');
        if (!flowElement) return;
        
        if (format === 'png') {
          // Convert to PNG using html2canvas
          const html2canvas = (await import('html2canvas')).default;
          const canvas = await html2canvas(flowElement as HTMLElement, {
            backgroundColor: '#ffffff',
            scale: 2,
            useCORS: true
          });
          canvas.toBlob((blob) => {
            if (blob) {
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `flowsheet_${flowsheetId}.png`;
              a.click();
              URL.revokeObjectURL(url);
            }
          }, 'image/png');
        } else if (format === 'svg') {
          // Create SVG export using React Flow's built-in method
          const reactFlowBounds = flowElement.getBoundingClientRect();
          const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
          svg.setAttribute('width', reactFlowBounds.width.toString());
          svg.setAttribute('height', reactFlowBounds.height.toString());
          svg.setAttribute('viewBox', `0 0 ${reactFlowBounds.width} ${reactFlowBounds.height}`);
          
          const svgData = new XMLSerializer().serializeToString(svg);
          const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
          const url = URL.createObjectURL(svgBlob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `flowsheet_${flowsheetId}.svg`;
          a.click();
          URL.revokeObjectURL(url);
        }
        return;
      }
      
      const data = await apiService.exportFlowsheet(flowsheetId, format);
      
      if (format === 'json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flowsheet_${flowsheetId}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } else if (format === 'csv') {
        const blob = new Blob([data.data], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flowsheet_${flowsheetId}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  }, [flowsheetId]);

  return (
    <>
      <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <div className="flex items-center gap-1">
          <h1 className="text-xl font-bold text-gray-900">DeepSim</h1>
          <span className="text-sm text-gray-500 ml-2">Chemical Process Simulator</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={runSimulation}
            disabled={!flowsheetId || isSimulating}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isSimulating ? (
              <Loader size={16} className="animate-spin" />
            ) : (
              <Play size={16} />
            )}
            {isSimulating ? 'Running...' : 'Simulate'}
          </button>

          <button
            onClick={saveFlowsheet}
            disabled={!flowsheetId}
            className="flex items-center gap-2 px-3 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed"
          >
            <Save size={16} />
            Save
          </button>

          <button
            onClick={loadFlowsheets}
            className="flex items-center gap-2 px-3 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            <FolderOpen size={16} />
            Load
          </button>

          <div className="relative group">
            <button className="flex items-center gap-2 px-3 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed">
              <Download size={16} />
              Export
            </button>
            {flowsheetId && (
              <div className="absolute right-0 top-full mt-1 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                <button
                  onClick={() => exportFlowsheet('json')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  JSON
                </button>
                <button
                  onClick={() => exportFlowsheet('csv')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  CSV
                </button>
                <button
                  onClick={() => exportFlowsheet('png')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  PNG
                </button>
                <button
                  onClick={() => exportFlowsheet('svg')}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  SVG
                </button>
              </div>
            )}
          </div>

          <button className="flex items-center gap-2 px-3 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50">
            <FileText size={16} />
            Report
          </button>

          <button className="flex items-center gap-2 px-3 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50">
            <Settings size={16} />
          </button>
        </div>
      </div>

      {showLoadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 max-h-96 overflow-y-auto">
            <h3 className="text-lg font-medium mb-4">Load Flowsheet</h3>
            
            {availableFlowsheets.length === 0 ? (
              <p className="text-gray-500">No saved flowsheets found</p>
            ) : (
              <div className="space-y-2">
                {availableFlowsheets.map((flowsheet) => (
                  <button
                    key={flowsheet.id}
                    onClick={() => {
                      window.location.href = `?flowsheet=${flowsheet.id}`;
                      setShowLoadModal(false);
                    }}
                    className="w-full text-left p-3 border border-gray-200 rounded-md hover:bg-gray-50"
                  >
                    <div className="font-medium">{flowsheet.name}</div>
                    <div className="text-sm text-gray-500">{flowsheet.description}</div>
                    <div className="text-xs text-gray-400">
                      Modified: {new Date(flowsheet.updated_at).toLocaleDateString()}
                    </div>
                  </button>
                ))}
              </div>
            )}
            
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowLoadModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Toolbar;