/**
 * Web Audio Service - Frontend audio engine for Sonic UX
 * Integrates with backend SoundEngineerAgent asset definitions
 */

// Audio Event Types (must match backend)
export enum AudioEventType {
  // UI Interactions
  BUTTON_HOVER = "button.hover",
  BUTTON_CLICK = "button.click",
  BUTTON_PRESS = "button.press",
  BUTTON_RELEASE = "button.release",
  
  // Feedback
  SUCCESS = "feedback.success",
  ERROR = "feedback.error",
  WARNING = "feedback.warning",
  INFO = "feedback.info",
  
  // Notifications
  NOTIFICATION = "notification.default",
  NOTIFICATION_URGENT = "notification.urgent",
  NOTIFICATION_SUBTLE = "notification.subtle",
  
  // Loading & Transitions
  LOADING_START = "loading.start",
  LOADING_COMPLETE = "loading.complete",
  LOADING_PROGRESS = "loading.progress",
  TRANSITION = "transition.default",
  TRANSITION_PAGE = "transition.page",
  TRANSITION_MODAL = "transition.modal",
  
  // Project Lifecycle
  PROJECT_CREATED = "project.created",
  PROJECT_STARTED = "project.started",
  PROJECT_COMPLETED = "project.completed",
  PROJECT_FAILED = "project.failed",
  
  // Task Lifecycle
  TASK_STARTED = "task.started",
  TASK_COMPLETED = "task.completed",
  TASK_FAILED = "task.failed",
  TASK_BLOCKED = "task.blocked",
  
  // Agent Events
  AGENT_STARTED = "agent.started",
  AGENT_COMPLETED = "agent.completed",
  AGENT_FAILED = "agent.failed",
  
  // Model Events
  MODEL_SELECTED = "model.selected",
  MODEL_FALLBACK = "model.fallback",
  MODEL_RECOVERED = "model.recovered",
  
  // Build Events
  BUILD_STARTED = "build.started",
  BUILD_COMPLETED = "build.completed",
  BUILD_FAILED = "build.failed",
  
  // Test Events
  TEST_STARTED = "test.started",
  TEST_COMPLETED = "test.completed",
  TEST_FAILED = "test.failed",
  
  // Ambient
  AMBIENT_IDLE = "ambient.idle",
  AMBIENT_WORKING = "ambient.working",
  AMBIENT_FOCUS = "ambient.focus",
}

export enum AudioPriority {
  LOW = "low",
  NORMAL = "normal",
  HIGH = "high",
  CRITICAL = "critical",
}

export enum AudioFormat {
  WAV = "wav",
  MP3 = "mp3",
  OGG = "ogg",
  WEBM = "webm",
}

export interface AudioAsset {
  event_type: AudioEventType;
  asset_id: string;
  format: AudioFormat;
  duration_ms: number;
  volume: number;
  loop: boolean;
  priority: AudioPriority;
  tags: string[];
  description: string;
}

export interface AudioEvent {
  event_type: AudioEventType;
  trigger: string;
  timestamp: number;
  volume: number;
  priority: AudioPriority;
  metadata: Record<string, any>;
  spatial_position?: [number, number, number];
}

export interface AudioEventPayload {
  type: "audio_event";
  audio_event: AudioEvent;
  asset: {
    asset_id: string;
    duration_ms: number;
    volume: number;
    loop: boolean;
    priority: AudioPriority;
  };
  timestamp: number;
}

export interface SonicIdentity {
  palette: string;
  base_frequency: number;
  style: string;
  instruments: string[];
  color: string;
}

export interface SoundEngineStatus {
  initialized: boolean;
  enabled: boolean;
  reduced_audio: boolean;
  master_volume: number;
  playing_count: number;
  cached_assets: number;
  context_state: string;
  asset_count: number;
  sonic_identity: SonicIdentity | null;
}

class WebAudioEngine {
  private context: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private audioBuffers: Map<string, AudioBuffer> = new Map();
  private playingSources: Array<{ source: AudioBufferSourceNode; gain: GainNode; assetId: string }> = [];
  private enabled = true;
  private reducedAudio = false;
  private masterVolume = 1.0;
  private initialized = false;
  private initializationPromise: Promise<void> | null = null;

  async initialize(): Promise<void> {
    if (this.initialized) return;
    
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) {
        console.warn('Web Audio API not supported');
        return;
      }
      
