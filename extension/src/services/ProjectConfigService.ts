import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import {
  ProjectConfig,
  SetupReadiness,
  DEFAULT_PROJECT_CONFIG,
  RECOMMENDED_PERMISSIONS,
} from '../models/ProjectConfig';

/**
 * Service for managing AVT project configuration.
 * Configuration is stored in .avt/project-config.json
 * Permissions are synced to .claude/settings.local.json
 */
export class ProjectConfigService {
  private configPath: string;
  private claudeSettingsPath: string;
  private avtRoot: string;

  constructor(workspaceRoot: string) {
    this.avtRoot = path.join(workspaceRoot, '.avt');
    this.configPath = path.join(this.avtRoot, 'project-config.json');
    this.claudeSettingsPath = path.join(workspaceRoot, '.claude', 'settings.local.json');
  }

  /**
   * Get the AVT root directory path
   */
  getAvtRoot(): string {
    return this.avtRoot;
  }

  /**
   * Load project configuration from .avt/project-config.json
   * Returns defaults if file doesn't exist
   */
  load(): ProjectConfig {
    if (!fs.existsSync(this.configPath)) {
      return { ...DEFAULT_PROJECT_CONFIG };
    }

    try {
      const raw = fs.readFileSync(this.configPath, 'utf-8');
      const config = JSON.parse(raw) as ProjectConfig;
      // Merge with defaults to handle missing fields from older versions
      return {
        ...DEFAULT_PROJECT_CONFIG,
        ...config,
        settings: { ...DEFAULT_PROJECT_CONFIG.settings, ...config.settings },
        quality: { ...DEFAULT_PROJECT_CONFIG.quality, ...config.quality },
        ingestion: { ...DEFAULT_PROJECT_CONFIG.ingestion, ...config.ingestion },
      };
    } catch {
      return { ...DEFAULT_PROJECT_CONFIG };
    }
  }

  /**
   * Save project configuration to .avt/project-config.json
   * Uses atomic write (write to .tmp, then rename)
   */
  save(config: ProjectConfig): void {
    // Ensure .avt directory exists
    if (!fs.existsSync(this.avtRoot)) {
      fs.mkdirSync(this.avtRoot, { recursive: true });
    }

    const tmpPath = this.configPath + '.tmp';
    fs.writeFileSync(tmpPath, JSON.stringify(config, null, 2), 'utf-8');
    fs.renameSync(tmpPath, this.configPath);
  }

  /**
   * Check if setup has been completed
   */
  isSetupComplete(): boolean {
    const config = this.load();
    return config.setupComplete;
  }

  /**
   * Get detailed setup readiness status
   */
  getReadiness(): SetupReadiness {
    const visionDir = path.join(this.avtRoot, 'vision');
    const archDir = path.join(this.avtRoot, 'architecture');

    const hasVisionDocs = this.hasDocsInFolder(visionDir);
    const hasArchitectureDocs = this.hasDocsInFolder(archDir);
    const hasProjectConfig = fs.existsSync(this.configPath);

    const config = this.load();
    const hasKgIngestion = config.ingestion.lastVisionIngest !== null;

    return {
      hasVisionDocs,
      hasArchitectureDocs,
      hasProjectConfig,
      hasKgIngestion,
      isComplete: hasVisionDocs && hasArchitectureDocs && hasProjectConfig && hasKgIngestion,
    };
  }

  /**
   * Check if a folder contains .md files (excluding README.md)
   */
  private hasDocsInFolder(folderPath: string): boolean {
    if (!fs.existsSync(folderPath)) {
      return false;
    }

    try {
      const files = fs.readdirSync(folderPath);
      return files.some(f =>
        f.endsWith('.md') &&
        f.toLowerCase() !== 'readme.md'
      );
    } catch {
      return false;
    }
  }

  /**
   * Sync permissions to .claude/settings.local.json
   * This writes the permissions in the format Claude Code expects
   */
  syncPermissionsToClaudeSettings(permissions: string[]): void {
    const claudeDir = path.dirname(this.claudeSettingsPath);
    if (!fs.existsSync(claudeDir)) {
      fs.mkdirSync(claudeDir, { recursive: true });
    }

    // Load existing settings.local.json if it exists
    let existingSettings: Record<string, unknown> = {};
    if (fs.existsSync(this.claudeSettingsPath)) {
      try {
        const raw = fs.readFileSync(this.claudeSettingsPath, 'utf-8');
        existingSettings = JSON.parse(raw);
      } catch {
        // If parse fails, start fresh
      }
    }

    // Update the permissions section
    existingSettings.permissions = {
      allow: permissions,
    };

    // Write back
    const tmpPath = this.claudeSettingsPath + '.tmp';
    fs.writeFileSync(tmpPath, JSON.stringify(existingSettings, null, 2), 'utf-8');
    fs.renameSync(tmpPath, this.claudeSettingsPath);
  }

