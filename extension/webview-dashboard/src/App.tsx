import { SessionTimeline } from './components/SessionTimeline';
import { MessageFeed } from './components/MessageFeed';
import { QualityGates } from './components/QualityGates';
import { AgentCards } from './components/AgentCards';

export default function App() {
  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-bold">Collab Intelligence Dashboard</h1>
      <div className="grid grid-cols-2 gap-4">
        <AgentCards />
        <QualityGates />
      </div>
      <SessionTimeline />
      <MessageFeed />
    </div>
  );
}
