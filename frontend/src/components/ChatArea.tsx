import React, { useEffect, useRef, useState } from 'react';
import { Send, Menu, Sparkles, Globe, Database, RefreshCw, PanelRightClose, PanelRightOpen, ArrowRight } from 'lucide-react';
import { Message, SourceCitation, MemoryReference } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatAreaProps {
  messages: Message[];
  conversationTitle: string;
  isStreaming: boolean;
  onSendMessage: (text: string) => void;
  onToggleSidebar: () => void;
  onToggleContextPanel: () => void;
  isContextPanelOpen: boolean;
  activeSources: SourceCitation[];
  activeMemories: MemoryReference[];
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  conversationTitle,
  isStreaming,
  onSendMessage,
  onToggleSidebar,
  onToggleContextPanel,
  isContextPanelOpen,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const samplePrompts = [
    {
      title: "Live Web Research",
      prompt: "What are the best backend frameworks for scalable applications?",
      desc: "Triggers Tavily search with grounded citations.",
    },
    {
      title: "Temporal Memory Recall",
      prompt: "What frameworks did we discuss yesterday?",
      desc: "Queries persistent memory without fabricating.",
    },
    {
      title: "Then vs Now Comparison",
      prompt: "Has anything changed since then?",
      desc: "Diffs past research with fresh web intelligence.",
    },
  ];

  return (
    <main className="flex-1 flex flex-col h-full bg-[#0b0f19] relative overflow-hidden">
      {/* Top Navigation */}
      <header className="h-14 border-b border-slate-800/80 px-4 flex items-center justify-between shrink-0 bg-[#090d18]/80 backdrop-blur-md z-20">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-slate-100 truncate max-w-[200px] md:max-w-md">
              {conversationTitle || 'New Conversation'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onToggleContextPanel}
            className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors border ${
              isContextPanelOpen
                ? 'bg-sky-500/15 text-sky-400 border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 border-slate-800 hover:bg-slate-800/60'
            }`}
            title="Toggle Context & Sources Panel"
          >
            {isContextPanelOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            <span className="hidden sm:inline">Context Panel</span>
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-8 animate-fade-in">
            <div className="space-y-3">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-sky-600 to-cyan-400 shadow-xl shadow-sky-500/25">
                <Sparkles className="w-7 h-7 text-white" />
              </div>
              <h1 className="text-3xl font-extrabold text-white tracking-tight">
                Welcome to ECHO
              </h1>
              <p className="text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
                "It doesn't just remember what you asked. It remembers when, why, and what happened next."
              </p>
            </div>

            {/* Prompt Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-left">
              {samplePrompts.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendMessage(p.prompt)}
                  className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-800/60 border border-slate-800 hover:border-sky-500/40 transition-all group flex flex-col justify-between"
                >
                  <div className="space-y-1">
                    <div className="text-[11px] font-bold text-sky-400 uppercase tracking-wider">
                      {p.title}
                    </div>
                    <div className="text-xs font-medium text-slate-200 group-hover:text-white transition-colors">
                      "{p.prompt}"
                    </div>
                  </div>
                  <div className="text-[10px] text-slate-400 mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between">
                    <span>{p.desc}</span>
                    <ArrowRight className="w-3 h-3 text-sky-400 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/40">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onOpenContextPanel={onToggleContextPanel}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800/80 bg-[#090d18]/90 backdrop-blur-md">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-2">
          <div className="relative flex items-end rounded-2xl bg-slate-900 border border-slate-800 focus-within:border-sky-500/60 focus-within:ring-1 focus-within:ring-sky-500/40 transition-all p-2 shadow-lg">
            <textarea
              rows={1}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything... (supports live web search and temporal memory)"
              className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-400 focus:outline-none resize-none px-3 py-1.5 max-h-36 overflow-y-auto"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isStreaming}
              className={`p-2.5 rounded-xl transition-all ${
                inputText.trim() && !isStreaming
                  ? 'bg-sky-600 hover:bg-sky-500 text-white shadow-md shadow-sky-600/30'
                  : 'bg-slate-800 text-slate-400 cursor-not-allowed'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 px-2">
            <span>Press Enter to send, Shift + Enter for new line</span>
            <span>Single tool: Tavily Search • Memory: PostgreSQL + pgvector</span>
          </div>
        </form>
      </div>
    </main>
  );
};
