import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import {
  ProjectConfig,
  SetupReadiness,
  DEFAULT_PROJECT_CONFIG,
  DEFAULT_RULES_CONFIG,
  RECOMMENDED_PERMISSIONS,
} from '../models/ProjectConfig';
import { ResearchPrompt, toPromptYaml } from '../models/ResearchPrompt';

/**
 * Service for managing AVT project configuration.
 * Configuration is stored in .avt/project-config.json
 * Permissions are synced to .claude/settings.local.json
 */
export class ProjectConfigService {
  private configPath: string;
  private claudeSettingsPath: string;
  private avtRoot: string;
  private docsRoot: string;

  constructor(workspaceRoot: string) {
    this.avtRoot = path.join(workspaceRoot, '.avt');
    this.docsRoot = path.join(workspaceRoot, 'docs');
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
   * Get the docs root directory path
   */
  getDocsRoot(): string {
    return this.docsRoot;
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
        settings: {
          ...DEFAULT_PROJECT_CONFIG.settings,
          ...config.settings,
          qualityGates: {
            ...DEFAULT_PROJECT_CONFIG.settings.qualityGates,
            ...config.settings?.qualityGates,
          },
          contextReinforcement: {
            ...DEFAULT_PROJECT_CONFIG.settings.contextReinforcement,
            ...(config.settings?.contextReinforcement ?? {}),
          },
        },
        quality: { ...DEFAULT_PROJECT_CONFIG.quality, ...config.quality },
        ingestion: { ...DEFAULT_PROJECT_CONFIG.ingestion, ...config.ingestion },
        rules: config.rules ?? DEFAULT_RULES_CONFIG,
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
    const visionDir = path.join(this.docsRoot, 'vision');
    const archDir = path.join(this.docsRoot, 'architecture');

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
      return files.some((f) => f.endsWith('.md') && f.toLowerCase() !== 'readme.md');
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
    return RECOMMENDED_PERMISSIONS.map((p) => p.pattern);
  }

  /**
   * Create a vision document in docs/vision/
   */
  createVisionDoc(name: string, content: string): string {
    const visionDir = path.join(this.docsRoot, 'vision');
    if (!fs.existsSync(visionDir)) {
      fs.mkdirSync(visionDir, { recursive: true });
    }

    const filename = this.sanitizeFilename(name) + '.md';
    const filepath = path.join(visionDir, filename);
    fs.writeFileSync(filepath, content, 'utf-8');
    return filepath;
  }

  /**
   * Create an architecture document in docs/architecture/
   */
  createArchitectureDoc(name: string, content: string): string {
    const archDir = path.join(this.docsRoot, 'architecture');
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
    const visionDir = path.join(this.docsRoot, 'vision');
    return this.listDocsInFolder(visionDir);
  }

  /**
   * List architecture documents
   */
  listArchitectureDocs(): string[] {
    const archDir = path.join(this.docsRoot, 'architecture');
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
      return files.filter((f) => f.endsWith('.md') && f.toLowerCase() !== 'readme.md');
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
      path.join(this.avtRoot, 'task-briefs'),
      path.join(this.avtRoot, 'memory'),
      path.join(this.avtRoot, 'research-prompts'),
      path.join(this.avtRoot, 'research-briefs'),
      path.join(this.docsRoot, 'vision'),
      path.join(this.docsRoot, 'architecture'),
    ];

    for (const dir of dirs) {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    }

    // Create starter documents if they don't exist
    this.createFileIfMissing(path.join(this.docsRoot, 'vision', 'vision.md'), VISION_STARTER);
    this.createFileIfMissing(
      path.join(this.docsRoot, 'architecture', 'architecture.md'),
      ARCHITECTURE_STARTER,
    );
    this.createFileIfMissing(
      path.join(this.avtRoot, 'research-prompts', 'README.md'),
      RESEARCH_PROMPTS_README,
    );
    this.createFileIfMissing(
      path.join(this.avtRoot, 'research-briefs', 'README.md'),
      RESEARCH_BRIEFS_README,
    );
  }

