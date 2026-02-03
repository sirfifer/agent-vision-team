import { useDashboard } from '../context/DashboardContext';

export function SetupBanner() {
  const { setupReadiness, setShowWizard } = useDashboard();

  // Don't show banner if setup is complete or we don't have readiness info
  if (!setupReadiness || setupReadiness.isComplete) {
    return null;
  }

  const missingItems: string[] = [];
  if (!setupReadiness.hasVisionDocs) {
    missingItems.push('Vision documents');
  }
  if (!setupReadiness.hasArchitectureDocs) {
    missingItems.push('Architecture documents');
  }
  if (!setupReadiness.hasProjectConfig) {
    missingItems.push('Project configuration');
  }
  if (!setupReadiness.hasKgIngestion) {
    missingItems.push('Knowledge Graph ingestion');
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-amber-900/30 border-b border-amber-600/50 text-amber-200">
      <svg
        className="w-5 h-5 flex-shrink-0 text-amber-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <div className="flex-1">
        <span className="font-medium">Setup Incomplete</span>
        <span className="text-amber-300/80 ml-2">
          Missing: {missingItems.join(', ')}
        </span>
      </div>
      <button
        onClick={() => setShowWizard(true)}
        className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition-colors"
      >
        Run Setup Wizard
      </button>
    </div>
  );
}
