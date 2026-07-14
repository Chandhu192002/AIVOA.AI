import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchHcps } from '../api/client';
import { addTip } from '../store/chatSlice';
import {
  addSuggestionToFollowUps,
  clearRecentlyUpdated,
  setField,
} from '../store/formSlice';

const INTERACTION_TYPES = ['Meeting', 'Call', 'Email', 'Conference', 'Virtual'];

const SENTIMENTS = [
  { value: 'Positive', emoji: '😄' },
  { value: 'Neutral', emoji: '😐' },
  { value: 'Negative', emoji: '😞' },
];

export default function LogInteractionForm() {
  const dispatch = useDispatch();
  const { fields, suggestedFollowUps, recentlyUpdated } = useSelector((s) => s.form);
  const [hcps, setHcps] = useState([]);

  useEffect(() => {
    fetchHcps().then(setHcps).catch(() => setHcps([]));
  }, []);

  /* Let the AI-driven highlight fade out after a moment. */
  useEffect(() => {
    if (recentlyUpdated.length === 0) return undefined;
    const timer = setTimeout(() => dispatch(clearRecentlyUpdated()), 2200);
    return () => clearTimeout(timer);
  }, [recentlyUpdated, dispatch]);

  const set = (field) => (e) => dispatch(setField({ field, value: e.target.value }));
  const flash = (field) => (recentlyUpdated.includes(field) ? ' ai-updated' : '');

  const voiceNoteTip = () =>
    dispatch(
      addTip(
        'Voice note summarization requires explicit HCP consent and is outside ' +
          'this demo. Describe the interaction in the chat instead and I will ' +
          'log it for you.'
      )
    );

  const materialsTip = () =>
    dispatch(
      addTip(
        'This form is AI-driven — tell me, e.g., "Add the OncoBoost brochure to ' +
          'materials shared" and I will update it.'
      )
    );

  const samplesTip = () =>
    dispatch(
      addTip(
        'This form is AI-driven — tell me, e.g., "I gave Dr. Smith two ' +
          'OncoBoost 10mg samples" and I will update it.'
      )
    );

  return (
    <section className="card form-card" aria-label="Log HCP Interaction form">
      <div className="form-scroll">
        <h1 className="page-title">Log HCP Interaction</h1>

        <h2 className="section-title">Interaction Details</h2>

        <div className="grid-2">
          <div className="field">
            <label htmlFor="hcpName">HCP Name</label>
            <input
              id="hcpName"
              list="hcp-directory"
              placeholder="Search or select HCP..."
              value={fields.hcpName}
              onChange={set('hcpName')}
              className={flash('hcpName')}
            />
            <datalist id="hcp-directory">
              {hcps.map((h) => (
                <option key={h.id} value={h.name}>
                  {h.specialty} — {h.institution}
                </option>
              ))}
            </datalist>
          </div>

          <div className="field">
            <label htmlFor="interactionType">Interaction Type</label>
            <select
              id="interactionType"
              value={fields.interactionType}
              onChange={set('interactionType')}
              className={flash('interactionType')}
            >
              {INTERACTION_TYPES.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid-2">
          <div className="field">
            <label htmlFor="date">Date</label>
            <input
              id="date"
              type="date"
              value={fields.date}
              onChange={set('date')}
              className={flash('date')}
            />
          </div>
          <div className="field">
            <label htmlFor="time">Time</label>
            <input
              id="time"
              type="time"
              value={fields.time}
              onChange={set('time')}
              className={flash('time')}
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="attendees">Attendees</label>
          <input
            id="attendees"
            placeholder="Enter names or search..."
            value={fields.attendees}
            onChange={set('attendees')}
            className={flash('attendees')}
          />
        </div>

        <div className="field">
          <label htmlFor="topics">Topics Discussed</label>
          <textarea
            id="topics"
            rows={4}
            placeholder="Enter key discussion points..."
            value={fields.topicsDiscussed}
            onChange={set('topicsDiscussed')}
            className={flash('topicsDiscussed')}
          />
        </div>

        <button type="button" className="link-btn" onClick={voiceNoteTip}>
          <span aria-hidden="true">🎙️</span> Summarize from Voice Note (Requires
          Consent)
        </button>

        <h2 className="section-title tight">Materials Shared / Samples Distributed</h2>

        <div className="subfield">
          <div className="subfield-head">
            <label>Materials Shared</label>
            <button type="button" className="mini-btn" onClick={materialsTip}>
              <span aria-hidden="true">🔍</span> Search/Add
            </button>
          </div>
          <p className={`chips${flash('materialsShared')}`}>
            {fields.materialsShared.length > 0 ? (
              `${fields.materialsShared.join(', ')}.`
            ) : (
              <span className="muted">No materials added.</span>
            )}
          </p>
        </div>

        <div className="subfield">
          <div className="subfield-head">
            <label>Samples Distributed</label>
            <button type="button" className="mini-btn" onClick={samplesTip}>
              <span aria-hidden="true">＋</span> Add Sample
            </button>
          </div>
          <p className={`chips${flash('samplesDistributed')}`}>
            {fields.samplesDistributed.length > 0 ? (
              `${fields.samplesDistributed.join(', ')}.`
            ) : (
              <span className="muted">No samples added.</span>
            )}
          </p>
        </div>

        <div className="field">
          <label>Observed/Inferred HCP Sentiment</label>
          <div className={`sentiment-row${flash('sentiment')}`} role="radiogroup">
            {SENTIMENTS.map(({ value, emoji }) => (
              <label key={value} className="sentiment-option">
                <input
                  type="radio"
                  name="sentiment"
                  value={value}
                  checked={fields.sentiment === value}
                  onChange={set('sentiment')}
                />
                <span aria-hidden="true">{emoji}</span> {value}
              </label>
            ))}
          </div>
        </div>

        <div className="field">
          <label htmlFor="outcomes">Outcomes</label>
          <textarea
            id="outcomes"
            rows={3}
            placeholder="Key outcomes or agreements..."
            value={fields.outcomes}
            onChange={set('outcomes')}
            className={flash('outcomes')}
          />
        </div>

        <div className="field">
          <label htmlFor="followUps">Follow-up Actions</label>
          <textarea
            id="followUps"
            rows={3}
            placeholder="Enter next steps or tasks..."
            value={fields.followUpActions}
            onChange={set('followUpActions')}
            className={flash('followUpActions')}
          />
        </div>

        {suggestedFollowUps.length > 0 && (
          <div className="suggestions">
            <span className="suggestions-label">AI Suggested Follow-ups:</span>
            {suggestedFollowUps.map((s) => (
              <button
                key={s}
                type="button"
                className="suggestion-link"
                onClick={() => dispatch(addSuggestionToFollowUps(s))}
                title="Add to Follow-up Actions"
              >
                + {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
