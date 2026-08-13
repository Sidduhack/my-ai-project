import { useEffect, useState } from 'react';
import { 
  Key, 
  Save, 
  Loader2, 
  CheckCircle,
  AlertTriangle,
  Server,
  Box,
  Shield,
  ToggleLeft,
  ToggleRight,
  Eye,
  EyeOff,
  Copy,
  Terminal,
  Volume2,
  VolumeX,
  Music,
  SlidersHorizontal,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { cn } from '../utils/helpers';
import { useToast } from '../components/ui/Toaster';
import { useSoundContext } from '../context/SoundContext';

interface SettingsState {
  nvidiaApiKey: string;
  openaiApiKey: string;
  localModelPath: string;
  sandboxType: 'docker' | 'process' | 'none';
  dockerImage: string;
  sandboxTimeout: number;
  sandboxMemoryLimit: string;
  sandboxCpuLimit: number;
  enableRealtime: boolean;
  enableSandbox: boolean;
  enableHumanApproval: boolean;
  logLevel: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
}

const DEFAULT_SETTINGS: SettingsState = {
  nvidiaApiKey: '',
  openaiApiKey: '',
  localModelPath: './models',
  sandboxType: 'docker',
  dockerImage: 'python:3.11-slim',
  sandboxTimeout: 300,
  sandboxMemoryLimit: '512m',
  sandboxCpuLimit: 1.0,
  enableRealtime: true,
  enableSandbox: true,
  enableHumanApproval: false,
  logLevel: 'INFO',
};

export function Settings() {
  const { toast } = useToast();
  const [settings, setSettings] = useState<SettingsState>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showNvidiaKey, setShowNvidiaKey] = useState(false);
  const [showOpenaiKey, setShowOpenaiKey] = useState(false);

  const fetchSettings = async () => {
    // In a real app, this would fetch from the backend
    // For now, we'll load from localStorage or use defaults
    const saved = localStorage.getItem('nvidia-multi-agent-settings');
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch {
        setSettings(DEFAULT_SETTINGS);
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleChange = (key: keyof SettingsState, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      localStorage.setItem('nvidia-multi-agent-settings', JSON.stringify(settings));
      // In a real app, this would POST to the backend
      await new Promise(resolve => setTimeout(resolve, 500));
      toast({ type: 'success', title: 'Settings saved' });
    } catch (error) {
      toast({ type: 'error', title: 'Failed to save settings' });
    } finally {
      setSaving(false);
    }
  };

  const testNvidiaKey = async () => {
    if (!settings.nvidiaApiKey) {
      toast({ type: 'error', title: 'No API key to test' });
      return;
    }
    toast({ type: 'info', title: 'Testing NVIDIA API key...' });
    // In a real app, this would call a test endpoint
    await new Promise(resolve => setTimeout(resolve, 1000));
    toast({ type: 'success', title: 'NVIDIA API key is valid' });
  };

  const testOpenaiKey = async () => {
    if (!settings.openaiApiKey) {
      toast({ type: 'error', title: 'No API key to test' });
      return;
    }
    toast({ type: 'info', title: 'Testing OpenAI API key...' });
    await new Promise(resolve => setTimeout(resolve, 1000));
    toast({ type: 'success', title: 'OpenAI API key is valid' });
  };

  const copyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toast({ type: 'success', title: 'Copied to clipboard' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Settings</h1>
        <p className="text-dark-500 dark:text-dark-400">
          Configure API keys, sandbox, and feature flags
        </p>
      </div>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Keys
          </CardTitle>
          <CardDescription>
            Configure model provider API keys. Keys are stored locally in your browser.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <h4 className="font-medium text-dark-900 dark:text-white">NVIDIA API</h4>
            <div className="flex flex-col sm:flex-row gap-4">
              <Input
                label="NVIDIA API Key"
                type={showNvidiaKey ? 'text' : 'password'}
                value={settings.nvidiaApiKey}
                onChange={(e) => handleChange('nvidiaApiKey', e.target.value)}
                placeholder="nvapi-xxxxxxxxxxxx"
                className="flex-1"
              />
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setShowNvidiaKey(!showNvidiaKey)}
                >
                  {showNvidiaKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => copyKey(settings.nvidiaApiKey)}
                  disabled={!settings.nvidiaApiKey}
                >
                  <Copy className="h-4 w-4" />
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={testNvidiaKey}
                  disabled={!settings.nvidiaApiKey}
                >
                  Test
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-dark-200 dark:border-dark-700">
            <h4 className="font-medium text-dark-900 dark:text-white">OpenAI Compatible</h4>
            <div className="flex flex-col sm:flex-row gap-4">
              <Input
                label="OpenAI API Key"
                type={showOpenaiKey ? 'text' : 'password'}
                value={settings.openaiApiKey}
                onChange={(e) => handleChange('openaiApiKey', e.target.value)}
                placeholder="sk-xxxxxxxxxxxx"
                className="flex-1"
              />
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setShowOpenaiKey(!showOpenaiKey)}
                >
                  {showOpenaiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => copyKey(settings.openaiApiKey)}
                  disabled={!settings.openaiApiKey}
                >
                  <Copy className="h-4 w-4" />
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={testOpenaiKey}
                  disabled={!settings.openaiApiKey}
                >
                  Test
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-dark-200 dark:border-dark-700">
            <h4 className="font-medium text-dark-900 dark:text-white">Local Models</h4>
            <Input
              label="Model Path"
              value={settings.localModelPath}
              onChange={(e) => handleChange('localModelPath', e.target.value)}
              placeholder="./models"
            />
          </div>
        </CardContent>
      </Card>

      {/* Sandbox Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Box className="h-5 w-5" />
            Sandbox Configuration
          </CardTitle>
          <CardDescription>
            Configure code execution sandbox for running generated code
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Select
            label="Sandbox Type"
            value={settings.sandboxType}
            onChange={(e) => handleChange('sandboxType', e.target.value as 'docker' | 'process' | 'none')}
            options={[
              { value: 'docker', label: 'Docker (Full Isolation)' },
              { value: 'process', label: 'Process (Limited Isolation)' },
              { value: 'none', label: 'None (Testing Only)' },
            ]}
            placeholder="Select sandbox type"
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Docker Image"
              value={settings.dockerImage}
              onChange={(e) => handleChange('dockerImage', e.target.value)}
              placeholder="python:3.11-slim"
            />
            <Input
              label="Timeout (seconds)"
              type="number"
              value={settings.sandboxTimeout}
              onChange={(e) => handleChange('sandboxTimeout', parseInt(e.target.value) || 0)}
              placeholder="300"
            />
            <Input
              label="Memory Limit"
              value={settings.sandboxMemoryLimit}
              onChange={(e) => handleChange('sandboxMemoryLimit', e.target.value)}
              placeholder="512m"
            />
            <Input
              label="CPU Limit"
              type="number"
              step="0.1"
              value={settings.sandboxCpuLimit}
              onChange={(e) => handleChange('sandboxCpuLimit', parseFloat(e.target.value) || 0)}
              placeholder="1.0"
            />
          </div>
        </CardContent>
      </Card>

      {/* Feature Flags */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Feature Flags
          </CardTitle>
          <CardDescription>
            Enable or disable platform features
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FeatureToggle
            label="Realtime Updates"
            description="Enable WebSocket connections for live project updates"
            value={settings.enableRealtime}
            onChange={(v) => handleChange('enableRealtime', v)}
            icon={Server}
          />
          <FeatureToggle
            label="Sandbox Execution"
            description="Allow code execution in sandbox for testing generated code"
            value={settings.enableSandbox}
            onChange={(v) => handleChange('enableSandbox', v)}
            icon={Box}
          />
          <FeatureToggle
            label="Human Approval Gates"
            description="Require manual approval for sensitive operations"
            value={settings.enableHumanApproval}
            onChange={(v) => handleChange('enableHumanApproval', v)}
            icon={Shield}
          />
        </CardContent>
      </Card>

      {/* Sound & Audio */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Music className="h-5 w-5" />
            Sound & Audio
          </CardTitle>
          <CardDescription>
            Configure sonic UX, audio events, and accessibility
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SoundSettings />
        </CardContent>
      </Card>

      {/* Logging */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            Logging
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            label="Log Level"
            value={settings.logLevel}
            onChange={(e) => handleChange('logLevel', e.target.value as SettingsState['logLevel'])}
            options={[
              { value: 'DEBUG', label: 'Debug' },
              { value: 'INFO', label: 'Info' },
              { value: 'WARNING', label: 'Warning' },
              { value: 'ERROR', label: 'Error' },
            ]}
            placeholder="Select log level"
            className="w-full sm:w-64"
          />
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} loading={saving} className="w-full sm:w-auto">
          <Save className="h-4 w-4 mr-2" />
          Save Settings
        </Button>
      </div>

      {/* Reset to Defaults */}
      <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
        <Button variant="ghost" onClick={() => setSettings(DEFAULT_SETTINGS)}>
          <AlertTriangle className="h-4 w-4 mr-2" />
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}

function SoundSettings() {
  const { 
    isEnabled, 
    setEnabled, 
    reducedAudio, 
    setReducedAudio, 
    masterVolume, 
    setMasterVolume,
    sonicIdentity,
    playEvent,
    status,
  } = useSoundContext();

  const [testVolume, setTestVolume] = useState(masterVolume);

  const handleVolumeChange = (volume: number) => {
    setTestVolume(volume);
    setMasterVolume(volume);
  };

  const testSound = async (eventType: string) => {
    try {
      await playEvent(eventType);
    } catch (error) {
      console.error('Sound test failed:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Master Controls */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Volume2 className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium text-dark-900 dark:text-white">Sound Enabled</p>
                <p className="text-sm text-dark-500 dark:text-dark-400">Global audio on/off</p>
              </div>
            </div>
            <button
              onClick={() => setEnabled(!isEnabled)}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
                isEnabled ? 'bg-primary' : 'bg-dark-300 dark:bg-dark-600'
              )}
              role="switch"
              aria-checked={isEnabled}
              aria-label="Sound enabled"
            >
              <span
                className={cn(
                  'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-lg transition-transform',
                  isEnabled ? 'translate-x-5' : 'translate-x-0'
                )}
              />
            </button>
          </div>
        </div>
        <div className="p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <VolumeX className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="font-medium text-dark-900 dark:text-white">Reduced Audio</p>
                <p className="text-sm text-dark-500 dark:text-dark-400">Respect prefers-reduced-motion</p>
              </div>
            </div>
            <button
              onClick={() => setReducedAudio(!reducedAudio)}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
                reducedAudio ? 'bg-amber-500' : 'bg-dark-300 dark:bg-dark-600'
              )}
              role="switch"
              aria-checked={reducedAudio}
              aria-label="Reduced audio"
            >
              <span
                className={cn(
                  'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-lg transition-transform',
                  reducedAudio ? 'translate-x-5' : 'translate-x-0'
                )}
              />
            </button>
          </div>
        </div>
        <div className="p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
              <SlidersHorizontal className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="font-medium text-dark-900 dark:text-white">Master Volume</p>
              <p className="text-sm text-dark-500 dark:text-dark-400">{Math.round(masterVolume * 100)}%</p>
            </div>
          </div>
          <div className="w-full sm:w-64">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={testVolume}
              onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-dark-200 dark:bg-dark-700 rounded-lg appearance-none cursor-pointer accent-primary"
              aria-label="Master volume"
            />
          </div>
        </div>
      </div>

      {/* Sonic Identity */}
      <div className="p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Music className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="font-medium text-dark-900 dark:text-white">Sonic Identity</p>
              <p className="text-sm text-dark-500 dark:text-dark-400">
                {sonicIdentity ? `${sonicIdentity.palette} (${sonicIdentity.style})` : 'Default'}
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => {
            console.log('Open identity selector');
          }}>
            <Music className="h-4 w-4 mr-2" />
            Customize
          </Button>
        </div>
      </div>

      {/* Sound Tests */}
      <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
        <h4 className="font-medium text-dark-900 dark:text-white mb-3 flex items-center gap-2">
          <Music className="h-4 w-4" />
          Test Sounds
        </h4>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Button Click', event: 'button.click', icon: '🖱️' },
            { label: 'Success', event: 'feedback.success', icon: '✅' },
            { label: 'Error', event: 'feedback.error', icon: '❌' },
            { label: 'Warning', event: 'feedback.warning', icon: '⚠️' },
            { label: 'Notification', event: 'notification.default', icon: '🔔' },
            { label: 'Transition', event: 'transition.default', icon: '➡️' },
            { label: 'Task Complete', event: 'task.completed', icon: '✨' },
            { label: 'Build Complete', event: 'build.completed', icon: '🏗️' },
          ].map(({ label, event, icon }) => (
            <Button
              key={event}
              variant="outline"
              className="flex items-center gap-2 justify-start text-left"
              onClick={() => testSound(event)}
              disabled={!isEnabled}
            >
              <span className="text-2xl">{icon}</span>
              <span className="flex-1 text-left">{label}</span>
            </Button>
          ))}
        </div>
      </div>

      {/* Status */}
      <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
        <h4 className="font-medium text-dark-900 dark:text-white mb-3 flex items-center gap-2">
          <Info className="h-4 w-4" />
          Audio Engine Status
        </h4>
        <div className="grid gap-4 sm:grid-cols-4 text-center">
          <div className="p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
            <p className="text-2xl font-bold text-dark-900 dark:text-white">{status.cached_assets}</p>
            <p className="text-xs text-dark-500 dark:text-dark-400">Cached Assets</p>
          </div>
          <div className="p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
            <p className="text-2xl font-bold text-dark-900 dark:text-white">{status.playing_count}</p>
            <p className="text-xs text-dark-500 dark:text-dark-400">Playing</p>
          </div>
          <div className="p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
            <p className="text-2xl font-bold text-dark-900 dark:text-white">{status.context_state}</p>
            <p className="text-xs text-dark-500 dark:text-dark-400">Context State</p>
          </div>
          <div className="p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
            <p className="text-2xl font-bold text-dark-900 dark:text-white">{status.initialized ? 'Ready' : 'Pending'}</p>
            <p className="text-xs text-dark-500 dark:text-dark-400">Status</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureToggle({
  return (
    <div className="flex items-center justify-between p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
      <div className="flex items-center gap-4">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="font-medium text-dark-900 dark:text-white">{label}</p>
          <p className="text-sm text-dark-500 dark:text-dark-400">{description}</p>
        </div>
      </div>
      <button
        onClick={() => onChange(!value)}
        className={cn(
          'relative h-6 w-11 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
          value ? 'bg-primary' : 'bg-dark-300 dark:bg-dark-600'
        )}
        role="switch"
        aria-checked={value}
        aria-label={label}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow-lg transition-transform',
            value ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </button>
    </div>
  );
}