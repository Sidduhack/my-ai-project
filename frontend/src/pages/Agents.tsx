import { useEffect, useState } from 'react';
import { 
  Bot, 
  Cpu, 
  MemoryStick, 
  Settings, 
  RefreshCw, 
  Loader2,
  ChevronDown,
  ChevronUp,
  Edit2,
  Save,
  X,
  CheckCircle,
  AlertCircle,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { ws } from '../services/websocket';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { cn, getStatusColor } from '../utils/helpers';
import { useToast } from '../components/ui/Toaster';
import type { Agent, AgentTypeInfo, ModelRoute, ModelHealth, ModelScore } from '../types';

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  planner: Zap,
  architect: Bot,
  ui_ux: Bot,
  creative_director: Zap,
  motion_designer: Zap,
  frontend: Zap,
  backend: Cpu,
  database: MemoryStick,
  security: AlertCircle,
  performance: Zap,
  testing: CheckCircle,
  integration: Zap,
  debugging: Zap,
  sound_engineer: Zap,
  accessibility: Zap,
  seo: Zap,
  documentation: Zap,
  code_reviewer: Zap,
};

const AGENT_CATEGORIES = [
  { key: 'planning', label: 'Planning & Architecture', types: ['planner', 'architect'] },
  { key: 'design', label: 'Design & Creative', types: ['ui_ux', 'creative_director', 'motion_designer'] },
  { key: 'engineering', label: 'Engineering', types: ['frontend', 'backend', 'database'] },
  { key: 'quality', label: 'Quality & Security', types: ['security', 'performance', 'testing', 'integration', 'debugging'] },
  { key: 'specialized', label: 'Specialized', types: ['sound_engineer', 'accessibility', 'seo', 'documentation', 'code_reviewer'] },
];

