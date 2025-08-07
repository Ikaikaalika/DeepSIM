export interface UnitOperation {
  id: string;
  type: string;
  name: string;
  position: { x: number; y: number };
  parameters: Record<string, any>;
  inlet_ports: string[];
  outlet_ports: string[];
}

export interface Stream {
  id: string;
  name: string;
  temperature?: number;
  pressure?: number;
  molar_flow?: number;
  mass_flow?: number;
  composition: Record<string, number>;
  properties: Record<string, any>;
}

export interface Connection {
  id: string;
  from_unit: string;
  from_port: string;
  to_unit: string;
  to_port: string;
  stream_id: string;
}

export interface Flowsheet {
  id: string;
  name: string;
  description: string;
  units: UnitOperation[];
  streams: Stream[];
  connections: Connection[];
  simulation_results?: any;
  created_at: string;
  updated_at: string;
}

export interface SimulationResults {
  simulation_id: string;
  status: string;
  timestamp: string;
  units: Record<string, any>;
  streams: Record<string, any>;
  convergence?: any;
  error?: string;
}

export interface LLMResponse {
  action: string;
  message: string;
  flowsheet_update?: any;
  analysis?: any;
  recommendations?: string[];
  reasoning?: string;
  timestamp: string;
}

export const UNIT_TYPES = [
  'Reactor',
  'Heater', 
  'Cooler',
  'Pump',
  'Compressor',
  'Valve',
  'DistillationColumn',
  'Mixer',
  'Splitter',
  'Flash',
  'HeatExchanger'
] as const;

export type UnitType = typeof UNIT_TYPES[number];