import AiAssistantPanel from './components/AiAssistantPanel';
import LogInteractionForm from './components/LogInteractionForm';

export default function App() {
  return (
    <main className="layout">
      <LogInteractionForm />
      <AiAssistantPanel />
    </main>
  );
}
