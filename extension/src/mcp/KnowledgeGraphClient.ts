import { McpClientService } from '../services/McpClientService';
import { Entity, ProtectionTier } from '../models/Entity';

export class KnowledgeGraphClient {
  constructor(private mcp: McpClientService) {}

  async createEntities(
    entities: {
      name: string;
      entityType: string;
      observations: string[];
    }[]
  ): Promise<{ created: number }> {
    return (await this.mcp.callTool('knowledge-graph', 'create_entities', {
      entities,
    })) as { created: number };
  }

  async createRelations(
    relations: {
      from: string;
      to: string;
      relationType: string;
    }[]
  ): Promise<{ created: number }> {
    return (await this.mcp.callTool('knowledge-graph', 'create_relations', {
      relations,
    })) as { created: number };
  }

  async addObservations(
    entityName: string,
    observations: string[]
  ): Promise<{ added: number }> {
    return (await this.mcp.callTool('knowledge-graph', 'add_observations', {
      entityName,
      observations,
    })) as { added: number };
  }

  async searchNodes(query: string): Promise<Entity[]> {
    return (await this.mcp.callTool('knowledge-graph', 'search_nodes', {
      query,
    })) as Entity[];
  }

  async getEntity(name: string): Promise<Entity> {
    return (await this.mcp.callTool('knowledge-graph', 'get_entity', {
      name,
    })) as Entity;
  }

  async getEntitiesByTier(tier: ProtectionTier): Promise<Entity[]> {
    return (await this.mcp.callTool('knowledge-graph', 'get_entities_by_tier', {
      tier,
    })) as Entity[];
  }

  async validateTierAccess(
    entityName: string,
    operation: 'read' | 'write' | 'delete',
    callerRole: string
  ): Promise<{ allowed: boolean; reason?: string }> {
    return (await this.mcp.callTool('knowledge-graph', 'validate_tier_access', {
      entityName,
      operation,
      callerRole,
    })) as { allowed: boolean; reason?: string };
  }

  /**
   * Ingest markdown documents from a folder into KG entities.
   * @param tier 'vision' or 'architecture'
   * @returns Ingestion result with counts and any errors
   */
  async ingestDocuments(
    tier: 'vision' | 'architecture'
  ): Promise<{
    ingested: number;
    entities: string[];
    errors: string[];
    skipped: string[];
  }> {
    const folder = `docs/${tier}/`;
    return (await this.mcp.callTool('knowledge-graph', 'ingest_documents', {
      folder,
      tier,
    })) as {
      ingested: number;
      entities: string[];
      errors: string[];
      skipped: string[];
    };
  }
}
