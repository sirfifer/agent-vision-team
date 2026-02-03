/**
 * Research prompt types for the researcher agent
 */

export type ResearchType = 'periodic' | 'exploratory';
export type ResearchModelHint = 'opus' | 'sonnet' | 'auto';
export type ResearchOutputFormat = 'change_report' | 'research_brief' | 'custom';
export type ResearchStatus = 'pending' | 'scheduled' | 'in_progress' | 'completed' | 'failed';

export interface ResearchSchedule {
  type: 'once' | 'daily' | 'weekly' | 'monthly';
  dayOfWeek?: number;  // 0-6 for weekly
  dayOfMonth?: number; // 1-31 for monthly
  time?: string;       // HH:MM format
  lastRun?: string;    // ISO timestamp
  nextRun?: string;    // ISO timestamp
}

export interface ResearchResult {
  timestamp: string;
  success: boolean;
  summary?: string;
  briefPath?: string;
  error?: string;
}

export interface ResearchPrompt {
  id: string;
  name: string;
  type: ResearchType;
  topic: string;
  context: string;
  scope: string;
  modelHint: ResearchModelHint;
  output: ResearchOutputFormat;
  relatedEntities: string[];
  schedule?: ResearchSchedule;
  status: ResearchStatus;
  createdAt: string;
  updatedAt: string;
  lastResult?: ResearchResult;
}

/**
 * Convert a ResearchPrompt to a YAML prompt file format
 * that can be written to .avt/research-prompts/
 */
export function toPromptYaml(prompt: ResearchPrompt): string {
  const lines: string[] = [
    '---',
    `type: ${prompt.type}`,
    `topic: "${prompt.topic}"`,
    `context: "${prompt.context}"`,
    `scope: "${prompt.scope}"`,
    `model_hint: ${prompt.modelHint}`,
    `output: ${prompt.output}`,
  ];

  if (prompt.relatedEntities.length > 0) {
    lines.push(`related_entities:`);
    for (const entity of prompt.relatedEntities) {
      lines.push(`  - "${entity}"`);
    }
  }

  if (prompt.schedule) {
    lines.push(`schedule:`);
    lines.push(`  type: ${prompt.schedule.type}`);
    if (prompt.schedule.time) {
      lines.push(`  time: "${prompt.schedule.time}"`);
    }
    if (prompt.schedule.dayOfWeek !== undefined) {
      lines.push(`  day_of_week: ${prompt.schedule.dayOfWeek}`);
    }
    if (prompt.schedule.dayOfMonth !== undefined) {
      lines.push(`  day_of_month: ${prompt.schedule.dayOfMonth}`);
    }
  }

  lines.push('---');
  lines.push('');
  lines.push(`# ${prompt.name}`);
  lines.push('');
  lines.push('## Research Instructions');
  lines.push('');
  lines.push(prompt.context);
  lines.push('');
  lines.push('## Scope');
  lines.push('');
  lines.push(prompt.scope);
  lines.push('');

  return lines.join('\n');
}
