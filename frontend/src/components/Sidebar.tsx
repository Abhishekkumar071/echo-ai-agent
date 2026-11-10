import React from 'react';
import { Plus, MessageSquare, History, Sparkles, ChevronRight, Compass } from 'lucide-react';
import { ConversationSummary } from '../types';

interface SidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onOpenTimeline: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  conversations,
  activeId,
  onSelectConversation,
  onNewChat,
  onOpenTimeline,
  isOpen,
  onToggle,
}) => {
  return (
    <aside
      className={`fixed md:static inset-y-0 left-0 z-40 w-72 bg-[#0c1222] border-r border-slate-800 flex flex-col transition-transform duration-300 ease-in-out ${
        isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      }`}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <Compass className="w-5 h-5 text-white animate-spin-slow" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-lg tracking-wider text-white">ECHO</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 truncate max-w-[170px]">
              Context-Aware Web Intelligence
            </p>
          </div>
        </div>
      </div>

      {/* Primary Actions */}
      <div className="p-3 space-y-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm transition-all shadow-md shadow-sky-600/25 active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          <span>New Conversation</span>
        </button>

        <button
          onClick={onOpenTimeline}
          className="w-full flex items-center gap-2.5 py-2 px-3 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 text-sm transition-colors"
        >
          <History className="w-4 h-4 text-sky-400" />
          <span>Memory Timeline</span>
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        <div className="px-2 pb-1 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          Recent Conversations
        </div>
        {conversations.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No previous conversations. Start a new topic!
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === activeId;
            return (
              <button
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all group ${
                  isActive
                    ? 'bg-sky-500/15 text-sky-300 font-medium border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <MessageSquare className={`w-4 h-4 shrink-0 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                <span className="truncate flex-1">{conv.title}</span>
                {isActive && <ChevronRight className="w-3.5 h-3.5 text-sky-400" />}
              </button>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-[#090d18] text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Groq LPU + Tavily Online</span>
        </div>
        <span className="text-slate-400">pgvector ready</span>
      </div>
    </aside>
  );
};
