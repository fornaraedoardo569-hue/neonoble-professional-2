import React, { useEffect, useRef, useState } from 'react';
import api, { tokenStore } from '../../api';
import { Sparkles, X, Send, RotateCcw, Loader2 } from 'lucide-react';

const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LABELS = {
  dashboard: { title: 'NoNo — AI Assistant', hint: 'Ask about NENO, KYC, buying or selling…' },
  devportal: { title: 'NoNo — Dev Assistant', hint: 'Ask about API keys, HMAC auth, endpoints…' },
  admin: { title: 'NoNo — Compliance Copilot', hint: 'Ask about MiCAR, AML, Travel Rule, KYC…' },
};

export const AssistantWidget = ({ context }) => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const sessionKey = `neonoble_assistant_${context}`;
  const scrollRef = useRef(null);
  const label = LABELS[context] || LABELS.dashboard;

  useEffect(() => {
    if (!open) return;
    const sid = localStorage.getItem(sessionKey);
    if (sid && messages.length === 0) {
      api.get(`/assistant/sessions/${sid}/messages`)
        .then(({ data }) => setMessages(data.map((m) => ({ role: m.role, content: m.content }))))
        .catch(() => localStorage.removeItem(sessionKey));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streaming]);

  const ensureSession = async () => {
    let sid = localStorage.getItem(sessionKey);
    if (sid) return sid;
    const { data } = await api.post('/assistant/sessions', { context });
    localStorage.setItem(sessionKey, data.id);
    return data.id;
  };

  const send = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    setStreaming(true);
    setMessages((m) => [...m, { role: 'user', content: text }, { role: 'assistant', content: '' }]);
    try {
      const sid = await ensureSession();
      const res = await fetch(`${API_BASE}/assistant/sessions/${sid}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokenStore.getAccess()}`,
        },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let payload;
          try { payload = JSON.parse(line.slice(6)); } catch { continue; }
          if (payload.delta) {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = {
                role: 'assistant',
                content: copy[copy.length - 1].content + payload.delta,
              };
              return copy;
            });
          } else if (payload.error) {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { role: 'assistant', content: payload.error, error: true };
              return copy;
            });
          }
        }
      }
    } catch (e) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = {
          role: 'assistant',
          content: 'Connection error — please try again.',
          error: true,
        };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  };

  const newChat = () => {
    localStorage.removeItem(sessionKey);
    setMessages([]);
  };

  return (
    <>
      {!open && (
        <button
          data-testid="assistant-fab"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-purple-600 hover:bg-purple-500 text-white px-4 py-3 shadow-lg shadow-purple-900/50 transition-colors"
        >
          <Sparkles className="h-5 w-5" />
          <span className="text-sm font-semibold hidden sm:inline">AI Assistant</span>
        </button>
      )}
      {open && (
        <div
          data-testid="assistant-panel"
          className="fixed bottom-6 right-6 z-50 flex flex-col w-[95vw] max-w-[400px] h-[70vh] max-h-[600px] rounded-2xl border border-purple-500/30 bg-slate-900/95 backdrop-blur-xl shadow-2xl shadow-purple-900/40 overflow-hidden"
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-purple-600/20">
            <div className="flex items-center gap-2 text-white">
              <Sparkles className="h-4 w-4 text-purple-300" />
              <span className="text-sm font-semibold">{label.title}</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                data-testid="assistant-new-chat-btn"
                onClick={newChat}
                title="New conversation"
                className="p-1.5 rounded-lg text-gray-300 hover:text-white hover:bg-white/10"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
              <button
                data-testid="assistant-close-btn"
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-gray-300 hover:text-white hover:bg-white/10"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div ref={scrollRef} data-testid="assistant-messages" className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-gray-400 mt-6 text-center px-4">
                <Sparkles className="h-8 w-8 mx-auto mb-3 text-purple-400/60" />
                {label.hint}
                <p className="mt-2 text-xs text-gray-500">Powered by Claude (claude-sonnet-4-6)</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-purple-600 text-white rounded-br-sm'
                      : m.error
                      ? 'bg-red-500/15 border border-red-500/30 text-red-200 rounded-bl-sm'
                      : 'bg-white/8 border border-white/10 text-gray-100 rounded-bl-sm'
                  }`}
                >
                  {m.content || (streaming && i === messages.length - 1 ? (
                    <Loader2 className="h-4 w-4 animate-spin text-purple-300" />
                  ) : '')}
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 border-t border-white/10">
            <div className="flex items-end gap-2">
              <textarea
                data-testid="assistant-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                rows={1}
                placeholder={label.hint}
                className="flex-1 resize-none rounded-xl bg-slate-800 border border-white/10 text-white text-sm px-3 py-2.5 placeholder-gray-500 focus:outline-none focus:border-purple-500/60 max-h-28"
              />
              <button
                data-testid="assistant-send-btn"
                onClick={send}
                disabled={streaming || !input.trim()}
                className="p-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
              >
                {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
