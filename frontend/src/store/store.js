import { configureStore } from '@reduxjs/toolkit';
import chatReducer from './chatSlice';
import formReducer from './formSlice';

export const store = configureStore({
  reducer: {
    form: formReducer,
    chat: chatReducer,
  },
});
