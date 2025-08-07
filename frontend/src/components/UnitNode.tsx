import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { 
  Zap, 
  Thermometer, 
  Droplets, 
  ArrowUp, 
  ArrowDown, 
  Gauge, 
  Beaker,
  RotateCw,
  GitBranch,
  Layers
} from 'lucide-react';

const getUnitIcon = (unitType: string) => {
  switch (unitType) {
    case 'Reactor':
      return <Beaker size={16} />;
    case 'Heater':
      return <Thermometer size={16} className="text-red-500" />;
    case 'Cooler':
      return <Thermometer size={16} className="text-blue-500" />;
    case 'Pump':
      return <ArrowUp size={16} className="text-green-500" />;
    case 'Compressor':
      return <ArrowUp size={16} className="text-orange-500" />;
    case 'Valve':
      return <ArrowDown size={16} className="text-gray-500" />;
    case 'DistillationColumn':
      return <Layers size={16} className="text-purple-500" />;
    case 'Mixer':
      return <RotateCw size={16} className="text-yellow-500" />;
    case 'Splitter':
      return <GitBranch size={16} className="text-indigo-500" />;
    case 'Flash':
      return <Zap size={16} className="text-pink-500" />;
    case 'HeatExchanger':
      return <Droplets size={16} className="text-teal-500" />;
    default:
      return <Gauge size={16} />;
  }
};

const getUnitColor = (unitType: string) => {
  switch (unitType) {
    case 'Reactor':
      return 'border-green-400 bg-green-50';
    case 'Heater':
      return 'border-red-400 bg-red-50';
    case 'Cooler':
      return 'border-blue-400 bg-blue-50';
    case 'Pump':
    case 'Compressor':
      return 'border-orange-400 bg-orange-50';
    case 'Valve':
      return 'border-gray-400 bg-gray-50';
    case 'DistillationColumn':
      return 'border-purple-400 bg-purple-50';
    case 'Mixer':
      return 'border-yellow-400 bg-yellow-50';
    case 'Splitter':
      return 'border-indigo-400 bg-indigo-50';
    case 'Flash':
      return 'border-pink-400 bg-pink-50';
    case 'HeatExchanger':
      return 'border-teal-400 bg-teal-50';
    default:
      return 'border-gray-400 bg-white';
  }
};

interface UnitNodeData {
  unitType: string;
  name: string;
  parameters: Record<string, any>;
}

const UnitNode: React.FC<NodeProps<UnitNodeData>> = ({ data, selected }) => {
  const { unitType, name, parameters } = data;
  
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 shadow-md min-w-[120px] max-w-[200px]
        ${getUnitColor(unitType)}
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
      `}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-gray-400 border-2 border-white"
      />
      
      <div className="flex items-center gap-2 mb-1">
        {getUnitIcon(unitType)}
        <span className="font-medium text-sm text-gray-800 truncate">
          {name}
        </span>
      </div>
      
      <div className="text-xs text-gray-600 font-mono">
        {unitType}
      </div>
      
      {Object.keys(parameters).length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          {Object.entries(parameters).slice(0, 2).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="truncate">{key}:</span>
              <span className="ml-1 font-mono">
                {typeof value === 'number' ? value.toFixed(1) : String(value)}
              </span>
            </div>
          ))}
          {Object.keys(parameters).length > 2 && (
            <div className="text-gray-400">...</div>
          )}
        </div>
      )}
      
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-gray-400 border-2 border-white"
      />
    </div>
  );
};

export default UnitNode;