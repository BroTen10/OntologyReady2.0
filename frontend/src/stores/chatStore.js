import { create } from 'zustand';
import * as ragApi from '../api/rag';

export const useChatStore = create((set, get) => ({
  conversations: [],
  currentConv: null,
  messages: [],
  streaming: '',
  loading: false,
  kbs: [],

  loadKBs: async () => {
    try {
      const res = await ragApi.listKnowledgeBases();
      if (res.code === 0) set({ kbs: res.data || [] });
    } catch { /* */ }
  },

  loadConversations: async () => {
    try {
      const res = await ragApi.listConversations();
      if (res.code === 0) set({ conversations: res.data || [] });
    } catch { /* */ }
  },

  createConversation: async (kbId, title = '新对话', modelParams = {}, systemPrompt = '') => {
    const res = await ragApi.createConversation(kbId, title, modelParams, systemPrompt);
    if (res.code === 0) {
      const conv = res.data;
      set((s) => ({ conversations: [conv, ...s.conversations], currentConv: conv, messages: [] }));
      return conv;
    }
    return null;
  },

  selectConversation: async (convId) => {
    try {
      const res = await ragApi.getConversation(convId);
      if (res.code === 0) {
        set({
          currentConv: res.data.conversation,
          messages: res.data.messages || [],
          streaming: '',
        });
      }
    } catch { /* */ }
  },

  deleteConversation: async (convId) => {
    await ragApi.deleteConversation(convId);
    set((s) => {
      const conversations = s.conversations.filter((c) => c.conv_id !== convId);
      const currentConv = s.currentConv?.conv_id === convId ? null : s.currentConv;
      return { conversations, currentConv, messages: currentConv ? s.messages : [] };
    });
  },

  sendMessage: async (question) => {
    const { currentConv } = get();
    if (!currentConv || !question.trim()) return;

    set((s) => ({
      messages: [...s.messages, { role: 'user', content: question }],
      loading: true,
      streaming: '',
    }));

    try {
      const token = localStorage.getItem('auth_access_token');
      const response = await fetch(`/api/rag/conversations/${currentConv.conv_id}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let citations = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.sources) {
                citations = parsed.sources;
              }
            } catch {
              fullContent += data;
              set({ streaming: fullContent });
            }
          }
        }
      }

      set((s) => ({
        messages: [...s.messages, { role: 'assistant', content: fullContent, citations }],
        loading: false,
        streaming: '',
      }));
    } catch {
      set({ loading: false, streaming: '' });
    }
  },

  clearStreaming: () => set({ streaming: '', loading: false }),
}));
