import React, { useState } from 'react';
import { X, Database, Globe, Calendar, ExternalLink, Sparkles } from 'lucide-react';
import { SourceCitation, MemoryReference } from '../types';

interface ContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceCitation[];
  memories: MemoryReference[];
  isThenVsNow?: boolean;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({
  isOpen,
  onClose,
  sources,
  memories,
  isThenVsNow,
}) => {
  const [activeTab, setActiveTab] = useState<'memories' | 'sources'>('memories');

  if (!isOpen) return null;

  return (
    <aside className="w-80 md:w-96 bg-[#0c1222] border-l border-slate-800 flex flex-col h-full shrink-0 z-30 transition-all duration-300">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-sky-400" />
          <h3 className="font-semibold text-sm text-slate-100">Context & Grounding</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 bg-[#090d18]">
        <button
          onClick={() => setActiveTab('memories')}
          className={`flex-1 py-2.5 px-3 text-xs font-medium flex items-center justify-center gap-1.5 border-b-2 transition-colors ${
            activeTab === 'memories'
              ? 'border-sky-500 text-sky-400 bg-sky-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>Memories ({memories.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('sources')}
          className={`flex-1 py-2.5 px-3 text-xs font-medium flex items-center justify-center gap-1.5 border-b-2 transition-colors ${
            activeTab === 'sources'
              ? 'border-sky-500 text-sky-400 bg-sky-500/10'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          <span>Sources ({sources.length})</span>
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {activeTab === 'memories' ? (
          memories.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              No historical memories were triggered for this answer.
            </div>
          ) : (
            memories.map((mem) => (
              <div
                key={mem.id}
                className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 text-xs hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="flex items-center gap-1 text-purple-400 font-medium">
                    <Calendar className="w-3 h-3" />
                    {new Date(mem.created_at).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                  {mem.similarity_score !== undefined && (
                    <span className="px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300 font-mono text-[10px]">
                      {(mem.similarity_score * 100).toFixed(0)}% match
                    </span>
                  )}
                </div>

                {mem.original_query && (
                  <div>
                    <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                      Verbatim Question
                    </div>
                    <div className="text-slate-200 font-medium mt-0.5 italic">
                      "{mem.original_query}"
                    </div>
                  </div>
                )}

                <div>
                  <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                    Context / Finding
                  </div>
                  <div className="text-slate-300 mt-0.5 leading-relaxed">
                    {mem.content}
                  </div>
                </div>
              </div>
            ))
          )
        ) : sources.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-xs">
            No live web search was needed for this query.
          </div>
        ) : (
          sources.map((src, i) => (
            <div
              key={i}
              className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 text-xs hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-sky-400 hover:text-sky-300 leading-snug flex items-center gap-1 group"
                >
                  <span>{src.title}</span>
                  <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-sky-400 shrink-0" />
                </a>
              </div>

              <div className="text-[11px] text-slate-400 leading-relaxed">
                {src.snippet}
              </div>

              <div className="pt-1 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-800/60">
                <span className="truncate max-w-[180px]">{src.url}</span>
                {src.score !== undefined && (
                  <span className="text-emerald-400 font-mono">Score: {src.score.toFixed(2)}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
