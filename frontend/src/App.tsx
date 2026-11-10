import React, { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { ContextPanel } from './components/ContextPanel';
import { TimelineModal } from './components/TimelineModal';
import { ConversationSummary, Message, SourceCitation, MemoryReference } from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [conversationTitle, setConversationTitle] = useState<string>('New Conversation');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  // Layout UI states
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isContextPanelOpen, setIsContextPanelOpen] = useState<boolean>(true);
  const [isTimelineOpen, setIsTimelineOpen] = useState<boolean>(false);

  // Active grounding state for context panel
  const [activeSources, setActiveSources] = useState<SourceCitation[]>([]);
  const [activeMemories, setActiveMemories] = useState<MemoryReference[]>([]);
  const [isThenVsNow, setIsThenVsNow] = useState<boolean>(false);

  useEffect(() => {
    initialize();
  }, []);

  const initialize = async () => {
    try {
      await api.ensureSession();
      await loadConversations();
    } catch (err) {
      console.error('Initialization error:', err);
    }
  };

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const handleSelectConversation = async (id: string) => {
    try {
      setActiveConversationId(id);
      setIsSidebarOpen(false);
      const data = await api.getConversation(id);
      setConversationTitle(data.title);
      setMessages(data.messages);

      // Find the last assistant message's sources & memories for the panel
      const lastAsst = [...data.messages].reverse().find((m) => m.role === 'assistant');
      if (lastAsst) {
        setActiveSources(lastAsst.sources || []);
        setActiveMemories(lastAsst.memory_references || []);
        setIsThenVsNow(Boolean(lastAsst.is_then_vs_now));
      } else {
        setActiveSources([]);
        setActiveMemories([]);
        setIsThenVsNow(false);
      }
    } catch (err) {
      console.error('Failed to load conversation details:', err);
    }
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setConversationTitle('New Conversation');
    setMessages([]);
    setActiveSources([]);
    setActiveMemories([]);
    setIsThenVsNow(false);
    setIsSidebarOpen(false);
  };

  const handleSendMessage = async (text: string) => {
    if (isStreaming) return;

    const userMessageId = `user-${Date.now()}`;
    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    const asstMessageId = `asst-${Date.now()}`;
    const initialAsstMessage: Message = {
      id: asstMessageId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
      sources: [],
      memory_references: [],
    };

    setMessages((prev) => [...prev, userMessage, initialAsstMessage]);
    setIsStreaming(true);

    try {
      await api.streamChat(
        text,
        activeConversationId,
        (metadata) => {
          setActiveConversationId(metadata.conversation_id);
          setActiveSources(metadata.sources || []);
          setActiveMemories(metadata.memory_references || []);
          setIsThenVsNow(metadata.is_then_vs_now);

          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstMessageId
                ? {
                    ...m,
                    sources: metadata.sources,
                    memory_references: metadata.memory_references,
                    search_used: metadata.search_used,
                    is_then_vs_now: metadata.is_then_vs_now,
                  }
                : m
            )
          );
        },
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstMessageId
                ? { ...m, content: m.content + chunk }
                : m
            )
          );
        },
        (doneData) => {
          setIsStreaming(false);
          setActiveConversationId(doneData.conversation_id);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstMessageId
                ? { ...m, id: doneData.message_id, latency_ms: doneData.latency_ms, isStreaming: false }
                : m
            )
          );
          loadConversations();
        },
        (err) => {
          console.warn('Streaming error handled:', err);
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstMessageId
                ? {
                    ...m,
                    content: m.content || `Notice: ${err.message}`,
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      );
    } catch (err: any) {
      console.error('Chat execution failed:', err);
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === asstMessageId
            ? {
                ...m,
                content: `An error occurred: ${err?.message || 'Server error'}`,
                isStreaming: false,
              }
            : m
        )
      );
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0f19] text-slate-100">
      {/* Left Sidebar */}
      <Sidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onOpenTimeline={() => setIsTimelineOpen(true)}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((prev) => !prev)}
      />

      {/* Main Chat Area */}
      <ChatArea
        messages={messages}
        conversationTitle={conversationTitle}
        isStreaming={isStreaming}
        onSendMessage={handleSendMessage}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        onToggleContextPanel={() => setIsContextPanelOpen((prev) => !prev)}
        isContextPanelOpen={isContextPanelOpen}
        activeSources={activeSources}
        activeMemories={activeMemories}
      />

      {/* Right Context Panel */}
      <ContextPanel
        isOpen={isContextPanelOpen}
        onClose={() => setIsContextPanelOpen(false)}
        sources={activeSources}
        memories={activeMemories}
        isThenVsNow={isThenVsNow}
      />

      {/* Memory Timeline Modal */}
      <TimelineModal
        isOpen={isTimelineOpen}
        onClose={() => setIsTimelineOpen(false)}
        onSelectQuery={(q) => handleSendMessage(q)}
      />
    </div>
  );
};

export default App;
