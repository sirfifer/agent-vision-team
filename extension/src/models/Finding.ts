export type Tier = 'vision' | 'architecture' | 'quality';

export type Severity =
  | 'vision_conflict'
  | 'security'
  | 'architectural'
  | 'logic'
  | 'style'
  | 'formatting';

export interface FindingPayload {
  component: string;
  finding: string;
  rationale: string;
  suggestion?: string;
  standard_ref?: string;
}

export interface Finding {
  id: string;
  from: string;
  tier: Tier;
  severity: Severity;
  payload: FindingPayload;
  status: 'open' | 'acknowledged' | 'resolved' | 'dismissed';
  timestamp: string;
}
