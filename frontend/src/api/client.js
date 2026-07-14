const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export async function postChat({ message, history, formState, interactionId }) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history,
      form_state: formState,
      interaction_id: interactionId,
    }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`Chat request failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function fetchHcps() {
  const res = await fetch(`${API_BASE}/api/hcps`);
  if (!res.ok) throw new Error('Failed to load HCPs');
  return res.json();
}
