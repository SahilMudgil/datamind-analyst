import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  Database, Sparkles, Send, LogOut, 
  Plus, Upload, CheckCircle2, AlertCircle, 
  MessageSquare, PanelRightOpen, PanelRightClose, Loader2, 
  ArrowRight, Trash2, Zap, RefreshCw, LayoutDashboard, Bookmark
} from 'lucide-react';
import SchemaExplorer from '../components/SchemaExplorer';
import ConnectDatabaseModal from '../components/ConnectDatabaseModal';
import CSVUploader from '../components/CSVUploader';
import ChatMessage from '../components/ChatMessage';
import AgentStepTrace from '../components/AgentStepTrace';

export default function Chat() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [health, setHealth] = useState(null);
  const [queryInput, setQueryInput] = useState('');
  const [viewMode, setViewMode] = useState('dashboard'); // 'dashboard' | 'chat'
  
  // Connection states
  const [connections, setConnections] = useState([]);
  const [activeConnectionId, setActiveConnectionId] = useState(null);

  // Conversations & Messages
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  // Streaming & Query Execution State
  const [isQueryRunning, setIsQueryRunning] = useState(false);
  const [liveSteps, setLiveSteps] = useState([]);
  const [currentRunningStep, setCurrentRunningStep] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Modals & Panels
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [isCSVModalOpen, setIsCSVModalOpen] = useState(false);
  const [isSchemaOpen, setIsSchemaOpen] = useState(false);

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, liveSteps]);

  // Load Health and Connections
  useEffect(() => {
    const fetchInit = async () => {
      try {
        const h = await api.checkHealth();
        setHealth(h);
      } catch {
        setHealth({ status: 'offline', database: 'unavailable' });
      }

      try {
        const connList = await api.getConnections();
        setConnections(connList);
        if (connList.length > 0) {
          setActiveConnectionId(connList[0].id);
        }
      } catch (err) {
        console.error("Failed to load connections:", err);
      }
    };
    fetchInit();
  }, []);

  // Load Conversations when active connection changes or on mount
  useEffect(() => {
    const loadConversations = async () => {
      try {
        const list = await api.getConversations();
        setConversations(list || []);
      } catch (err) {
        console.error("Failed to load conversations:", err);
      }
    };
    loadConversations();
  }, [activeConnectionId]);

  // When arriving at /dashboard or /, always open fresh workspace dashboard
  useEffect(() => {
    if (location.pathname === '/dashboard' || location.pathname === '/') {
      if (!isQueryRunning) {
        setViewMode('dashboard');
        setCurrentConversationId(null);
        setMessages([]);
      }
    } else if (location.pathname === '/chat') {
      setViewMode('chat');
    }
  }, [location.pathname]);

  // Load Messages when active conversation changes
  useEffect(() => {
    if (!currentConversationId) {
      setMessages([]);
      return;
    }
    // Do not wipe out chat state if a query is currently executing
    if (isQueryRunning) {
      return;
    }
    const loadMessages = async () => {
      setLoadingMessages(true);
      try {
        const msgs = await api.getConversationMessages(currentConversationId);
        setMessages(msgs);
      } catch (err) {
        console.error("Failed to load messages:", err);
      } finally {
        setLoadingMessages(false);
      }
    };
    loadMessages();
  }, [currentConversationId]);

  // Establish WebSocket Connection with Auto-Reconnect
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    let isMounted = true;

    const connectWebSocket = () => {
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        return;
      }

      const apiUrl = import.meta.env.VITE_API_URL;
      let wsHost = window.location.host;
      if (apiUrl) {
        try {
          const parsed = new URL(apiUrl);
          wsHost = parsed.host;
        } catch (e) {
          // fallback to window.location.host
        }
      }
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${wsHost}/api/chat/ws?token=${token}`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setWsConnected(true);
          console.log("WebSocket connected for live streaming.");
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'step_complete') {
              setCurrentRunningStep(data.step_name);
              setLiveSteps(prev => [...prev, {
                step_name: data.step_name,
                status: 'completed',
                details: data.details,
                duration_ms: data.duration_ms
              }]);
            } else if (data.type === 'final_result') {
              setIsQueryRunning(false);
              setCurrentRunningStep(null);
              setLiveSteps([]);
              // Append assistant message
              setMessages(prev => [...prev, {
                id: data.message_id,
                conversation_id: data.conversation_id,
                role: 'assistant',
                content: data.content,
                final_sql: data.final_sql,
                query_result: data.query_result,
                analysis_result: data.analysis_result,
                chart_type: data.chart_type,
                chart_config: data.chart_config,
                was_successful: data.was_successful,
                total_latency_ms: data.total_latency_ms,
                trace_steps: data.trace_steps
              }]);
            } else if (data.type === 'conversation_created') {
              setCurrentConversationId(data.conversation_id);
              setConversations(prev => [{
                id: data.conversation_id,
                connection_id: activeConnectionId,
                title: data.title
              }, ...prev]);
            } else if (data.type === 'error') {
              setIsQueryRunning(false);
              setCurrentRunningStep(null);
              setMessages(prev => [...prev, {
                id: Date.now(),
                role: 'assistant',
                content: `An error occurred: ${data.message || 'Pipeline execution failed'}`,
                was_successful: false
              }]);
              console.error("WebSocket error message:", data.message);
            }
          } catch (e) {
            console.error("Failed to parse WS message:", e);
          }
        };

        ws.onerror = (err) => {
          console.warn("WebSocket error, fallback to REST available:", err);
          if (isMounted) setWsConnected(false);
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setWsConnected(false);
          // Try to reconnect in 4s
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 4000);
        };
      } catch (err) {
        console.warn("Could not initiate WebSocket:", err);
        if (isMounted) setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [activeConnectionId]);

  // Handle Query Submission
  const handleSendQuery = async (queryToSend = null) => {
    const promptText = (typeof queryToSend === 'string' ? queryToSend : queryInput).trim();
    if (!promptText || !activeConnectionId || isQueryRunning) return;

    setQueryInput('');
    setIsQueryRunning(true);
    setLiveSteps([]);
    setCurrentRunningStep('intent_check');

    // Optimistically append user message to local feed
    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: promptText
    };
    setMessages(prev => [...prev, tempUserMsg]);

    // 1. Try WebSocket submission
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        query: promptText,
        connection_id: activeConnectionId,
        conversation_id: currentConversationId
      }));
    } else {
      // 2. REST HTTP Fallback
      try {
        const assistantRes = await api.sendQueryRest(activeConnectionId, promptText, currentConversationId);
        setMessages(prev => [...prev, assistantRes]);

        // If a new conversation was created on the backend
        if (assistantRes.conversation_id && !currentConversationId) {
          setCurrentConversationId(assistantRes.conversation_id);
          setConversations(prev => [{
            id: assistantRes.conversation_id,
            connection_id: activeConnectionId,
            title: promptText.slice(0, 36) + (promptText.length > 36 ? '...' : '')
          }, ...prev]);
        }
      } catch (err) {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          role: 'assistant',
          content: `Query failed: ${err.message || 'Server error occurred'}`,
          was_successful: false
        }]);
      } finally {
        setIsQueryRunning(false);
        setCurrentRunningStep(null);
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuery();
    }
  };

  const handleStartChat = () => {
    setViewMode('chat');
    setCurrentConversationId(null);
    setMessages([]);
    setLiveSteps([]);
    setCurrentRunningStep(null);
    setQueryInput('');
  };

  const handleGoToDashboard = () => {
    setViewMode('dashboard');
    setCurrentConversationId(null);
    setMessages([]);
    setLiveSteps([]);
    setCurrentRunningStep(null);
    setQueryInput('');
    if (location.pathname !== '/dashboard') {
      navigate('/dashboard');
    }
  };

  const handleSelectConversation = (conv) => {
    if (conv.connection_id && conv.connection_id !== activeConnectionId) {
      setActiveConnectionId(conv.connection_id);
    }
    setViewMode('chat');
    setCurrentConversationId(conv.id);
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(convId);
      setConversations(prev => prev.filter(c => c.id !== convId));
      if (currentConversationId === convId) {
        handleGoToDashboard();
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const activeConnection = connections.find(c => c.id === activeConnectionId) || connections[0];

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: 'var(--bg-main)' }}>
      {/* Left Sidebar */}
      <div style={{
        width: '280px',
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px 16px'
      }}>
        {/* Brand - Click to return to starter dashboard */}
        <div 
          onClick={handleGoToDashboard}
          style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', paddingLeft: '8px', cursor: 'pointer' }}
          title="Return to Main Dashboard"
        >
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px var(--primary-glow)'
          }}>
            <Database size={20} color="#ffffff" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: '800', lineHeight: 1.1 }}>
              Data<span style={{ color: '#818cf8' }}>Mind</span>
            </h2>
            <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>Text-to-SQL Analyst</span>
          </div>
        </div>

        {/* Database Connection Selector & Action Buttons */}
        <div className="glass-panel" style={{ padding: '14px', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>
              Active Source
            </span>
            <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
              Read-Only
            </span>
          </div>

          {connections.length > 0 ? (
            <select
              value={activeConnectionId || ''}
              onChange={(e) => setActiveConnectionId(Number(e.target.value))}
              style={{
                width: '100%',
                background: 'var(--bg-main)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.85rem',
                fontWeight: '600',
                marginBottom: '10px',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              {connections.map(c => (
                <option key={c.id} value={c.id}>
                  {c.display_name} ({c.db_type})
                </option>
              ))}
            </select>
          ) : (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
              No database connected yet.
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <button
              onClick={() => setIsConnectModalOpen(true)}
              className="btn btn-secondary"
              style={{ padding: '6px 8px', fontSize: '0.75rem', width: '100%' }}
              title="Connect a SQL database"
            >
              <Plus size={14} /> Connect DB
            </button>
            <button
              onClick={() => setIsCSVModalOpen(true)}
              className="btn btn-secondary"
              style={{ padding: '6px 8px', fontSize: '0.75rem', width: '100%' }}
              title="Upload CSV spreadsheet"
            >
              <Upload size={14} /> CSV Upload
            </button>
          </div>

          <button
            onClick={() => navigate('/connections')}
            style={{
              width: '100%',
              marginTop: '8px',
              padding: '6px 8px',
              background: 'rgba(30, 41, 59, 0.4)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.color = '#fff';
              e.currentTarget.style.borderColor = 'var(--primary)';
              e.currentTarget.style.background = 'rgba(99, 102, 241, 0.1)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.color = 'var(--text-secondary)';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
              e.currentTarget.style.background = 'rgba(30, 41, 59, 0.4)';
            }}
            title="Manage and inspect database connections and CSVs"
          >
            <Database size={13} />
            <span>Manage Databases & CSV</span>
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={handleStartChat}
          className="btn btn-primary"
          style={{ width: '100%', padding: '8px', fontSize: '0.825rem', marginBottom: '16px' }}
        >
          <Plus size={15} /> New Analysis Chat
        </button>

        {/* Conversations History */}
        <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700', marginBottom: '8px', paddingLeft: '8px' }}>
            Recent Sessions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {conversations.length === 0 ? (
              <div style={{ padding: '12px 8px', fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                No previous sessions yet.
              </div>
            ) : (
              conversations.map(conv => (
                <div
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv)}
                  className="session-item"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    background: currentConversationId === conv.id ? 'var(--bg-surface-elevated)' : 'transparent',
                    color: currentConversationId === conv.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                    border: currentConversationId === conv.id ? '1px solid var(--border-medium)' : '1px solid transparent',
                    cursor: 'pointer',
                    fontSize: '0.825rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <MessageSquare size={13} color="#818cf8" style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {conv.title}
                    </span>
                  </div>

                  <button
                    onClick={(e) => handleDeleteConversation(e, conv.id)}
                    title="Delete Session"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '2px 4px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      opacity: 0.6
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.color = '#ef4444';
                      e.currentTarget.style.opacity = 1;
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.color = 'var(--text-muted)';
                      e.currentTarget.style.opacity = 0.6;
                    }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* User Profile & Logout */}
        <div style={{
          paddingTop: '16px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: '700', color: 'var(--text-primary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
              {user?.name || user?.email?.split('@')[0]}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
              {user?.email}
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign Out"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--radius-sm)'
            }}
            onMouseOver={(e) => e.currentTarget.style.color = 'var(--danger)'}
            onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>

      {/* Main Center Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Top Header */}
        <header style={{
          height: '60px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: 'var(--bg-surface-translucent)',
          backdropFilter: 'blur(10px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontWeight: '700', fontSize: '0.95rem' }}>
              {activeConnection ? activeConnection.display_name : 'No Connection'}
            </span>
            <span className="badge badge-primary" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Zap size={11} /> LangGraph Multi-Node Pipeline
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Real-time streaming status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem' }}>
              <span style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: wsConnected ? '#10b981' : '#38bdf8',
                boxShadow: wsConnected ? '0 0 8px #10b981' : 'none'
              }} />
              <span style={{ color: 'var(--text-secondary)' }}>
                {wsConnected ? 'WebSocket Live' : 'REST Active'}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}>
              {health?.database === 'connected' ? (
                <>
                  <CheckCircle2 size={16} color="#10b981" />
                  <span style={{ color: 'var(--text-secondary)' }}>DB Online</span>
                </>
              ) : (
                <>
                  <AlertCircle size={16} color="#ef4444" />
                  <span style={{ color: 'var(--danger)' }}>DB Offline</span>
                </>
              )}
            </div>

            {/* Main Dashboard Navigation Button */}
            <button
              onClick={handleGoToDashboard}
              className={viewMode === 'dashboard' ? "btn btn-primary" : "btn btn-secondary"}
              style={{ padding: '6px 12px', fontSize: '0.825rem' }}
              title="Return to Workspace Dashboard"
            >
              <LayoutDashboard size={15} />
              <span>Dashboard</span>
            </button>

            {/* Schema Explorer Toggle */}
            <button
              onClick={() => setIsSchemaOpen(!isSchemaOpen)}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '0.825rem' }}
            >
              {isSchemaOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
              <span>Schema Explorer</span>
            </button>
          </div>
        </header>

        {/* Central Messages Container */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px 32px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center'
        }}>
          {loadingMessages ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', margin: 'auto', gap: '14px', color: 'var(--text-muted)' }}>
              <Loader2 size={36} className="animate-spin" color="var(--primary)" />
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Loading conversation messages...</span>
            </div>
          ) : viewMode === 'dashboard' ? (
            /* Dashboard View: Only Database Connection & Management Info (No Chat Box, No Suggested Questions) */
            connections.length === 0 ? (
              /* State A: No Database Connected (Matching user screenshot) */
              <div className="glass-panel" style={{ maxWidth: '640px', width: '100%', padding: '48px 36px', textAlign: 'center', margin: 'auto' }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '20px',
                  background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(16,185,129,0.2) 100%)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '20px',
                  border: '1px solid rgba(99,102,241,0.3)'
                }}>
                  <Database size={32} color="#818cf8" />
                </div>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '800', marginBottom: '12px' }}>
                  No Database Connected Yet
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '28px' }}>
                  To chat with your data and generate AI-driven SQL analyses, connect an existing PostgreSQL database or upload a CSV spreadsheet.
                </p>
                <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => setIsConnectModalOpen(true)}
                    className="btn btn-primary"
                    style={{ padding: '10px 22px', fontSize: '0.9rem' }}
                  >
                    <Plus size={16} />
                    <span>Connect PostgreSQL DB</span>
                  </button>
                  <button
                    onClick={() => setIsCSVModalOpen(true)}
                    className="btn btn-secondary"
                    style={{ padding: '10px 22px', fontSize: '0.9rem' }}
                  >
                    <Upload size={16} />
                    <span>Upload CSV File</span>
                  </button>
                </div>
              </div>
            ) : (
              /* State B: Database Connected (Clean Database Connection & Management Info) */
              <div className="glass-panel" style={{ maxWidth: '680px', width: '100%', padding: '40px 36px', textAlign: 'center', margin: 'auto' }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '20px',
                  background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(16,185,129,0.2) 100%)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '16px',
                  border: '1px solid rgba(99,102,241,0.3)'
                }}>
                  <Database size={32} color="#818cf8" />
                </div>

                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.25)', padding: '3px 12px', borderRadius: '20px', marginBottom: '14px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 6px #10b981' }} />
                  <span style={{ fontSize: '0.78rem', fontWeight: '600', color: '#10b981' }}>
                    Connected: {activeConnection ? activeConnection.display_name : 'PostgreSQL'}
                  </span>
                </div>

                <h2 style={{ fontSize: '1.55rem', fontWeight: '800', marginBottom: '8px' }}>
                  Database Connected & Ready
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: 1.5, marginBottom: '24px' }}>
                  Active data source is connected in read-only mode with automated AST safety guardrails.
                </p>

                {/* Connection & Management Details Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: '12px',
                  textAlign: 'left',
                  background: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 20px',
                  marginBottom: '26px'
                }}>
                  <div>
                    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>
                      Database Name
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: '600', color: 'var(--text-primary)', marginTop: '2px' }}>
                      {activeConnection?.display_name || 'PostgreSQL'}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>
                      Database Engine
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: '600', color: 'var(--text-primary)', marginTop: '2px' }}>
                      {String(activeConnection?.db_type || 'postgresql').toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>
                      Security Mode
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: '600', color: '#10b981', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={13} /> Read-Only Agent Guard
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: '700' }}>
                      Pipeline Protection
                    </div>
                    <div style={{ fontSize: '0.88rem', fontWeight: '600', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      sqlglot AST & Limit Guard
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={handleStartChat}
                    className="btn btn-primary"
                    style={{ padding: '10px 22px', fontSize: '0.9rem' }}
                  >
                    <MessageSquare size={16} />
                    <span>Start New Analysis Chat</span>
                  </button>
                  <button
                    onClick={() => navigate('/connections')}
                    className="btn btn-secondary"
                    style={{ padding: '10px 20px', fontSize: '0.88rem' }}
                    title="Manage connected databases and CSV files"
                  >
                    <Database size={15} />
                    <span>Databases & CSV Manager</span>
                  </button>
                  <button
                    onClick={() => setIsSchemaOpen(true)}
                    className="btn btn-secondary"
                    style={{ padding: '10px 20px', fontSize: '0.88rem' }}
                  >
                    <PanelRightOpen size={15} />
                    <span>Schema Explorer</span>
                  </button>
                  <button
                    onClick={() => setIsConnectModalOpen(true)}
                    className="btn btn-secondary"
                    style={{ padding: '10px 18px', fontSize: '0.88rem' }}
                  >
                    <Plus size={15} />
                    <span>Connect Another DB</span>
                  </button>
                  <button
                    onClick={() => setIsCSVModalOpen(true)}
                    className="btn btn-secondary"
                    style={{ padding: '10px 18px', fontSize: '0.88rem' }}
                  >
                    <Upload size={15} />
                    <span>Upload CSV</span>
                  </button>
                </div>
              </div>
            )
          ) : (
            /* Chat View */
            <div style={{ width: '100%', maxWidth: '880px' }}>
              {/* Active Conversation Breadcrumb Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                marginBottom: '16px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                  <MessageSquare size={14} color="#818cf8" style={{ flexShrink: 0 }} />
                  <span style={{ fontSize: '0.825rem', fontWeight: '600', color: 'var(--text-primary)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {conversations.find(c => c.id === currentConversationId)?.title || 'New Analysis Session'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    onClick={handleStartChat}
                    className="btn btn-secondary"
                    style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Start another chat"
                  >
                    <Plus size={12} />
                    <span>New Chat</span>
                  </button>
                  <button
                    onClick={handleGoToDashboard}
                    className="btn btn-secondary"
                    style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Return to Workspace Dashboard"
                  >
                    <LayoutDashboard size={12} />
                    <span>Back to Dashboard</span>
                  </button>
                </div>
              </div>

              {messages.length === 0 && !isQueryRunning ? (
                <div style={{ textAlign: 'center', margin: '60px auto', padding: '40px 20px', color: 'var(--text-secondary)' }}>
                  <div style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '16px',
                    background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(6,182,212,0.2) 100%)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '16px',
                    border: '1px solid rgba(99,102,241,0.3)'
                  }}>
                    <Sparkles size={28} color="#818cf8" />
                  </div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '8px' }}>
                    New Analysis Session
                  </h3>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', maxWidth: '440px', margin: '0 auto' }}>
                    Type your question in the chat box below to generate safe SQL against <strong>{activeConnection?.display_name || 'your database'}</strong>.
                  </p>
                </div>
              ) : (
                messages.map((msg, i) => (
                  <ChatMessage key={msg.id || i} message={msg} />
                ))
              )}

              {/* Live Streaming Step Execution Progress */}
              {isQueryRunning && (
                <div style={{ margin: '20px 0', maxWidth: '880px', width: '100%' }}>
                  <div className="glass-panel" style={{ padding: '16px 20px', border: '1px solid var(--border-focus)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                      <Loader2 size={16} className="animate-spin" color="#818cf8" />
                      <span style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        Agent Pipeline Running: {currentRunningStep || "Analyzing query..."}
                      </span>
                    </div>
                    {liveSteps.length > 0 && (
                      <AgentStepTrace steps={liveSteps} isLive={true} />
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Input Area: Only rendered in Chat Mode */}
        {viewMode === 'chat' && (
          <div style={{
            padding: '16px 24px 20px',
            background: 'var(--bg-surface)',
            borderTop: '1px solid var(--border-subtle)'
          }}>
            <div style={{
              maxWidth: '880px',
              margin: '0 auto',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: 'var(--bg-main)',
              borderRadius: 'var(--radius-lg)',
              padding: '8px 16px',
              border: '1px solid var(--border-medium)',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
            }}>
              <input
                type="text"
                placeholder={connections.length === 0 ? "Connect a database or upload a CSV to begin asking questions..." : (activeConnection ? `Ask a question about ${activeConnection.display_name}...` : "Select a database connection...")}
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isQueryRunning || !activeConnectionId || connections.length === 0}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '0.95rem',
                  outline: 'none',
                  padding: '8px 0',
                  cursor: (isQueryRunning || connections.length === 0) ? 'not-allowed' : 'text'
                }}
              />
              <button
                className="btn btn-primary"
                style={{ padding: '8px 18px', borderRadius: 'var(--radius-md)' }}
                disabled={isQueryRunning || !queryInput.trim() || !activeConnectionId || connections.length === 0}
                onClick={() => handleSendQuery()}
              >
                {isQueryRunning ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Send size={16} />
                    <span>Ask Analyst</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Right Drawer: Schema Explorer */}
      {isSchemaOpen && (
        <SchemaExplorer
          connectionId={activeConnectionId}
          onClose={() => setIsSchemaOpen(false)}
        />
      )}

      {/* Modals */}
      <ConnectDatabaseModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        onConnectionCreated={(conn) => {
          setConnections(prev => [conn, ...prev]);
          setActiveConnectionId(conn.id);
        }}
      />

      <CSVUploader
        isOpen={isCSVModalOpen}
        onClose={() => setIsCSVModalOpen(false)}
        onUploadComplete={(res) => {
          if (res.connection_id) {
            setConnections(prev => [{
              id: res.connection_id,
              display_name: res.display_name,
              db_type: 'csv_import'
            }, ...prev]);
            setActiveConnectionId(res.connection_id);
          }
        }}
      />
    </div>
  );
}
