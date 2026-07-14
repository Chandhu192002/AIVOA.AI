import { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage } from '../store/chatSlice';

/* Minimal, safe markdown-lite: escape everything, then allow **bold** + line breaks. */
function renderAssistant(content) {
  const escaped = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
  const html = escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
  return { __html: html };
}

export default function AiAssistantPanel() {
  const dispatch = useDispatch();
  const { messages, status } = useSelector((s) => s.chat);
  const [draft, setDraft] = useState('');
  const scrollRef = useRef(null);

  const loading = status === 'loading';

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const submit = () => {
    const text = draft.trim();
    if (!text || loading) return;
    setDraft('');
    dispatch(sendMessage(text));
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <aside className="card chat-card" aria-label="AI Assistant">
      <header className="chat-header">
        <div className="chat-title">
          <span className="bot-emoji" aria-hidden="true">
            🤖
          </span>
          <span>AI Assistant</span>
        </div>
        <p className="chat-subtitle">Log Interaction details here via chat</p>
      </header>

      <div className="chat-messages" ref={scrollRef}>
        <div className="bubble info">
          Log interaction details here (e.g., &quot;Met Dr. Smith, discussed
          Product X efficacy, positive sentiment, shared brochure&quot;) or ask
          for help.
        </div>

        {messages.map((m, i) => {
          if (m.role === 'user') {
            return (
              <div key={i} className="bubble user">
                {m.content}
              </div>
            );
          }
          if (m.role === 'tip') {
            return (
              <div key={i} className="bubble info">
                {m.content}
              </div>
            );
          }
          return (
            <div
              key={i}
              className="bubble assistant"
              dangerouslySetInnerHTML={renderAssistant(m.content)}
            />
          );
        })}

        {loading && (
          <div className="bubble assistant typing" aria-live="polite">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        )}
      </div>

      <div className="chat-input-row">
        <textarea
          rows={1}
          placeholder="Describe Interaction..."
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Describe interaction"
        />
        <button
          type="button"
          className="log-btn"
          onClick={submit}
          disabled={loading || !draft.trim()}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 2l1.9 5.6L19.5 9.5l-5.6 1.9L12 17l-1.9-5.6L4.5 9.5l5.6-1.9L12 2z" />
            <path d="M19 14l.9 2.6L22.5 17.5l-2.6.9L19 21l-.9-2.6-2.6-.9 2.6-.9L19 14z" />
          </svg>
          <span>Log</span>
        </button>
      </div>
    </aside>
  );
}
