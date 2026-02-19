import { useState } from 'react';
import { useProjects } from '../context/ProjectContext';

export function ProjectTabBar() {
  const {
    projects,
    activeProjectId,
    switchProject,
    addProject,
    removeProject,
    startProject,
    stopProject,
    loading,
  } = useProjects();
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newPath, setNewPath] = useState('');
  const [newName, setNewName] = useState('');
  const [adding, setAdding] = useState(false);

  if (loading && projects.length === 0) {
    return (
      <div className="flex items-center h-9 px-3 bg-[var(--vscode-editorGroupHeader-tabsBackground)] border-b border-vscode-border">
        <span className="text-xs text-vscode-muted">Loading projects...</span>
      </div>
    );
  }

  const handleAdd = async () => {
    if (!newPath.trim()) return;
    setAdding(true);
    try {
      await addProject(newPath.trim(), newName.trim() || undefined);
      setShowAddDialog(false);
      setNewPath('');
      setNewName('');
    } catch (err) {
      console.error('Failed to add project:', err);
    } finally {
      setAdding(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-400';
      case 'starting':
        return 'bg-yellow-400';
      case 'error':
        return 'bg-red-400';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="flex flex-col">
      {/* Tab bar */}
      <div className="flex items-center h-9 bg-[var(--vscode-editorGroupHeader-tabsBackground)] border-b border-vscode-border overflow-x-auto">
        {projects.map((p) => (
          <div
            key={p.id}
            className={`group flex items-center gap-1.5 px-3 h-full cursor-pointer text-xs font-medium border-r border-vscode-border transition-colors shrink-0 ${
              p.id === activeProjectId
                ? 'bg-vscode-bg text-vscode-fg border-b-2 border-b-blue-500'
                : 'text-vscode-muted hover:text-vscode-fg hover:bg-vscode-bg/50'
            }`}
            onClick={() => switchProject(p.id)}
          >
            {/* Status dot */}
            <span
              className={`w-2 h-2 rounded-full ${statusColor(p.status)} shrink-0`}
              title={p.status}
            />

            {/* Project name */}
            <span className="truncate max-w-[120px]" title={p.path}>
              {p.name}
            </span>

            {/* Close button (visible on hover, not for active single project) */}
            {projects.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`Remove project "${p.name}"?`)) {
                    removeProject(p.id);
                  }
                }}
                className="ml-1 opacity-0 group-hover:opacity-100 text-vscode-muted hover:text-vscode-fg transition-opacity"
                title="Remove project"
              >
                x
              </button>
            )}
          </div>
        ))}

        {/* Add project button */}
        <button
          onClick={() => setShowAddDialog(!showAddDialog)}
          className="px-3 h-full text-vscode-muted hover:text-vscode-fg transition-colors text-sm shrink-0"
          title="Add project"
        >
          +
        </button>
      </div>

      {/* Add project dialog (inline) */}
      {showAddDialog && (
        <div className="flex items-center gap-2 px-3 py-2 bg-[var(--vscode-editorGroupHeader-tabsBackground)] border-b border-vscode-border">
          <input
            type="text"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            placeholder="Project path (e.g. /home/user/my-project)"
            className="flex-1 px-2 py-1 text-xs rounded bg-[var(--vscode-input-background)] text-[var(--vscode-input-foreground)] border border-[var(--vscode-input-border)] focus:outline-none focus:border-[var(--vscode-focusBorder)]"
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Name (optional)"
            className="w-32 px-2 py-1 text-xs rounded bg-[var(--vscode-input-background)] text-[var(--vscode-input-foreground)] border border-[var(--vscode-input-border)] focus:outline-none focus:border-[var(--vscode-focusBorder)]"
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />
          <button
            onClick={handleAdd}
            disabled={!newPath.trim() || adding}
            className="px-3 py-1 text-xs rounded bg-[var(--vscode-button-background)] text-[var(--vscode-button-foreground)] hover:bg-[var(--vscode-button-hoverBackground)] disabled:opacity-50"
          >
            {adding ? '...' : 'Add'}
          </button>
          <button
            onClick={() => {
              setShowAddDialog(false);
              setNewPath('');
              setNewName('');
            }}
            className="px-2 py-1 text-xs text-vscode-muted hover:text-vscode-fg"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
