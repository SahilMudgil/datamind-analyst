import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Navigation from '../components/Navigation';

export default function Bookmarks() {
  const navigate = useNavigate();
  const [bookmarks, setBookmarks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFolder, setSelectedFolder] = useState('All');
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    fetchBookmarks();
  }, []);

  const fetchBookmarks = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getBookmarks();
      setBookmarks(data);
    } catch (e) {
      console.error('Failed to fetch bookmarks', e);
      setError(e.message || 'Failed to load saved bookmarks.');
    } finally {
      setLoading(false);
    }
  };

  const deleteBookmark = async (id) => {
    if (!window.confirm('Delete this saved bookmark?')) return;
    try {
      await api.deleteBookmark(id);
      setBookmarks(prev => prev.filter(b => b.id !== id));
    } catch (e) {
      console.error('Failed to delete bookmark', e);
    }
  };

  const copySQL = (id, sql) => {
    navigator.clipboard.writeText(sql);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const folders = ['All', ...new Set(bookmarks.map(b => b.folder || 'General'))];

  const filteredBookmarks = bookmarks.filter(b => {
    const matchesFolder = selectedFolder === 'All' || b.folder === selectedFolder;
    const matchesSearch = !search ||
      b.label?.toLowerCase().includes(search.toLowerCase()) ||
      b.content?.toLowerCase().includes(search.toLowerCase()) ||
      b.final_sql?.toLowerCase().includes(search.toLowerCase());
    return matchesFolder && matchesSearch;
  });

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', color: 'var(--text-primary)' }}>
      <Navigation />

      <main style={{ maxWidth: '1100px', margin: '0 auto', padding: '32px 24px' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '28px'
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
              Saved Business Queries & Insights
            </h1>
            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Curated repository of bookmarked analytical findings and safe SQL statements.
            </p>
          </div>

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
            + Ask in Dashboard
          </button>
        </div>

        {/* Filters Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
          marginBottom: '24px',
          flexWrap: 'wrap'
        }}>
          {/* Folders */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {folders.map(f => (
              <button
                key={f}
                onClick={() => setSelectedFolder(f)}
                style={{
                  background: selectedFolder === f ? 'rgba(99, 102, 241, 0.2)' : 'rgba(30, 41, 59, 0.6)',
                  border: selectedFolder === f ? '1px solid #6366f1' : '1px solid var(--border-subtle)',
                  color: selectedFolder === f ? '#fff' : 'var(--text-secondary)',
                  padding: '6px 14px',
                  borderRadius: '20px',
                  fontSize: '0.82rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                📁 {f}
              </button>
            ))}
          </div>

          {/* Search */}
          <div style={{ position: 'relative', width: '280px' }}>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search bookmarks or SQL..."
              style={{
                width: '100%',
                background: 'rgba(15, 23, 42, 0.7)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '0.85rem',
                color: 'var(--text-primary)',
                outline: 'none'
              }}
            />
          </div>
        </div>

        {/* Error Alert */}
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
              onClick={fetchBookmarks}
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

        {/* Bookmarks List */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
            Loading Saved Bookmarks...
          </div>
        ) : filteredBookmarks.length === 0 ? (
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px dashed var(--border-subtle)',
            borderRadius: '16px',
            padding: '48px 24px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>🔖</div>
            <h3 style={{ margin: '0 0 6px 0', color: 'var(--text-primary)' }}>
              {search || selectedFolder !== 'All' ? 'No Matching Bookmarks' : 'No Bookmarks Saved Yet'}
            </h3>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
              {search || selectedFolder !== 'All' 
                ? 'Try adjusting your search terms or selecting "All" folders.'
                : 'Click "🔖 Bookmark" on any assistant answer in the chat to save queries here for quick access.'}
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {filteredBookmarks.map(b => {
              const isCopied = copiedId === b.id;

              return (
                <div
                  key={b.id}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '14px',
                    padding: '20px',
                    boxShadow: '0 4px 14px rgba(0, 0, 0, 0.2)'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '12px'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <span style={{
                          fontSize: '0.72rem',
                          background: 'rgba(56, 189, 248, 0.15)',
                          color: '#38bdf8',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 600
                        }}>
                          {b.folder || 'General'}
                        </span>
                        {b.chart_type && (
                          <span style={{
                            fontSize: '0.72rem',
                            background: 'rgba(99, 102, 241, 0.15)',
                            color: '#818cf8',
                            padding: '2px 8px',
                            borderRadius: '4px'
                          }}>
                            {b.chart_type.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {b.label}
                      </h3>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      {b.final_sql && (
                        <button
                          onClick={() => copySQL(b.id, b.final_sql)}
                          style={{
                            background: 'rgba(30, 41, 59, 0.7)',
                            border: '1px solid var(--border-subtle)',
                            color: isCopied ? '#10b981' : 'var(--text-secondary)',
                            borderRadius: '6px',
                            padding: '6px 12px',
                            fontSize: '0.78rem',
                            cursor: 'pointer'
                          }}
                        >
                          {isCopied ? '✓ Copied SQL' : 'Copy SQL'}
                        </button>
                      )}

                      <button
                        onClick={() => deleteBookmark(b.id)}
                        style={{
                          background: 'rgba(239, 68, 68, 0.1)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          color: '#f87171',
                          borderRadius: '6px',
                          padding: '6px 10px',
                          fontSize: '0.78rem',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {b.content && (
                    <p style={{
                      margin: '0 0 14px 0',
                      fontSize: '0.9rem',
                      lineHeight: 1.5,
                      color: 'var(--text-secondary)'
                    }}>
                      {b.content}
                    </p>
                  )}

                  {b.final_sql && (
                    <pre style={{
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      borderRadius: '8px',
                      padding: '12px',
                      fontSize: '0.82rem',
                      fontFamily: 'Consolas, monospace',
                      color: '#a5b4fc',
                      margin: 0,
                      overflowX: 'auto'
                    }}>
                      {b.final_sql}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