  /**
   * Get the default recommended permissions
   */
  getDefaultPermissions(): string[] {
    return RECOMMENDED_PERMISSIONS.map(p => p.pattern);
  }

  /**
   * Create a vision document in .avt/vision/
   */
  createVisionDoc(name: string, content: string): string {
    const visionDir = path.join(this.avtRoot, 'vision');
    if (!fs.existsSync(visionDir)) {
      fs.mkdirSync(visionDir, { recursive: true });
    }

    const filename = this.sanitizeFilename(name) + '.md';
    const filepath = path.join(visionDir, filename);
    fs.writeFileSync(filepath, content, 'utf-8');
    return filepath;
  }

  /**
   * Create an architecture document in .avt/architecture/
   */
  createArchitectureDoc(name: string, content: string): string {
    const archDir = path.join(this.avtRoot, 'architecture');
    if (!fs.existsSync(archDir)) {
      fs.mkdirSync(archDir, { recursive: true });
    }

    const filename = this.sanitizeFilename(name) + '.md';
    const filepath = path.join(archDir, filename);
    fs.writeFileSync(filepath, content, 'utf-8');
    return filepath;
  }

  /**
   * List vision documents
   */
  listVisionDocs(): string[] {
    const visionDir = path.join(this.avtRoot, 'vision');
    return this.listDocsInFolder(visionDir);
  }

  /**
   * List architecture documents
   */
  listArchitectureDocs(): string[] {
    const archDir = path.join(this.avtRoot, 'architecture');
    return this.listDocsInFolder(archDir);
  }

  /**
   * List .md files in a folder (excluding README.md)
   */
  private listDocsInFolder(folderPath: string): string[] {
    if (!fs.existsSync(folderPath)) {
      return [];
    }

    try {
      const files = fs.readdirSync(folderPath);
      return files.filter(f =>
        f.endsWith('.md') &&
        f.toLowerCase() !== 'readme.md'
      );
    } catch {
      return [];
    }
  }

  /**
   * Sanitize a string for use as a filename
   */
  private sanitizeFilename(name: string): string {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }

  /**
   * Ensure .avt folder structure exists with README files
   */
  ensureFolderStructure(): void {
    const dirs = [
      this.avtRoot,
      path.join(this.avtRoot, 'vision'),
      path.join(this.avtRoot, 'architecture'),
      path.join(this.avtRoot, 'task-briefs'),
      path.join(this.avtRoot, 'memory'),
    ];

    for (const dir of dirs) {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    }

    // Create README files if they don't exist
    this.createReadmeIfMissing(
      path.join(this.avtRoot, 'vision', 'README.md'),
      VISION_README
    );
    this.createReadmeIfMissing(
      path.join(this.avtRoot, 'architecture', 'README.md'),
      ARCHITECTURE_README
    );
  }

  private createReadmeIfMissing(filepath: string, content: string): void {
    if (!fs.existsSync(filepath)) {
      fs.writeFileSync(filepath, content, 'utf-8');
    }
  }
}

const VISION_README = `# Vision Standards

This folder contains vision standard documents. Each \`.md\` file defines one vision standard that will be ingested into the Knowledge Graph.

## Format

Each document should follow this format:

\`\`\`markdown
# <Standard Name>

## Statement
<Clear, actionable statement of the standard>

## Rationale
<Why this standard exists>

## Examples
- Compliant: <example of code/behavior that follows the standard>
- Violation: <example of code/behavior that violates the standard>
\`\`\`

## Important Notes

- Vision standards are **immutable** once ingested — only humans can modify them
- Violations of vision standards **block all related work**
- Standards should be clear, specific, and actionable
- One file per standard

## Examples

- \`protocol-based-di.md\` — "All services use protocol-based dependency injection"
- \`no-singletons.md\` — "No singletons in production code"
- \`error-handling.md\` — "Error handling uses Result types, not exceptions"
`;

const ARCHITECTURE_README = `# Architecture Documents

This folder contains architecture documents. Each \`.md\` file defines an architectural standard, pattern, or component that will be ingested into the Knowledge Graph.

## Format

Each document should follow this format:

\`\`\`markdown
# <Name>

## Type
<One of: architectural_standard, pattern, component>

## Description
<What this represents>

## Rationale
<Why this exists or why this pattern was chosen>

## Usage
<How to use this pattern or interact with this component>
\`\`\`

## Document Types

- **Architectural Standard**: Design rules enforced across the codebase
- **Pattern**: Established implementation patterns agents should follow
- **Component**: Tracked system components with state and behavior

## Important Notes

- Architecture documents can be modified with human approval
- Deviations require governance review
- Components track state through observations in the Knowledge Graph

## Examples

- \`service-registry.md\` — Pattern for service discovery and registration
- \`auth-service.md\` — Component definition for authentication service
- \`api-versioning.md\` — Architectural standard for API versioning
`;
