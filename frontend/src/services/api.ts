import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  Project,
  ProjectCreate,
  ProjectStatusResponse,
  Task,
  Agent,
  AgentTypeInfo,
  Model,
  ModelHealth,
  ModelScore,
  ModelRoute,
  SystemHealth,
  ReadinessCheck,
  Metrics,
  Event,
  AgentMemory,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    const response = await this.client.get<Project[]>('/projects');
    return response.data;
  }

  async getProject(id: string): Promise<Project> {
    const response = await this.client.get<Project>(`/projects/${id}`);
    return response.data;
  }

  async createProject(data: ProjectCreate): Promise<Project> {
    const response = await this.client.post<Project>('/projects', data);
    return response.data;
  }

  async startProject(id: string): Promise<Project> {
    const response = await this.client.post<Project>(`/projects/${id}/start`);
    return response.data;
  }

  async pauseProject(id: string): Promise<Project> {
    const response = await this.client.post<Project>(`/projects/${id}/pause`);
    return response.data;
  }

  async cancelProject(id: string): Promise<Project> {
    const response = await this.client.post<Project>(`/projects/${id}/cancel`);
    return response.data;
  }

  async getProjectStatus(id: string): Promise<ProjectStatusResponse> {
    const response = await this.client.get<ProjectStatusResponse>(`/projects/${id}/status`);
    return response.data;
  }

  async getProjectTasks(id: string): Promise<Task[]> {
    const response = await this.client.get<Task[]>(`/projects/${id}/tasks`);
    return response.data;
  }

  async getProjectEvents(id: string): Promise<Event[]> {
    const response = await this.client.get<Event[]>(`/projects/${id}/events`);
    return response.data;
  }

  // Agents
  async getAgents(): Promise<Agent[]> {
    const response = await this.client.get<Agent[]>('/agents');
    return response.data;
  }

  async getAgentTypes(): Promise<AgentTypeInfo[]> {
    const response = await this.client.get<AgentTypeInfo[]>('/agents/types');
    return response.data;
  }

  async getAgent(id: string): Promise<Agent> {
    const response = await this.client.get<Agent>(`/agents/${id}`);
    return response.data;
  }

  async getAgentMemory(agentId: string): Promise<AgentMemory> {
    const response = await this.client.get<AgentMemory>(`/agents/${agentId}/memory`);
    return response.data;
  }

  async setAgentMemory(agentId: string, key: string, value: Record<string, any>): Promise<void> {
    await this.client.post(`/agents/${agentId}/memory`, { key, value });
  }

  // Models
  async getModels(provider?: string): Promise<Model[]> {
    const response = await this.client.get<Model[]>('/models', { params: { provider } });
    return response.data;
  }

  async getModelsHealth(): Promise<ModelHealth[]> {
    const response = await this.client.get<ModelHealth[]>('/models/health');
    return response.data;
  }

  async getModelHealth(provider: string, modelId: string): Promise<ModelHealth> {
    const response = await this.client.get<ModelHealth>(`/models/health/${provider}/${modelId}`);
    return response.data;
  }

  async getModelScores(agentType?: string): Promise<ModelScore[]> {
    const response = await this.client.get<ModelScore[]>('/models/scores', { 
      params: { agent_type: agentType } 
    });
    return response.data;
  }

  async getAgentModelScores(agentType: string): Promise<ModelScore[]> {
    const response = await this.client.get<ModelScore[]>(`/models/scores/${agentType}`);
    return response.data;
  }

  async getModelRoutes(): Promise<Record<string, ModelRoute>> {
    const response = await this.client.get<Record<string, ModelRoute>>('/models/routes');
    return response.data;
  }

  async triggerHealthCheck(): Promise<Record<string, boolean>> {
    const response = await this.client.post<Record<string, boolean>>('/models/health/check');
    return response.data;
  }

  async getProviders(): Promise<Record<string, string[]>> {
    const response = await this.client.get<Record<string, string[]>>('/models/providers');
    return response.data;
  }

  // System
  async getHealth(): Promise<SystemHealth> {
    const response = await this.client.get<SystemHealth>('/system/health');
    return response.data;
  }

  async getReadiness(): Promise<ReadinessCheck> {
    const response = await this.client.get<ReadinessCheck>('/system/health/ready');
    return response.data;
  }

  async getLiveness(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/system/health/live');
    return response.data;
  }

  async getMetrics(): Promise<Metrics> {
    const response = await this.client.get<Metrics>('/system/metrics');
    return response.data;
  }
}

export const api = new ApiService();