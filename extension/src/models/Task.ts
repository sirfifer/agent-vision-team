export type TaskStatus = 'pending' | 'in_progress' | 'review' | 'complete';

export interface Task {
  id: string;
  title: string;
  description: string;
  assigned_worker?: string;
  status: TaskStatus;
  acceptance_criteria: string[];
  constraints: string[];
  scope: string[];
  created_at: string;
  updated_at: string;
}
