import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Play, 
  Pause, 
  X, 
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  FolderOpen,
  FileText,
  Terminal,
  AlertTriangle,
  CheckCircle,
  Clock,
  Bot,
  ExternalLink,
  MoreHorizontal,
} from 'lucide-react';
import { api } from '../services/api';
import { ws } from '../services/websocket';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { cn, formatRelativeTime, getStatusColor, formatDuration } from '../utils/helpers';
import { useToast } from '../components/ui/Toaster';
import type { Project, ProjectStatusResponse, Task, Event, Agent } from '../types';

const AGENT_COLORS: Record<string, string> = {
  planner: 'bg-blue-500',
  architect: 'bg-purple-500',
  ui_ux: 'bg-pink-500',
  creative_director: 'bg-orange-500',
  motion_designer: 'bg-red-500',
  frontend: 'bg-cyan-500',
  backend: 'bg-green-500',
  database: 'bg-emerald-500',
  security: 'bg-red-600',
  performance: 'bg-yellow-500',
  testing: 'bg-indigo-500',
  integration: 'bg-teal-500',
  debugging: 'bg-rose-500',
  sound_engineer: 'bg-amber-500',
  accessibility: 'bg-violet-500',
  seo: 'bg-lime-500',
  documentation: 'bg-sky-500',
  code_reviewer: 'bg-gray-500',
};

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [project, setProject] = useState<Project | null>(null);
  const [status, setStatus] = useState<ProjectStatusResponse | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'events' | 'agents'>('overview');
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

  const fetchData = async () => {
    if (!id) return;
    try {
      const [projectData, statusData, eventsData] = await Promise.all([
        api.getProject(id),
        api.getProjectStatus(id),
        api.getProjectEvents(id),
      ]);
      setProject(projectData);
      setStatus(statusData);
      setEvents(eventsData);
    } catch (error) {
      toast({ type: 'error', title: 'Failed to load project' });
      navigate('/projects');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Subscribe to realtime updates
    const unsub = ws.subscribeToProject(id!, {
      onStatusUpdate: (newStatus) => setStatus(newStatus),
      onTaskUpdate: (task) => setStatus(prev => prev ? {
        ...prev,
        tasks: prev.tasks.map(t => t.id === task.id ? task : t)
      } : null),
      onEvent: (event) => setEvents(prev => [event, ...prev]),
    });
    return () => unsub();
  }, [id]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleAction = async (action: 'start' | 'pause' | 'cancel') => {
    if (!project) return;
    try {
      if (action === 'start') await api.startProject(project.id);
      if (action === 'pause') await api.pauseProject(project.id);
      if (action === 'cancel') await api.cancelProject(project.id);
      toast({ type: 'success', title: `Project ${action}ed` });
      fetchData();
    } catch {
      toast({ type: 'error', title: `Failed to ${action} project` });
    }
  };

  const toggleTask = (taskId: string) => {
    setExpandedTasks(prev => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!project) return null;

  const statusColors: Record<ProjectStatus, string> = {
    created: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    planning: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    running: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  };

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/projects')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-dark-900 dark:text-white">{project.name}</h1>
            <p className="text-dark-500 dark:text-dark-400">{project.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge 
            className={cn('text-sm px-3 py-1', statusColors[project.status])}
          >
            {project.status}
          </Badge>
          <Button variant="outline" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={cn('h-4 w-4 mr-2', refreshing && 'animate-spin')} />
            Refresh
          </Button>
          {['created', 'paused'].includes(project.status) && (
            <Button onClick={() => handleAction('start')}>
              <Play className="h-4 w-4 mr-2" /> Start
            </Button>
          )}
          {project.status === 'running' && (
            <Button variant="outline" onClick={() => handleAction('pause')}>
              <Pause className="h-4 w-4 mr-2" /> Pause
            </Button>
          )}
          {['created', 'planning', 'running', 'paused'].includes(project.status) && (
            <Button variant="destructive" onClick={() => handleAction('cancel')}>
              <X className="h-4 w-4 mr-2" /> Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-200 dark:border-dark-700">
        <nav className="flex gap-1" role="tablist">
          {[
            { id: 'overview', label: 'Overview', icon: FolderOpen },
            { id: 'tasks', label: 'Tasks', icon: FileText, count: status?.tasks.length },
            { id: 'events', label: 'Events', icon: Terminal, count: events.length },
            { id: 'agents', label: 'Agents', icon: Bot },
          ].map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-dark-500 hover:text-dark-700 dark:hover:text-dark-300'
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
              {tab.count !== undefined && (
                <span className={cn(
                  'px-2 py-0.5 text-xs rounded-full',
                  activeTab === tab.id
                    ? 'bg-primary/20 text-primary'
                    : 'bg-dark-100 text-dark-600 dark:bg-dark-800 dark:text-dark-400'
                )}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Total Tasks" value={status?.tasks.length || 0} icon={FileText} color="bg-blue-500" />
            <StatCard title="Running" value={status?.tasks.filter(t => t.status === 'running').length} icon={Loader2} color="bg-green-500" />
            <StatCard title="Completed" value={status?.tasks.filter(t => t.status === 'completed').length} icon={CheckCircle} color="bg-emerald-500" />
            <StatCard title="Failed" value={status?.tasks.filter(t => t.status === 'failed').length} icon={AlertTriangle} color="bg-red-500" />
          </div>

          {/* Project Info */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Project Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <InfoRow label="ID" value={project.id} copyable />
                <InfoRow label="Status" value={
                  <Badge className={statusColors[project.status]}>{project.status}</Badge>
                } />
                <InfoRow label="Created" value={formatRelativeTime(project.created_at)} />
                <InfoRow label="Started" value={project.started_at ? formatRelativeTime(project.started_at) : '—'} />
                <InfoRow label="Completed" value={project.completed_at ? formatRelativeTime(project.completed_at) : '—'} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Requirements</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-sm text-dark-600 dark:text-dark-400 bg-dark-100 dark:bg-dark-800 p-4 rounded-lg overflow-x-auto">
                  {JSON.stringify(project.requirements, null, 2) || '{}'}
                </pre>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'tasks' && (
        <div className="space-y-4">
          {status?.tasks.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FileText className="h-12 w-12 mx-auto text-dark-300 dark:text-dark-600 mb-4" />
                <p className="text-dark-500 dark:text-dark-400">No tasks yet</p>
                <p className="text-sm text-dark-400 dark:text-dark-500 mt-1">
                  Tasks will appear when the project starts
                </p>
              </CardContent>
            </Card>
          ) : (
            status?.tasks.map((task) => (
              <TaskCard 
                key={task.id} 
                task={task} 
                expanded={expandedTasks.has(task.id)}
                onToggle={() => toggleTask(task.id)}
              />
            ))
          )}
        </div>
      )}

      {activeTab === 'events' && (
        <Card>
          <CardContent className="p-0">
            {events.length === 0 ? (
              <div className="p-12 text-center">
                <Terminal className="h-12 w-12 mx-auto text-dark-300 dark:text-dark-600 mb-4" />
                <p className="text-dark-500 dark:text-dark-400">No events yet</p>
              </div>
            ) : (
              <div className="divide-y divide-dark-200 dark:divide-dark-700">
                {events.slice(0, 50).map((event) => (
                  <EventRow key={event.id} event={event} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'agents' && (
        <div className="space-y-4">
          {status?.tasks.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Bot className="h-12 w-12 mx-auto text-dark-300 dark:text-dark-600 mb-4" />
                <p className="text-dark-500 dark:text-dark-400">No agents have run yet</p>
              </CardContent>
            </Card>
          ) : (
            [...new Set(status.tasks.map(t => t.agent_id))].map((agentId) => {
              const agentTasks = status.tasks.filter(t => t.agent_id === agentId);
              const completed = agentTasks.filter(t => t.status === 'completed').length;
              const failed = agentTasks.filter(t => t.status === 'failed').length;
              const running = agentTasks.filter(t => t.status === 'running').length;
              const color = AGENT_COLORS[agentId] || 'bg-gray-500';
              
              return (
                <Card key={agentId}>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={cn('h-10 w-10 rounded-lg flex items-center justify-center', color)}>
                          <Bot className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <h4 className="font-medium text-dark-900 dark:text-white capitalize">
                            {agentId.replace(/_/g, ' ')}
                          </h4>
                          <p className="text-sm text-dark-500 dark:text-dark-400">
                            {agentTasks.length} tasks • {completed} done • {failed} failed • {running} running
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge status={running > 0 ? 'running' : failed > 0 ? 'failed' : 'completed'}>
                          {running > 0 ? 'Active' : 'Idle'}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          )}
        </div>
      )}
    </div>
  );
}

// Helper Components
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

function InfoRow({ label, value, copyable }: { label: string; value: React.ReactNode; copyable?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-dark-100 dark:border-dark-800 last:border-0">
      <span className="text-sm text-dark-500 dark:text-dark-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono text-dark-900 dark:text-white break-all max-w-[300px]">
          {value}
        </span>
      </div>
    </div>
  );
}

function TaskCard({ task, expanded, onToggle }: { task: Task; expanded: boolean; onToggle: () => void }) {
  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    running: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    blocked: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  };

  const agentColor = AGENT_COLORS[task.agent_id] || 'bg-gray-500';

  return (
    <Card className={cn('overflow-hidden transition-all', expanded && 'shadow-lg')}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Button variant="ghost" size="icon" onClick={onToggle} aria-label={expanded ? 'Collapse' : 'Expand'}>
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
            <div className={cn('h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0', agentColor)}>
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="min-w-0">
              <h4 className="font-medium text-dark-900 dark:text-white truncate">{task.description}</h4>
              <div className="flex items-center gap-3 text-sm text-dark-500 dark:text-dark-400">
                <span className="capitalize">{task.agent_id.replace(/_/g, ' ')}</span>
                <Badge priority={task.priority} className="text-xs" />
                {task.assigned_model && (
                  <span className="font-mono text-xs bg-dark-100 dark:bg-dark-800 px-2 py-0.5 rounded">
                    {task.assigned_model}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <Badge className={statusColors[task.status]}>{task.status}</Badge>
            {task.error && (
              <Button variant="ghost" size="icon" className="text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20">
                <AlertTriangle className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-dark-100 dark:border-dark-800 space-y-4 animate-in">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailItem label="Task ID" value={task.id} copyable />
              <DetailItem label="Priority" value={<Badge priority={task.priority} />}/>
              <DetailItem label="Retry" value={`${task.retry_count}/${task.max_retries}`} />
              <DetailItem label="Dependencies" value={task.dependencies?.join(', ') || 'None'} />
            </div>

            {task.input_data && Object.keys(task.input_data).length > 0 && (
              <DetailSection title="Input Data" content={JSON.stringify(task.input_data, null, 2)} />
            )}

            {task.output_data && Object.keys(task.output_data).length > 0 && (
              <DetailSection title="Output Data" content={JSON.stringify(task.output_data, null, 2)} />
            )}

            {task.error && (
              <DetailSection title="Error" content={task.error} error />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DetailItem({ label, value, copyable }: { label: string; value: React.ReactNode; copyable?: boolean }) {
  return (
    <div>
      <p className="text-xs text-dark-500 dark:text-dark-400">{label}</p>
      <p className="text-sm font-mono text-dark-900 dark:text-white break-all">{value}</p>
    </div>
  );
}

function DetailSection({ title, content, error }: { title: string; content: string; error?: boolean }) {
  return (
    <div className={cn('bg-dark-100 dark:bg-dark-800 rounded-lg p-4', error && 'border border-red-200 dark:border-red-800')}>
      <p className="text-xs font-medium text-dark-500 dark:text-dark-400 mb-2">{title}</p>
      <pre className={cn('text-sm font-mono overflow-x-auto', error && 'text-red-600 dark:text-red-400')}>
        {content}
      </pre>
    </div>
  );
}

function EventRow({ event }: { event: Event }) {
  const eventIcons: Record<string, React.ComponentType<{ className?: string }>> = {
    PROJECT_CREATED: FolderOpen,
    PROJECT_STARTED: Play,
    PROJECT_COMPLETED: CheckCircle,
    PROJECT_FAILED: AlertTriangle,
    TASK_CREATED: FileText,
    TASK_STARTED: Play,
    TASK_COMPLETED: CheckCircle,
    TASK_FAILED: AlertTriangle,
    AGENT_STARTED: Bot,
    AGENT_COMPLETED: CheckCircle,
    AGENT_FAILED: AlertTriangle,
    MODEL_SELECTED: Bot,
    MODEL_FALLBACK: AlertTriangle,
    MODEL_RECOVERED: CheckCircle,
  };

  const Icon = eventIcons[event.event_type] || Terminal;
  const isError = event.event_type.includes('FAILED') || event.event_type.includes('ERROR');

  return (
    <div className="p-4 hover:bg-dark-50 dark:hover:bg-dark-800/50 flex items-start gap-3">
      <div className={cn('p-2 rounded-lg flex-shrink-0', isError ? 'bg-red-100 dark:bg-red-900/30 text-red-600' : 'bg-dark-100 dark:bg-dark-800 text-dark-600')}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-dark-900 dark:text-white capitalize">
          {event.event_type.replace(/_/g, ' ').toLowerCase()}
        </p>
        <p className="text-xs text-dark-500 dark:text-dark-400 font-mono">
          {formatRelativeTime(event.timestamp)}
        </p>
        {event.payload && Object.keys(event.payload).length > 0 && (
          <pre className="mt-2 text-xs text-dark-600 dark:text-dark-400 bg-dark-100 dark:bg-dark-800 p-2 rounded overflow-x-auto max-h-32 overflow-y-auto">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}