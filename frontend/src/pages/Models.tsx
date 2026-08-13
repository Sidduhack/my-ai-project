import { useEffect, useState } from 'react';
import { 
  Cpu, 
  HeartPulse, 
  TrendingUp, 
  RefreshCw, 
  Loader2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Zap,
  BarChart3,
  Settings,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';
import { api } from '../services/api';
import { ws } from '../services/websocket';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import { cn, getStatusColor, getPriorityColor } from '../utils/helpers';
import { useToast } from '../components/ui/Toaster';
import type { Model, ModelHealth, ModelScore, ModelRoute, AgentType } from '../types';

export function Models() {
  const { toast } = useToast();
  const [models, setModels] = useState<Model[]>([]);
  const [modelHealth, setModelHealth] = useState<ModelHealth[]>([]);
  const [modelRoutes, setModelRoutes] = useState<Record<string, ModelRoute>>({});
  const [selectedAgentType, setSelectedAgentType] = useState<string>('all');
  const [agentTypes] = useState<AgentType[]>([
    'planner', 'architect', 'ui_ux', 'creative_director', 'motion_designer',
    'frontend', 'backend', 'database', 'security', 'performance',
    'testing', 'integration', 'debugging', 'sound_engineer',
    'accessibility', 'seo', 'documentation', 'code_reviewer'
  ]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scoresByAgent, setScoresByAgent] = useState<Record<string, ModelScore[]>>({});
  const [viewMode, setViewMode] = useState<'health' | 'scoring' | 'routes'>('health');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [modelsData, healthData, routesData] = await Promise.all([
        api.getModels(),
        api.getModelsHealth(),
        api.getModelRoutes(),
      ]);
      setModels(modelsData);
      setModelHealth(healthData);
      setModelRoutes(routesData);

      // Fetch scores for each agent type
      for (const agentType of agentTypes) {
        const scores = await api.getAgentModelScores(agentType);
        setScoresByAgent(prev => ({ ...prev, [agentType]: scores }));
      }
    } catch (error) {
      toast({ type: 'error', title: 'Failed to load models' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    const unsub = ws.subscribeToSystem({
      onHealthChange: () => fetchData(),
    });
    return () => unsub();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const triggerHealthCheck = async () => {
    try {
      await api.triggerHealthCheck();
      toast({ type: 'success', title: 'Health check triggered' });
      fetchData();
    } catch {
      toast({ type: 'error', title: 'Failed to trigger health check' });
    }
  };

  const getHealthForModel = (provider: string, modelId: string): ModelHealth | undefined => {
    return modelHealth.find(h => h.provider === provider && h.model_id === modelId);
  };

  const filteredModels = models;
  const healthyCount = modelHealth.filter(h => h.state === 'healthy').length;
  const degradedCount = modelHealth.filter(h => h.state === 'degraded').length;
  const cooldownCount = modelHealth.filter(h => h.state === 'cooldown').length;
  const totalModels = modelHealth.length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Models</h1>
          <p className="text-dark-500 dark:text-dark-400">
            Model registry, health monitoring, and adaptive scoring
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={triggerHealthCheck} variant="outline">
            <HeartPulse className="h-4 w-4 mr-2" />
            Health Check
          </Button>
          <Button onClick={handleRefresh} disabled={refreshing} variant="outline">
            <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard 
          title="Total Models" 
          value={totalModels} 
          icon={Cpu} 
          color="bg-blue-500" 
        />
        <StatCard 
          title="Healthy" 
          value={healthyCount} 
          icon={CheckCircle} 
          color="bg-green-500" 
        />
        <StatCard 
          title="Degraded" 
          value={degradedCount} 
          icon={AlertTriangle} 
          color="bg-yellow-500" 
        />
        <StatCard 
          title="Cooldown" 
          value={cooldownCount} 
          icon={XCircle} 
          color="bg-red-500" 
        />
      </div>

      {/* View Tabs */}
      <div className="flex gap-1 border-b border-dark-200 dark:border-dark-700">
        {[
          { id: 'health', label: 'Health', icon: HeartPulse },
          { id: 'scoring', label: 'Scoring', icon: TrendingUp },
          { id: 'routes', label: 'Routes', icon: BarChart3 },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setViewMode(tab.id as typeof viewMode)}
            className={cn(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
              viewMode === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-dark-500 hover:text-dark-700 dark:hover:text-dark-300'
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Health View */}
      {viewMode === 'health' && (
        <Card>
          <CardHeader>
            <CardTitle>Model Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-200 dark:border-dark-700">
                    <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Model</th>
                    <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Provider</th>
                    <th className="text-center py-3 px-4 font-medium text-dark-500 dark:text-dark-400">State</th>
                    <th className="text-right py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Success Rate</th>
                    <th className="text-right py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Avg Latency</th>
                    <th className="text-right py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Recent Latency</th>
                    <th className="text-right py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Failures</th>
                    <th className="text-center py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Available</th>
                  </tr>
                </thead>
                <tbody>
                  {modelHealth.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-12 text-center text-dark-500 dark:text-dark-400">
                        No model health data available
                      </td>
                    </tr>
                  ) : (
                    modelHealth.map((health) => (
                      <tr key={`${health.provider}/${health.model_id}`} className="border-b border-dark-100 dark:border-dark-800 hover:bg-dark-50 dark:hover:bg-dark-800/50">
                        <td className="py-3 px-4 font-mono text-dark-900 dark:text-white">
                          {health.model_id}
                        </td>
                        <td className="py-3 px-4 text-dark-500 dark:text-dark-400">
                          {health.provider}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge status={health.state} />
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {(health.get_success_rate ? health.get_success_rate() * 100 : 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {health.avg_latency_ms > 0 ? `${health.avg_latency_ms.toFixed(0)}ms` : '—'}
                        </td>
                        <td className="py-3 px-4 text-right font-mono">
                          {health.recent_avg_latency_ms > 0 ? `${health.recent_avg_latency_ms.toFixed(0)}ms` : '—'}
                        </td>
                        <td className="py-3 px-4 text-right text-dark-500 dark:text-dark-400">
                          {health.failure_count}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge variant={health.is_available ? 'default' : 'destructive'}>
                            {health.is_available ? 'Yes' : 'No'}
                          </Badge>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Scoring View */}
      {viewMode === 'scoring' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <h2 className="text-xl font-semibold text-dark-900 dark:text-white">Adaptive Scores</h2>
            <Select
              value={selectedAgentType}
              onChange={(e) => setSelectedAgentType(e.target.value)}
              options={[
                { value: 'all', label: 'All Agent Types' },
                ...agentTypes.map(t => ({ value: t, label: t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }))
              ]}
              placeholder="Filter by agent type"
              className="w-full sm:w-64"
            />
          </div>

          {selectedAgentType === 'all' ? (
            <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
              {agentTypes.map((agentType) => (
                <ScoringCard 
                  key={agentType} 
                  agentType={agentType} 
                  scores={scoresByAgent[agentType] || []}
                  modelHealth={modelHealth}
                />
              ))}
            </div>
          ) : (
            <ScoringCard 
              agentType={selectedAgentType} 
              scores={scoresByAgent[selectedAgentType] || []}
              modelHealth={modelHealth}
              expanded
            />
          )}
        </div>
      )}

      {/* Routes View */}
      {viewMode === 'routes' && (
        <div className="space-y-6">
          {Object.entries(modelRoutes).length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <BarChart3 className="h-12 w-12 mx-auto text-dark-300 dark:text-dark-600 mb-4" />
                <p className="text-dark-500 dark:text-dark-400">No model routes configured</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {Object.entries(modelRoutes).map(([agentType, route]) => (
                <RouteCard key={agentType} agentType={agentType} route={route} modelHealth={modelHealth} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color }: { title: string; value: number; icon: React.ComponentType<{ className?: string }>; color: string }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-dark-500 dark:text-dark-400">{title}</p>
            <p className="mt-1 text-3xl font-bold text-dark-900 dark:text-white">{value}</p>
          </div>
          <div className={cn('p-3 rounded-xl', color)}>
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ScoringCard({ agentType, scores, modelHealth, expanded }: { agentType: string; scores: ModelScore[]; modelHealth: ModelHealth[]; expanded?: boolean }) {
  const topScores = scores
    .filter(s => s.total_score > 0)
    .sort((a, b) => b.total_score - a.total_score)
    .slice(0, expanded ? 10 : 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="capitalize">{agentType.replace(/_/g, ' ')}</CardTitle>
      </CardHeader>
      <CardContent>
        {topScores.length === 0 ? (
          <p className="text-dark-500 dark:text-dark-400 text-center py-8">No scoring data</p>
        ) : (
          <div className="space-y-2">
            {topScores.map((score, index) => {
              const health = modelHealth.find(h => `${h.provider}/${h.model_id}` === score.model_id);
              return (
                <div key={score.model_id} className="flex items-center gap-3">
                  <span className="w-6 text-center text-dark-400 dark:text-dark-500 font-medium">
                    #{index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm text-dark-900 dark:text-white truncate">
                      {score.model_id}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 h-1.5 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${score.total_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-dark-500 dark:text-dark-400 w-10 text-right">
                        {(score.total_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  {health && <Badge status={health.state} className="text-xs" />}
                </div>
              );
            })}
          </div>
        )}
        {expanded && scores.length > 5 && (
          <p className="mt-3 text-xs text-dark-500 dark:text-dark-400 text-center">
            Showing top {topScores.length} of {scores.filter(s => s.total_score > 0).length} models
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function RouteCard({ agentType, route, modelHealth }: { agentType: string; route: ModelRoute; modelHealth: ModelHealth[] }) {
  const primaryHealth = modelHealth.find(h => `${h.provider}/${h.model_id}` === route.primary_model)?.state || 'unknown';
  const fallbackHealth = route.fallback_models.map(fb => modelHealth.find(h => `${h.provider}/${h.model_id}` === fb)?.state || 'unknown');

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="capitalize">{agentType.replace(/_/g, ' ')}</span>
          <Badge variant={route.enabled ? 'default' : 'secondary'}>
            {route.enabled ? 'Enabled' : 'Disabled'}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-3 p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
          <Zap className="h-5 w-5 text-primary" />
          <div className="flex-1">
            <p className="text-sm text-dark-500 dark:text-dark-400">Primary</p>
            <p className="font-mono text-dark-900 dark:text-white">{route.primary_model}</p>
          </div>
          <Badge status={primaryHealth} />
        </div>
        {route.fallback_models.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-dark-500 dark:text-dark-400">Fallbacks</p>
            {route.fallback_models.map((fb, i) => (
              <div key={i} className="flex items-center gap-3 p-2 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
                <span className="w-6 text-center text-dark-400 dark:text-dark-500 text-sm font-medium">#{i + 1}</span>
                <div className="flex-1">
                  <p className="font-mono text-sm text-dark-900 dark:text-white">{fb}</p>
                </div>
                <Badge status={fallbackHealth[i]} className="text-xs" />
              </div>
            ))}
          </div>
        )}
        <div className="pt-2 border-t border-dark-100 dark:border-dark-800 flex items-center justify-between text-sm text-dark-500 dark:text-dark-400">
          <span>Priority: {route.priority}</span>
          <Button variant="ghost" size="sm">
            <Settings className="h-3 w-3 mr-1" /> Edit
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}