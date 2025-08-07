import React, { useState, useCallback } from 'react';
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
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';

import FlowsheetCanvas from './components/FlowsheetCanvas';
import PropertiesPanel from './components/PropertiesPanel';
import ChatPanel from './components/ChatPanel';
import ResultsPanel from './components/ResultsPanel';
import Toolbar from './components/Toolbar';

function App() {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [flowsheetId, setFlowsheetId] = useState<string | null>(null);
  const [simulationResults, setSimulationResults] = useState<any>(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleNodeSelect = useCallback((node: Node | null) => {
    setSelectedNode(node);
  }, []);

  const handleSimulationComplete = useCallback((results: any) => {
    setSimulationResults(results);
    setIsSimulating(false);
  }, []);

  const handleSimulationStart = useCallback(() => {
    setIsSimulating(true);
    setSimulationResults(null);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50">
      <Toolbar 
        flowsheetId={flowsheetId}
        onSimulationStart={handleSimulationStart}
        onSimulationComplete={handleSimulationComplete}
        isSimulating={isSimulating}
      />
      
      <div className="flex-1 flex">
        <div className="flex-1 relative">
          <ReactFlowProvider>
            <FlowsheetCanvas
              onNodeSelect={handleNodeSelect}
              flowsheetId={flowsheetId}
              onFlowsheetIdChange={setFlowsheetId}
            />
          </ReactFlowProvider>
        </div>
        
        <div className="w-80 border-l border-gray-300 flex flex-col">
          <PropertiesPanel
            selectedNode={selectedNode}
            flowsheetId={flowsheetId}
          />
          
          <div className="border-t border-gray-300">
            <ResultsPanel
              results={simulationResults}
              isSimulating={isSimulating}
            />
          </div>
        </div>
        
        <div className="w-96 border-l border-gray-300">
          <ChatPanel
            flowsheetId={flowsheetId}
            simulationResults={simulationResults}
          />
        </div>
      </div>
    </div>
  );
}

export default App;