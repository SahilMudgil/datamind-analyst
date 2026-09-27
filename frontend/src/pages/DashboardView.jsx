import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, MessageSquare, RefreshCw, Trash2, 
  ExternalLink, Bookmark, Clock, Database, Plus, ChevronRight, CheckCircle2
} from 'lucide-react';
import ChartRenderer from '../components/ChartRenderer';
import SQLViewer from '../components/SQLViewer';

export default function DashboardView() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  const [widgets, setWidgets] = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState('widgets'); // 'widgets' | 'bookmarks'
  const [refreshingWidgetId, setRefreshingWidgetId] = useState(null);

  // Fetch all live widgets and bookmarks
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [liveWidgets, userBookmarks] = await Promise.all([
        api.getDashboardWidgetsLive().catch(() => []),
        api.getBookmarks().catch(() => [])
      ]);
      setWidgets(liveWidgets);
      setBookmarks(userBookmarks);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Refresh single widget
  const handleRefreshWidget = async (widgetId) => {
    setRefreshingWidgetId(widgetId);
    try {
      const refreshed = await api.refreshDashboardWidget(widgetId);
      setWidgets(prev => prev.map(w => {
        if (w.id === widgetId) {
          return {
            ...w,
            data: refreshed.data,
            columns: refreshed.columns
          };
        }
        return w;
      }));
    } catch (err) {
      console.error("Failed to refresh widget:", err);
    } finally {
      setRefreshingWidgetId(null);
    }
  };

  // Delete widget
  const handleDeleteWidget = async (widgetId) => {
    try {
      await api.deleteDashboardWidget(widgetId);
      setWidgets(prev => prev.filter(w => w.id !== widgetId));
    } catch (err) {
      console.error("Failed to delete widget:", err);
    }
  };

  // Delete bookmark
  const handleDeleteBookmark = async (bookmarkId) => {
    try {
      await api.deleteBookmark(bookmarkId);
      setBookmarks(prev => prev.filter(b => b.id !== bookmarkId));
    } catch (err) {
      console.error("Failed to delete bookmark:", err);
    }
  };

  // Refresh all
  const handleRefreshAll = async () => {
    setRefreshing(true);
    await fetchDashboardData();
    setRefreshing(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: 'var(--bg-main)', overflow: 'hidden' }}>
      {/* Top Navigation Bar */}
      <header style={{
        height: '60px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 28px',
        background: 'var(--bg-surface-translucent)',
        backdropFilter: 'blur(10px)',
        flexShrink: 0
      }}>
        {/* Brand & Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'var(--primary-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px var(--primary-glow)'
            }}>
              <LayoutDashboard size={18} color="#ffffff" />
            </div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: '800' }}>
              Executive <span style={{ color: '#818cf8' }}>Dashboard</span>
            </h2>
          </div>

          <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 0, 0.3)', padding: '3px', borderRadius: 'var(--radius-sm)' }}>
            <button
              onClick={() => setActiveTab('widgets')}
              style={{
                padding: '4px 12px',
                border: 'none',
                background: activeTab === 'widgets' ? 'var(--primary)' : 'transparent',
                color: activeTab === 'widgets' ? '#ffffff' : 'var(--text-muted)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <LayoutDashboard size={13} /> Pinned KPI Widgets ({widgets.length})
            </button>
            <button
              onClick={() => setActiveTab('bookmarks')}
              style={{
                padding: '4px 12px',
                border: 'none',
                background: activeTab === 'bookmarks' ? 'var(--primary)' : 'transparent',
                color: activeTab === 'bookmarks' ? '#ffffff' : 'var(--text-muted)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Bookmark size={13} /> Saved Insights ({bookmarks.length})
            </button>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleRefreshAll}
            disabled={refreshing}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            <span>{refreshing ? "Refreshing..." : "Refresh Live Data"}</span>
          </button>

          <button
            onClick={() => navigate('/chat')}
            className="btn btn-primary"
            style={{ padding: '6px 14px', fontSize: '0.8rem' }}
          >
            <MessageSquare size={14} />
            <span>Open Chat Analyst</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60%' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="animate-spin" style={{ marginBottom: '12px', color: '#818cf8' }} />
              <div>Loading executive dashboard...</div>
            </div>
          </div>
        ) : activeTab === 'widgets' ? (
          /* Pinned Widgets Tab */
          widgets.length === 0 ? (
            <div className="glass-panel" style={{ maxWidth: '580px', margin: '60px auto', padding: '40px', textAlign: 'center' }}>
              <div style={{
                width: '50px',
                height: '50px',
                borderRadius: '14px',
                background: 'rgba(99, 102, 241, 0.15)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px'
              }}>
                <LayoutDashboard size={24} color="#818cf8" />
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '700', marginBottom: '8px' }}>
                No Pinned KPI Widgets Yet
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6, marginBottom: '20px' }}>
                Pin any chart or table result from your chat sessions to monitor real-time business metrics on this dashboard.
              </p>
              <button
                onClick={() => navigate('/chat')}
                className="btn btn-primary"
                style={{ padding: '8px 20px' }}
              >
                <Plus size={16} /> Start Analysis in Chat
              </button>
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(540px, 1fr))',
              gap: '20px'
            }}>
              {widgets.map(w => (
                <div
                  key={w.id}
                  className="glass-panel glow-card"
                  style={{
                    padding: '20px',
                    borderRadius: 'var(--radius-lg)',
                    display: 'flex',
                    flexDirection: 'column',
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)'
                  }}
                >
                  {/* Widget Header */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '14px',
                    paddingBottom: '8px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)'
                  }}>
                    <div>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {w.title}
                      </h4>
                      <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                        Type: {w.chart_type} • {w.data ? `${w.data.length} records` : 'Ready'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <button
                        onClick={() => handleRefreshWidget(w.id)}
                        disabled={refreshingWidgetId === w.id}
                        title="Refresh this metric"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: 'var(--radius-sm)'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.color = '#38bdf8'}
                        onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                      >
                        <RefreshCw size={13} className={refreshingWidgetId === w.id ? "animate-spin" : ""} />
                      </button>

                      <button
                        onClick={() => handleDeleteWidget(w.id)}
                        title="Unpin widget"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: 'var(--radius-sm)'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.color = '#ef4444'}
                        onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  {/* Widget Visualization */}
                  <div style={{ flex: 1 }}>
                    <ChartRenderer
                      chartType={w.chart_type}
                      chartConfig={w.chart_config}
                      data={w.data}
                    />
                  </div>

                  {/* SQL Preview Accordion */}
                  <div style={{ marginTop: '8px' }}>
                    <SQLViewer sql={w.sql_query} />
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          /* Bookmarks Tab */
          bookmarks.length === 0 ? (
            <div className="glass-panel" style={{ maxWidth: '580px', margin: '60px auto', padding: '40px', textAlign: 'center' }}>
              <div style={{
                width: '50px',
                height: '50px',
                borderRadius: '14px',
                background: 'rgba(56, 189, 248, 0.15)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px'
              }}>
                <Bookmark size={24} color="#38bdf8" />
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '700', marginBottom: '8px' }}>
                No Saved Insights Yet
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.6, marginBottom: '20px' }}>
                Bookmark key analytical queries or summaries in chat to save them here for quick reference.
              </p>
              <button
                onClick={() => navigate('/')}
                className="btn btn-primary"
                style={{ padding: '8px 20px' }}
              >
                <Plus size={16} /> Open Analysis Chat
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '850px', margin: '0 auto' }}>
              {bookmarks.map(b => (
                <div
                  key={b.id}
                  className="glass-panel glow-card"
                  style={{
                    padding: '16px 20px',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    border: '1px solid var(--border-subtle)'
                  }}
                >
                  <div style={{ flex: 1, overflow: 'hidden', paddingRight: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                      <span className="badge badge-primary" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                        {b.folder || "General"}
                      </span>
                      <h4 style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        {b.label}
                      </h4>
                    </div>
                    {b.content && (
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {b.content}
                      </p>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      onClick={() => navigate('/')}
                      className="btn btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      title="Open query in Chat"
                    >
                      <ExternalLink size={12} /> Chat
                    </button>
                    <button
                      onClick={() => handleDeleteBookmark(b.id)}
                      title="Remove Bookmark"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        padding: '4px',
                        borderRadius: 'var(--radius-sm)'
                      }}
                      onMouseOver={(e) => e.currentTarget.style.color = '#ef4444'}
                      onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
