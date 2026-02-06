import { useState, useCallback, useRef, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { WIZARD_STEPS, WIZARD_STEP_LABELS, type WizardStep, type ProjectConfig } from '../../types';
import { WizardStepIndicator } from './WizardStepIndicator';
import { WelcomeStep } from './steps/WelcomeStep';
import { VisionDocsStep } from './steps/VisionDocsStep';
import { ArchitectureDocsStep } from './steps/ArchitectureDocsStep';
import { QualityConfigStep } from './steps/QualityConfigStep';
import { PermissionsStep } from './steps/PermissionsStep';
import { SettingsStep } from './steps/SettingsStep';
import { RulesStep } from './steps/RulesStep';
import { IngestionStep } from './steps/IngestionStep';
import { CompleteStep } from './steps/CompleteStep';

const DEFAULT_CONFIG: ProjectConfig = {
  version: 1,
  setupComplete: false,
  languages: [],
  metadata: {
    isOpenSource: false,
  },
  settings: {
    mockTests: false,
    mockTestsForCostlyOps: true,
    coverageThreshold: 80,
    autoGovernance: true,
    qualityGates: {
      build: true,
      lint: true,
      tests: true,
      coverage: true,
      findings: true,
    },
    kgAutoCuration: true,
  },
  quality: {
    testCommands: {},
    lintCommands: {},
    buildCommands: {},
    formatCommands: {},
  },
  permissions: [],
  ingestion: {
    lastVisionIngest: null,
    lastArchitectureIngest: null,
    visionDocCount: 0,
    architectureDocCount: 0,
  },
};

export function SetupWizard() {
  const { showWizard, setShowWizard, projectConfig, sendMessage } = useDashboard();
  const [currentStep, setCurrentStep] = useState<WizardStep>('welcome');
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStep>>(new Set());
  const [draftConfig, setDraftConfig] = useState<ProjectConfig>(
    projectConfig ?? DEFAULT_CONFIG
  );
  const contentRef = useRef<HTMLDivElement>(null);

  const currentIndex = WIZARD_STEPS.indexOf(currentStep);

  // Scroll step content to top whenever the current step changes
  useEffect(() => {
    contentRef.current?.scrollTo(0, 0);
  }, [currentStep]);
  const isFirstStep = currentIndex === 0;
  const isLastStep = currentIndex === WIZARD_STEPS.length - 1;

  const handleNext = useCallback(() => {
    // Mark current step as completed
    setCompletedSteps(prev => new Set([...prev, currentStep]));

    if (!isLastStep) {
      setCurrentStep(WIZARD_STEPS[currentIndex + 1]);
    }
  }, [currentStep, currentIndex, isLastStep]);

  const handleBack = useCallback(() => {
    if (!isFirstStep) {
      setCurrentStep(WIZARD_STEPS[currentIndex - 1]);
    }
  }, [currentIndex, isFirstStep]);

  const handleSkip = useCallback(() => {
    if (!isLastStep) {
      setCurrentStep(WIZARD_STEPS[currentIndex + 1]);
    }
  }, [currentIndex, isLastStep]);

  const handleStepClick = useCallback((step: WizardStep) => {
    const stepIndex = WIZARD_STEPS.indexOf(step);
    if (stepIndex <= currentIndex || completedSteps.has(step)) {
      setCurrentStep(step);
    }
  }, [currentIndex, completedSteps]);

  const handleClose = useCallback(() => {
    sessionStorage.setItem('avt-wizard-dismissed', 'true');
    setShowWizard(false);
  }, [setShowWizard]);

  const handleComplete = useCallback(() => {
    // Save config with setupComplete = true
    const finalConfig: ProjectConfig = {
      ...draftConfig,
      setupComplete: true,
    };
    sendMessage({ type: 'saveProjectConfig', config: finalConfig });
    sessionStorage.setItem('avt-wizard-dismissed', 'true');
    setShowWizard(false);
  }, [draftConfig, sendMessage, setShowWizard]);

  const updateConfig = useCallback((updates: Partial<ProjectConfig>) => {
    setDraftConfig(prev => ({ ...prev, ...updates }));
  }, []);

  const updateSettings = useCallback((updates: Partial<ProjectConfig['settings']>) => {
    setDraftConfig(prev => ({
      ...prev,
      settings: { ...prev.settings, ...updates },
    }));
  }, []);

  const updateQuality = useCallback((updates: Partial<ProjectConfig['quality']>) => {
    setDraftConfig(prev => ({
      ...prev,
      quality: { ...prev.quality, ...updates },
    }));
  }, []);

  if (!showWizard) {
    return null;
  }

  const renderStep = () => {
    const stepProps = {
      config: draftConfig,
      updateConfig,
      updateSettings,
      updateQuality,
      onNext: handleNext,
      onBack: handleBack,
      onSkip: handleSkip,
    };

    switch (currentStep) {
      case 'welcome':
        return <WelcomeStep {...stepProps} />;
      case 'vision-docs':
        return <VisionDocsStep {...stepProps} />;
      case 'architecture-docs':
        return <ArchitectureDocsStep {...stepProps} />;
      case 'quality-config':
        return <QualityConfigStep {...stepProps} />;
      case 'rules':
        return <RulesStep {...stepProps} />;
      case 'permissions':
        return <PermissionsStep {...stepProps} />;
      case 'settings':
        return <SettingsStep {...stepProps} />;
      case 'ingestion':
        return <IngestionStep {...stepProps} />;
      case 'complete':
        return <CompleteStep {...stepProps} onComplete={handleComplete} />;
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-vscode-bg border border-vscode-border rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-vscode-border">
          <h2 className="text-lg font-semibold">
            AVT Setup Wizard
          </h2>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-vscode-widget-bg rounded transition-colors"
            title="Close wizard (you can reopen it later)"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Step indicator */}
        <WizardStepIndicator
          currentStep={currentStep}
          completedSteps={completedSteps}
          onStepClick={handleStepClick}
        />

        {/* Step content */}
        <div ref={contentRef} className="flex-1 overflow-y-auto p-6">
          {renderStep()}
        </div>

        {/* Footer navigation */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-vscode-border">
          <div>
            {!isFirstStep && (
              <button
                onClick={handleBack}
                className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
              >
                Back
              </button>
            )}
          </div>
          <div className="flex gap-2">
            {!isLastStep && currentStep !== 'welcome' && (
              <button
                onClick={handleSkip}
                className="px-4 py-2 rounded text-vscode-muted hover:text-vscode-fg transition-colors"
              >
                Skip
              </button>
            )}
            {!isLastStep ? (
              <button
                onClick={handleNext}
                className="px-4 py-2 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
              >
                {currentStep === 'welcome' ? 'Get Started' : 'Next'}
              </button>
            ) : (
              <button
                onClick={handleComplete}
                className="px-4 py-2 rounded bg-tier-quality text-white hover:opacity-80 transition-opacity"
              >
                Complete Setup
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
