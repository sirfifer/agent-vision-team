import { useState, useEffect } from 'react';

interface Job {
  id: string;
  prompt: string;
  agent_type: string | null;
  model: string;
  status: string;
  submitted_at: string;
  started_at: string | null;
  completed_at: string | null;
  output: string;
  exit_code: number | null;
  error: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  queued: 'bg-yellow-600/20 text-yellow-300',
  running: 'bg-blue-600/20 text-blue-300',
  completed: 'bg-green-600/20 text-green-300',
  failed: 'bg-red-600/20 text-red-300',
  cancelled: 'bg-gray-600/20 text-gray-300',
};

export function JobList() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchJobs = async () => {
    try {
      const apiBase = (window as any).__AVT_API_BASE__ || '';
      const apiKey = (window as any).__AVT_API_KEY__ || '';
      const headers: Record<string, string> = {};
      if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

      const resp = await fetch(`${apiBase}/api/jobs`, { headers });
      const data = await resp.json();
      setJobs(data.jobs || []);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  // Also listen for WebSocket job_status events
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'job_status' || (msg.data && msg.data.status)) {
        fetchJobs(); // Refresh on any job status change
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  if (jobs.length === 0) {
    return (
      <div className="p-4 text-center text-vscode-muted text-sm">
        No jobs submitted yet. Use the form above to submit work.
      </div>
    );
  }

  return (
    <div className="divide-y divide-[var(--vscode-widget-border)]">
      {jobs.map((job) => (
        <div key={job.id} className="p-3">
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => setExpandedId(expandedId === job.id ? null : job.id)}
          >
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[job.status] || ''}`}
            >
              {job.status}
            </span>
            <span className="text-xs text-vscode-muted font-mono">{job.id}</span>
            <span className="flex-1 text-sm truncate">{job.prompt.slice(0, 80)}</span>
            <span className="text-xs text-vscode-muted">
              {job.model}
              {job.agent_type ? ` / ${job.agent_type}` : ''}
            </span>
          </div>

          {expandedId === job.id && (
            <div className="mt-2 space-y-2">
              <div className="text-xs text-vscode-muted">
                Submitted: {new Date(job.submitted_at).toLocaleString()}
                {job.started_at && <> | Started: {new Date(job.started_at).toLocaleString()}</>}
                {job.completed_at && (
                  <> | Completed: {new Date(job.completed_at).toLocaleString()}</>
                )}
              </div>

              {job.error && (
                <div className="p-2 rounded bg-red-900/20 text-red-300 text-xs">{job.error}</div>
              )}

              {job.output && (
                <pre className="p-2 rounded bg-[var(--vscode-input-background)] text-xs overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap">
                  {job.output}
                </pre>
              )}

              <div className="text-xs text-vscode-muted">
                <strong>Prompt:</strong> {job.prompt}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
