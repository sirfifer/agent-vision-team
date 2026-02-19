import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { setActiveProject as setTransportProject } from '../hooks/useTransport';

export interface ProjectInfo {
  id: string;
  name: string;
  path: string;
  status: string; // stopped | starting | running | error
  slot: number;
  mcp_base_port: number;
  kg_port: number;
  quality_port: number;
  governance_port: number;
}

interface ProjectContextValue {
  projects: ProjectInfo[];
  activeProjectId: string | null;
  loading: boolean;
  switchProject: (id: string) => void;
  addProject: (path: string, name?: string) => Promise<void>;
  removeProject: (id: string) => Promise<void>;
  startProject: (id: string) => Promise<void>;
  stopProject: (id: string) => Promise<void>;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

function getApiBase(): string {
  return (window as any).__AVT_API_BASE__ || '';
}

function getApiKey(): string {
  return (
    (window as any).__AVT_API_KEY__ || new URLSearchParams(window.location.search).get('key') || ''
  );
}

async function apiFetch(path: string, init?: RequestInit): Promise<any> {
  const apiBase = getApiBase();
  const apiKey = getApiKey();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init?.headers as Record<string, string>) || {}),
  };
  if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

  const resp = await fetch(`${apiBase}${path}`, { ...init, headers });
  if (!resp.ok) throw new Error(`API ${resp.status}: ${resp.statusText}`);
  return resp.json();
}

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProjects = useCallback(async () => {
    try {
      const data = await apiFetch('/api/projects');
      const list: ProjectInfo[] = data.projects || [];
      setProjects(list);

      // Auto-select first project if none active
      if (list.length > 0 && !activeProjectId) {
        const first = list[0];
        setActiveProjectId(first.id);
        setTransportProject(first.id);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  }, [activeProjectId]);

  useEffect(() => {
    refreshProjects();
  }, []);

  const switchProject = useCallback((id: string) => {
    setActiveProjectId(id);
    setTransportProject(id);
  }, []);

  const addProject = useCallback(
    async (path: string, name?: string) => {
      const data = await apiFetch('/api/projects', {
        method: 'POST',
        body: JSON.stringify({ path, name }),
      });
      const project: ProjectInfo = data.project;

      // Start the project automatically
      try {
        await apiFetch(`/api/projects/${project.id}/start`, { method: 'POST' });
      } catch {
        // May fail if MCP servers aren't ready yet
      }

      await refreshProjects();
      switchProject(project.id);
    },
    [refreshProjects, switchProject],
  );

  const removeProject = useCallback(
    async (id: string) => {
      await apiFetch(`/api/projects/${id}`, { method: 'DELETE' });
      await refreshProjects();

      // If we removed the active project, switch to another
      if (activeProjectId === id) {
        setProjects((prev) => {
          const remaining = prev.filter((p) => p.id !== id);
          if (remaining.length > 0) {
            switchProject(remaining[0].id);
          } else {
            setActiveProjectId(null);
            setTransportProject(undefined);
          }
          return remaining;
        });
      }
    },
    [activeProjectId, refreshProjects, switchProject],
  );

  const startProject = useCallback(
    async (id: string) => {
      await apiFetch(`/api/projects/${id}/start`, { method: 'POST' });
      await refreshProjects();
    },
    [refreshProjects],
  );

  const stopProject = useCallback(
    async (id: string) => {
      await apiFetch(`/api/projects/${id}/stop`, { method: 'POST' });
      await refreshProjects();
    },
    [refreshProjects],
  );

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProjectId,
        loading,
        switchProject,
        addProject,
        removeProject,
        startProject,
        stopProject,
        refreshProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjects(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error('useProjects must be used within ProjectProvider');
  return ctx;
}
