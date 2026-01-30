import { Tier, Severity, FindingPayload } from './Finding';

export type MessageType =
  | 'finding'
  | 'response'
  | 'change_proposal'
  | 'status_update'
  | 'drift_alert'
  | 'broadcast';

export type MessageStatus = 'sent' | 'read' | 'acknowledged';

export interface ResponsePayload {
  ref: string;
  status: 'acknowledged' | 'fixed' | 'reworked' | 'clarification_needed';
  plan?: string;
}

export interface ChangeProposalPayload {
  standard: string;
  current: string;
  proposed: string;
  rationale: string;
  impact: string;
}

export interface StatusPayload {
  status: string;
  detail?: string;
}

export interface DriftPayload {
  drift_type: 'time' | 'loop' | 'scope' | 'quality';
  description: string;
  duration?: string;
}

export type MessagePayload =
  | FindingPayload
  | ResponsePayload
  | ChangeProposalPayload
  | StatusPayload
  | DriftPayload;

export interface Message {
  id: string;
  from: string;
  to: string;
  type: MessageType;
  tier?: Tier;
  severity?: Severity;
  timestamp: string;
  status: MessageStatus;
  payload: MessagePayload;
}