      this.context = new AudioContextClass();
      this.masterGain = this.context.createGain();
      this.masterGain.connect(this.context.destination);
      this.masterGain.gain.value = this.masterVolume;
      this.initialized = true;
      console.log('Web Audio Engine initialized');
    } catch (error) {
      console.error('Web Audio Engine initialization failed:', error);
    }
  }

  async resume(): Promise<void> {
    if (this.context && this.context.state === 'suspended') {
      await this.context.resume();
    }
  }

  async loadAsset(asset: AudioAsset, base64Data?: string, filePath?: string): Promise<boolean> {
    if (!this.initialized) await this.initialize();
    if (!this.context) return false;
    if (this.audioBuffers.has(asset.asset_id)) return true;

    try {
      let arrayBuffer: ArrayBuffer;

      if (base64Data) {
        arrayBuffer = this.base64ToArrayBuffer(base64Data);
      } else if (filePath) {
        const response = await fetch(filePath);
        arrayBuffer = await response.arrayBuffer();
      } else {
        // Generate synthetic audio if no source provided
        return await this.generateSyntheticAsset(asset);
      }

      const audioBuffer = await this.context.decodeAudioData(arrayBuffer);
      this.audioBuffers.set(asset.asset_id, audioBuffer);
      console.log('Audio asset loaded:', asset.asset_id);
      return true;
    } catch (error) {
      console.error('Audio asset load failed:', asset.asset_id, error);
      return false;
    }
  }

  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  private async generateSyntheticAsset(asset: AudioAsset): Promise<boolean> {
    if (!this.context) return false;

    try {
      const sampleRate = this.context.sampleRate;
      const duration = asset.duration_ms / 1000;
      const numFrames = Math.ceil(sampleRate * duration);
      
      const offline = new OfflineAudioContext(1, numFrames, sampleRate);
      const osc = offline.createOscillator();
      const gain = offline.createGain();
      
      osc.type = 'sine';
      osc.frequency.value = this.getFrequencyForEvent(asset.event_type);
      gain.gain.value = asset.volume;
      
      osc.connect(gain);
      gain.connect(offline.destination);
      
      osc.start(0);
      osc.stop(duration);
      
      const rendered = await offline.startRendering();
      this.audioBuffers.set(asset.asset_id, rendered);
      return true;
    } catch (error) {
      console.error('Synthetic asset generation failed:', error);
      return false;
    }
  }

  private getFrequencyForEvent(eventType: AudioEventType): number {
    const frequencies: Record<AudioEventType, number> = {
      [AudioEventType.BUTTON_HOVER]: 800,
      [AudioEventType.BUTTON_CLICK]: 600,
      [AudioEventType.SUCCESS]: 523,
      [AudioEventType.ERROR]: 200,
      [AudioEventType.WARNING]: 400,
      [AudioEventType.NOTIFICATION]: 880,
      [AudioEventType.LOADING_START]: 440,
      [AudioEventType.TRANSITION]: 300,
      [AudioEventType.PROJECT_COMPLETED]: 659,
      [AudioEventType.BUILD_COMPLETED]: 659,
      [AudioEventType.TASK_COMPLETED]: 659,
      [AudioEventType.AGENT_STARTED]: 550,
      [AudioEventType.MODEL_FALLBACK]: 400,
      [AudioEventType.AMBIENT_IDLE]: 220,
      [AudioEventType.AMBIENT_WORKING]: 330,
      [AudioEventType.AMBIENT_FOCUS]: 440,
      [AudioEventType.TASK_STARTED]: 440,
      [AudioEventType.TASK_FAILED]: 150,
      [AudioEventType.TASK_BLOCKED]: 300,
      [AudioEventType.AGENT_COMPLETED]: 784,
      [AudioEventType.AGENT_FAILED]: 150,
      [AudioEventType.PROJECT_CREATED]: 440,
      [AudioEventType.PROJECT_STARTED]: 523,
      [AudioEventType.PROJECT_FAILED]: 150,
      [AudioEventType.MODEL_SELECTED]: 550,
      [AudioEventType.MODEL_RECOVERED]: 659,
      [AudioEventType.BUILD_STARTED]: 440,
      [AudioEventType.BUILD_FAILED]: 150,
      [AudioEventType.TEST_STARTED]: 440,
      [AudioEventType.TEST_COMPLETED]: 784,
      [AudioEventType.TEST_FAILED]: 150,
      [AudioEventType.LOADING_COMPLETE]: 784,
      [AudioEventType.LOADING_PROGRESS]: 440,
      [AudioEventType.TRANSITION_PAGE]: 300,
      [AudioEventType.TRANSITION_MODAL]: 350,
      [AudioEventType.NOTIFICATION_URGENT]: 880,
      [AudioEventType.NOTIFICATION_SUBTLE]: 660,
      [AudioEventType.BUTTON_PRESS]: 500,
      [AudioEventType.BUTTON_RELEASE]: 600,
      [AudioEventType.INFO]: 523,
    };
    return frequencies[eventType] || 440;
  }

  async play(event: AudioEvent, asset: AudioAsset): Promise<boolean> {
    if (!this.enabled || !this.initialized || !this.context) return false;
    if (this.reducedAudio && (asset.priority === AudioPriority.LOW || asset.priority === AudioPriority.NORMAL)) {
      return false;
    }

    try {
      if (this.context.state === 'suspended') {
        await this.resume();
      }

      let audioBuffer = this.audioBuffers.get(asset.asset_id);
      if (!audioBuffer) {
        const loaded = await this.loadAsset(asset);
        if (!loaded) return false;
        audioBuffer = this.audioBuffers.get(asset.asset_id)!;
      }

      const source = this.context.createBufferSource();
      source.buffer = audioBuffer;
      
      const gain = this.context.createGain();
      gain.gain.value = asset.volume * event.volume * this.masterVolume;
      
      source.connect(gain);
      gain.connect(this.masterGain!);
      
      if (asset.loop) {
        source.loop = true;
      }
      
      source.start(0);
      this.playingSources.push({ source, gain, assetId: asset.asset_id });
      
      source.onended = () => {
        this.playingSources = this.playingSources.filter(s => s.source !== source);
        gain.disconnect();
      };
      
      return true;
    } catch (error) {
      console.error('Audio play failed:', event.event_type, error);
      return false;
    }
  }

  async stop(assetId: string): Promise<void> {
    const sources = this.playingSources.filter(s => s.assetId === assetId);
    for (const { source, gain } of sources) {
      try {
        source.stop();
        gain.disconnect();
      } catch {}
    }
    this.playingSources = this.playingSources.filter(s => s.assetId !== assetId);
  }

  async stopAll(): Promise<void> {
    for (const { source, gain } of this.playingSources) {
      try {
        source.stop();
        gain.disconnect();
      } catch {}
    }
    this.playingSources = [];
  }

  setMasterVolume(volume: number): void {
    this.masterVolume = Math.max(0, Math.min(1, volume));
    if (this.masterGain) {
      this.masterGain.gain.value = this.masterVolume;
    }
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) this.stopAll();
  }

  setReducedAudio(reduced: boolean): void {
    this.reducedAudio = reduced;
  }

  getStatus(): SoundEngineStatus {
    return {
      initialized: this.initialized,
      enabled: this.enabled,
      reduced_audio: this.reducedAudio,
      master_volume: this.masterVolume,
      playing_count: this.playingSources.length,
      cached_assets: this.audioBuffers.size,
      context_state: this.context?.state || 'none',
      asset_count: this.audioBuffers.size,
      sonic_identity: null,
    };
  }
}

