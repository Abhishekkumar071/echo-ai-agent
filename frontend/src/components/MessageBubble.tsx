import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExternalLink, Database, Globe, RefreshCw, Clock, Bot, User as UserIcon } from 'lucide-react';
import { Message, SourceCitation } from '../types';

interface MessageBubbleProps {
  message: Message;
  onOpenContextPanel?: () => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onOpenContextPanel }) => {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`py-4 px-4 md:px-6 transition-colors ${isAssistant ? 'bg-[#101729]/70 border-y border-slate-800/40' : 'bg-transparent'}`}>
      <div className="max-w-4xl mx-auto flex gap-4">
        {/* Avatar */}
        <div className="shrink-0 pt-0.5">
          {isAssistant ? (
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-600 to-cyan-500 flex items-center justify-center shadow-md shadow-sky-500/20">
              <Bot className="w-4 h-4 text-white" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-slate-700/80 flex items-center justify-center text-slate-300">
              <UserIcon className="w-4 h-4" />
            </div>
          )}
        </div>

        {/* Content Body */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Header & Badges */}
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="font-semibold text-slate-200">
              {isAssistant ? 'ECHO Intelligence' : 'You'}
            </span>
            <span className="text-[11px] text-slate-400">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>

            {isAssistant && (
              <div className="flex items-center gap-1.5 ml-auto">
                {message.is_then_vs_now && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    <RefreshCw className="w-2.5 h-2.5" />
                    Then vs Now
                  </span>
                )}
                {message.memory_used && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-500/15 text-purple-300 border border-purple-500/30">
                    <Database className="w-2.5 h-2.5" />
                    Memory Recalled
                  </span>
                )}
                {message.search_used && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                    <Globe className="w-2.5 h-2.5" />
                    Tavily Live
                  </span>
                )}
                {message.latency_ms !== undefined && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                    <Clock className="w-2.5 h-2.5" />
                    {message.latency_ms}ms
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Markdown Content */}
          <div className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ node, ...props }) => (
                  <a
                    {...props}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sky-400 hover:text-sky-300 underline underline-offset-2 font-medium inline-flex items-center gap-0.5"
                  />
                ),
                code: ({ node, className, children, ...props }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code className="px-1.5 py-0.5 rounded bg-slate-800 text-sky-300 font-mono text-[12px]" {...props}>
                      {children}
                    </code>
                  ) : (
                    <pre className="p-3 my-2 rounded-xl bg-[#090d18] border border-slate-800 overflow-x-auto text-[12px] font-mono">
                      <code {...props}>{children}</code>
                    </pre>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 bg-sky-400 ml-1 animate-pulse align-middle" />
            )}
          </div>

          {/* Grounded Sources Footnote */}
          {isAssistant && message.sources && message.sources.length > 0 && (
            <div className="pt-3 border-t border-slate-800/60 mt-3">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
                <span>Verified Sources Used ({message.sources.length})</span>
                {onOpenContextPanel && (
                  <button
                    onClick={onOpenContextPanel}
                    className="text-sky-400 hover:text-sky-300 text-[10px] normal-case"
                  >
                    Inspect Context →
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {message.sources.map((src, idx) => {
                  const domain = src.metadata?.domain || new URL(src.url).hostname.replace('www.', '');
                  return (
                    <a
                      key={idx}
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700/80 text-xs text-slate-300 hover:text-white transition-all border border-slate-700/60 group"
                      title={src.title}
                    >
                      <span className="w-4 h-4 rounded-full bg-sky-500/20 text-sky-400 flex items-center justify-center text-[10px] font-bold">
                        {idx + 1}
                      </span>
                      <span className="truncate max-w-[150px]">{src.title || domain}</span>
                      <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-sky-400 shrink-0" />
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
