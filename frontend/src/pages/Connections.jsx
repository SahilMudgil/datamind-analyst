import React, { useState, useEffect } from 'react';
import { Trash2 } from 'lucide-react';
import { api } from '../services/api';
import Navigation from '../components/Navigation';
import ConnectDatabaseModal from '../components/ConnectDatabaseModal';
import CSVUploader from '../components/CSVUploader';
import SchemaExplorer from '../components/SchemaExplorer';

export default function Connections() {
  const [connections, setConnections] = useState([]);
  const [selectedConnection, setSelectedConnection] = useState(null);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [showCSVModal, setShowCSVModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchConnections();
  }, []);

  const fetchConnections = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getConnections();
      setConnections(data);
      if (data.length > 0 && !selectedConnection) {
        setSelectedConnection(data[0]);
      }
    } catch (e) {
      console.error('Failed to fetch connections', e);
      setError(e.message || 'Failed to fetch database connections.');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectionCreated = (newConn) => {
    setConnections(prev => [newConn, ...prev]);
    setSelectedConnection(newConn);
    setShowConnectModal(false);
  };

  const handleCSVUploaded = (uploadData) => {
    fetchConnections();
    setShowCSVModal(false);
  };

  const handleDeleteConnection = async (e, connId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to remove this connection?')) return;
    try {
      await api.deleteConnection(connId);
      setConnections(prev => prev.filter(c => c.id !== connId));
      if (selectedConnection?.id === connId) {
        const remaining = connections.filter(c => c.id !== connId);
        setSelectedConnection(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (err) {
      alert('Failed to delete connection: ' + (err.message || 'Unknown error'));
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-main)', color: 'var(--text-primary)' }}>
      <Navigation />

      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 24px' }}>
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
              Database Connections & Schema Catalogs
            </h1>
            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Manage read-only PostgreSQL data sources, CSV tabular imports, and vector schema embeddings.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => setShowCSVModal(true)}
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
              📄 Upload CSV
            </button>

            <button
              onClick={() => setShowConnectModal(true)}
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
              + Connect Database
            </button>
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
              onClick={fetchConnections}
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

        {/* Content Layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
          {/* Connection List Sidebar */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            padding: '20px',
            height: 'fit-content'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', color: 'var(--text-primary)' }}>
              Connected Sources ({connections.length})
            </h3>

            {loading ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading sources...</p>
            ) : connections.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: 1.5 }}>
                No active connections. Click "+ Connect Database" or "Upload CSV" to begin.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {connections.map(c => {
                  const isSelected = selectedConnection?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => setSelectedConnection(c)}
                      style={{
                        padding: '12px',
                        borderRadius: '10px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'rgba(15, 23, 42, 0.5)',
                        border: isSelected ? '1px solid #6366f1' : '1px solid transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <span style={{ fontSize: '1.1rem' }}>
                            {c.db_type === 'csv_import' ? '📄' : '🐘'}
                          </span>
                          <div style={{
                            fontWeight: 600,
                            fontSize: '0.92rem',
                            color: isSelected ? '#fff' : 'var(--text-primary)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {c.display_name}
                          </div>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {c.db_type === 'csv_import' ? 'CSV Import Table' : `${c.host}:${c.port} / ${c.db_name}`}
                        </div>
                      </div>

                      <button
                        onClick={(e) => handleDeleteConnection(e, c.id)}
                        title="Delete connection"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '6px',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          marginLeft: '8px',
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
                        <Trash2 size={16} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Schema Explorer */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            padding: '24px',
            minHeight: '600px'
          }}>
            {selectedConnection ? (
              <SchemaExplorer connectionId={selectedConnection.id} />
            ) : connections.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '80px 24px',
                maxWidth: '480px',
                margin: '0 auto',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '16px'
              }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '16px',
                  background: 'rgba(99, 102, 241, 0.1)',
                  border: '1px solid rgba(99, 102, 241, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '24px'
                }}>
                  🔌
                </div>
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-primary)' }}>
                  No Database Sources Connected
                </h3>
                <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  Connect an existing PostgreSQL database or upload a CSV file. The agent will inspect table columns, generate AI summaries, and compute vector embeddings for schema linking.
                </p>
                <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                  <button
                    onClick={() => setShowConnectModal(true)}
                    style={{
                      background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                      border: 'none',
                      color: '#fff',
                      padding: '8px 18px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    + Connect Database
                  </button>
                  <button
                    onClick={() => setShowCSVModal(true)}
                    style={{
                      background: 'rgba(30, 41, 59, 0.7)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-primary)',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      fontSize: '0.85rem',
                      fontWeight: 500,
                      cursor: 'pointer'
                    }}
                  >
                    📄 Upload CSV
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '100px 0', color: 'var(--text-muted)' }}>
                Select a database source from the left to explore its schema tables and vector embeddings.
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Modals */}
      {showConnectModal && (
        <ConnectDatabaseModal
          onClose={() => setShowConnectModal(false)}
          onConnected={handleConnectionCreated}
        />
      )}

      {showCSVModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            maxWidth: '560px',
            width: '100%',
            padding: '24px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0 }}>Import CSV File</h3>
              <button
                onClick={() => setShowCSVModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>
            <CSVUploader onUploadComplete={handleCSVUploaded} />
          </div>
        </div>
      )}
    </div>
  );
}
