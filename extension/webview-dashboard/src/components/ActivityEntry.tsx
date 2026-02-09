import { useState } from 'react';
import type { ActivityEntry as ActivityEntryType } from '../types';

const tierBorderColors: Record<string, string> = {
  vision: 'border-l-tier-vision',
  architecture: 'border-l-tier-architecture',
  quality: 'border-l-tier-quality',
};

const typeIcons: Record<string, string> = {
  finding: '\u26A0',
  guidance: '\u2139',
  response: '\u2713',
  status: '\u25CF',
  drift: '\u21BB',
  decision: '\u2696',
  review: '\u2611',
};

const typeDescriptions: Record<string, string> = {
  finding: 'Finding: a quality or governance issue detected during review',
  guidance: 'Guidance: actionable recommendation from a reviewer',
  response: 'Response: an agent acted on a finding or guidance',
  status: 'Status: an operational update from an agent',
  drift: 'Drift: a deviation from expected behavior or timeline detected',
  decision: 'Decision: a governance checkpoint submitted by an agent',
  review: 'Review: a governance verdict returned for a decision or plan',
};

const agentColors: Record<string, string> = {
  orchestrator: 'bg-blue-600',
  worker: 'bg-purple-600',
  'quality-reviewer': 'bg-tier-vision',
  'kg-librarian': 'bg-tier-architecture',
  'governance-reviewer': 'bg-tier-quality',
};

const agentDescriptions: Record<string, string> = {
  orchestrator: 'Orchestrator: coordinates workers, maintains governance, manages session lifecycle',
  worker: 'Worker: implements scoped task briefs under governance checkpoints',
  'quality-reviewer': 'Quality Reviewer: runs deterministic quality gates (build, lint, tests, coverage)',
  'kg-librarian': 'KG Librarian: curates Knowledge Graph entities and observations',
  'governance-reviewer': 'Governance Reviewer: evaluates decisions against vision and architecture standards',
};

function getAgentInitials(agent: string): string {
  if (agent.includes('orchestrator') || agent === 'Orch') return 'OR';
  if (agent.includes('worker')) return 'W' + (agent.match(/\d+/)?.[0] ?? '');
  if (agent.includes('quality')) return 'QR';
  if (agent.includes('kg') || agent.includes('librarian')) return 'KG';
  if (agent.includes('governance')) return 'GV';
  return agent.slice(0, 2).toUpperCase();
}

function getAgentColor(agent: string): string {
  for (const [key, color] of Object.entries(agentColors)) {
    if (agent.toLowerCase().includes(key)) return color;
  }
  return 'bg-agent-idle';
}

function getAgentDescription(agent: string): string {
  for (const [key, desc] of Object.entries(agentDescriptions)) {
    if (agent.toLowerCase().includes(key)) return desc;
  }
  return agent;
}

export function ActivityEntryComponent({ entry }: { entry: ActivityEntryType }) {
  const [expanded, setExpanded] = useState(false);
  const tierBorder = entry.tier ? tierBorderColors[entry.tier] : 'border-l-vscode-border';
  const time = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  const tierLabel = entry.tier ? `Protection tier: ${entry.tier}` : 'No tier assigned';
  const entryTooltip = `${entry.summary}\n\nAgent: ${entry.agent} | Type: ${entry.type} | ${tierLabel}${entry.detail ? '\n\nClick to expand details' : ''}`;

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className={`w-full text-left border-l-2 ${tierBorder} px-3 py-2 hover:bg-vscode-widget-bg/50 transition-colors border-b border-vscode-border`}
      title={entryTooltip}
    >
      <div className="flex items-start gap-2">
        <span
          className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-2xs font-bold text-white ${getAgentColor(entry.agent)}`}
          title={getAgentDescription(entry.agent)}
        >
          {getAgentInitials(entry.agent)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-2xs text-vscode-muted" title={`Timestamp: ${entry.timestamp}`}>{time}</span>
            <span className="text-2xs" title={typeDescriptions[entry.type] ?? entry.type}>{typeIcons[entry.type] ?? ''}</span>
            <span className="text-xs truncate" title={entry.summary}>{entry.summary}</span>
          </div>
          {entry.governanceRef && (
            <span className="text-2xs text-vscode-muted" title={`References governance entity: ${entry.governanceRef}. This activity is linked to a Knowledge Graph entity.`}>
              re: {entry.governanceRef}
            </span>
          )}
        </div>
      </div>

      {expanded && entry.detail && (
        <div className="mt-2 ml-8 text-xs text-vscode-muted whitespace-pre-wrap border-l-2 border-vscode-border pl-2" title="Full detail for this activity entry">
          {entry.detail}
        </div>
      )}
    </button>
  );
}
