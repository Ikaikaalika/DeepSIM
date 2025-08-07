import { Flowsheet, SimulationResults, LLMResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public type: string = 'api_error'
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.detail || errorMessage;
        } catch {
          errorMessage = await response.text() || errorMessage;
        }
        
        throw new ApiError(errorMessage, response.status);
      }

      return response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Network or other errors
      if (error instanceof TypeError) {
        throw new ApiError('Network error - please check your connection', 0);
      }
      
      throw new ApiError(error instanceof Error ? error.message : 'Unknown error occurred', 500);
    }
  }

  async createFlowsheet(name: string, description?: string): Promise<{ flowsheet_id: string }> {
    return this.request('/flowsheet', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    });
  }

  async getFlowsheet(id: string): Promise<Flowsheet> {
    return this.request(`/flowsheet/${id}`);
  }

  async updateFlowsheet(id: string, update: Partial<Flowsheet>): Promise<{ message: string }> {
    return this.request(`/flowsheet/${id}`, {
      method: 'PUT',
      body: JSON.stringify(update),
    });
  }

  async deleteFlowsheet(id: string): Promise<{ message: string }> {
    return this.request(`/flowsheet/${id}`, {
      method: 'DELETE',
    });
  }

  async listFlowsheets(): Promise<{ flowsheets: Array<Omit<Flowsheet, 'units' | 'streams' | 'connections'>> }> {
    return this.request('/flowsheets');
  }

  async runSimulation(flowsheetId: string): Promise<SimulationResults> {
    return this.request('/simulate', {
      method: 'POST',
      body: JSON.stringify({ flowsheet_id: flowsheetId }),
    });
  }

  async chatWithLLM(
    message: string,
    flowsheetId?: string,
    context?: Record<string, any>
  ): Promise<LLMResponse> {
    return this.request('/llm/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        flowsheet_id: flowsheetId,
        context,
      }),
    });
  }

  async exportFlowsheet(id: string, format: string = 'json'): Promise<any> {
    return this.request(`/export/${id}?format=${format}`, {
      method: 'POST',
    });
  }

  async getUnitTypes(): Promise<{ unit_types: Array<{ type: string; description: string }> }> {
    return this.request('/units/types');
  }

  async checkHealth(): Promise<{ status: string; timestamp: string; services: Record<string, string> }> {
    return this.request('/health');
  }
}

export const apiService = new ApiService();