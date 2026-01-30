export type ProtectionTier = 'vision' | 'architecture' | 'quality';
export type Mutability = 'human_only' | 'human_approved_only' | 'automated';

export type EntityType =
  | 'component'
  | 'vision_standard'
  | 'architectural_standard'
  | 'pattern'
  | 'problem'
  | 'solution_pattern';

export interface Relation {
  from: string;
  to: string;
  relationType: string;
}

export interface Entity {
  name: string;
  entityType: EntityType;
  observations: string[];
  relations: Relation[];
}