class SoundEngineerClient {
  private engine = new WebAudioEngine();
  private assetRegistry: Map<string, AudioAsset> = new Map();
  private sonicIdentity: SonicIdentity | null = null;
  private eventToAudioMap: Map<string, AudioEventType> = new Map();
  private eventHandlers: Map<string, (payload: AudioEventPayload) => void> = new Map();
  private wsCallback: ((payload: AudioEventPayload) => void) | null = null;

  constructor() {
    this.initializeDefaultMapping();
    this.initializeDefaultAssets();
  }

  private initializeDefaultMapping(): void {
    const mapping: Record<string, AudioEventType> = {
      'task.created': AudioEventType.TASK_STARTED,
      'task.started': AudioEventType.TASK_STARTED,
      'task.completed': AudioEventType.TASK_COMPLETED,
      'task.failed': AudioEventType.TASK_FAILED,
      'task.blocked': AudioEventType.TASK_BLOCKED,
      'agent.started': AudioEventType.AGENT_STARTED,
      'agent.completed': AudioEventType.AGENT_COMPLETED,
      'agent.failed': AudioEventType.AGENT_FAILED,
      'project.created': AudioEventType.PROJECT_CREATED,
      'project.started': AudioEventType.PROJECT_STARTED,
      'project.completed': AudioEventType.PROJECT_COMPLETED,
      'project.failed': AudioEventType.PROJECT_FAILED,
      'model.selected': AudioEventType.MODEL_SELECTED,
      'model.fallback': AudioEventType.MODEL_FALLBACK,
      'model.recovered': AudioEventType.MODEL_RECOVERED,
      'build.started': AudioEventType.BUILD_STARTED,
      'build.completed': AudioEventType.BUILD_COMPLETED,
      'build.failed': AudioEventType.BUILD_FAILED,
      'test.started': AudioEventType.TEST_STARTED,
      'test.completed': AudioEventType.TEST_COMPLETED,
      'test.failed': AudioEventType.TEST_FAILED,
    };

    for (const [event, audioType] of Object.entries(mapping)) {
      this.eventToAudioMap.set(event, audioType);
    }
  }

