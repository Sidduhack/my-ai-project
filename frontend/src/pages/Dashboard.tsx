import { useEffect, useState } from 'react';
import { 
  FolderKanban, 
  Bot, 
  Cpu, 
  AlertTriangle,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { cn, formatRelativeTime, getStatusColor } from '../utils/helpers';
import type { Project, SystemHealth, Metrics, ModelHealth } from '../types';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  trend?: string;
  trendUp?: boolean;
  color: string;
}

function StatCard({ title, value, icon: Icon, trend, trendUp, color }: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-dark-500 dark:text-dark-400">{title}</p>
            <p className="mt-1 text-3xl font-bold text-dark-900 dark:text-white">{value}</p>
            {trend && (
              <p className={cn('mt-1 text-sm', trendUp ? 'text-green-600' : 'text-red-600')}>
                {trend}
              </p>
            )}
          </div>
          <div className={cn('p-3 rounded-xl', color)}>
            <Icon className="h-6 w-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [modelHealth, setModelHealth] = useState<ModelHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const [projectsData, healthData, metricsData, modelHealthData] = await Promise.all([
        api.getProjects(),
        api.getHealth(),
        api.getMetrics(),
        api.getModelsHealth(),
      ]);
      setProjects(projectsData);
      setHealth(healthData);
      setMetrics(metricsData);
      setModelHealth(modelHealthData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  useEffect(() => {
    fetchData();
  }, []);

  const recentProjects = projects.slice(0, 5);
  const runningProjects = projects.filter(p => p.status === 'running').length;
  const completedProjects = projects.filter(p => p.status === 'completed').length;
  const failedProjects = projects.filter(p => p.status === 'failed').length;

  const healthyModels = modelHealth.filter(m => m.state === 'healthy').length;
  const degradedModels = modelHealth.filter(m => m.state === 'degraded').length;
  const cooldownModels = modelHealth.filter(m => m.state === 'cooldown').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Dashboard</h1>
          <p className="text-dark-500 dark:text-dark-400">
            Overview of your multi-agent projects and system health
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing} variant="outline">
          <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Projects"
          value={projects.length}
          icon={FolderKanban}
          color="bg-blue-500"
        />
        <StatCard
          title="Running"
          value={runningProjects}
          icon={Bot}
          color="bg-green-500"
        />
        <StatCard
          title="Completed"
          value={completedProjects}
          icon={CheckCircle}
          color="bg-emerald-500"
        />
        <StatCard
          title="Failed"
          value={failedProjects}
          icon={XCircle}
          color="bg-red-500"
        />
      </div>

      {/* System Health & Model Health */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              System Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-dark-600 dark:text-dark-400">Status</span>
                <Badge 
                  status={health?.status || 'healthy'}
                  className="text-xs"
                >
                  {health?.status || 'healthy'}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-dark-600 dark:text-dark-400">Version</span>
                <span className="text-sm font-mono text-dark-900 dark:text-white">
                  {health?.version || '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-dark-600 dark:text-dark-400">Environment</span>
                <Badge variant="outline" className="text-xs">
                  {health?.environment || 'development'}
                </Badge>
              </div>
              {metrics && (
                <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
                  <h4 className="text-sm font-medium text-dark-900 dark:text-white mb-3">Queue Status</h4>
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div>
                      <p className="text-2xl font-bold text-dark-900 dark:text-white">
                        {metrics.orchestrator.queue.pending}
                      </p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">Pending</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-blue-600">
                        {metrics.orchestrator.queue.running}
                      </p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">Running</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-green-600">
                        {metrics.orchestrator.queue.completed}
                      </p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">Completed</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-red-600">
                        {metrics.orchestrator.queue.failed}
                      </p>
                      <p className="text-xs text-dark-500 dark:text-dark-400">Failed</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Model Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              Model Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className={cn('p-3 rounded-lg', getStatusColor('healthy').replace('text-', 'bg-').replace('dark:bg-', 'dark:bg-').replace('dark:text-', 'dark:bg-'))}>
                  <p className="text-2xl font-bold text-white">{healthyModels}</p>
                  <p className="text-xs text-white/80">Healthy</p>
                </div>
                <div className={cn('p-3 rounded-lg', getStatusColor('degraded').replace('text-', 'bg-').replace('dark:bg-', 'dark:bg-').replace('dark:text-', 'dark:bg-'))}>
                  <p className="text-2xl font-bold text-white">{degradedModels}</p>
                  <p className="text-xs text-white/80">Degraded</p>
                </div>
                <div className={cn('p-3 rounded-lg', getStatusColor('cooldown').replace('text-', 'bg-').replace('dark:bg-', 'dark:bg-').replace('dark:text-', 'dark:bg-'))}>
                  <p className="text-2xl font-bold text-white">{cooldownModels}</p>
                  <p className="text-xs text-white/80">Cooldown</p>
                </div>
              </div>
              {modelHealth.length > 0 && (
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-dark-200 dark:border-dark-700">
                        <th className="text-left py-2 px-3 font-medium text-dark-500 dark:text-dark-400">Model</th>
                        <th className="text-left py-2 px-3 font-medium text-dark-500 dark:text-dark-400">Provider</th>
                        <th className="text-center py-2 px-3 font-medium text-dark-500 dark:text-dark-400">State</th>
                        <th className="text-right py-2 px-3 font-medium text-dark-500 dark:text-dark-400">Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelHealth.slice(0, 10).map((model) => (
                        <tr key={`${model.provider}/${model.model_id}`} className="border-b border-dark-100 dark:border-dark-800 hover:bg-dark-50 dark:hover:bg-dark-800/50">
                          <td className="py-2 px-3 text-dark-900 dark:text-white truncate max-w-[150px]">
                            {model.model_id}
                          </td>
                          <td className="py-2 px-3 text-dark-500 dark:text-dark-400">
                            {model.provider}
                          </td>
                          <td className="py-2 px-3 text-center">
                            <Badge status={model.state} className="text-xs" />
                          </td>
                          <td className="py-2 px-3 text-right text-dark-500 dark:text-dark-400 font-mono">
                            {model.recent_avg_latency_ms > 0 
                              ? `${model.recent_avg_latency_ms.toFixed(0)}ms` 
                              : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Projects */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Projects</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <a href="/projects">View All</a>
          </Button>
        </CardHeader>
        <CardContent>
          {recentProjects.length === 0 ? (
            <div className="text-center py-12">
              <FolderKanban className="h-12 w-12 mx-auto text-dark-300 dark:text-dark-600" />
              <p className="mt-4 text-dark-500 dark:text-dark-400">No projects yet</p>
              <Button className="mt-4" asChild>
                <a href="/projects">Create Project</a>
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-200 dark:border-dark-700">
                    <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Project</th>
                    <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Created</th>
                    <th className="text-right py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentProjects.map((project) => (
                    <tr key={project.id} className="border-b border-dark-100 dark:border-dark-800 hover:bg-dark-50 dark:hover:bg-dark-800/50">
                      <td className="py-3 px-4">
                        <div className="font-medium text-dark-900 dark:text-white">{project.name}</div>
                        {project.description && (
                          <div className="text-sm text-dark-500 dark:text-dark-400 truncate max-w-xs">
                            {project.description}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <Badge status={project.status} />
                      </td>
                      <td className="py-3 px-4 text-dark-500 dark:text-dark-400">
                        {formatRelativeTime(project.created_at)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button variant="ghost" size="sm" asChild>
                          <a href={`/projects/${project.id}`}>View</a>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}