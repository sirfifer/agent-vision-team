import { useDashboard } from '../context/DashboardContext';
import type { AgentStatus } from '../types';

const roleLabels: Record<string, string> = {
  orchestrator: 'Orch',
  worker: 'Worker',
  'quality-reviewer': 'QR',
  'kg-librarian': 'KG-Lib',
};

const statusDotClass: Record<string, string> = {
  active: 'bg-agent-active',
  idle: 'bg-agent-idle',
  'not-configured': 'border border-agent-idle bg-transparent',
};

function AgentCard({ agent, isSelected, onSelect }: {
  agent: AgentStatus;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`flex-1 min-w-0 p-2.5 rounded border transition-colors text-left ${
        isSelected
          ? 'border-tier-quality bg-tier-quality/10'
          : 'border-vscode-border bg-vscode-widget-bg hover:border-vscode-muted'
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotClass[agent.status] ?? 'bg-agent-idle'}`} />
        <span className="font-semibold text-xs truncate">{agent.name}</span>
        <span className="ml-auto text-2xs text-vscode-muted uppercase">{roleLabels[agent.role] ?? agent.role}</span>
      </div>
      <div className="text-2xs text-vscode-muted truncate">
        {agent.currentTask ?? (agent.status === 'not-configured' ? 'Not configured' : 'Idle')}
      </div>
    </button>
  );
}

export function AgentCards() {
  const { data, agentFilter, setAgentFilter } = useDashboard();
  const { agents } = data;

  if (agents.length === 0) {
    return (
      <div className="flex gap-2 px-4 py-2">
        {['Orchestrator', 'Worker', 'Quality Reviewer', 'KG Librarian'].map(name => (
          <div key={name} className="flex-1 p-2.5 rounded border border-vscode-border bg-vscode-widget-bg opacity-50">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full border border-agent-idle" />
              <span className="font-semibold text-xs">{name}</span>
            </div>
            <div className="text-2xs text-vscode-muted">No data</div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex gap-2 px-4 py-2">
      {agents.map(agent => (
        <AgentCard
          key={agent.id}
          agent={agent}
          isSelected={agentFilter === agent.id}
          onSelect={() => setAgentFilter(agentFilter === agent.id ? null : agent.id)}
        />
      ))}
    </div>
  );
}