  private initializeDefaultAssets(): void {
    const defaults: Partial<Record<AudioEventType, Partial<AudioAsset>>> = {
      [AudioEventType.BUTTON_HOVER]: { duration_ms: 50, volume: 0.1, priority: AudioPriority.LOW },
      [AudioEventType.BUTTON_CLICK]: { duration_ms: 100, volume: 0.2, priority: AudioPriority.NORMAL },
      [AudioEventType.SUCCESS]: { duration_ms: 350, volume: 0.35, priority: AudioPriority.HIGH },
      [AudioEventType.ERROR]: { duration_ms: 500, volume: 0.4, priority: AudioPriority.CRITICAL },
      [AudioEventType.WARNING]: { duration_ms: 400, volume: 0.3, priority: AudioPriority.HIGH },
      [AudioEventType.NOTIFICATION]: { duration_ms: 300, volume: 0.25, priority: AudioPriority.NORMAL },
      [AudioEventType.LOADING_START]: { duration_ms: 200, volume: 0.15, priority: AudioPriority.LOW },
      [AudioEventType.TRANSITION]: { duration_ms: 200, volume: 0.2, priority: AudioPriority.LOW },
      [AudioEventType.PROJECT_COMPLETED]: { duration_ms: 1000, volume: 0.4, priority: AudioPriority.HIGH },
      [AudioEventType.BUILD_COMPLETED]: { duration_ms: 800, volume: 0.35, priority: AudioPriority.HIGH },
      [AudioEventType.TASK_COMPLETED]: { duration_ms: 300, volume: 0.3, priority: AudioPriority.NORMAL },
      [AudioEventType.AGENT_STARTED]: { duration_ms: 150, volume: 0.2, priority: AudioPriority.NORMAL },
      [AudioEventType.MODEL_FALLBACK]: { duration_ms: 250, volume: 0.25, priority: AudioPriority.NORMAL },
      [AudioEventType.AMBIENT_IDLE]: { duration_ms: 30000, volume: 0.05, loop: true, priority: AudioPriority.LOW },
      [AudioEventType.AMBIENT_WORKING]: { duration_ms: 60000, volume: 0.08, loop: true, priority: AudioPriority.LOW },
    };

    for (const [eventType, config] of Object.entries(defaults)) {
      const asset: AudioAsset = {
        event_type: eventType as AudioEventType,
        asset_id: eventType.toLowerCase().replace('.', '_'),
        format: AudioFormat.WAV,
        duration_ms: config.duration_ms || 200,
        volume: config.volume || 0.3,
        loop: config.loop || false,
        priority: config.priority || AudioPriority.NORMAL,
        tags: ['default'],
        description: `Default ${eventType} sound`,
      };
      this.assetRegistry.set(asset.asset_id, asset);
    }
  }

  async initialize(): Promise<void> {
    await this.engine.initialize();
  }

  async loadAssets(assets: AudioAsset[]): Promise<void> {
    for (const asset of assets) {
      this.assetRegistry.set(asset.asset_id, asset);
      await this.engine.loadAsset(asset);
    }
  }

