import { useState } from 'react';
import type { BootstrapReviewItem } from '../../types';

type TierTab = 'vision' | 'architecture' | 'quality';

const ENTITY_TYPE_OPTIONS: Record<TierTab, Array<{ value: string; label: string }>> = {
  vision: [
    { value: 'vision_standard', label: 'Vision Standard' },
  ],
  architecture: [
    { value: 'architectural_standard', label: 'Arch Standard' },
    { value: 'pattern', label: 'Pattern' },
    { value: 'component', label: 'Component' },
  ],
  quality: [
    { value: 'coding_convention', label: 'Convention' },
    { value: 'observation', label: 'Observation' },
  ],
};

export function AddItemForm({
  tier,
  onAdd,
  onCancel,
}: {
  tier: TierTab;
  onAdd: (item: BootstrapReviewItem) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState('');
  const [statement, setStatement] = useState('');
  const typeOptions = ENTITY_TYPE_OPTIONS[tier];
  const [entityType, setEntityType] = useState(typeOptions[0].value);

  const handleSubmit = () => {
    if (!name.trim() || !statement.trim()) return;

    const id = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

    onAdd({
      id,
      name: name.trim(),
      description: statement.trim().slice(0, 120),
      tier,
      entityType,
      observations: [`protection_tier: ${tier}`, `statement: ${statement.trim()}`],
      status: 'approved',
      isUserCreated: true,
    });
  };

  return (
    <div className="border border-blue-500/30 rounded bg-vscode-widget-bg p-3 space-y-3">
      <div className="text-2xs font-semibold text-blue-400 uppercase tracking-wider">
        Add {tier} item
      </div>

      <div className="space-y-2">
        <div>
          <label className="text-2xs text-vscode-muted block mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder={tier === 'vision' ? 'e.g. Protocol-Based Dependency Injection' : 'e.g. Repository Pattern'}
            className="w-full text-xs p-2 rounded bg-vscode-bg border border-vscode-border text-vscode-fg placeholder:text-vscode-muted/50"
            autoFocus
          />
        </div>

        <div>
          <label className="text-2xs text-vscode-muted block mb-1">Statement</label>
          <textarea
            value={statement}
            onChange={e => setStatement(e.target.value)}
            placeholder={tier === 'vision'
              ? 'e.g. All services must use protocol-based dependency injection'
              : 'Describe the standard, pattern, or component'}
            className="w-full h-20 text-xs p-2 rounded bg-vscode-bg border border-vscode-border text-vscode-fg resize-y placeholder:text-vscode-muted/50"
          />
        </div>

        {typeOptions.length > 1 && (
          <div>
            <label className="text-2xs text-vscode-muted block mb-1">Type</label>
            <select
              value={entityType}
              onChange={e => setEntityType(e.target.value)}
              className="text-xs p-1.5 rounded bg-vscode-bg border border-vscode-border text-vscode-fg"
            >
              {typeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={!name.trim() || !statement.trim()}
          className="text-2xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Add
        </button>
        <button
          onClick={onCancel}
          className="text-2xs px-3 py-1 rounded bg-vscode-widget-bg text-vscode-muted hover:text-vscode-fg border border-vscode-border transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
