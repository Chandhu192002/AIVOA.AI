import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { postChat } from '../api/client';
import { REVERSE_KEY_MAP } from './formSlice';

/**
 * One turn of the conversation. Sends the message, the recent chat history
 * and the *current form state* to the LangGraph agent; the fulfilled payload
 * carries the assistant reply plus any form_updates produced by its tools.
 */
export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (text, { getState }) => {
    const state = getState();

    const history = state.chat.messages
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .slice(-12)
      .map(({ role, content }) => ({ role, content }));

    const formState = {};
    Object.entries(state.form.fields).forEach(([camelKey, value]) => {
      const snakeKey = REVERSE_KEY_MAP[camelKey];
      if (!snakeKey) return;
      const isEmpty =
        value === '' || value === null || (Array.isArray(value) && value.length === 0);
      if (!isEmpty) formState[snakeKey] = value;
    });

    return postChat({
      message: text,
      history,
      formState,
      interactionId: state.form.lastInteractionId,
    });
  }
);

const initialState = {
  /* role: 'user' | 'assistant' | 'tip' (local UI hints, never sent to the API) */
  messages: [],
  status: 'idle', // idle | loading | failed
  lastToolCalls: [],
  modelUsed: '',
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addTip(state, action) {
      state.messages.push({ role: 'tip', content: action.payload });
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = 'loading';
        state.messages.push({ role: 'user', content: action.meta.arg });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = 'idle';
        state.messages.push({ role: 'assistant', content: action.payload.reply });
        state.lastToolCalls = action.payload.tool_calls || [];
        state.modelUsed = action.payload.model_used || '';
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = 'failed';
        state.messages.push({
          role: 'assistant',
          content:
            '⚠️ I could not reach the AI backend. Check that the FastAPI server is ' +
            'running on port 8000 and that GROQ_API_KEY is set.\n\n' +
            `Details: ${action.error?.message || 'unknown error'}`,
        });
      });
  },
});

export const { addTip } = chatSlice.actions;
export default chatSlice.reducer;