export function Agents() {
  const { toast } = useToast();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentTypes, setAgentTypes] = useState<AgentTypeInfo[]>([]);
  const [modelRoutes, setModelRoutes] = useState<Record<string, ModelRoute>>({});
  const [modelHealth, setModelHealth] = useState<ModelHealth[]>([]);
  const [modelScores, setModelScores] = useState<Record<string, ModelScore[]>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editingRoute, setEditingRoute] = useState<string | null>(null);
  const [routeForm, setRouteForm] = useState<Partial<ModelRoute>>({});

  const fetchData = async () => {
    try {
      setLoading(true);
      const [agentsData, typesData, routesData, healthData] = await Promise.all([
        api.getAgents(),
        api.getAgentTypes(),
        api.getModelRoutes(),
        api.getModelsHealth(),
      ]);
      setAgents(agentsData);
      setAgentTypes(typesData);
      setModelRoutes(routesData);
      setModelHealth(healthData);

      // Fetch scores for each agent type
      for (const type of typesData) {
        const scores = await api.getAgentModelScores(type.type);
        setModelScores(prev => ({ ...prev, [type.type]: scores }));
      }
    } catch (error) {
      toast({ type: 'error', title: 'Failed to load agents' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Subscribe to system health updates
    const unsub = ws.subscribeToSystem({
      onHealthChange: () => fetchData(),
      onMetricsUpdate: () => fetchData(),
    });
    return () => unsub();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const getAgentByType = (type: string) => agents.find(a => a.agent_type === type);

  const startEditRoute = (agentType: string) => {
    const route = modelRoutes[agentType];
    if (route) {
      setEditingRoute(agentType);
      setRouteForm({ ...route });
    }
  };

  const saveRoute = async (agentType: string) => {
    try {
      // This would need a backend endpoint - for now just update locally
      setModelRoutes(prev => ({ ...prev, [agentType]: { ...prev[agentType], ...routeForm } }));
      setEditingRoute(null);
      toast({ type: 'success', title: 'Route updated' });
    } catch {
      toast({ type: 'error', title: 'Failed to update route' });
    }
  };

  const cancelEdit = () => {
    setEditingRoute(null);
    setRouteForm({});
  };

  const getModelStatus = (modelSpec: string) => {
    const health = modelHealth.find(h => `${h.provider}/${h.model_id}` === modelSpec);
    return health?.state || 'unknown';
  };

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
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Agents</h1>
          <p className="text-dark-500 dark:text-dark-400">
            Manage 19 specialist agents and their model routing
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing} variant="outline">
          <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Agent Categories */}
      {AGENT_CATEGORIES.map((category) => (
        <Card key={category.key}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              {category.label}
              <span className="text-sm font-normal text-dark-500 dark:text-dark-400">
                ({category.types.length} agents)
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {category.types.map((type) => {
                const agent = getAgentByType(type);
                const route = modelRoutes[type];
                const scores = modelScores[type] || [];
                const Icon = AGENT_ICONS[type] || Bot;
                const isActive = agent?.is_active ?? true;

                return (
                  <AgentCard
                    key={type}
                    type={type}
                    agent={agent}
                    route={route}
                    scores={scores}
                    modelHealth={modelHealth}
                    isActive={isActive}
                    Icon={Icon}
                    onEditRoute={startEditRoute}
                    editing={editingRoute === type}
                    routeForm={routeForm}
                    setRouteForm={setRouteForm}
                    onSaveRoute={() => saveRoute(type)}
                    onCancelEdit={cancelEdit}
                  />
                );
              })}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function AgentCard({ 
  type, 
  agent, 
  route, 
  scores, 
  modelHealth, 
  isActive, 
  Icon,
  onEditRoute,
  editing,
  routeForm,
  setRouteForm,
  onSaveRoute,
  onCancelEdit,
}: {
  type: string;
  agent: Agent | undefined;
  route: ModelRoute | undefined;
  scores: ModelScore[];
  modelHealth: ModelHealth[];
  isActive: boolean;
  Icon: React.ComponentType<{ className?: string }>;
  onEditRoute: (type: string) => void;
  editing: boolean;
  routeForm: Partial<ModelRoute>;
  setRouteForm: React.Dispatch<React.SetStateAction<Partial<ModelRoute>>>;
  onSaveRoute: () => void;
  onCancelEdit: () => void;
}) {
  const statusColors: Record<string, string> = {
    healthy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    degraded: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    cooldown: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  };

  const primaryHealth = route ? getModelStatus(route.primary_model) : 'unknown';
  const fallbackHealth = route?.fallback_models.map(getModelStatus) || [];

  if (editing) {
    return (
      <div className="border-2 border-primary bg-primary/5 dark:bg-primary-900/10 rounded-xl p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-dark-900 dark:text-white capitalize">
            {type.replace(/_/g, ' ')} - Editing Route
          </h4>
        </div>
        <div className="space-y-3">
          <Input
            label="Primary Model"
            value={routeForm.primary_model || ''}
            onChange={(e) => setRouteForm(prev => ({ ...prev, primary_model: e.target.value }))}
            placeholder="provider/model-id"
          />
          <Input
            label="Fallback Models (comma-separated)"
            value={(routeForm.fallback_models as string[])?.join(', ') || ''}
            onChange={(e) => setRouteForm(prev => ({ 
              ...prev, 
              fallback_models: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
            }))}
            placeholder="provider/model-id, provider/model-id"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={onCancelEdit}>
              <X className="h-4 w-4 mr-1" /> Cancel
            </Button>
            <Button size="sm" onClick={onSaveRoute}>
              <Save className="h-4 w-4 mr-1" /> Save
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      'border rounded-xl p-4 space-y-4 transition-all',
      isActive ? 'bg-white dark:bg-dark-900' : 'opacity-50 bg-dark-50 dark:bg-dark-900/50'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h4 className="font-medium text-dark-900 dark:text-white capitalize">
              {type.replace(/_/g, ' ')}
            </h4>
            <p className="text-sm text-dark-500 dark:text-dark-400">
              {agent?.role || 'No description'}
            </p>
          </div>
        </div>
        <Badge variant={isActive ? 'default' : 'secondary'}>
          {isActive ? 'Active' : 'Inactive'}
        </Badge>
      </div>

      {/* Model Route */}
      {route && (
        <div className="space-y-2 pt-2 border-t border-dark-100 dark:border-dark-800">
          <div className="flex items-center justify-between text-sm">
            <span className="text-dark-500 dark:text-dark-400">Primary Model</span>
            <div className="flex items-center gap-2">
              <Badge 
                variant="outline" 
                className="font-mono text-xs flex-1 truncate"
              >
                {route.primary_model}
              </Badge>
              <Badge status={primaryHealth} className="text-xs" />
              <Button variant="ghost" size="icon" onClick={() => onEditRoute(type)}>
                <Settings className="h-3 w-3" />
              </Button>
            </div>
          </div>
          {route.fallback_models.length > 0 && (
            <div className="space-y-1 ml-8">
              {route.fallback_models.map((fb, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="text-dark-400 dark:text-dark-500">#{i + 1}</span>
                  <Badge variant="outline" className="font-mono text-xs flex-1 truncate">
                    {fb}
                  </Badge>
                  <Badge status={fallbackHealth[i]} className="text-xs" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Top Scored Models */}
      {scores.length > 0 && (
        <div className="pt-2 border-t border-dark-100 dark:border-dark-800">
          <p className="text-xs text-dark-500 dark:text-dark-400 mb-2">Top Models by Score</p>
          <div className="space-y-1">
            {scores
              .sort((a, b) => b.total_score - a.total_score)
              .slice(0, 3)
              .map((score) => {
                const health = modelHealth.find(h => `${h.provider}/${h.model_id}` === score.model_id);
                return (
                  <div key={score.model_id} className="flex items-center gap-2 text-xs">
                    <span className="font-mono text-dark-600 dark:text-dark-400 truncate flex-1">
                      {score.model_id}
                    </span>
                    <div className="flex items-center gap-1">
                      <div className="w-16 h-1.5 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${score.total_score * 100}%` }}
                        />
                      </div>
                      <span className="text-dark-500 dark:text-dark-400 font-mono w-10">
                        {(score.total_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {health && <Badge status={health.state} className="text-[10px]" />}
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Agent Memory (if agent exists) */}
      {agent && (
        <Button variant="ghost" size="sm" className="w-full" onClick={() => {
          // Could open memory modal
        }}>
          <MemoryStick className="h-4 w-4 mr-2" />
          View Memory
        </Button>
      )}
    </div>
  );
}

function getModelStatus(modelHealth: ModelHealth[], modelSpec: string): string {
  const health = modelHealth.find(h => `${h.provider}/${h.model_id}` === modelSpec);
  return health?.state || 'unknown';
}