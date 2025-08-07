import React, { useState, useEffect, useCallback } from 'react';
import { Node } from 'reactflow';
import { Settings, Save, X } from 'lucide-react';

interface PropertiesPanelProps {
  selectedNode: Node | null;
  flowsheetId: string | null;
}

const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  selectedNode,
  flowsheetId,
}) => {
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [name, setName] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (selectedNode) {
      setParameters(selectedNode.data.parameters || {});
      setName(selectedNode.data.name || '');
      setHasChanges(false);
    } else {
      setParameters({});
      setName('');
      setHasChanges(false);
    }
  }, [selectedNode]);

  const handleParameterChange = useCallback((key: string, value: any) => {
    setParameters((prev) => ({
      ...prev,
      [key]: value,
    }));
    setHasChanges(true);
  }, []);

  const handleNameChange = useCallback((newName: string) => {
    setName(newName);
    setHasChanges(true);
  }, []);

  const saveChanges = useCallback(() => {
    if (selectedNode && hasChanges) {
      selectedNode.data.parameters = parameters;
      selectedNode.data.name = name;
      setHasChanges(false);
    }
  }, [selectedNode, parameters, name, hasChanges]);

  const resetChanges = useCallback(() => {
    if (selectedNode) {
      setParameters(selectedNode.data.parameters || {});
      setName(selectedNode.data.name || '');
      setHasChanges(false);
    }
  }, [selectedNode]);

  const getDefaultParameters = (unitType: string): Record<string, any> => {
    switch (unitType) {
      case 'Reactor':
        return {
          temperature: 250,
          pressure: 1.0,
          conversion: 0.85,
          reactor_type: 'CSTR',
          volume: 10.0,
        };
      case 'Heater':
        return {
          outlet_temperature: 200,
          heat_duty: 1000,
          pressure_drop: 0.1,
        };
      case 'Cooler':
        return {
          outlet_temperature: 50,
          heat_duty: -500,
          pressure_drop: 0.1,
        };
      case 'Pump':
        return {
          outlet_pressure: 5.0,
          efficiency: 0.75,
          power: 100,
        };
      case 'Compressor':
        return {
          pressure_ratio: 3.0,
          efficiency: 0.8,
          power: 1000,
        };
      case 'Valve':
        return {
          pressure_drop: 1.0,
          cv: 100,
        };
      case 'DistillationColumn':
        return {
          stages: 20,
          reflux_ratio: 2.5,
          pressure: 1.0,
          feed_stage: 10,
        };
      case 'Mixer':
        return {
          pressure_drop: 0.05,
        };
      case 'Splitter':
        return {
          split_fraction: 0.5,
        };
      case 'Flash':
        return {
          temperature: 100,
          pressure: 1.0,
        };
      case 'HeatExchanger':
        return {
          hot_outlet_temperature: 80,
          cold_outlet_temperature: 150,
          pressure_drop_hot: 0.1,
          pressure_drop_cold: 0.1,
        };
      default:
        return {};
    }
  };

  const addDefaultParameters = useCallback(() => {
    if (selectedNode) {
      const defaults = getDefaultParameters(selectedNode.data.unitType);
      const combined = { ...defaults, ...parameters };
      setParameters(combined);
      setHasChanges(true);
    }
  }, [selectedNode, parameters]);

  const renderParameterInput = (key: string, value: any) => {
    const inputType = typeof value === 'number' ? 'number' : 'text';
    
    return (
      <div key={key} className="mb-3">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
        </label>
        <input
          type={inputType}
          value={value}
          onChange={(e) => {
            const newValue = inputType === 'number' 
              ? parseFloat(e.target.value) || 0 
              : e.target.value;
            handleParameterChange(key, newValue);
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
          step={inputType === 'number' ? 'any' : undefined}
        />
      </div>
    );
  };

  if (!selectedNode) {
    return (
      <div className="h-96 p-4 bg-white">
        <div className="flex items-center gap-2 mb-4">
          <Settings size={20} className="text-gray-500" />
          <h3 className="text-lg font-medium text-gray-900">Properties</h3>
        </div>
        <div className="text-center text-gray-500 mt-8">
          <Settings size={48} className="mx-auto mb-4 text-gray-300" />
          <p>Select a unit operation to edit its properties</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-96 p-4 bg-white overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Settings size={20} className="text-gray-700" />
          <h3 className="text-lg font-medium text-gray-900">Properties</h3>
        </div>
        {hasChanges && (
          <div className="flex gap-2">
            <button
              onClick={saveChanges}
              className="p-1 text-green-600 hover:bg-green-50 rounded"
              title="Save changes"
            >
              <Save size={16} />
            </button>
            <button
              onClick={resetChanges}
              className="p-1 text-red-600 hover:bg-red-50 rounded"
              title="Reset changes"
            >
              <X size={16} />
            </button>
          </div>
        )}
      </div>

      <div className="mb-4 p-3 bg-gray-50 rounded-md">
        <div className="text-sm text-gray-600 mb-1">Unit Type</div>
        <div className="font-medium text-gray-900">{selectedNode.data.unitType}</div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-gray-700">Parameters</h4>
          {Object.keys(parameters).length === 0 && (
            <button
              onClick={addDefaultParameters}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Add defaults
            </button>
          )}
        </div>
        
        {Object.keys(parameters).length > 0 ? (
          Object.entries(parameters).map(([key, value]) =>
            renderParameterInput(key, value)
          )
        ) : (
          <div className="text-sm text-gray-500 italic">
            No parameters set
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <button
          className="w-full px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
          onClick={() => {
            const newKey = prompt('Parameter name:');
            if (newKey && !parameters[newKey]) {
              handleParameterChange(newKey, 0);
            }
          }}
        >
          Add Parameter
        </button>
      </div>
    </div>
  );
};

export default PropertiesPanel;