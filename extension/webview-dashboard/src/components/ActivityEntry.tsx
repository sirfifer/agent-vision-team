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
};

const agentColors: Record<string, string> = {
  orchestrator: 'bg-blue-600',
  worker: 'bg-purple-600',
  'quality-reviewer': 'bg-tier-vision',
  'kg-librarian': 'bg-tier-architecture',
};

function getAgentInitials(agent: string): string {
  if (agent.includes('orchestrator') || agent === 'Orch') return 'OR';
  if (agent.includes('worker')) return 'W' + (agent.match(/\d+/)?.[0] ?? '');
  if (agent.includes('quality')) return 'QR';
  if (agent.includes('kg') || agent.includes('librarian')) return 'KG';
  return agent.slice(0, 2).toUpperCase();
}

function getAgentColor(agent: string): string {
  for (const [key, color] of Object.entries(agentColors)) {
    if (agent.toLowerCase().includes(key)) return color;
  }
  return 'bg-agent-idle';
}

export function ActivityEntryComponent({ entry }: { entry: ActivityEntryType }) {
  const [expanded, setExpanded] = useState(false);
  const tierBorder = entry.tier ? tierBorderColors[entry.tier] : 'border-l-vscode-border';
  const time = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className={`w-full text-left border-l-2 ${tierBorder} px-3 py-2 hover:bg-vscode-widget-bg/50 transition-colors border-b border-vscode-border`}
    >
      <div className="flex items-start gap-2">
        <span className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-2xs font-bold text-white ${getAgentColor(entry.agent)}`}>
          {getAgentInitials(entry.agent)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-2xs text-vscode-muted">{time}</span>
            <span className="text-2xs">{typeIcons[entry.type] ?? ''}</span>
            <span className="text-xs truncate">{entry.summary}</span>
          </div>
          {entry.governanceRef && (
            <span className="text-2xs text-vscode-muted">
              re: {entry.governanceRef}
            </span>
          )}
        </div>
      </div>

      {expanded && entry.detail && (
        <div className="mt-2 ml-8 text-xs text-vscode-muted whitespace-pre-wrap border-l-2 border-vscode-border pl-2">
          {entry.detail}
        </div>
      )}
    </button>
  );
}
