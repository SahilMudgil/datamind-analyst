import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Navigation from '../components/Navigation';
import ChartRenderer from '../components/ChartRenderer';

export default function Dashboard() {
  const navigate = useNavigate();
  const [widgets, setWidgets] = useState([]);
  const [widgetData, setWidgetData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState({});
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    fetchWidgets();
  }, []);

  const fetchWidgets = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDashboardWidgets();
      setWidgets(data);
      // Auto-refresh each widget to fetch fresh rows
      data.forEach(w => refreshWidget(w.id));
    } catch (e) {
      console.error('Failed to fetch widgets', e);
      setError(e.message || 'Failed to load dashboard widgets. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const refreshWidget = async (widgetId) => {
    setRefreshing(prev => ({ ...prev, [widgetId]: true }));
    try {
      const data = await api.refreshDashboardWidget(widgetId);
      setWidgetData(prev => ({ ...prev, [widgetId]: data }));
    } catch (e) {
      console.error(`Failed to refresh widget ${widgetId}`, e);
      setWidgetData(prev => ({ ...prev, [widgetId]: { error: e.message || 'Execution failed' } }));
    } finally {
      setRefreshing(prev => ({ ...prev, [widgetId]: false }));
    }
  };

  const deleteWidget = async (widgetId) => {
    if (!window.confirm('Are you sure you want to remove this widget from your dashboard?')) return;
    try {
      await api.deleteDashboardWidget(widgetId);
      setWidgets(prev => prev.filter(w => w.id !== widgetId));
      setWidgetData(prev => {
        const next = { ...prev };
        delete next[widgetId];
        return next;
      });
    } catch (e) {
      console.error('Failed to delete widget', e);
    }
  };

  const copySQL = (widgetId, sql) => {
    navigator.clipboard.writeText(sql);
    setCopiedId(widgetId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', color: 'var(--text-primary)' }}>
      <Navigation />

      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 24px' }}>
        {/* Header Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '32px'
        }}>
          <div>
            <h1 style={{
              fontSize: '1.8rem',
              fontWeight: 700,
              margin: '0 0 6px 0',
              letterSpacing: '-0.02em',
              background: 'linear-gradient(135deg, #fff 0%, #cbd5e1 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}>
              Executive Intelligence Dashboard
            </h1>
            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Live KPI metrics, trend charts, and pinned business queries.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => widgets.forEach(w => refreshWidget(w.id))}
              style={{
                background: 'rgba(30, 41, 59, 0.7)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                padding: '8px 16px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                cursor: 'pointer',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              🔄 Refresh All
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              style={{
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                border: 'none',
                color: '#fff',
                padding: '8px 18px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                cursor: 'pointer',
                fontWeight: 600,
                boxShadow: '0 4px 14px rgba(99, 102, 241, 0.35)'
              }}
            >
              + Ask New Query
            </button>
          </div>
        </div>

        {/* Error Alert Banner */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            padding: '16px 20px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#f87171', fontSize: '0.9rem' }}>
              <span>⚠️</span>
              <span>{error}</span>
            </div>
            <button
              onClick={fetchWidgets}
              style={{
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#fca5a5',
                borderRadius: '6px',
                padding: '6px 14px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                fontWeight: 600
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)' }}>
            <div style={{
              width: '36px',
              height: '36px',
              border: '3px solid var(--border-subtle)',
              borderTopColor: 'var(--primary)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 16px'
            }} />
            <p>Loading Dashboard Widgets...</p>
          </div>
        ) : widgets.length === 0 ? (
          /* Empty State */
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px dashed var(--border-subtle)',
            borderRadius: '20px',
            padding: '64px 24px',
            textAlign: 'center',
            maxWidth: '600px',
            margin: '40px auto'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
            <h3 style={{ fontSize: '1.3rem', margin: '0 0 8px 0', color: 'var(--text-primary)' }}>
              No Visualizations Pinned Yet
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.5 }}>
              Ask any business question in the Analyst Chat, then click the <strong>"📌 Pin to Dashboard"</strong> button on any chart or metric to monitor it here in real-time.
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              style={{
                background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                border: 'none',
                color: '#fff',
                padding: '10px 24px',
                borderRadius: '10px',
                fontSize: '0.92rem',
                fontWeight: 600,
                cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(99, 102, 241, 0.4)'
              }}
            >
              Open Main Dashboard
            </button>
          </div>
        ) : (
          /* Widgets Grid */
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(460px, 1fr))',
            gap: '24px'
          }}>
            {widgets.map(w => {
              const live = widgetData[w.id];
              const isRef = refreshing[w.id];
              const isCopied = copiedId === w.id;

              return (
                <div
                  key={w.id}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '16px',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
                    transition: 'border-color 0.2s',
                    position: 'relative'
                  }}
                >
                  {/* Card Header */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '16px'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{
                          fontSize: '0.72rem',
                          textTransform: 'uppercase',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: 'rgba(99, 102, 241, 0.15)',
                          color: '#818cf8',
                          border: '1px solid rgba(99, 102, 241, 0.3)'
                        }}>
                          {w.chart_type?.toUpperCase() || 'METRIC'}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {live?.row_count !== undefined ? `${live.row_count} rows` : ''}
                        </span>
                      </div>
                      <h3 style={{
                        margin: 0,
                        fontSize: '1.05rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        lineHeight: 1.3
                      }}>
                        {w.title}
                      </h3>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        onClick={() => copySQL(w.id, w.sql_query)}
                        style={{
                          background: 'rgba(30, 41, 59, 0.6)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '6px',
                          padding: '4px 8px',
                          color: isCopied ? '#10b981' : 'var(--text-muted)',
                          fontSize: '0.75rem',
                          cursor: 'pointer'
                        }}
                        title="Copy SQL Query"
                      >
                        {isCopied ? '✓ Copied' : 'SQL'}
                      </button>

                      <button
                        onClick={() => refreshWidget(w.id)}
                        disabled={isRef}
                        style={{
                          background: 'rgba(30, 41, 59, 0.6)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: '6px',
                          padding: '4px 8px',
                          color: 'var(--text-muted)',
                          fontSize: '0.75rem',
                          cursor: 'pointer'
                        }}
                        title="Refresh Live Data"
                      >
                        {isRef ? '⏳' : '🔄'}
                      </button>

                      <button
                        onClick={() => deleteWidget(w.id)}
                        style={{
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.2)',
                          borderRadius: '6px',
                          padding: '4px 8px',
                          color: '#f87171',
                          fontSize: '0.75rem',
                          cursor: 'pointer'
                        }}
                        title="Remove from Dashboard"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  {/* Chart Body */}
                  <div style={{ flex: 1, minHeight: '260px' }}>
                    {isRef ? (
                      <div style={{
                        height: '260px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-muted)',
                        fontSize: '0.85rem'
                      }}>
                        Updating metric data...
                      </div>
                    ) : live?.error ? (
                      <div style={{
                        height: '260px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--danger)',
                        fontSize: '0.85rem',
                        border: '1px dashed rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px',
                        padding: '16px',
                        textAlign: 'center'
                      }}>
                        <div style={{ marginBottom: '6px', fontWeight: 600 }}>⚠️ Query Execution Error</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{live.error}</div>
                      </div>
                    ) : live?.data && live.data.length > 0 ? (
                      <ChartRenderer
                        data={live.data}
                        chartType={w.chart_type}
                        chartConfig={w.chart_config}
                      />
                    ) : (
                      <div style={{
                        height: '260px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-muted)',
                        fontSize: '0.85rem',
                        border: '1px dashed var(--border-subtle)',
                        borderRadius: '8px'
                      }}>
                        Click refresh 🔄 to load live data
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
