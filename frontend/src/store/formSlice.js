import { createSlice } from '@reduxjs/toolkit';
import { sendMessage } from './chatSlice';

/* The AI backend speaks snake_case; the form state is camelCase. */
export const KEY_MAP = {
  hcp_name: 'hcpName',
  interaction_type: 'interactionType',
  date: 'date',
  time: 'time',
  attendees: 'attendees',
  topics_discussed: 'topicsDiscussed',
  materials_shared: 'materialsShared',
  samples_distributed: 'samplesDistributed',
  sentiment: 'sentiment',
  outcomes: 'outcomes',
  follow_up_actions: 'followUpActions',
};

export const REVERSE_KEY_MAP = Object.fromEntries(
  Object.entries(KEY_MAP).map(([snake, camel]) => [camel, snake])
);

const pad = (n) => String(n).padStart(2, '0');
const now = new Date();

const initialState = {
  fields: {
    hcpName: '',
    interactionType: 'Meeting',
    date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    time: `${pad(now.getHours())}:${pad(now.getMinutes())}`,
    attendees: '',
    topicsDiscussed: '',
    materialsShared: [],
    samplesDistributed: [],
    sentiment: 'Neutral',
    outcomes: '',
    followUpActions: '',
  },
  suggestedFollowUps: [],
  lastInteractionId: null,
  /* Fields the AI just updated – used for the brief highlight animation. */
  recentlyUpdated: [],
};

const formSlice = createSlice({
  name: 'form',
  initialState,
  reducers: {
    setField(state, action) {
      const { field, value } = action.payload;
      state.fields[field] = value;
    },
    addSuggestionToFollowUps(state, action) {
      const text = action.payload;
      const existing = state.fields.followUpActions.trim();
      state.fields.followUpActions = existing ? `${existing}\n${text}` : text;
      state.suggestedFollowUps = state.suggestedFollowUps.filter((s) => s !== text);
    },
    clearRecentlyUpdated(state) {
      state.recentlyUpdated = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(sendMessage.fulfilled, (state, action) => {
      const { form_updates: updates, suggested_followups: suggestions, interaction_id: id } =
        action.payload;

      const touched = [];
      Object.entries(updates || {}).forEach(([snakeKey, value]) => {
        const camelKey = KEY_MAP[snakeKey];
        if (camelKey && value !== null && value !== undefined) {
          state.fields[camelKey] = value;
          touched.push(camelKey);
        }
      });
      state.recentlyUpdated = touched;

      if (Array.isArray(suggestions) && suggestions.length > 0) {
        state.suggestedFollowUps = suggestions;
      }
      if (id) {
        state.lastInteractionId = id;
      }
    });
  },
});

export const { setField, addSuggestionToFollowUps, clearRecentlyUpdated } =
  formSlice.actions;
export default formSlice.reducer;
