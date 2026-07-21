'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Header from '@/components/Header';
import { api } from '@/lib/api';
import {
  Library,
  MessageSquare,
  Sparkles,
  History,
  Send,
  Plus,
  Trash2,
  CheckCircle,
  Loader2
} from 'lucide-react';
import NyayaLogo from '@/components/NyayaLogo';

interface Citation {
  act_name: string;
  section: string;
  quote: string;
}

interface Message {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  created_at?: string;
}

interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
}

export default function RAGChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const querySessionId = searchParams.get('session_id');

  // Chat State
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string>('New Research Session');
  
  // UI Inputs
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [hoveredSourceIdx, setHoveredSourceIdx] = useState<number | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<string | null>(null);

  // Auto-scroll ref
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Suggested questions
  const suggestions = [
    'Is a 60-day post-termination non-compete clause valid in an employment contract?',
    'What are the rules regarding MSME payments under Section 15 of MSMED Act?',
    'What constitutes disclosure of personal data without consent under DPDP Act?'
  ];

  // Fetch session history list
  const fetchSessionsList = async () => {
    try {
      const res = await api.get('/api/v1/chat/sessions');
      setSessions(res.data);
    } catch (err) {
      console.error('Error fetching sessions:', err);
    }
  };

  // Load active session message stream
  const loadActiveSession = async (sessionId: string) => {
    setLoadingHistory(true);
    try {
      const res = await api.get(`/api/v1/chat/sessions/${sessionId}`);
      setMessages(res.data.messages || []);
      setSessionTitle(res.data.title || 'Research Session');
      setActiveSessionId(sessionId);
    } catch (err) {
      console.error('Error loading session:', err);
      // Clear invalid session query
      router.push('/chat');
      setActiveSessionId(null);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    const initPage = async () => {
      await fetchSessionsList();
      if (querySessionId) {
        await loadActiveSession(querySessionId);
      } else {
        setMessages([]);
        setSessionTitle('New Research Session');
        setActiveSessionId(null);
        setLoadingHistory(false);
      }
    };
    initPage();
  }, [querySessionId]);

  useEffect(() => {
    // Scroll to bottom on new messages
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || query;
    if (!textToSend.trim() || loading) return;

    setErrorMsg(null);
    
    // Optimistically add User Message
    const userMsgId = Math.random().toString();
    const newUserMsg: Message = {
      message_id: userMsgId,
      role: 'user',
      content: textToSend
    };
    setMessages(prev => [...prev, newUserMsg]);
    setQuery('');
    setLoading(true);

    try {
      const res = await api.post('/api/v1/chat', {
        message: textToSend,
        session_id: activeSessionId
      });

      const { session_id, answer } = res.data;

      // Add Assistant Message
      const newAssistantMsg: Message = {
        message_id: Math.random().toString(),
        role: 'assistant',
        content: answer.answer,
        citations: answer.citations || []
      };

      setMessages(prev => [...prev, newAssistantMsg]);

      // If a new session was created
      if (!activeSessionId) {
        setActiveSessionId(session_id);
        // Refresh sessions list
        await fetchSessionsList();
        // Update URL query parameters without full reload
        window.history.pushState(null, '', `/chat?session_id=${session_id}`);
      }
    } catch (err: any) {
      console.error('Error sending query:', err);
      const detail = err.response?.data?.detail;
      const errorMsgText = typeof detail === 'string' ? detail : 'An error occurred during statutory lookup.';
      
      const errorMsg: Message = {
        message_id: Math.random().toString(),
        role: 'assistant',
        content: `Error: ${errorMsgText}`
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setQuery('');
    setActiveSessionId(null);
    setSessionTitle('New Research Session');
    router.push('/chat');
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this research session?')) return;

    try {
      await api.delete(`/api/v1/chat/sessions/${sessionId}`);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      if (activeSessionId === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      alert('Failed to delete chat session.');
    }
  };

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Helper to extract active citations (from the last assistant message in the stream)
  const getActiveCitations = (): Citation[] => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant' && messages[i].citations) {
        return messages[i].citations || [];
      }
    }
    return [];
  };

  const activeCitations = getActiveCitations();

  // Helper to highlight terms in markdown
  const renderHighlightedContent = (content: string, citations: Citation[] = []) => {
    if (!citations || citations.length === 0) return <p className="text-sm leading-relaxed text-secondary whitespace-pre-line">{content}</p>;
    
    let renderedText = content;
    // Map citations to highlighted spans
    citations.forEach((c, idx) => {
      // Find section matches, e.g. "Section 27" or "Section 15" or section number
      const regexStr = `(Section\\s+${c.section}|Section\\s+${c.section}\\b|Section\\s+${c.section} of the ${c.act_name}|Section\\s+${c.section} of ${c.act_name})`;
      try {
        const regex = new RegExp(regexStr, 'gi');
        renderedText = renderedText.replace(regex, (match) => {
          return `<span class="mem-highlight ${hoveredSourceIdx === idx ? 'active' : ''}" data-index="${idx}">${match}</span>`;
        });
      } catch (e) {}
    });

    return (
      <div 
        className="text-sm leading-relaxed text-secondary whitespace-pre-line"
        dangerouslySetInnerHTML={{ __html: renderedText }}
        onMouseOver={(e) => {
          const target = e.target as HTMLElement;
          if (target.classList.contains('mem-highlight')) {
            const index = target.getAttribute('data-index');
            if (index) setHoveredSourceIdx(parseInt(index, 10));
          }
        }}
        onMouseOut={(e) => {
          const target = e.target as HTMLElement;
          if (target.classList.contains('mem-highlight')) {
            setHoveredSourceIdx(null);
          }
        }}
      />
    );
  };

  return (
    <div className="flex flex-col h-screen bg-page transition-all duration-300">
      {/* Header */}
      <Header workspaceLabel="Mode 2: Research Workstation" />

      {/* ==================== MAIN COLUMNS ==================== */}
      <main className="flex-1 flex flex-col lg:flex-row gap-4 p-4 overflow-hidden">
        
        {/* ==================== LEFT COLUMN: EVIDENCE BINDER ==================== */}
        <aside 
          className="bg-surface border-kite rounded-lg flex flex-col overflow-hidden shrink-0 min-w-[240px] max-w-[500px]"
          style={{ resize: 'horizontal', width: '280px' }}
        >
          <div className="p-4 border-kite-b">
            <h2 className="font-display font-semibold text-sm text-primary flex items-center gap-2">
              <Library className="w-4 h-4 text-rose-gold" />
              Cited Statutory Authority
            </h2>
            <p className="text-[10px] text-muted mt-1">
              {activeCitations.length} chunk{activeCitations.length !== 1 ? 's' : ''} retrieved · Sorted by relevance
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {activeCitations.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-muted p-4">
                <Library className="w-8 h-8 mb-2 opacity-40" />
                <p className="text-xs">No citations retrieved yet.</p>
                <p className="text-[10px] opacity-75 mt-1">Ask a statutory question to load supporting authority.</p>
              </div>
            ) : (
              activeCitations.map((c, idx) => (
                <div
                  key={idx}
                  onMouseOver={() => setHoveredSourceIdx(idx)}
                  onMouseOut={() => setHoveredSourceIdx(null)}
                  className={`source-card transition-all ${hoveredSourceIdx === idx ? 'active' : ''}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="text-[9px] font-mono text-muted uppercase tracking-wider line-clamp-1">
                      {c.act_name}
                    </div>
                    <div className="text-[9px] font-mono font-bold text-rose-gold bg-rose-gold/10 px-1.5 py-0.5 rounded">
                      Grounded Match
                    </div>
                  </div>
                  <h3 className="text-xs font-semibold text-primary mb-2">
                    Section {c.section}
                  </h3>
                  <div className="border-l-2 border-[var(--black-kite-15)] pl-3">
                    <p className="text-[11px] text-secondary leading-relaxed italic">
                      &quot;{c.quote}&quot;
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* ==================== CENTER COLUMN: MEMORANDUM VIEWER ==================== */}
        <section className="flex-1 min-w-0 bg-surface border-kite rounded-lg flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-5 border-kite-b flex justify-between items-center flex-shrink-0">
            <div>
              <h2 className="font-display font-bold text-base text-primary line-clamp-1">
                {sessionTitle}
              </h2>
              <p className="text-[10px] text-muted mt-0.5">
                Research Opinion Workspace · Indian Statutory RAG Engine
              </p>
            </div>
            {messages.length > 0 && (
              <div className="badge-verified px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5" />
                Grounded Citation
              </div>
            )}
          </div>

          {/* Scrollable Content / Chat feed */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center max-w-md mx-auto text-center">
                <NyayaLogo height={48} className="mb-4" />
                <h3 className="font-display font-bold text-lg text-primary mb-2">
                  Nyaya RAG Research Workspace
                </h3>
                <p className="text-xs text-secondary mb-6 leading-relaxed">
                  Consult our Indian Central Statutes database. Enter a legal query or choose a suggested follow-up topic on the right.
                </p>
                <div className="grid grid-cols-1 gap-2 w-full text-left">
                  {suggestions.map((s, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(s)}
                      className="suggestion-chip hover:border-toxic-orange transition-all text-xs"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.message_id}
                  className={`flex flex-col p-4 rounded-lg border border-[var(--black-kite-15)] ${
                    m.role === 'user' ? 'bg-amazon-mist/30 ml-8' : 'bg-surface mr-8'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`text-[10px] font-mono uppercase tracking-wider font-bold ${
                        m.role === 'user' ? 'text-rose-gold' : 'text-toxic-orange'
                      }`}
                    >
                      {m.role === 'user' ? 'Advocate / Query' : 'Nyaya Legal AI'}
                    </span>
                  </div>
                  {m.role === 'user' ? (
                    <p className="text-sm text-primary leading-relaxed whitespace-pre-line">{m.content}</p>
                  ) : (
                    renderHighlightedContent(m.content, m.citations)
                  )}
                </div>
              ))
            )}

            {/* Live LLM generation spinner */}
            {loading && (
              <div className="flex flex-col p-4 rounded-lg border border-[var(--black-kite-15)] bg-surface mr-8">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-toxic-orange animate-pulse">
                    Analyzing Statutes...
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-[var(--toxic-orange)]" />
                  <span>Consulting Tier 1 LLM (Groq) and searching Qdrant database...</span>
                </div>
              </div>
            )}
            
            <div ref={chatEndRef} />
          </div>

          {/* Footer stats / summary */}
          {activeCitations.length > 0 && (
            <div className="p-4 border-t border-[var(--black-kite-15)] flex items-center justify-between flex-shrink-0 bg-[var(--amazon-mist)]/30">
              <div className="flex items-center gap-4">
                <div className="relative w-10 h-10 flex items-center justify-center">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--black-kite-15)" strokeWidth="3" />
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--rose-gold)" strokeWidth="3" strokeDasharray="100, 100" strokeLinecap="round" />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-primary font-mono">
                    100%
                  </div>
                </div>
                <div>
                  <div className="text-xs font-semibold text-primary">Cite-or-Refuse Status</div>
                  <div className="text-[10px] text-muted">Statutory analysis grounded in active corpus</div>
                </div>
              </div>
              <button 
                onClick={() => alert('Memorandum export coming soon.')}
                className="text-xs font-medium text-[var(--toxic-orange)] hover:underline flex items-center gap-1"
              >
                Export Opinion
              </button>
            </div>
          )}
        </section>

        {/* ==================== RIGHT COLUMN: QUERY CONTROL ==================== */}
        <aside className="w-[340px] shrink-0 flex flex-col gap-4 overflow-hidden">
          
          {/* Active Search Scope Filters */}
          <div className="bg-surface border-kite rounded-lg p-4 flex-shrink-0">
            <div className="flex items-center gap-2 mb-3">
              <h3 className="font-display font-semibold text-xs text-primary uppercase tracking-wider">
                Grounded Corpus Scope
              </h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="filter-tag active select-none">Indian Contract Act</span>
              <span className="filter-tag active select-none">MSMED Act</span>
              <span className="filter-tag active select-none">DPDP Act</span>
              <span className="filter-tag active select-none">Specific Relief Act</span>
            </div>
          </div>

          {/* Chat History Stream */}
          <div className="bg-surface border-kite rounded-lg p-4 flex-1 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-muted" />
                <h3 className="font-display font-semibold text-sm text-primary">Research Sessions</h3>
              </div>
              <button
                onClick={handleNewChat}
                className="p-1.5 bg-page hover:bg-amazon-mist border border-[var(--black-kite-15)] rounded text-xs font-semibold text-primary flex items-center gap-1 transition-all"
                title="Start New Chat"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {loadingHistory ? (
              <div className="p-4 text-center text-muted">
                <Loader2 className="w-4 h-4 animate-spin mx-auto mb-2 text-rose-gold" />
                <span className="text-[10px]">Loading history...</span>
              </div>
            ) : (
              <div className="space-y-3">
                {sessions.length === 0 ? (
                  <p className="text-xs text-muted text-center py-4">No past sessions found.</p>
                ) : (
                  sessions.map((s) => (
                    <div
                      key={s.session_id}
                      onClick={() => router.push(`/chat?session_id=${s.session_id}`)}
                      className={`p-3 rounded-md border border-[var(--black-kite-15)] cursor-pointer transition-colors flex items-center justify-between gap-4 ${
                        activeSessionId === s.session_id
                          ? 'bg-[var(--amazon-mist)] border-rose-gold'
                          : 'bg-page hover:bg-[var(--amazon-mist)]/55'
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-primary line-clamp-2">{s.title || 'Untitled Chat'}</p>
                      </div>
                      <button
                        onClick={(e) => handleDeleteSession(s.session_id, e)}
                        className="text-muted hover:text-[var(--garnet)] transition-colors p-1"
                        title="Delete Session"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Query Input Area */}
          <div className="bg-surface border-kite rounded-lg p-5 flex-shrink-0">
            {/* Input area */}
            <div className="flex flex-col gap-3">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={4}
                placeholder="Enter your legal query..."
                className="query-input w-full resize-none"
              />
              <div className="flex justify-end">
                <button
                  onClick={() => handleSend()}
                  disabled={loading || !query.trim()}
                  className="btn-primary text-xs flex items-center gap-1.5 py-2 px-4 w-auto disabled:opacity-50 transition-all"
                >
                  Send <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

        </aside>
      </main>
    </div>
  );
}
