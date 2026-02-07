import type { DashboardData } from '../types';

const now = new Date();
const ago = (minutes: number) => new Date(now.getTime() - minutes * 60_000).toISOString();

export const DEMO_DATA: DashboardData = {
  connectionStatus: 'connected',
  serverPorts: { kg: 3101, quality: 3102, governance: 3103 },

  // ── Agents ──────────────────────────────────────────────────────────────────
  agents: [
    {
      id: 'orchestrator',
      name: 'Orchestrator',
      role: 'orchestrator',
      status: 'active',
      currentTask: 'Coordinating voice pipeline implementation',
    },
    {
      id: 'worker',
      name: 'Worker',
      role: 'worker',
      status: 'active',
      currentTask: 'Implementing speech-to-text adapter',
    },
    {
      id: 'quality-reviewer',
      name: 'Quality Reviewer',
      role: 'quality-reviewer',
      status: 'reviewing',
      currentTask: 'Reviewing NLU intent classifier',
    },
    {
      id: 'kg-librarian',
      name: 'KG Librarian',
      role: 'kg-librarian',
      status: 'idle',
    },
    {
      id: 'governance-reviewer',
      name: 'Governance Reviewer',
      role: 'governance-reviewer',
      status: 'reviewing',
      currentTask: '2 review(s) pending',
    },
    {
      id: 'researcher',
      name: 'Researcher',
      role: 'researcher',
      status: 'active',
      currentTask: 'Evaluating WebSocket streaming protocols',
    },
    {
      id: 'project-steward',
      name: 'Project Steward',
      role: 'project-steward',
      status: 'idle',
    },
  ],

  // ── Vision Standards ────────────────────────────────────────────────────────
  visionStandards: [
    {
      name: 'Latency Budget',
      entityType: 'vision_standard',
      observations: [
        'All voice interactions must complete within 500ms end-to-end latency budget',
        'Includes STT + NLU + response generation + TTS pipeline',
        'protection_tier: vision',
      ],
      relations: [],
    },
    {
      name: 'Audio Privacy',
      entityType: 'vision_standard',
      observations: [
        'No audio data stored beyond session scope without explicit user consent',
        'Session recordings purged within 24 hours unless opted in',
        'protection_tier: vision',
      ],
      relations: [],
    },
    {
      name: 'Protocol-Based DI',
      entityType: 'vision_standard',
      observations: [
        'All services use protocol-based dependency injection',
        'No singletons in production code; test mocks are acceptable',
        'protection_tier: vision',
      ],
      relations: [],
    },
    {
      name: 'Graceful Degradation',
      entityType: 'vision_standard',
      observations: [
        'Voice agent must gracefully degrade when any pipeline stage fails',
        'Fallback to text-based interaction if STT or TTS is unavailable',
        'protection_tier: vision',
      ],
      relations: [],
    },
  ],

  // ── Architecture Elements ───────────────────────────────────────────────────
  architecturalElements: [
    {
      name: 'VoiceStreamPipeline',
      entityType: 'pattern',
      observations: [
        'Streaming pipeline: AudioCapture -> VAD -> STT -> NLU -> DialogManager -> TTS -> AudioPlayback',
        'Each stage is a protocol-conforming processor with backpressure support',
        'protection_tier: architecture',
      ],
      relations: [
        { from: 'VoiceStreamPipeline', to: 'IntentClassifier', relationType: 'uses' },
        { from: 'VoiceStreamPipeline', to: 'AudioSessionManager', relationType: 'managed_by' },
      ],
    },
    {
      name: 'IntentClassifier',
      entityType: 'component',
      observations: [
        'Transformer-based NLU model for intent recognition and slot filling',
        'Supports 47 intent categories with 92% F1 score',
        'Hot-swappable model versions via feature flags',
        'protection_tier: architecture',
      ],
      relations: [
        { from: 'IntentClassifier', to: 'DialogManager', relationType: 'feeds' },
      ],
    },
    {
      name: 'AudioSessionManager',
      entityType: 'component',
      observations: [
        'Manages WebSocket connections for bidirectional audio streaming',
        'Handles session lifecycle: create, stream, pause, resume, terminate',
        'Implements automatic reconnection with exponential backoff',
        'protection_tier: architecture',
      ],
      relations: [],
    },
    {
      name: 'WebSocket Gateway',
      entityType: 'pattern',
      observations: [
        'Gateway pattern for real-time audio streaming via WebSocket',
        'Supports binary audio frames (16-bit PCM, 16kHz) and JSON control messages',
        'Rate limiting: 100 concurrent sessions per node',
        'protection_tier: architecture',
      ],
      relations: [],
    },
    {
      name: 'DialogManager',
      entityType: 'component',
      observations: [
        'State machine managing multi-turn conversation flow',
        'Tracks dialog context, slot values, and conversation history',
        'Supports context carryover across turns with 5-turn memory window',
        'protection_tier: architecture',
      ],
      relations: [],
    },
  ],

  // ── Activity Feed ───────────────────────────────────────────────────────────
  activities: [
    {
      id: 'act-demo-1',
      timestamp: ago(2),
      agent: 'orchestrator',
      type: 'status',
      summary: 'Connected to MCP servers',
    },
    {
      id: 'act-demo-2',
      timestamp: ago(5),
      agent: 'worker',
      type: 'decision',
      summary: '[pattern_choice] Use WebSocket for real-time audio streaming',
      tier: 'architecture',
      detail: 'Verdict: approved. WebSocket provides the lowest latency for bidirectional audio. Evaluated against SSE and HTTP/2 streaming.',
      governanceRef: 'dec-ws-001',
    },
    {
      id: 'act-demo-3',
      timestamp: ago(8),
      agent: 'governance-reviewer',
      type: 'review',
      summary: 'Governance: 7 approved, 1 blocked, 2 pending',
      tier: 'architecture',
    },
    {
      id: 'act-demo-4',
      timestamp: ago(12),
      agent: 'quality-reviewer',
      type: 'finding',
      summary: 'Quality gates: 3/5 passed (tests, findings failing)',
      tier: 'quality',
      detail: 'Build: pass, Lint: pass, Tests: 3 failing in NLU module, Coverage: 87%, Findings: 2 open',
    },
    {
      id: 'act-demo-5',
      timestamp: ago(15),
      agent: 'worker',
      type: 'decision',
      summary: '[component_design] IntentClassifier uses transformer-based model',
      tier: 'architecture',
      detail: 'Verdict: approved. Transformer model provides best accuracy/latency tradeoff for our intent categories.',
      governanceRef: 'dec-nlp-002',
    },
    {
      id: 'act-demo-6',
      timestamp: ago(20),
      agent: 'researcher',
      type: 'research',
      summary: 'Starting research: "WebSocket streaming protocol evaluation"',
      detail: 'Topic: Compare WebSocket, SSE, and gRPC for bidirectional audio streaming\nModel: opus',
    },
    {
      id: 'act-demo-7',
      timestamp: ago(25),
      agent: 'kg-librarian',
      type: 'status',
      summary: 'Memory refreshed: 14 entities (4 vision, 5 architecture)',
    },
    {
      id: 'act-demo-8',
      timestamp: ago(30),
      agent: 'worker',
      type: 'decision',
      summary: '[api_design] Voice session API: REST for setup, WebSocket for streaming',
      tier: 'architecture',
      detail: 'Verdict: approved. REST handles session creation/configuration; WebSocket handles real-time audio bidirectional streaming.',
      governanceRef: 'dec-api-003',
    },
    {
      id: 'act-demo-9',
      timestamp: ago(35),
      agent: 'quality-reviewer',
      type: 'finding',
      summary: 'AudioProcessor missing error boundary for malformed PCM frames',
      tier: 'quality',
    },
    {
      id: 'act-demo-10',
      timestamp: ago(40),
      agent: 'orchestrator',
      type: 'status',
      summary: 'MCP servers started and connected automatically',
    },
  ],

  // ── Task Counts ─────────────────────────────────────────────────────────────
  tasks: { active: 3, total: 7 },
  sessionPhase: 'implementing',

  // ── Governed Tasks ──────────────────────────────────────────────────────────
  governedTasks: [
    {
      id: 'gt-001',
      implementationTaskId: 'avt/1',
      subject: 'Implement speech-to-text adapter using Whisper API',
      status: 'approved',
      reviews: [
        {
          id: 'rev-001',
          reviewType: 'governance',
          status: 'approved',
          verdict: 'approved',
          guidance: 'Approved. Use the VoiceStreamPipeline pattern. Ensure latency stays within 200ms for STT stage.',
          createdAt: ago(45),
          completedAt: ago(42),
        },
      ],
      createdAt: ago(50),
      releasedAt: ago(42),
    },
    {
      id: 'gt-002',
      implementationTaskId: 'avt/2',
      subject: 'Add WebSocket streaming to voice pipeline',
      status: 'pending_review',
      reviews: [
        {
          id: 'rev-002',
          reviewType: 'governance',
          status: 'pending',
          createdAt: ago(10),
        },
      ],
      createdAt: ago(15),
    },
    {
      id: 'gt-003',
      implementationTaskId: 'avt/3',
      subject: 'Refactor NLU intent classifier for multi-language support',
      status: 'blocked',
      reviews: [
        {
          id: 'rev-003',
          reviewType: 'governance',
          status: 'blocked',
          verdict: 'blocked',
          guidance: 'Blocked: multi-language support requires updating the Latency Budget vision standard. Current 500ms budget may be insufficient for translation pipeline. Needs human review.',
          createdAt: ago(30),
          completedAt: ago(28),
        },
      ],
      createdAt: ago(35),
    },
    {
      id: 'gt-004',
      implementationTaskId: 'avt/4',
      subject: 'Implement voice session analytics dashboard',
      status: 'completed',
      reviews: [
        {
          id: 'rev-004',
          reviewType: 'governance',
          status: 'approved',
          verdict: 'approved',
          guidance: 'Approved. Analytics must respect Audio Privacy standard: no PII in metrics.',
          createdAt: ago(120),
          completedAt: ago(115),
        },
      ],
      createdAt: ago(125),
      releasedAt: ago(115),
    },
    {
      id: 'gt-005',
      implementationTaskId: 'avt/5',
      subject: 'Add fallback handling for unrecognized intents',
      status: 'in_progress',
      reviews: [
        {
          id: 'rev-005',
          reviewType: 'governance',
          status: 'approved',
          verdict: 'approved',
          guidance: 'Approved. Follow the Graceful Degradation vision standard. Fallback should offer text-based alternatives.',
          createdAt: ago(60),
          completedAt: ago(55),
        },
      ],
      createdAt: ago(65),
      releasedAt: ago(55),
    },
    {
      id: 'gt-006',
      implementationTaskId: 'avt/6',
      subject: 'Implement voice activity detection (VAD) module',
      status: 'approved',
      reviews: [
        {
          id: 'rev-006a',
          reviewType: 'governance',
          status: 'approved',
          verdict: 'approved',
          guidance: 'Approved. VAD must operate within 50ms to preserve latency budget.',
          createdAt: ago(90),
          completedAt: ago(85),
        },
        {
          id: 'rev-006b',
          reviewType: 'architecture',
          status: 'approved',
          verdict: 'approved',
          guidance: 'Architecture review passed. VAD integrates correctly with VoiceStreamPipeline.',
          createdAt: ago(85),
          completedAt: ago(80),
        },
      ],
      createdAt: ago(95),
      releasedAt: ago(80),
    },
  ],

  // ── Governance Stats ────────────────────────────────────────────────────────
  governanceStats: {
    totalDecisions: 10,
    approved: 7,
    blocked: 1,
    pending: 2,
    pendingReviews: 2,
    totalGovernedTasks: 6,
    needsHumanReview: 1,
  },

  // ── Quality Gates ───────────────────────────────────────────────────────────
  qualityGateResults: {
    build: { name: 'build', passed: true, detail: 'TypeScript compilation successful' },
    lint: { name: 'lint', passed: true, detail: '0 lint violations' },
    tests: { name: 'tests', passed: false, detail: '3 tests failing in NLU intent classifier module' },
    coverage: { name: 'coverage', passed: true, detail: '87% coverage (threshold: 80%)' },
    findings: { name: 'findings', passed: false, detail: '2 open findings requiring attention' },
    all_passed: false,
    timestamp: ago(12),
  },

  // ── Decision History ────────────────────────────────────────────────────────
  decisionHistory: [
    {
      id: 'dec-ws-001',
      taskId: 'avt/2',
      agent: 'worker',
      category: 'pattern_choice',
      summary: 'Use WebSocket for real-time bidirectional audio streaming',
      confidence: 'high',
      verdict: 'approved',
      guidance: 'WebSocket provides lowest latency for bidirectional audio. Aligns with VoiceStreamPipeline architecture.',
      createdAt: ago(5),
    },
    {
      id: 'dec-nlp-002',
      taskId: 'avt/3',
      agent: 'worker',
      category: 'component_design',
      summary: 'IntentClassifier uses distilled transformer model for on-device inference',
      confidence: 'high',
      verdict: 'approved',
      guidance: 'Transformer model achieves 92% F1 with <100ms inference. Fits within latency budget.',
      createdAt: ago(15),
    },
    {
      id: 'dec-api-003',
      taskId: 'avt/1',
      agent: 'worker',
      category: 'api_design',
      summary: 'Voice session API: REST for lifecycle, WebSocket for streaming',
      confidence: 'high',
      verdict: 'approved',
      guidance: 'Clean separation of concerns. REST handles session CRUD; WebSocket handles real-time audio.',
      createdAt: ago(30),
    },
    {
      id: 'dec-lang-004',
      taskId: 'avt/3',
      agent: 'worker',
      category: 'deviation',
      summary: 'Multi-language support requires exceeding 500ms latency budget for translation',
      confidence: 'medium',
      verdict: 'blocked',
      guidance: 'Deviating from Latency Budget vision standard requires human approval. Consider async translation pipeline.',
      createdAt: ago(28),
    },
    {
      id: 'dec-vad-005',
      taskId: 'avt/6',
      agent: 'worker',
      category: 'pattern_choice',
      summary: 'Use Silero VAD for voice activity detection with WebRTC integration',
      confidence: 'high',
      verdict: 'approved',
      guidance: 'Silero VAD operates in <30ms, well within the 50ms allocation for VAD stage.',
      createdAt: ago(85),
    },
    {
      id: 'dec-tts-006',
      taskId: 'avt/5',
      agent: 'worker',
      category: 'component_design',
      summary: 'TTS fallback chain: primary neural TTS, secondary concatenative, text output',
      confidence: 'high',
      verdict: 'approved',
      guidance: 'Aligned with Graceful Degradation standard. Three-tier fallback ensures user always gets a response.',
      createdAt: ago(55),
    },
  ],

  // ── Trust Engine Findings ───────────────────────────────────────────────────
  findings: [
    {
      id: 'FIND-001',
      tool: 'eslint',
      severity: 'warning',
      component: 'AudioProcessor',
      description: 'Missing error boundary for malformed PCM frames in AudioProcessor.processChunk()',
      createdAt: ago(35),
      status: 'open',
    },
    {
      id: 'FIND-002',
      tool: 'coverage',
      severity: 'info',
      component: 'VoiceSession',
      description: 'VoiceSession.handleReconnect() has 0% branch coverage',
      createdAt: ago(20),
      status: 'open',
    },
    {
      id: 'FIND-003',
      tool: 'eslint',
      severity: 'error',
      component: 'IntentClassifier',
      description: 'Unused import: TranslationPipeline in IntentClassifier.ts',
      createdAt: ago(60),
      status: 'dismissed',
    },
  ],

  // ── Hook Governance Status ──────────────────────────────────────────────────
  hookGovernanceStatus: {
    totalInterceptions: 8,
    lastInterceptionAt: ago(10),
    recentInterceptions: [
      { timestamp: ago(10), subject: 'Add WebSocket streaming to voice pipeline' },
      { timestamp: ago(30), subject: 'Refactor NLU intent classifier' },
      { timestamp: ago(55), subject: 'Add fallback handling for unrecognized intents' },
    ],
  },

  // ── Session State ───────────────────────────────────────────────────────────
  sessionState: {
    phase: 'implementing',
    lastCheckpoint: 'checkpoint-003',
    activeWorktrees: ['../voiceflow-worker-1', '../voiceflow-worker-2'],
  },

  // ── Job Summary ────────────────────────────────────────────────────────────
  jobSummary: { running: 1, queued: 0, total: 3 },
};