  private createFileIfMissing(filepath: string, content: string): void {
    if (!fs.existsSync(filepath)) {
      fs.writeFileSync(filepath, content, 'utf-8');
    }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Research Prompts
  // ─────────────────────────────────────────────────────────────────────────────

  private get researchPromptsPath(): string {
    return path.join(this.avtRoot, 'research-prompts.json');
  }

  private get researchPromptsDir(): string {
    return path.join(this.avtRoot, 'research-prompts');
  }

  private get researchBriefsDir(): string {
    return path.join(this.avtRoot, 'research-briefs');
  }

  /**
   * List all research prompts
   */
  listResearchPrompts(): ResearchPrompt[] {
    if (!fs.existsSync(this.researchPromptsPath)) {
      return [];
    }

    try {
      const raw = fs.readFileSync(this.researchPromptsPath, 'utf-8');
      return JSON.parse(raw) as ResearchPrompt[];
    } catch {
      return [];
    }
  }

  /**
   * Save a research prompt (create or update)
   */
  saveResearchPrompt(prompt: ResearchPrompt): void {
    const prompts = this.listResearchPrompts();
    const idx = prompts.findIndex((p) => p.id === prompt.id);

    if (idx >= 0) {
      prompts[idx] = prompt;
    } else {
      prompts.push(prompt);
    }

    // Ensure directory exists
    if (!fs.existsSync(this.avtRoot)) {
      fs.mkdirSync(this.avtRoot, { recursive: true });
    }

    // Save to JSON file
    const tmpPath = this.researchPromptsPath + '.tmp';
    fs.writeFileSync(tmpPath, JSON.stringify(prompts, null, 2), 'utf-8');
    fs.renameSync(tmpPath, this.researchPromptsPath);

    // Also write a YAML prompt file that the researcher agent can read
    this.writeResearchPromptFile(prompt);
  }

  /**
   * Delete a research prompt
   */
  deleteResearchPrompt(id: string): void {
    const prompts = this.listResearchPrompts();
    const filtered = prompts.filter((p) => p.id !== id);

    if (filtered.length === prompts.length) {
      return; // Not found
    }

    const tmpPath = this.researchPromptsPath + '.tmp';
    fs.writeFileSync(tmpPath, JSON.stringify(filtered, null, 2), 'utf-8');
    fs.renameSync(tmpPath, this.researchPromptsPath);

    // Remove the prompt file if it exists
    const promptFile = path.join(this.researchPromptsDir, `${id}.md`);
    if (fs.existsSync(promptFile)) {
      fs.unlinkSync(promptFile);
    }
  }

  /**
   * Get a single research prompt by ID
   */
  getResearchPrompt(id: string): ResearchPrompt | undefined {
    const prompts = this.listResearchPrompts();
    return prompts.find((p) => p.id === id);
  }

  /**
   * Update the status of a research prompt
   */
  updateResearchPromptStatus(
    id: string,
    status: ResearchPrompt['status'],
    result?: ResearchPrompt['lastResult'],
  ): void {
    const prompt = this.getResearchPrompt(id);
    if (!prompt) return;

    prompt.status = status;
    prompt.updatedAt = new Date().toISOString();
    if (result) {
      prompt.lastResult = result;
    }

    this.saveResearchPrompt(prompt);
  }

  /**
   * Write a research prompt as a markdown file that the researcher agent can read
   */
  private writeResearchPromptFile(prompt: ResearchPrompt): void {
    if (!fs.existsSync(this.researchPromptsDir)) {
      fs.mkdirSync(this.researchPromptsDir, { recursive: true });
    }

    const content = toPromptYaml(prompt);
    const filepath = path.join(this.researchPromptsDir, `${prompt.id}.md`);
    fs.writeFileSync(filepath, content, 'utf-8');
  }

  /**
   * Ensure research-related directories exist
   */
  ensureResearchDirectories(): void {
    if (!fs.existsSync(this.researchPromptsDir)) {
      fs.mkdirSync(this.researchPromptsDir, { recursive: true });
    }
    if (!fs.existsSync(this.researchBriefsDir)) {
      fs.mkdirSync(this.researchBriefsDir, { recursive: true });
    }
  }
}

const VISION_STARTER = `# Vision Standards

Define your project's core principles below. Each standard is an inviolable rule that governs all development. Once ingested into the Knowledge Graph, vision standards are immutable — only humans can modify them.

For larger projects, you can split standards into separate files in this folder (e.g. \`no-singletons.md\`, \`error-handling.md\`). For smaller projects, listing them all here works well.

## Standards

<!-- Replace these examples with your project's actual vision standards -->

### Example: Protocol-Based Dependency Injection

**Statement:** All services use protocol-based dependency injection.

**Rationale:** Enables testability and loose coupling between components.

### Example: No Singletons in Production Code

**Statement:** No singletons in production code (test mocks are OK).

**Rationale:** Singletons create hidden coupling and make testing difficult.
`;

const ARCHITECTURE_STARTER = `# Architecture

Define your project's architectural standards, patterns, and key components below. These are ingested into the Knowledge Graph and used by agents to make design decisions. Architecture documents can be modified with human approval; deviations require governance review.

For larger projects, you can break this into separate files in this folder (e.g. \`service-registry.md\`, \`auth-service.md\`, \`api-versioning.md\`). For smaller projects, a single document works well.

## Architectural Standards

<!-- Replace these examples with your project's actual architecture -->

### Example: API Versioning

**Description:** All public APIs use URL-based versioning (e.g. \`/v1/users\`).

**Rationale:** Enables backward-compatible evolution without breaking existing clients.

## Patterns

### Example: Service Registry

**Description:** Services register themselves at startup and are discovered via a central registry.

**Usage:** Inject \`ServiceRegistry\` and call \`registry.resolve(ServiceProtocol)\`.

## Components

### Example: AuthService

**Description:** Handles JWT-based authentication with refresh token rotation.

**State:** Tracked via observations in the Knowledge Graph.
`;

const RESEARCH_PROMPTS_README = `# Research Prompts

This folder contains research prompt definitions for the researcher agent.

## Prompt Types

- **Periodic**: Scheduled checks for changes in external dependencies, APIs, or technologies
- **Exploratory**: Deep investigation to inform architectural decisions or new features

## Format

Each prompt file follows this format:

\`\`\`yaml
---
type: periodic | exploratory
topic: "What to research"
context: "Why this research matters"
scope: "Boundaries of the research"
model_hint: opus | sonnet | auto
output: change_report | research_brief | custom
related_entities:
  - "KG entity name"
schedule:  # Only for periodic
  type: once | daily | weekly | monthly
  time: "09:00"
  day_of_week: 1  # For weekly (0=Sunday)
  day_of_month: 1  # For monthly
---

# Research Title

## Research Instructions
[Detailed instructions for the researcher agent]

## Scope
[What to include and exclude]
\`\`\`

## Managing Prompts

Prompts are typically managed via the dashboard, but can also be created manually.
The registry is stored in \`.avt/research-prompts.json\`.

## Output

Research results are stored in \`.avt/research-briefs/\` as markdown files.
`;

const RESEARCH_BRIEFS_README = `# Research Briefs

This folder contains completed research output from the researcher agent.

## Brief Types

- **Change Reports**: For periodic/maintenance research tracking external changes
- **Research Briefs**: For exploratory research informing architectural decisions

## Change Report Format

\`\`\`markdown
## Change Report: [Technology/API Name]

**Date**: YYYY-MM-DD
**Sources**: [URLs consulted]

### Breaking Changes
- [Change]: [Impact] → [Required Action]

### Deprecations
- [Feature]: [Timeline] → [Migration Path]

### New Features
- [Feature]: [Relevance to Project]

### Recommendations
1. [Priority action items]
\`\`\`

## Research Brief Format

\`\`\`markdown
## Research Brief: [Topic]

**Question**: [What decision this informs]
**Date**: YYYY-MM-DD

### Options Evaluated

#### Option A: [Name]
- **Pros**: [In our context]
- **Cons**: [In our context]
- **Risks**: [What could go wrong]

### Recommendation
[Recommended approach with rationale]

### Open Questions
[What still needs human decision]
\`\`\`

## Using Briefs

Reference research briefs in task briefs when spawning workers:

\`\`\`markdown
## Context
See research brief: .avt/research-briefs/rb-auth-approaches.md
\`\`\`
`;
