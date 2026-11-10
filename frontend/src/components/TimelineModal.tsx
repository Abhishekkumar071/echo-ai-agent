import React, { useEffect, useState } from 'react';
import { X, Calendar, Clock, Search, MessageSquare, ArrowRight } from 'lucide-react';
import { TimelineEntry } from '../types';
import { api } from '../services/api';

interface TimelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectQuery?: (query: string) => void;
}

export const TimelineModal: React.FC<TimelineModalProps> = ({
  isOpen,
  onClose,
  onSelectQuery,
}) => {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchFilter, setSearchFilter] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      loadTimeline();
    }
  }, [isOpen]);

  const loadTimeline = async () => {
    setLoading(true);
    try {
      const data = await api.getTimeline();
      setEntries(data);
    } catch (err) {
      console.error('Failed to load timeline:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const filteredEntries = entries.filter((e) => {
    const q = searchFilter.toLowerCase();
    return (
      (e.original_query || '').toLowerCase().includes(q) ||
      e.content.toLowerCase().includes(q) ||
      (e.summary || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl bg-[#0e1526] border border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-sky-400" />
              <span>Temporal Memory Timeline</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Chronological log of what you asked, when you asked it, and stored findings.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filter bar */}
        <div className="p-4 border-b border-slate-800 bg-[#090d18] flex items-center gap-2">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search past memories and questions..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full bg-transparent text-sm text-slate-200 placeholder-slate-400 focus:outline-none"
          />
        </div>

        {/* Timeline list */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              Loading chronological memories...
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              {searchFilter ? 'No memories match your search filter.' : 'No memories saved yet. Start chatting!'}
            </div>
          ) : (
            filteredEntries.map((entry) => (
              <div
                key={entry.id}
                className="relative pl-6 pb-4 border-l-2 border-slate-800 last:border-transparent group"
              >
                {/* Node Dot */}
                <div className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-[#0e1526] border-2 border-sky-400 group-hover:scale-125 transition-transform" />

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5 font-medium text-sky-400">
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(entry.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    {onSelectQuery && entry.original_query && (
                      <button
                        onClick={() => {
                          onSelectQuery(entry.original_query!);
                          onClose();
                        }}
                        className="text-[11px] text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
                      >
                        Ask again <ArrowRight className="w-3 h-3" />
                      </button>
                    )}
                  </div>

                  {entry.original_query && (
                    <div className="text-sm font-semibold text-white">
                      "{entry.original_query}"
                    </div>
                  )}

                  <div className="text-xs text-slate-300 leading-relaxed">
                    {entry.content}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
