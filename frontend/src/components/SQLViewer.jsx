import React, { useState } from 'react';
import { Terminal, Copy, Check, ChevronDown, ChevronRight, ShieldCheck } from 'lucide-react';

const SQL_KEYWORDS = new Set([
  'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL', 'LIKE',
  'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'JOIN', 'LEFT', 'RIGHT',
  'INNER', 'OUTER', 'CROSS', 'ON', 'AS', 'ASC', 'DESC', 'UNION', 'ALL',
  'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'BETWEEN', 'EXISTS'
]);

const SQL_FUNCTIONS = new Set([
  'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'COALESCE', 'DATE_TRUNC',
  'EXTRACT', 'NOW', 'UPPER', 'LOWER', 'TRIM', 'CAST', 'SUBSTRING', 'LENGTH'
]);

// Lightweight SQL Syntax Colorizer
function highlightSQL(sql) {
  if (!sql) return '';
  
  // Tokenize regex preserving strings, words, numbers, and symbols
  const tokens = sql.split(/('(?:''|[^'])*'|\b[A-Za-z_][A-Za-z0-9_]*\b|\d+(?:\.\d+)?|[(),;]|--.*)/g);

  return tokens.map((token, i) => {
    if (!token) return null;
    const upper = token.toUpperCase();

    if (token.startsWith("'")) {
      // String Literal
      return <span key={i} style={{ color: '#34d399' }}>{token}</span>;
    } else if (token.startsWith("--")) {
      // Comment
      return <span key={i} style={{ color: '#64748b', fontStyle: 'italic' }}>{token}</span>;
    } else if (SQL_KEYWORDS.has(upper)) {
      // Keyword
      return <span key={i} style={{ color: '#c084fc', fontWeight: '700' }}>{token}</span>;
    } else if (SQL_FUNCTIONS.has(upper)) {
      // Aggregate / Function
      return <span key={i} style={{ color: '#38bdf8', fontWeight: '600' }}>{token}</span>;
    } else if (/^\d+(?:\.\d+)?$/.test(token)) {
      // Numeric Literal
      return <span key={i} style={{ color: '#fbbf24' }}>{token}</span>;
    }
    // Standard Identifier / Column / Symbol
    return <span key={i} style={{ color: '#e2e8f0' }}>{token}</span>;
  });
}

export default function SQLViewer({ sql }) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!sql) return null;

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = sql.trim().split('\n');

  return (
    <div style={{
      marginTop: '12px',
      background: '#070b14',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      boxShadow: 'inset 0 1px 2px rgba(0, 0, 0, 0.4)'
    }}>
      {/* Header Banner */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          background: 'rgba(255, 255, 255, 0.02)',
          userSelect: 'none',
          transition: 'background 0.15s ease'
        }}
        onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)'}
        onMouseOut={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)'}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={14} color="#818cf8" />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
            Generated SQL Query
          </span>
          <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '1px 6px' }}>
            <ShieldCheck size={10} /> AST Validated
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleCopy}
            title="Copy SQL Query"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: copied ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.05)',
              border: `1px solid ${copied ? '#10b981' : 'var(--border-subtle)'}`,
              color: copied ? '#10b981' : 'var(--text-muted)',
              fontSize: '0.725rem',
              cursor: 'pointer',
              padding: '2px 8px',
              borderRadius: 'var(--radius-sm)',
              transition: 'all 0.15s ease'
            }}
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>

          {isOpen ? <ChevronDown size={14} color="var(--text-muted)" /> : <ChevronRight size={14} color="var(--text-muted)" />}
        </div>
      </div>

      {/* Code Body with Line Numbers */}
      {isOpen && (
        <div style={{
          display: 'flex',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          background: '#040711',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.8rem',
          lineHeight: 1.6,
          overflowX: 'auto',
          padding: '10px 0'
        }}>
          {/* Line Numbers Gutter */}
          <div style={{
            padding: '0 12px',
            color: '#475569',
            textAlign: 'right',
            userSelect: 'none',
            borderRight: '1px solid rgba(255, 255, 255, 0.05)',
            flexShrink: 0
          }}>
            {lines.map((_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>

          {/* Syntax Code Content */}
          <div style={{
            padding: '0 16px',
            whiteSpace: 'pre',
            flex: 1
          }}>
            {lines.map((line, i) => (
              <div key={i}>{highlightSQL(line)}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
