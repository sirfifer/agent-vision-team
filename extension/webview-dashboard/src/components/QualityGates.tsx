export function QualityGates() {
  return (
    <div className="border border-gray-600 rounded p-4">
      <h2 className="text-lg font-semibold mb-2">Quality Gates</h2>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span>Build</span>
          <span className="text-gray-400">--</span>
        </div>
        <div className="flex justify-between">
          <span>Lint</span>
          <span className="text-gray-400">--</span>
        </div>
        <div className="flex justify-between">
          <span>Tests</span>
          <span className="text-gray-400">--</span>
        </div>
        <div className="flex justify-between">
          <span>Coverage</span>
          <span className="text-gray-400">--</span>
        </div>
      </div>
    </div>
  );
}
