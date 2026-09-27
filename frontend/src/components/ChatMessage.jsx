import React, { useState } from 'react';
import { 
  Sparkles, User, TrendingUp, TrendingDown, 
  AlertTriangle, CheckCircle2, Clock, Share2, Database,
  Pin, Bookmark, Check
} from 'lucide-react';
import SQLViewer from './SQLViewer';
import ChartRenderer from './ChartRenderer';
import AgentStepTrace from './AgentStepTrace';
import { api } from '../services/api';

// Lightweight Markdown Formatter
function formatMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  return lines.map((line, idx) => {
    // Empty line
    if (!line.trim()) return <div key={idx} style={{ height: '8px' }} />;

    // Bullet point
    if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
      const content = line.trim().substring(2);
      return (
        <div key={idx} style={{ display: 'flex', gap: '8px', marginLeft: '8px', marginBottom: '4px' }}>
          <span style={{ color: '#818cf8', fontWeight: 'bold' }}>•</span>
          <span>{renderInlineMarkdown(content)}</span>
        </div>
      );
    }

    // Numbered list
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      return (
        <div key={idx} style={{ display: 'flex', gap: '8px', marginLeft: '8px', marginBottom: '4px' }}>
          <span style={{ color: '#38bdf8', fontWeight: '600', minWidth: '18px' }}>{numMatch[1]}.</span>
          <span>{renderInlineMarkdown(numMatch[2])}</span>
        </div>
      );
    }

    // Standard paragraph line
    return (
      <p key={idx} style={{ margin: '0 0 6px 0', lineHeight: 1.6 }}>
        {renderInlineMarkdown(line)}
      </p>
    );
  });
}

