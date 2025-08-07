import React, { useCallback, useEffect, useState, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  NodeTypes,
  useReactFlow,
  MiniMap,
  Panel,
  ReactFlowInstance,
  ConnectionMode,
} from 'reactflow';
import { Plus } from 'lucide-react';

import { UnitOperation, UNIT_TYPES } from '../types';
import { apiService } from '../services/api';
import UnitNode from './UnitNode';
import DistillationColumnNode from './DistillationColumnNode';

const nodeTypes: NodeTypes = {
  unit: UnitNode,
  distillationColumn: DistillationColumnNode,
};

interface FlowsheetCanvasProps {
  onNodeSelect: (node: Node | null) => void;
  flowsheetId: string | null;
  onFlowsheetIdChange: (id: string | null) => void;
}

const FlowsheetCanvas: React.FC<FlowsheetCanvasProps> = ({
  onNodeSelect,
  flowsheetId,
  onFlowsheetIdChange,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showUnitPalette, setShowUnitPalette] = useState(false);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
  const [history, setHistory] = useState<{ nodes: Node[], edges: Edge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const { project, getNodes, getEdges } = useReactFlow();

  // History management for undo/redo
  const saveToHistory = useCallback(() => {
    const currentState = { nodes: getNodes(), edges: getEdges() };
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push(currentState);
      return newHistory;
    });
    setHistoryIndex(prev => prev + 1);
  }, [getNodes, getEdges, historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const previousState = history[historyIndex - 1];
      setNodes(previousState.nodes);
      setEdges(previousState.edges);
      setHistoryIndex(prev => prev - 1);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1];
      setNodes(nextState.nodes);
      setEdges(nextState.edges);
      setHistoryIndex(prev => prev + 1);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        redo();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge(params, eds));
      saveToHistory();
    },
    [setEdges, saveToHistory]
  );

  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      onNodeSelect(node);
    },
    [onNodeSelect]
  );

  const onPaneClick = useCallback(() => {
    onNodeSelect(null);
    setShowUnitPalette(false);
  }, [onNodeSelect]);

  const onPaneContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    const position = project({ x: event.clientX, y: event.clientY });
    setShowUnitPalette(true);
  }, [project]);

  const addUnit = useCallback(
    (unitType: string) => {
      const id = `${unitType.toLowerCase()}_${Date.now()}`;
      
      // Special handling for distillation column
      const nodeType = unitType === 'DistillationColumn' ? 'distillationColumn' : 'unit';
      const defaultParams = unitType === 'DistillationColumn' ? {
        stages: 20,
        refluxRatio: 2.0,
        feedStage: 10,
        distillateRate: 50,
        pressure: 101325,
        trayEfficiency: 0.75
      } : {};
      
      const newNode: Node = {
        id,
        type: nodeType,
        position: { x: 300, y: 300 },
        data: {
          unitType,
          name: `${unitType} ${nodes.length + 1}`,
          parameters: defaultParams,
        },
      };

      setNodes((nds) => [...nds, newNode]);
      setShowUnitPalette(false);
      saveToHistory();

      if (flowsheetId) {
        updateFlowsheetInBackend();
      }
    },
    [nodes.length, setNodes, flowsheetId, saveToHistory]
  );

  const updateFlowsheetInBackend = useCallback(async () => {
    if (!flowsheetId) return;

    try {
      const units: UnitOperation[] = nodes.map((node) => ({
        id: node.id,
        type: node.data.unitType,
        name: node.data.name,
        position: node.position,
        parameters: node.data.parameters || {},
        inlet_ports: ['in1'],
        outlet_ports: ['out1'],
      }));

      const connections = edges.map((edge) => ({
        id: edge.id,
        from_unit: edge.source,
        from_port: 'out1',
        to_unit: edge.target,
        to_port: 'in1',
        stream_id: `stream_${edge.id}`,
      }));

      await apiService.updateFlowsheet(flowsheetId, {
        units,
        connections,
      });
    } catch (error) {
      console.error('Failed to update flowsheet:', error);
    }
  }, [flowsheetId, nodes, edges]);

  const loadFlowsheet = useCallback(async (id: string) => {
    try {
      const flowsheet = await apiService.getFlowsheet(id);
      
      const flowNodes: Node[] = flowsheet.units.map((unit) => ({
        id: unit.id,
        type: 'unit',
        position: unit.position,
        data: {
          unitType: unit.type,
          name: unit.name,
          parameters: unit.parameters,
        },
      }));

      const flowEdges: Edge[] = flowsheet.connections.map((conn) => ({
        id: conn.id,
        source: conn.from_unit,
        target: conn.to_unit,
        type: 'default',
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (error) {
      console.error('Failed to load flowsheet:', error);
    }
  }, [setNodes, setEdges]);

  const createNewFlowsheet = useCallback(async () => {
    try {
      const response = await apiService.createFlowsheet('New Flowsheet');
      onFlowsheetIdChange(response.flowsheet_id);
    } catch (error) {
      console.error('Failed to create flowsheet:', error);
    }
  }, [onFlowsheetIdChange]);

  useEffect(() => {
    if (flowsheetId) {
      loadFlowsheet(flowsheetId);
    }
  }, [flowsheetId, loadFlowsheet]);

  useEffect(() => {
    if (nodes.length > 0 || edges.length > 0) {
      updateFlowsheetInBackend();
    }
  }, [nodes, edges, updateFlowsheetInBackend]);

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onPaneContextMenu={onPaneContextMenu}
        onInit={setRfInstance}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[20, 20]}
        connectionMode={ConnectionMode.Loose}
        defaultEdgeOptions={{
          animated: false,
          style: { stroke: '#374151', strokeWidth: 2 },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Controls showInteractive={false} />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <MiniMap 
          nodeColor={(node) => {
            switch (node.data?.unitType) {
              case 'Reactor': return '#10B981';
              case 'Heater': return '#EF4444'; 
              case 'Cooler': return '#3B82F6';
              case 'DistillationColumn': return '#8B5CF6';
              default: return '#6B7280';
            }
          }}
          pannable
          zoomable
        />
        
        <Panel position="top-right" className="bg-white rounded-md shadow-md p-2">
          <div className="flex gap-2">
            <button
              onClick={undo}
              disabled={historyIndex <= 0}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 rounded"
              title="Undo (Ctrl+Z)"
            >
              Undo
            </button>
            <button
              onClick={redo}
              disabled={historyIndex >= history.length - 1}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 rounded"
              title="Redo (Ctrl+Y)"
            >
              Redo
            </button>
          </div>
        </Panel>
      </ReactFlow>

      {!flowsheetId && (
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
          <div className="text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              No flowsheet loaded
            </h3>
            <button
              onClick={createNewFlowsheet}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Create New Flowsheet
            </button>
          </div>
        </div>
      )}

      {showUnitPalette && (
        <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg border p-4">
          <h4 className="font-medium text-gray-900 mb-3">Add Unit Operation</h4>
          <div className="grid grid-cols-2 gap-2">
            {UNIT_TYPES.map((unitType) => (
              <button
                key={unitType}
                onClick={() => addUnit(unitType)}
                className="p-3 text-sm border rounded-md hover:bg-gray-50 text-left"
              >
                {unitType}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="absolute top-4 right-4">
        <button
          onClick={() => setShowUnitPalette(!showUnitPalette)}
          className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700"
          title="Add Unit"
        >
          <Plus size={20} />
        </button>
      </div>
    </div>
  );
};

export default FlowsheetCanvas;