  async loadAssetManifest(manifest: any[]): Promise<void> {
    for (const item of manifest) {
      const asset: AudioAsset = {
        event_type: item.event_type,
        asset_id: item.asset_id,
        format: item.format,
        duration_ms: item.duration_ms,
        volume: item.volume,
        loop: item.loop,
        priority: item.priority,
        tags: item.tags,
        description: item.description,
      };
      this.assetRegistry.set(asset.asset_id, asset);
      // Note: actual audio loading happens on first play or explicit load
    }
  }

  setSonicIdentity(identity: SonicIdentity): void {
    this.sonicIdentity = identity;
    console.log('Sonic identity applied:', identity);
  }

  getSonicIdentity(): SonicIdentity | null {
    return this.sonicIdentity;
  }

  registerAsset(asset: AudioAsset): void {
    this.assetRegistry.set(asset.asset_id, asset);
  }

  getAsset(assetId: string): AudioAsset | undefined {
    return this.assetRegistry.get(assetId);
  }

  getAssetForEvent(eventType: AudioEventType): AudioAsset | undefined {
    for (const asset of this.assetRegistry.values()) {
      if (asset.event_type === eventType) return asset;
    }
    return undefined;
  }

  getAllAssets(): AudioAsset[] {
    return Array.from(this.assetRegistry.values());
  }

  async playEvent(systemEventType: string, metadata?: Record<string, any>): Promise<boolean> {
    const audioType = this.eventToAudioMap.get(systemEventType);
    if (!audioType) return false;

    const asset = this.getAssetForEvent(audioType);
    if (!asset) return false;

    const event: AudioEvent = {
      event_type: audioType,
      trigger: systemEventType,
      timestamp: Date.now() / 1000,
      volume: 1.0,
      priority: asset.priority,
      metadata: metadata || {},
    };

    return await this.engine.play(event, asset);
  }

  async playAudioEvent(audioEvent: AudioEvent): Promise<boolean> {
    const asset = this.getAssetForEvent(audioEvent.event_type);
    if (!asset) return false;
    return await this.engine.play(audioEvent, asset);
  }

  setMasterVolume(volume: number): void {
    this.engine.setMasterVolume(volume);
  }

  setEnabled(enabled: boolean): void {
    this.engine.setEnabled(enabled);
  }

  setReducedAudio(reduced: boolean): void {
    this.engine.setReducedAudio(reduced);
  }

  getStatus(): SoundEngineStatus {
    const status = this.engine.getStatus();
    return {
      ...status,
      asset_count: this.assetRegistry.size,
      sonic_identity: this.sonicIdentity,
    };
  }

  // WebSocket integration
  setWebSocketCallback(callback: (payload: AudioEventPayload) => void): void {
    this.wsCallback = callback;
  }

  handleWebSocketMessage(message: any): void {
    if (message.type === 'audio_event' && message.audio_event && message.asset) {
      const audioEvent: AudioEvent = message.audio_event;
      const asset: AudioAsset = {
        event_type: audioEvent.event_type,
        asset_id: message.asset.asset_id,
        format: AudioFormat.WAV,
        duration_ms: message.asset.duration_ms,
        volume: message.asset.volume,
        loop: message.asset.loop,
        priority: message.asset.priority,
        tags: [],
        description: '',
      };
      this.engine.play(audioEvent, asset);
    }
  }

  // UI sound helpers
  async playButtonHover(): Promise<void> {
    await this.playEvent('button.hover');
  }

  async playButtonClick(): Promise<void> {
    await this.playEvent('button.click');
  }

  async playSuccess(): Promise<void> {
    await this.playEvent('feedback.success');
  }

  async playError(): Promise<void> {
    await this.playEvent('feedback.error');
  }

  async playWarning(): Promise<void> {
    await this.playEvent('feedback.warning');
  }

  async playNotification(): Promise<void> {
    await this.playEvent('notification.default');
  }

  async playTransition(): Promise<void> {
    await this.playEvent('transition.default');
  }

  async playLoadingStart(): Promise<void> {
    await this.playEvent('loading.start');
  }

  async playLoadingComplete(): Promise<void> {
    await this.playEvent('loading.complete');
  }
}

// Singleton instance
export const soundEngineer = new SoundEngineerClient();

// React hook
export function useSound() {
  return soundEngineer;
}

export { WebAudioEngine, SoundEngineerClient };