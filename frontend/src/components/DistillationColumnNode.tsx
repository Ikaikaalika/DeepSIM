import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Layers, Thermometer, Droplets } from 'lucide-react';

interface DistillationColumnData {
  unitType: string;
  name: string;
  parameters: {
    stages?: number;
    refluxRatio?: number;
    feedStage?: number;
    distillateRate?: number;
    pressure?: number;
    trayEfficiency?: number;
  };
}

const DistillationColumnNode: React.FC<NodeProps<DistillationColumnData>> = ({ data, selected }) => {
  const { name, parameters } = data;
  const {
    stages = 20,
    refluxRatio = 2.0,
    feedStage = 10,
    distillateRate = 50,
    pressure = 101325,
    trayEfficiency = 0.75
  } = parameters;

  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 shadow-lg min-w-[160px] max-w-[220px]
        border-purple-400 bg-purple-50
        ${selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
      `}
    >
      {/* Feed inlet */}
      <Handle
        type="target"
        position={Position.Left}
        id="feed"
        style={{ top: '50%' }}
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />
      
      {/* Condenser inlet */}
      <Handle
        type="target"
        position={Position.Top}
        id="condenser-utility"
        style={{ left: '25%' }}
        className="w-3 h-3 bg-cyan-500 border-2 border-white"
      />
      
      {/* Reboiler inlet */}
      <Handle
        type="target"
        position={Position.Bottom}
        id="reboiler-utility"
        style={{ left: '25%' }}
        className="w-3 h-3 bg-red-500 border-2 border-white"
      />
      
      <div className="flex items-center gap-2 mb-2">
        <Layers size={18} className="text-purple-600" />
        <span className="font-semibold text-sm text-gray-800 truncate">
          {name}
        </span>
      </div>
      
      <div className="text-xs text-gray-600 font-mono mb-2">
        Distillation Column
      </div>
      
      {/* Column visual representation */}
      <div className="flex justify-center mb-2">
        <div className="relative">
          {/* Column body */}
          <div className="w-8 h-20 bg-gradient-to-b from-purple-200 via-purple-300 to-purple-400 border border-purple-500 rounded-sm">
            {/* Trays visualization */}
            {Array.from({ length: Math.min(6, Math.ceil(stages / 3)) }).map((_, i) => (
              <div
                key={i}
                className="absolute w-full h-px bg-purple-600"
                style={{ top: `${15 + i * 10}px` }}
              />
            ))}
            
            {/* Feed arrow */}
            <div
              className="absolute -left-2 w-2 h-px bg-blue-500"
              style={{ top: `${feedStage ? (feedStage / stages) * 80 + 10 : 40}px` }}
            >
              <div className="absolute -left-1 -top-1 w-0 h-0 border-t-2 border-b-2 border-l-2 border-transparent border-l-blue-500" />
            </div>
          </div>
          
          {/* Condenser */}
          <div className="absolute -top-2 left-1 w-6 h-2 bg-cyan-200 border border-cyan-400 rounded-sm">
            <Thermometer size={8} className="text-cyan-600 absolute top-0 left-1" />
          </div>
          
          {/* Reboiler */}
          <div className="absolute -bottom-2 left-1 w-6 h-2 bg-red-200 border border-red-400 rounded-sm">
            <Thermometer size={8} className="text-red-600 absolute top-0 left-1" />
          </div>
        </div>
      </div>
      
      {/* Key parameters display */}
      <div className="text-xs text-gray-600 space-y-1">
        <div className="flex justify-between">
          <span>Stages:</span>
          <span className="font-mono text-purple-700">{stages}</span>
        </div>
        <div className="flex justify-between">
          <span>RR:</span>
          <span className="font-mono text-purple-700">{refluxRatio}</span>
        </div>
        <div className="flex justify-between">
          <span>Feed:</span>
          <span className="font-mono text-purple-700">{feedStage}</span>
        </div>
        <div className="flex justify-between">
          <span>η:</span>
          <span className="font-mono text-purple-700">{(trayEfficiency * 100).toFixed(0)}%</span>
        </div>
      </div>
      
      {/* Distillate outlet */}
      <Handle
        type="source"
        position={Position.Top}
        id="distillate"
        style={{ left: '75%' }}
        className="w-3 h-3 bg-green-500 border-2 border-white"
      />
      
      {/* Bottoms outlet */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottoms"
        style={{ left: '75%' }}
        className="w-3 h-3 bg-orange-500 border-2 border-white"
      />
      
      {/* Vapor outlet (if partial condenser) */}
      <Handle
        type="source"
        position={Position.Top}
        id="vapor"
        style={{ left: '50%' }}
        className="w-2 h-2 bg-gray-400 border border-white opacity-60"
      />
    </div>
  );
};

export default DistillationColumnNode;