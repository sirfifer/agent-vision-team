import { SUPPORTED_LANGUAGES, type ProjectConfig, type SupportedLanguage } from '../../../types';

interface QualityConfigStepProps {
  config: ProjectConfig;
  updateConfig: (updates: Partial<ProjectConfig>) => void;
  updateSettings: (updates: Partial<ProjectConfig['settings']>) => void;
  updateQuality: (updates: Partial<ProjectConfig['quality']>) => void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

const DEFAULT_COMMANDS: Record<SupportedLanguage, { test: string; lint: string; build: string; format: string }> = {
  python: {
    test: 'uv run pytest',
    lint: 'uv run ruff check',
    build: 'uv run python -m py_compile',
    format: 'uv run ruff format',
  },
  typescript: {
    test: 'npm run test',
    lint: 'npm run lint',
    build: 'npm run build',
    format: 'npm run format',
  },
  javascript: {
    test: 'npm test',
    lint: 'npm run lint',
    build: 'npm run build',
    format: 'npm run format',
  },
  swift: {
    test: 'swift test',
    lint: 'swiftlint',
    build: 'swift build',
    format: 'swiftformat .',
  },
  rust: {
    test: 'cargo test',
    lint: 'cargo clippy',
    build: 'cargo build',
    format: 'cargo fmt',
  },
};

const LANGUAGE_LABELS: Record<SupportedLanguage, string> = {
  python: 'Python',
  typescript: 'TypeScript',
  javascript: 'JavaScript',
  swift: 'Swift',
  rust: 'Rust',
};

export function QualityConfigStep({ config, updateConfig, updateSettings, updateQuality }: QualityConfigStepProps) {
  const handleLanguageToggle = (lang: SupportedLanguage) => {
    const current = config.languages as SupportedLanguage[];
    const newLanguages = current.includes(lang)
      ? current.filter(l => l !== lang)
      : [...current, lang];

    updateConfig({ languages: newLanguages });

    // Auto-populate commands for newly added languages
    if (!current.includes(lang)) {
      const defaults = DEFAULT_COMMANDS[lang];
      updateQuality({
        testCommands: { ...config.quality.testCommands, [lang]: defaults.test },
        lintCommands: { ...config.quality.lintCommands, [lang]: defaults.lint },
        buildCommands: { ...config.quality.buildCommands, [lang]: defaults.build },
        formatCommands: { ...config.quality.formatCommands, [lang]: defaults.format },
      });
    }
  };

  const handleCommandChange = (
    type: 'testCommands' | 'lintCommands' | 'buildCommands' | 'formatCommands',
    lang: string,
    value: string
  ) => {
    updateQuality({
      [type]: { ...config.quality[type], [lang]: value },
    });
  };

  const handleCoverageChange = (value: number) => {
    updateSettings({ coverageThreshold: value });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold mb-2">Quality Configuration</h3>
        <p className="text-vscode-muted">
          Select the languages used in your project and configure the commands for
          testing, linting, and building.
        </p>
      </div>

      {/* Language selection */}
      <div>
        <h4 className="font-medium mb-3">Languages</h4>
        <div className="flex flex-wrap gap-2">
          {SUPPORTED_LANGUAGES.map(lang => (
            <button
              key={lang}
              onClick={() => handleLanguageToggle(lang)}
              className={`
                px-3 py-1.5 rounded-full text-sm font-medium transition-colors
                ${config.languages.includes(lang)
                  ? 'bg-vscode-btn-bg text-vscode-btn-fg'
                  : 'bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg border border-vscode-border'
                }
              `}
            >
              {LANGUAGE_LABELS[lang]}
            </button>
          ))}
        </div>
      </div>

      {/* Coverage threshold */}
      <div>
        <h4 className="font-medium mb-2">Coverage Threshold</h4>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="100"
            value={config.settings.coverageThreshold}
            onChange={e => handleCoverageChange(Number(e.target.value))}
            className="flex-1"
          />
          <span className="w-16 text-right font-mono">
            {config.settings.coverageThreshold}%
          </span>
        </div>
        <p className="text-xs text-vscode-muted mt-1">
          Minimum test coverage required to pass the coverage gate
        </p>
      </div>

      {/* Commands per language */}
      {config.languages.length > 0 && (
        <div className="space-y-4">
          <h4 className="font-medium">Commands by Language</h4>

          {(config.languages as SupportedLanguage[]).map(lang => (
            <div key={lang} className="p-4 rounded-lg border border-vscode-border bg-vscode-widget-bg">
              <h5 className="font-medium mb-3">{LANGUAGE_LABELS[lang]}</h5>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs text-vscode-muted mb-1">Test Command</label>
                  <input
                    type="text"
                    value={config.quality.testCommands[lang] || ''}
                    onChange={e => handleCommandChange('testCommands', lang, e.target.value)}
                    placeholder={DEFAULT_COMMANDS[lang].test}
                    className="w-full px-2 py-1.5 rounded bg-vscode-input-bg border border-vscode-border text-sm font-mono focus:outline-none focus:border-vscode-btn-bg"
                  />
                </div>

                <div>
                  <label className="block text-xs text-vscode-muted mb-1">Lint Command</label>
                  <input
                    type="text"
                    value={config.quality.lintCommands[lang] || ''}
                    onChange={e => handleCommandChange('lintCommands', lang, e.target.value)}
                    placeholder={DEFAULT_COMMANDS[lang].lint}
                    className="w-full px-2 py-1.5 rounded bg-vscode-input-bg border border-vscode-border text-sm font-mono focus:outline-none focus:border-vscode-btn-bg"
                  />
                </div>

                <div>
                  <label className="block text-xs text-vscode-muted mb-1">Build Command</label>
                  <input
                    type="text"
                    value={config.quality.buildCommands[lang] || ''}
                    onChange={e => handleCommandChange('buildCommands', lang, e.target.value)}
                    placeholder={DEFAULT_COMMANDS[lang].build}
                    className="w-full px-2 py-1.5 rounded bg-vscode-input-bg border border-vscode-border text-sm font-mono focus:outline-none focus:border-vscode-btn-bg"
                  />
                </div>

                <div>
                  <label className="block text-xs text-vscode-muted mb-1">Format Command</label>
                  <input
                    type="text"
                    value={config.quality.formatCommands[lang] || ''}
                    onChange={e => handleCommandChange('formatCommands', lang, e.target.value)}
                    placeholder={DEFAULT_COMMANDS[lang].format}
                    className="w-full px-2 py-1.5 rounded bg-vscode-input-bg border border-vscode-border text-sm font-mono focus:outline-none focus:border-vscode-btn-bg"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {config.languages.length === 0 && (
        <div className="p-4 rounded-lg border border-amber-500/30 bg-amber-500/10 text-sm">
          Select at least one language to configure quality commands.
        </div>
      )}
    </div>
  );
}
