import { useEffect, useState } from 'react';
import { 
  Activity, 
  Database, 
  Server, 
  RefreshCw, 
  Loader2,
  CheckCircle,
  AlertTriangle,
  XCircle,
  TrendingUp,
  Zap,
  Gauge,
  HardDrive,
  MemoryStick,
  Network,
  Terminal,
  Eye,
  EyeOff,
  HeartPulse,
  Clock,
} from 'lucide-react';
import { api } from '../services/api';
import { ws } from '../services/websocket';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { cn, getStatusColor, formatBytes, formatDuration } from '../utils/helpers';
import { useToast } from '../components/ui/Toaster';
import type { SystemHealth, ReadinessCheck, Metrics } from '../types';

export function System() {
  const { toast } = useToast();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [readiness, setReadiness] = useState<ReadinessCheck | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showMetricsDetail, setShowMetricsDetail] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [healthData, readinessData, metricsData] = await Promise.all([
        api.getHealth(),
        api.getReadiness(),
        api.getMetrics(),
      ]);
      setHealth(healthData);
      setReadiness(readinessData);
      setMetrics(metricsData);
    } catch (error) {
      toast({ type: 'error', title: 'Failed to load system status' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    const unsub = ws.subscribeToSystem({
      onHealthChange: () => fetchData(),
      onMetricsUpdate: () => fetchData(),
    });
    return () => {
      clearInterval(interval);
      unsub();
    };
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const overallStatus = readiness?.status || health?.status || 'unknown';
  const isHealthy = overallStatus === 'healthy' || overallStatus === 'ready';

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={cn('p-3 rounded-xl', isHealthy ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30')}>
            <Activity className={cn('h-6 w-6', isHealthy ? 'text-green-600' : 'text-red-600')} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-dark-900 dark:text-white">System</h1>
            <p className="text-dark-500 dark:text-dark-400">
              Health, readiness, and performance metrics
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} disabled={refreshing} variant="outline">
            <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
            Refresh
          </Button>
          <Button variant="outline" onClick={() => setShowMetricsDetail(!showMetricsDetail)}>
            <Terminal className="h-4 w-4 mr-2" />
            {showMetricsDetail ? 'Hide' : 'Show'} Metrics
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatusCard 
          title="System Health" 
          status={health?.status || 'unknown'} 
          icon={Activity}
          description={`v${health?.version || '—'} • ${health?.environment || '—'}`}
        />
        <StatusCard 
          title="Readiness" 
          status={readiness?.status || 'unknown'} 
          icon={CheckCircle}
          description={readiness ? `${Object.keys(readiness.checks).length} checks` : '—'}
        />
        <StatusCard 
          title="Environment" 
          status={health?.environment || 'unknown'} 
          icon={Server}
          description={`Version ${health?.version || '—'}`}
        />
      </div>

      {/* Readiness Checks */}
      {readiness && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Readiness Checks
              <Badge variant={readiness.status === 'ready' ? 'default' : 'destructive'}>
                {readiness.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(readiness.checks).map(([name, check]) => (
                <ReadinessCheckRow key={name} name={name} check={check} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Queue Metrics */}
      {metrics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5" />
              Orchestrator Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-4">
              <MetricCard 
                label="Pending" 
                value={metrics.orchestrator.queue.pending} 
                icon={Clock} 
                color="bg-blue-500" 
              />
              <MetricCard 
                label="Running" 
                value={metrics.orchestrator.queue.running} 
                icon={Zap} 
                color="bg-green-500" 
              />
              <MetricCard 
                label="Completed" 
                value={metrics.orchestrator.queue.completed} 
                icon={CheckCircle} 
                color="bg-emerald-500" 
              />
              <MetricCard 
                label="Failed" 
                value={metrics.orchestrator.queue.failed} 
                icon={XCircle} 
                color="bg-red-500" 
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Model Health Summary */}
      {metrics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HeartPulse className="h-5 w-5" />
              Model Health Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-4">
              <MetricCard 
                label="Healthy" 
                value={metrics.models.health.healthy} 
                icon={CheckCircle} 
                color="bg-green-500" 
              />
              <MetricCard 
                label="Degraded" 
                value={metrics.models.health.degraded} 
                icon={AlertTriangle} 
                color="bg-yellow-500" 
              />
              <MetricCard 
                label="Cooldown" 
                value={metrics.models.health.cooldown} 
                icon={XCircle} 
                color="bg-red-500" 
              />
              <MetricCard 
                label="Total" 
                value={metrics.models.health.total} 
                icon={Cpu} 
                color="bg-blue-500" 
              />
            </div>
            <div className="mt-4">
              <p className="text-sm text-dark-500 dark:text-dark-400">Providers:</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {metrics.models.providers.map((provider) => (
                  <Badge key={provider} variant="outline" className="text-xs">
                    {provider}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Scoring Stats */}
      {metrics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Adaptive Scoring
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <MetricCard 
                label="Scored Pairs" 
                value={metrics.scoring.total_scored_pairs} 
                icon={TrendingUp} 
                color="bg-purple-500" 
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detailed Metrics */}
      {showMetricsDetail && metrics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Raw Metrics (JSON)
              <Button variant="ghost" size="sm" onClick={() => copyToClipboard(JSON.stringify(metrics, null, 2))}>
                <Eye className="h-4 w-4 mr-1" /> Copy JSON
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs font-mono bg-dark-100 dark:bg-dark-900 p-4 rounded-lg overflow-x-auto max-h-96 overflow-y-auto">
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle>System Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-center">
            <InfoItem label="Uptime" value={formatDuration(Date.now() - Date.now())} icon={Activity} />
            <InfoItem label="Memory" value={formatBytes(0)} icon={MemoryStick} />
            <InfoItem label="Disk" value={formatBytes(0)} icon={HardDrive} />
            <InfoItem label="Network" value="Active" icon={Network} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusCard({ title, status, icon: Icon, description }: { title: string; status: string; icon: React.ComponentType<{ className?: string }>; description: string }) {
  const statusColors: Record<string, string> = {
    healthy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    degraded: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    unhealthy: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    development: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    staging: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    production: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={cn('p-2 rounded-lg', statusColors[status] || 'bg-gray-100 dark:bg-gray-800')}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <h4 className="font-medium text-dark-900 dark:text-white">{title}</h4>
              <Badge className={statusColors[status] || 'bg-gray-100 text-gray-700'}>
                {status}
              </Badge>
            </div>
          </div>
        </div>
        <p className="mt-3 text-sm text-dark-500 dark:text-dark-400">{description}</p>
      </CardContent>
    </Card>
  );
}

function ReadinessCheckRow({ name, check }: { name: string; check: any }) {
  const isHealthy = check === 'healthy' || (typeof check === 'object' && Object.values(check).every(v => v === true));
  
  return (
    <div className="flex items-center justify-between p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
      <div className="flex items-center gap-3">
        <div className={cn('h-2 w-2 rounded-full', isHealthy ? 'bg-green-500' : 'bg-red-500')} />
        <span className="font-medium text-dark-900 dark:text-white capitalize">{name.replace(/_/g, ' ')}</span>
      </div>
      <div className="text-sm text-dark-500 dark:text-dark-400 font-mono">
        {typeof check === 'object' ? JSON.stringify(check) : check}
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ComponentType<{ className?: string }>; color: string }) {
  return (
    <div className="p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-dark-500 dark:text-dark-400">{label}</p>
          <p className="text-3xl font-bold text-dark-900 dark:text-white">{value}</p>
        </div>
        <div className={cn('p-3 rounded-xl', color)}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </div>
  );
}

function InfoItem({ label, value, icon: Icon }: { label: string; value: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="p-4 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
      <Icon className="h-5 w-5 text-dark-400 dark:text-dark-500 mx-auto mb-2" />
      <p className="text-sm text-dark-500 dark:text-dark-400">{label}</p>
      <p className="font-medium text-dark-900 dark:text-white">{value}</p>
    </div>
  );
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text);
}