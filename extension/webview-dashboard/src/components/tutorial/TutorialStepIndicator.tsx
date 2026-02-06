import { TUTORIAL_STEPS, TUTORIAL_STEP_LABELS, type TutorialStep } from '../../types';

interface TutorialStepIndicatorProps {
  currentStep: TutorialStep;
  onStepClick?: (step: TutorialStep) => void;
  completedSteps: Set<TutorialStep>;
}

export function TutorialStepIndicator({
  currentStep,
  onStepClick,
  completedSteps,
}: TutorialStepIndicatorProps) {
  const currentIndex = TUTORIAL_STEPS.indexOf(currentStep);

  return (
    <div className="flex items-center justify-center px-3 py-3 border-b border-vscode-border bg-vscode-widget-bg overflow-x-auto">
      {TUTORIAL_STEPS.map((step, index) => {
        const isCompleted = completedSteps.has(step);
        const isCurrent = step === currentStep;
        const isPast = index < currentIndex;
        const isClickable = onStepClick && (isCompleted || isPast);

        return (
          <div key={step} className="flex items-center">
            {index > 0 && (
              <div
                className={`w-4 h-0.5 ${
                  isPast || isCompleted ? 'bg-tier-quality' : 'bg-vscode-border'
                }`}
              />
            )}
            <button
              onClick={() => isClickable && onStepClick(step)}
              disabled={!isClickable}
              className={`
                flex items-center gap-1 px-1 py-1 rounded text-xs whitespace-nowrap
                transition-colors flex-shrink-0
                ${isCurrent ? 'bg-vscode-btn-bg text-vscode-btn-fg' : ''}
                ${isCompleted && !isCurrent ? 'text-tier-quality' : ''}
                ${!isCurrent && !isCompleted ? 'text-vscode-muted' : ''}
                ${isClickable ? 'hover:bg-vscode-btn-bg/50 cursor-pointer' : 'cursor-default'}
              `}
              title={TUTORIAL_STEP_LABELS[step]}
            >
              <span
                className={`
                  flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold flex-shrink-0
                  ${isCurrent ? 'bg-vscode-btn-fg text-vscode-btn-bg' : ''}
                  ${isCompleted && !isCurrent ? 'bg-tier-quality text-white' : ''}
                  ${!isCurrent && !isCompleted ? 'bg-vscode-border text-vscode-muted' : ''}
                `}
              >
                {isCompleted && !isCurrent ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  index + 1
                )}
              </span>
              {isCurrent && (
                <span className="text-[11px]">{TUTORIAL_STEP_LABELS[step]}</span>
              )}
            </button>
          </div>
        );
      })}
    </div>
  );
}