function renderInlineMarkdown(str) {
  // Regex to match **bold** and `code`
  const parts = str.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: '#ffffff', fontWeight: '700' }}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code
          key={i}
          style={{
            background: 'rgba(0, 0, 0, 0.4)',
            color: '#38bdf8',
            padding: '1px 6px',
            borderRadius: '4px',
            fontSize: '0.85em',
            fontFamily: 'var(--font-mono)'
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

export default function ChatMessage({ message, isStreaming = false }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        margin: '18px 0',
        paddingLeft: '60px'
      }}>
        <div style={{
          background: 'var(--primary-gradient)',
          color: '#ffffff',
          padding: '12px 18px',
          borderRadius: '18px 18px 4px 18px',
          fontSize: '0.95rem',
          fontWeight: '500',
          boxShadow: '0 4px 14px var(--primary-glow)',
          maxWidth: '80%',
          lineHeight: 1.5
        }}>
          {message.content}
        </div>
      </div>
    );
  }

  // Assistant Message
  const [pinned, setPinned] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);

  const handlePinWidget = async () => {
    if (!message.final_sql || pinned) return;
    try {
      await api.createDashboardWidget({
        connection_id: message.connection_id || 1,
        title: message.content ? message.content.slice(0, 36) + '...' : 'Pinned Metric',
        sql_query: message.final_sql,
        chart_type: message.chart_type || 'stat_card',
        chart_config: message.chart_config || {}
      });
      setPinned(true);
      setTimeout(() => setPinned(false), 3000);
    } catch (e) {
      console.error("Failed to pin widget:", e);
    }
  };

  const handleBookmark = async () => {
    if (!message.id || bookmarked) return;
    try {
      await api.createBookmark({
        message_id: message.id,
        label: message.content ? message.content.slice(0, 36) + '...' : 'Saved Query',
        folder: 'General'
      });
      setBookmarked(true);
      setTimeout(() => setBookmarked(false), 3000);
    } catch (e) {
      console.error("Failed to bookmark:", e);
    }
  };

  const analysis = message.analysis_result || {};
  const trends = analysis.trends || [];
  const outliers = analysis.outliers || [];
  const correlations = analysis.correlations || [];

  return (
    <div style={{
      display: 'flex',
      gap: '14px',
      margin: '24px 0',
      maxWidth: '880px',
      width: '100%'
    }}>
      {/* Agent Avatar */}
      <div style={{
        width: '38px',
        height: '38px',
        borderRadius: '12px',
        background: 'linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(6,182,212,0.2) 100%)',
        border: '1px solid rgba(99,102,241,0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '0 2px 8px rgba(99,102,241,0.15)'
      }}>
        <Sparkles size={18} color="#818cf8" />
      </div>

      {/* Message Card */}
      <div className="glass-panel" style={{
        flex: 1,
        padding: '20px 22px',
        borderRadius: '4px 18px 18px 18px',
        border: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)'
      }}>
        {/* Header with Latency, Pin & Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
          paddingBottom: '8px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.04)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: '700', color: 'var(--text-primary)' }}>
              Data Analyst
            </span>
            <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
              • LangGraph Autonomous Pipeline
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* Pin to Dashboard Button */}
            {message.final_sql && (
              <button
                onClick={handlePinWidget}
                title="Pin to Executive Dashboard"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: pinned ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${pinned ? '#10b981' : 'var(--border-subtle)'}`,
                  color: pinned ? '#10b981' : 'var(--text-muted)',
                  fontSize: '0.68rem',
                  fontWeight: '600',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {pinned ? <Check size={11} /> : <Pin size={11} />}
                <span>{pinned ? 'Pinned!' : 'Pin to Dashboard'}</span>
              </button>
            )}

            {/* Bookmark Query Button */}
            {message.id && (
              <button
                onClick={handleBookmark}
                title="Save as Bookmark"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: bookmarked ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${bookmarked ? '#38bdf8' : 'var(--border-subtle)'}`,
                  color: bookmarked ? '#38bdf8' : 'var(--text-muted)',
                  fontSize: '0.68rem',
                  fontWeight: '600',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {bookmarked ? <Check size={11} /> : <Bookmark size={11} />}
                <span>{bookmarked ? 'Saved!' : 'Bookmark'}</span>
              </button>
            )}

            {message.is_cached && (
              <span style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.68rem',
                fontWeight: '600',
                color: '#10b981',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: '12px',
                padding: '2px 8px'
              }}>
                ⚡ Cached (&lt;10ms)
              </span>
            )}

            {message.total_latency_ms && (
              <span style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono)'
              }}>
                <Clock size={11} /> {message.total_latency_ms}ms
              </span>
            )}
            {message.was_successful ? (
              <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                <CheckCircle2 size={10} /> Complete
              </span>
            ) : (
              <span className="badge badge-warning" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
                Failed
              </span>
            )}
          </div>
        </div>

        {/* Formatted Narrative Answer */}
        <div style={{
          fontSize: '0.925rem',
          lineHeight: 1.6,
          color: 'var(--text-primary)',
          marginBottom: '14px'
        }}>
          {formatMarkdown(message.content)}
        </div>

        {/* Statistical Insights Bar (Trends, Outliers, Correlations) */}
        {(trends.length > 0 || outliers.length > 0 || correlations.length > 0) && (
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
            margin: '12px 0 16px',
            padding: '10px 12px',
            background: 'rgba(0, 0, 0, 0.25)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255, 255, 255, 0.04)'
          }}>
            {trends.map((t, i) => (
              <div
                key={`trend-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  color: t.direction === 'increased' ? '#10b981' : '#f59e0b',
                  background: t.direction === 'increased' ? 'var(--success-bg)' : 'var(--warning-bg)',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)'
                }}
              >
                {t.direction === 'increased' ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                <span>{t.description}</span>
              </div>
            ))}

            {outliers.map((o, i) => (
              <div
                key={`outlier-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  color: '#fbbf24',
                  background: 'rgba(245, 158, 11, 0.12)',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)'
                }}
              >
                <AlertTriangle size={13} />
                <span>Outlier: {o.column} = {typeof o.value === 'number' ? o.value.toLocaleString() : o.value} (z-score: {o.z_score})</span>
              </div>
            ))}

            {correlations.map((c, i) => (
              <div
                key={`corr-${i}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  color: '#38bdf8',
                  background: 'rgba(56, 189, 248, 0.12)',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)'
                }}
              >
                <span>{c.description}</span>
              </div>
            ))}
          </div>
        )}

        {/* Data Visualization & Interactive Result Table */}
        {message.query_result && message.query_result.length > 0 && (
          <ChartRenderer
            chartType={message.chart_type}
            chartConfig={message.chart_config}
            data={message.query_result}
          />
        )}

        {/* Collapsible SQL Viewer */}
        {message.final_sql && (
          <SQLViewer sql={message.final_sql} />
        )}

        {/* Agent Execution Trace */}
        {message.trace_steps && message.trace_steps.length > 0 && (
          <AgentStepTrace steps={message.trace_steps} isLive={isStreaming} />
        )}
      </div>
    </div>
  );
}
