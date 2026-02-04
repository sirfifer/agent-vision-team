import { useDashboard } from '../context/DashboardContext';
import type { AgentStatus } from '../types';

const roleLabels: Record<string, string> = {
  orchestrator: 'Orch',
  worker: 'Worker',
  'quality-reviewer': 'QR',
  'kg-librarian': 'KG-Lib',
  'governance-reviewer': 'Gov',
  researcher: 'Research',
  'project-steward': 'Steward',
};

const roleDescriptions: Record<string, string> = {
  orchestrator: 'Orchestrator: coordinates subagents, decomposes tasks, enforces the three-tier governance hierarchy',
  worker: 'Worker: implements scoped task briefs, follows established patterns, submits decisions to governance',
  'quality-reviewer': 'Quality Reviewer: evaluates work through vision alignment, architectural conformance, and quality compliance',
  'kg-librarian': 'KG Librarian: curates institutional memory, consolidates observations, promotes solution patterns',
  'governance-reviewer': 'Governance Reviewer: AI-powered review of decisions and plans against vision and architecture standards',
  researcher: 'Researcher: gathers intelligence for architectural decisions and tracks external changes affecting the project',
  'project-steward': 'Project Steward: maintains project hygiene, naming conventions, organization, and essential file completeness',
};

const statusDotClass: Record<string, string> = {
  active: 'bg-agent-active',
  idle: 'bg-agent-idle',
  'not-configured': 'border border-agent-idle bg-transparent',
};

const statusDescriptions: Record<string, string> = {
  active: 'Agent definition found and ready',
  idle: 'Agent is idle, waiting for assignment',
  'not-configured': 'Agent definition not found in .claude/agents/',
};

function AgentCard({ agent, isSelected, onSelect }: {
  agent: AgentStatus;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const roleDesc = roleDescriptions[agent.role] ?? agent.role;
  const statusDesc = statusDescriptions[agent.status] ?? agent.status;
  const filterHint = isSelected ? 'Click to clear activity filter' : 'Click to filter Activity Feed to this agent';

  return (
    <button
      onClick={onSelect}
      title={`${roleDesc}\n\nStatus: ${statusDesc}\n${filterHint}`}
      className={`flex-1 min-w-0 p-2.5 rounded border transition-colors text-left ${
        isSelected
          ? 'border-tier-quality bg-tier-quality/10'
          : 'border-vscode-border bg-vscode-widget-bg hover:border-vscode-muted'
      }`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${statusDotClass[agent.status] ?? 'bg-agent-idle'}`}
          title={statusDesc}
        />
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
      <div className="flex gap-2 px-4 py-2" title="Agent cards appear here after connecting. Each card shows an agent's status and current task.">
        {['Orchestrator', 'Worker', 'Quality Reviewer', 'KG Librarian', 'Researcher', 'Steward'].map(name => (
          <div key={name} className="flex-1 p-2.5 rounded border border-vscode-border bg-vscode-widget-bg opacity-50" title={`${name}: no data yet. Connect to MCP servers to detect agents.`}>
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
    <div className="flex gap-2 px-4 py-2" title="Click an agent card to filter the Activity Feed to that agent's events">
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
