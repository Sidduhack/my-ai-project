import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Plus, 
  Search, 
  Filter, 
  ChevronLeft, 
  ChevronRight,
  MoreVertical,
  Play,
  Pause,
  X,
  Edit,
  Trash2,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { cn, formatRelativeTime, getStatusColor } from '../utils/helpers';
import { useToast } from '../components/ui/Toaster';
import type { Project, ProjectCreate, ProjectStatus } from '../types';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'created', label: 'Created' },
  { value: 'planning', label: 'Planning' },
  { value: 'running', label: 'Running' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

export function Projects() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(10);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newProject, setNewProject] = useState<ProjectCreate>({
    name: '',
    description: '',
    requirements: {},
  });

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getProjects();
      setProjects(data);
      setTotalPages(Math.ceil(data.length / pageSize));
    } catch (error) {
      toast({ type: 'error', title: 'Failed to load projects' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const filteredProjects = projects.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const paginatedProjects = filteredProjects.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProject.name.trim()) return;
    
    setCreating(true);
    try {
      await api.createProject(newProject);
      toast({ type: 'success', title: 'Project created' });
      setShowCreateModal(false);
      setNewProject({ name: '', description: '', requirements: {} });
      fetchProjects();
    } catch (error) {
      toast({ type: 'error', title: 'Failed to create project' });
    } finally {
      setCreating(false);
    }
  };

  const handleStart = async (id: string) => {
    try {
      await api.startProject(id);
      toast({ type: 'success', title: 'Project started' });
      fetchProjects();
    } catch {
      toast({ type: 'error', title: 'Failed to start project' });
    }
  };

  const handlePause = async (id: string) => {
    try {
      await api.pauseProject(id);
      toast({ type: 'success', title: 'Project paused' });
      fetchProjects();
    } catch {
      toast({ type: 'error', title: 'Failed to pause project' });
    }
  };

  const handleCancel = async (id: string) => {
    if (!confirm('Are you sure you want to cancel this project?')) return;
    try {
      await api.cancelProject(id);
      toast({ type: 'success', title: 'Project cancelled' });
      fetchProjects();
    } catch {
      toast({ type: 'error', title: 'Failed to cancel project' });
    }
  };

  const getActionButtons = (project: Project) => {
    const actions = [];
    if (project.status === 'created' || project.status === 'paused') {
      actions.push(
        <Button key="start" size="sm" onClick={() => handleStart(project.id)}>
          <Play className="h-3 w-3 mr-1" /> Start
        </Button>
      );
    }
    if (project.status === 'running') {
      actions.push(
        <Button key="pause" size="sm" variant="outline" onClick={() => handlePause(project.id)}>
          <Pause className="h-3 w-3 mr-1" /> Pause
        </Button>
      );
    }
    if (['created', 'planning', 'running', 'paused'].includes(project.status)) {
      actions.push(
        <Button key="cancel" size="sm" variant="destructive" onClick={() => handleCancel(project.id)}>
          <X className="h-3 w-3 mr-1" /> Cancel
        </Button>
      );
    }
    return actions;
  };

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">Projects</h1>
          <p className="text-dark-500 dark:text-dark-400">
            Manage your multi-agent software projects
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dark-400" />
              <Input
                placeholder="Search projects..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
                className="pl-10"
              />
            </div>
            <Select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
              options={STATUS_OPTIONS}
              placeholder="Filter by status"
              className="w-full sm:w-48"
            />
          </div>
        </CardContent>
      </Card>

      {/* Projects Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="p-12 text-center">
              <div className="h-16 w-16 mx-auto text-dark-300 dark:text-dark-600 mb-4">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-dark-500 dark:text-dark-400">No projects found</p>
              <Button className="mt-4" onClick={() => setShowCreateModal(true)}>
                Create your first project
              </Button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-dark-200 dark:border-dark-700 bg-dark-50 dark:bg-dark-800/50">
                      <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Project</th>
                      <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400 hidden md:table-cell">Description</th>
                      <th className="text-center py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Created</th>
                      <th className="text-right py-3 px-4 font-medium text-dark-500 dark:text-dark-400">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedProjects.map((project) => (
                      <tr key={project.id} className="border-b border-dark-100 dark:border-dark-800 hover:bg-dark-50 dark:hover:bg-dark-800/50">
                        <td className="py-3 px-4">
                          <div className="font-medium text-dark-900 dark:text-white">{project.name}</div>
                        </td>
                        <td className="py-3 px-4 hidden md:table-cell text-dark-500 dark:text-dark-400 truncate max-w-xs">
                          {project.description || '—'}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <Badge status={project.status} />
                        </td>
                        <td className="py-3 px-4 text-dark-500 dark:text-dark-400 whitespace-nowrap">
                          {formatRelativeTime(project.created_at)}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="sm" asChild>
                              <a href={`/projects/${project.id}`}>
                                <ExternalLink className="h-4 w-4" />
                              </a>
                            </Button>
                            {getActionButtons(project)}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-dark-200 dark:border-dark-700">
                  <p className="text-sm text-dark-500 dark:text-dark-400">
                    Page {currentPage} of {totalPages} • {filteredProjects.length} projects
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowCreateModal(false)}>
          <div className="w-full max-w-md bg-white dark:bg-dark-900 rounded-xl shadow-xl p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-dark-900 dark:text-white">Create Project</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowCreateModal(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <form onSubmit={handleCreate}>
              <Input
                label="Project Name"
                value={newProject.name}
                onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                placeholder="e.g. E-commerce Platform"
                required
                autoFocus
              />
              <Input
                label="Description (optional)"
                value={newProject.description}
                onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                placeholder="Brief description of the project"
              />
              <div className="mt-6 flex justify-end gap-3">
                <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" loading={creating}>
                  Create Project
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}