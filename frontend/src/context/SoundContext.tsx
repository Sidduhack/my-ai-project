import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { soundEngineer, AudioEventType, AudioPriority, SoundEngineStatus, SonicIdentity, AudioAsset } from '../services/sound';

interface SoundContextValue {
  engineer: typeof soundEngineer;
  status: SoundEngineStatus;
  isInitialized: boolean;
  isEnabled: boolean;
  reducedAudio: boolean;
  masterVolume: number;
  sonicIdentity: SonicIdentity | null;
  initialize: () => Promise<void>;
  setEnabled: (enabled: boolean) => void;
  setReducedAudio: (reduced: boolean) => void;
  setMasterVolume: (volume: number) => void;
  playEvent: (systemEventType: string, metadata?: Record<string, any>) => Promise<boolean>;
  playAudioEvent: (audioEvent: { event_type: AudioEventType; trigger: string; metadata?: Record<string, any> }) => Promise<boolean>;
  loadAssets: (assets: AudioAsset[]) => Promise<void>;
  applySonicIdentity: (identity: SonicIdentity) => void;
}

const SoundContext = createContext<SoundContextValue | null>(null);

export function SoundProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SoundEngineStatus>({
    initialized: false,
    enabled: true,
    reduced_audio: false,
    master_volume: 1.0,
    playing_count: 0,
    cached_assets: 0,
    context_state: 'none',
    asset_count: 0,
    sonic_identity: null,
  });
  const [isInitialized, setIsInitialized] = useState(false);

  const updateStatus = useCallback(() => {
    setStatus(soundEngineer.getStatus());
  }, []);

  const initialize = useCallback(async () => {
    if (isInitialized) return;
    await soundEngineer.initialize();
    setIsInitialized(true);
    updateStatus();
    
    // Load asset manifest from backend if available
    try {
      const response = await fetch('/api/models/sound/manifest');
      if (response.ok) {
        const manifest = await response.json();
        await soundEngineer.loadAssetManifest(manifest);
        updateStatus();
      }
    } catch {
      // Manifest endpoint not available, using defaults
    }
  }, [isInitialized, updateStatus]);

  // Auto-initialize on mount
  useEffect(() => {
    initialize();
  }, [initialize]);

  // Periodic status updates
  useEffect(() => {
    if (!isInitialized) return;
    const interval = setInterval(updateStatus, 1000);
    return () => clearInterval(interval);
  }, [isInitialized, updateStatus]);

  const value: SoundContextValue = {
    engineer: soundEngineer,
    status,
    isInitialized,
    isEnabled: status.enabled,
    reducedAudio: status.reduced_audio,
    masterVolume: status.master_volume,
    sonicIdentity: status.sonic_identity,
    initialize,
    setEnabled: (enabled) => {
      soundEngineer.setEnabled(enabled);
      updateStatus();
    },
    setReducedAudio: (reduced) => {
      soundEngineer.setReducedAudio(reduced);
      updateStatus();
    },
    setMasterVolume: (volume) => {
      soundEngineer.setMasterVolume(volume);
      updateStatus();
    },
    playEvent: async (systemEventType, metadata) => {
      const result = await soundEngineer.playEvent(systemEventType, metadata);
      updateStatus();
      return result;
    },
    playAudioEvent: async (audioEvent) => {
      const result = await soundEngineer.playAudioEvent(audioEvent);
      updateStatus();
      return result;
    },
    loadAssets: async (assets) => {
      await soundEngineer.loadAssets(assets);
      updateStatus();
    },
    applySonicIdentity: (identity) => {
      soundEngineer.setSonicIdentity(identity);
      updateStatus();
    },
  };

  return (
    <SoundContext.Provider value={value}>
      {children}
    </SoundContext.Provider>
  );
}

export function useSoundContext() {
  const context = useContext(SoundContext);
  if (!context) {
    throw new Error('useSoundContext must be used within a SoundProvider');
  }
  return context;
}

// Convenience hooks
export function useSound() {
  const { engineer, playEvent, playAudioEvent, ...rest } = useSoundContext();
  return { ...rest, playEvent, playAudioEvent };
}

export function useSoundStatus() {
  const { status, isInitialized, ...rest } = useSoundContext();
  return { status, isInitialized, ...rest };
}

export function useSoundControls() {
  const { 
    setEnabled, 
    setReducedAudio, 
    setMasterVolume,
    isEnabled,
    reducedAudio,
    masterVolume,
  } = useSoundContext();
  return { setEnabled, setReducedAudio, setMasterVolume, isEnabled, reducedAudio, masterVolume };
}