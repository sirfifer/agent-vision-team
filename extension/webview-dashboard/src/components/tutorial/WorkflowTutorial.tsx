import { useState, useCallback, useRef, useEffect } from 'react';
import { useDashboard } from '../../context/DashboardContext';
import { TUTORIAL_STEPS, type TutorialStep } from '../../types';
import { TutorialStepIndicator } from './TutorialStepIndicator';
import { WelcomeStep } from './steps/WelcomeStep';
import { BigPictureStep } from './steps/BigPictureStep';
import { SetupStep } from './steps/SetupStep';
import { StartingWorkStep } from './steps/StartingWorkStep';
import { BehindScenesStep } from './steps/BehindScenesStep';
import { MonitoringStep } from './steps/MonitoringStep';
import { KnowledgeGraphStep } from './steps/KnowledgeGraphStep';
import { QualityGatesStep } from './steps/QualityGatesStep';
import { TipsStep } from './steps/TipsStep';
import { ReadyStep } from './steps/ReadyStep';

export function WorkflowTutorial() {
  const { showTutorial, setShowTutorial, setShowWizard } = useDashboard();
  const [currentStep, setCurrentStep] = useState<TutorialStep>('welcome');
  const [completedSteps, setCompletedSteps] = useState<Set<TutorialStep>>(new Set());
  const contentRef = useRef<HTMLDivElement>(null);

  const currentIndex = TUTORIAL_STEPS.indexOf(currentStep);
  const isFirstStep = currentIndex === 0;
  const isLastStep = currentIndex === TUTORIAL_STEPS.length - 1;

  // Scroll step content to top on step change
  useEffect(() => {
    contentRef.current?.scrollTo(0, 0);
  }, [currentStep]);

  const handleNext = useCallback(() => {
    setCompletedSteps((prev) => new Set([...prev, currentStep]));
    if (!isLastStep) {
      setCurrentStep(TUTORIAL_STEPS[currentIndex + 1]);
    }
  }, [currentStep, currentIndex, isLastStep]);

  const handleBack = useCallback(() => {
    if (!isFirstStep) {
      setCurrentStep(TUTORIAL_STEPS[currentIndex - 1]);
    }
  }, [currentIndex, isFirstStep]);

  const handleStepClick = useCallback(
    (step: TutorialStep) => {
      const stepIndex = TUTORIAL_STEPS.indexOf(step);
      if (stepIndex <= currentIndex || completedSteps.has(step)) {
        setCurrentStep(step);
      }
    },
    [currentIndex, completedSteps],
  );

  const handleClose = useCallback(() => {
    sessionStorage.setItem('avt-tutorial-dismissed', 'true');
    setShowTutorial(false);
  }, [setShowTutorial]);

  const handleLaunchWizard = useCallback(() => {
    setShowTutorial(false);
    setShowWizard(true);
  }, [setShowTutorial, setShowWizard]);

  if (!showTutorial) {
    return null;
  }

  const renderStep = () => {
    switch (currentStep) {
      case 'welcome':
        return <WelcomeStep />;
      case 'big-picture':
        return <BigPictureStep />;
      case 'setup':
        return <SetupStep onLaunchWizard={handleLaunchWizard} />;
      case 'starting-work':
        return <StartingWorkStep />;
      case 'behind-scenes':
        return <BehindScenesStep />;
      case 'monitoring':
        return <MonitoringStep />;
      case 'knowledge-graph':
        return <KnowledgeGraphStep />;
      case 'quality-gates':
        return <QualityGatesStep />;
      case 'tips':
        return <TipsStep />;
      case 'ready':
        return <ReadyStep onLaunchWizard={handleLaunchWizard} />;
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-vscode-bg border border-vscode-border rounded-lg shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-vscode-border">
          <h2 className="text-lg font-semibold">Workflow Tutorial</h2>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-vscode-widget-bg rounded transition-colors"
            title="Close tutorial"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Step indicator */}
        <TutorialStepIndicator
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
          <span className="text-xs text-vscode-muted">
            Step {currentIndex + 1} of {TUTORIAL_STEPS.length}
          </span>
          <div>
            {!isLastStep ? (
              <button
                onClick={handleNext}
                className="px-4 py-2 rounded bg-vscode-btn-bg text-vscode-btn-fg hover:opacity-80 transition-opacity"
              >
                {currentStep === 'welcome' ? 'Get Started' : 'Next'}
              </button>
            ) : (
              <button
                onClick={handleClose}
                className="px-4 py-2 rounded bg-tier-quality text-white hover:opacity-80 transition-opacity"
              >
                Close Tutorial
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
