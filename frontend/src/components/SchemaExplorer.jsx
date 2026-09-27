import React, { useState, useEffect } from 'react';
import { 
  Database, Table, Columns, Key, Link2, 
  Search, RefreshCw, ChevronDown, ChevronRight, 
  Info, Sparkles, X, AlertCircle
} from 'lucide-react';
import { api } from '../services/api';

export default function SchemaExplorer({ connectionId, onClose }) {
  const [schemaData, setSchemaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTables, setExpandedTables] = useState({});

  const fetchSchema = async () => {
    if (!connectionId) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.getConnectionSchema(connectionId);
      setSchemaData(data);
      // Auto-expand all tables by default
      const initialExpanded = {};
      if (data?.tables) {
        data.tables.forEach(t => { initialExpanded[t.name] = true; });
      }
      setExpandedTables(initialExpanded);
    } catch (err) {
      setError(err.message || 'Failed to load schema cache.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, [connectionId]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refreshSchema(connectionId);
      await fetchSchema();
    } catch (err) {
      setError(err.message || 'Failed to refresh schema.');
    } finally {
      setRefreshing(false);
    }
  };

  const toggleTable = (tableName) => {
    setExpandedTables(prev => ({
      ...prev,
      [tableName]: !prev[tableName]
    }));
  };

  // Filter tables and columns based on search query
  const filteredTables = schemaData?.tables?.filter(table => {
    const q = searchQuery.toLowerCase();
    const tableMatch = table.name.toLowerCase().includes(q);
    const colMatch = table.columns.some(c => c.name.toLowerCase().includes(q) || (c.ai_description && c.ai_description.toLowerCase().includes(q)));
    return tableMatch || colMatch;
  }) || [];

  return (
    <div style={{
      width: '360px',
      height: '100%',
      background: 'var(--bg-surface)',
      borderLeft: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 20
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={18} color="#818cf8" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700' }}>Schema Explorer</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            title="Refresh Schema Cache"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: 'var(--radius-sm)'
            }}
          >
            <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px'
              }}
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Search Input */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'var(--bg-main)',
          borderRadius: 'var(--radius-md)',
          padding: '6px 10px',
          border: '1px solid var(--border-subtle)'
        }}>
          <Search size={14} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search tables & columns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.825rem',
              width: '100%'
            }}
          />
        </div>
      </div>

      {/* Schema Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <RefreshCw size={20} className="animate-spin" style={{ margin: '0 auto 8px' }} />
            <p>Introspecting database schema...</p>
          </div>
        ) : error ? (
          <div style={{
            background: 'var(--danger-bg)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            padding: '12px',
            borderRadius: 'var(--radius-md)',
            color: '#fca5a5',
            fontSize: '0.825rem'
          }}>
            <AlertCircle size={16} style={{ marginBottom: '4px' }} />
            <p>{error}</p>
          </div>
        ) : filteredTables.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No tables found matching your search.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {filteredTables.map(tbl => (
              <div
                key={tbl.name}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  overflow: 'hidden'
                }}
              >
                {/* Table Header */}
                <div
                  onClick={() => toggleTable(tbl.name)}
                  style={{
                    padding: '10px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    background: expandedTables[tbl.name] ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
                    userSelect: 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {expandedTables[tbl.name] ? <ChevronDown size={14} color="var(--text-muted)" /> : <ChevronRight size={14} color="var(--text-muted)" />}
                    <Table size={15} color="#818cf8" />
                    <span style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {tbl.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', background: 'var(--bg-main)', padding: '2px 6px', borderRadius: '4px' }}>
                    {tbl.columns.length} cols
                  </span>
                </div>

                {/* Columns List */}
                {expandedTables[tbl.name] && (
                  <div style={{ padding: '4px 10px 10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {tbl.columns.map(col => (
                      <div
                        key={col.name}
                        style={{
                          padding: '6px 8px',
                          borderRadius: 'var(--radius-sm)',
                          background: 'rgba(0, 0, 0, 0.2)',
                          border: '1px solid rgba(255, 255, 255, 0.03)'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            {col.is_primary_key ? (
                              <Key size={12} color="#f59e0b" title="Primary Key" />
                            ) : col.is_foreign_key ? (
                              <Link2 size={12} color="#38bdf8" title={`References ${col.references_table}`} />
                            ) : (
                              <Columns size={12} color="var(--text-muted)" />
                            )}
                            <span style={{
                              fontSize: '0.8rem',
                              fontWeight: col.is_primary_key ? '700' : '500',
                              color: col.is_primary_key ? '#fbbf24' : 'var(--text-primary)',
                              fontFamily: 'var(--font-mono)'
                            }}>
                              {col.name}
                            </span>
                          </div>
                          <span style={{
                            fontSize: '0.675rem',
                            color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                            background: 'rgba(255, 255, 255, 0.05)',
                            padding: '1px 5px',
                            borderRadius: '3px'
                          }}>
                            {col.data_type.toLowerCase()}
                          </span>
                        </div>

                        {/* Plain English AI Description */}
                        {col.ai_description && (
                          <div style={{
                            fontSize: '0.725rem',
                            color: 'var(--text-secondary)',
                            lineHeight: 1.35,
                            marginTop: '3px',
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '4px'
                          }}>
                            <Sparkles size={10} color="#818cf8" style={{ marginTop: '2px', flexShrink: 0 }} />
                            <span>{col.ai_description}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
