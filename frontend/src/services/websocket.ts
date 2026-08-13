import { io, Socket } from 'socket.io-client';
import type { WebSocketMessage, ProjectStatusResponse, Task, Event } from '../types';
import { soundEngineer } from './sound';

type EventCallback = (data: any) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<EventCallback>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(url?: string): void {
    if (this.socket?.connected) return;

    const wsUrl = url || import.meta.env.VITE_WS_URL || window.location.origin;
    
    this.socket = io(wsUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      autoConnect: true,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('disconnected', { connected: false, reason });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.emit('error', { message: 'Max reconnection attempts reached' });
      }
    });

    // Listen for all event types
    this.socket.onAny((eventName, data) => {
      // Handle audio events from backend
      if (eventName === 'audio_event' || (data && data.type === 'audio_event')) {
        soundEngineer.handleWebSocketMessage(data);
        return;
      }
      this.emit(eventName, data);
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  subscribe(eventName: string, callback: EventCallback): () => void {
    if (!this.listeners.has(eventName)) {
      this.listeners.set(eventName, new Set());
    }
    this.listeners.get(eventName)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.listeners.get(eventName)?.delete(callback);
    };
  }

  private emit(eventName: string, data: any): void {
    this.listeners.get(eventName)?.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in WebSocket listener for ${eventName}:`, error);
      }
    });
  }

  // Project-specific subscriptions
  subscribeToProject(projectId: string, callbacks: {
    onStatusUpdate?: (status: ProjectStatusResponse) => void;
    onTaskUpdate?: (task: Task) => void;
    onEvent?: (event: Event) => void;
  }): () => void {
    const unsubscribers: (() => void)[] = [];

    if (callbacks.onStatusUpdate) {
      unsubscribers.push(this.subscribe(`project:${projectId}:status`, callbacks.onStatusUpdate));
    }
    if (callbacks.onTaskUpdate) {
      unsubscribers.push(this.subscribe(`project:${projectId}:task`, callbacks.onTaskUpdate));
    }
    if (callbacks.onEvent) {
      unsubscribers.push(this.subscribe(`project:${projectId}:event`, callbacks.onEvent));
    }

    return () => {
      unsubscribers.forEach((unsub) => unsub());
    };
  }

  // Global subscriptions
  subscribeToSystem(callbacks: {
    onHealthChange?: (health: any) => void;
    onMetricsUpdate?: (metrics: any) => void;
  }): () => void {
    const unsubscribers: (() => void)[] = [];

    if (callbacks.onHealthChange) {
      unsubscribers.push(this.subscribe('system:health', callbacks.onHealthChange));
    }
    if (callbacks.onMetricsUpdate) {
      unsubscribers.push(this.subscribe('system:metrics', callbacks.onMetricsUpdate));
    }

    return () => {
      unsubscribers.forEach((unsub) => unsub());
    };
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const ws = new WebSocketService();