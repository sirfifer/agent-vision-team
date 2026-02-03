interface WarningDialogProps {
  title: string;
  message: string;
  severity: 'warning' | 'danger';
  onConfirm: () => void;
  onCancel: () => void;
  confirmText?: string;
  cancelText?: string;
}

export function WarningDialog({
  title,
  message,
  severity,
  onConfirm,
  onCancel,
  confirmText = 'I understand, proceed',
  cancelText = 'Cancel',
}: WarningDialogProps) {
  const bgColor = severity === 'danger' ? 'bg-red-500/10' : 'bg-amber-500/10';
  const borderColor = severity === 'danger' ? 'border-red-500/50' : 'border-amber-500/50';
  const iconColor = severity === 'danger' ? 'text-red-400' : 'text-amber-400';
  const btnColor = severity === 'danger'
    ? 'bg-red-600 hover:bg-red-500'
    : 'bg-amber-600 hover:bg-amber-500';

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70">
      <div className={`max-w-md w-full mx-4 p-6 rounded-lg border ${borderColor} ${bgColor}`}>
        <div className="flex items-start gap-4">
          <div className={`flex-shrink-0 ${iconColor}`}>
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold mb-2">{title}</h3>
            <p className="text-sm text-vscode-muted">{message}</p>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded bg-vscode-btn2-bg text-vscode-btn2-fg hover:opacity-80 transition-opacity"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded text-white ${btnColor} transition-colors`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
