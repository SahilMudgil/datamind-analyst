import React, { useState } from 'react';
import { Database, ShieldCheck, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function ConnectDatabaseModal({ isOpen, onClose, onConnectionCreated }) {
  const [formData, setFormData] = useState({
    display_name: 'E-commerce Sandbox',
    host: 'localhost',
    port: 5433,
    db_name: 'ecommerce_db',
    username: 'readonly_agent',
    password: 'readonly_secure_pass',
    db_type: 'postgresql'
  });

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'port' ? parseInt(value) || '' : value
    }));
    setTestResult(null);
    setError('');
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setError('');
    try {
      const res = await api.testConnection({
        db_type: formData.db_type,
        host: formData.host,
        port: Number(formData.port),
        db_name: formData.db_name,
        username: formData.username,
        password: formData.password
      });
      setTestResult(res);
    } catch (err) {
      setError(err.message || 'Connection test failed.');
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const res = await api.createConnection({
        ...formData,
        port: Number(formData.port)
      });
      if (onConnectionCreated) {
        onConnectionCreated(res);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save database connection.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{
        maxWidth: '520px',
        width: '100%',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '28px',
        position: 'relative'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px'
          }}
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Database size={22} color="#ffffff" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800' }}>Connect Database</h2>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
              Provide credentials for your target relational database
            </p>
          </div>
        </div>

        {/* Security Notice */}
        <div style={{
          background: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          borderRadius: 'var(--radius-md)',
          padding: '12px',
          marginBottom: '20px',
          display: 'flex',
          gap: '10px'
        }}>
          <ShieldCheck size={20} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '0.78rem', color: '#a7f3d0', lineHeight: 1.4 }}>
            <strong>Security Guardrail:</strong> Use a dedicated read-only database role. Destructive queries (DROP, INSERT, UPDATE) are AST-blocked.
          </div>
        </div>

        {error && (
          <div style={{
            background: 'var(--danger-bg)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            padding: '12px',
            borderRadius: 'var(--radius-md)',
            color: '#fca5a5',
            fontSize: '0.825rem',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        )}

        {testResult && testResult.success && (
          <div style={{
            background: 'var(--success-bg)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            padding: '12px',
            borderRadius: 'var(--radius-md)',
            color: '#6ee7b7',
            fontSize: '0.825rem',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <CheckCircle2 size={16} color="#10b981" />
            <span>Connection verified! Found {testResult.tables_found} tables ({testResult.tables?.slice(0, 3).join(', ')}...)</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="input-group">
              <label className="input-label">Database Engine</label>
              <select
                name="db_type"
                className="input-field"
                value={formData.db_type}
                onChange={(e) => {
                  const val = e.target.value;
                  setFormData(prev => ({
                    ...prev,
                    db_type: val,
                    port: val === 'mysql' ? 3306 : 5432
                  }));
                  setTestResult(null);
                  setError('');
                }}
                style={{ cursor: 'pointer' }}
              >
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
              </select>
            </div>

            <div className="input-group">
              <label className="input-label">Display Name</label>
              <input
                type="text"
                name="display_name"
                className="input-field"
                value={formData.display_name}
                onChange={handleChange}
                placeholder="e.g. Sales Production DB"
                required
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
            <div className="input-group">
              <label className="input-label">Host</label>
              <input
                type="text"
                name="host"
                className="input-field"
                value={formData.host}
                onChange={handleChange}
                placeholder="localhost"
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Port</label>
              <input
                type="number"
                name="port"
                className="input-field"
                value={formData.port}
                onChange={handleChange}
                placeholder="5432"
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Database Name</label>
            <input
              type="text"
              name="db_name"
              className="input-field"
              value={formData.db_name}
              onChange={handleChange}
              placeholder="ecommerce_db"
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="input-group">
              <label className="input-label">Username</label>
              <input
                type="text"
                name="username"
                className="input-field"
                value={formData.username}
                onChange={handleChange}
                placeholder="readonly_agent"
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Password</label>
              <input
                type="password"
                name="password"
                className="input-field"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••••••"
                required
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleTestConnection}
              disabled={testing || saving}
              style={{ flex: 1 }}
            >
              {testing ? <><Loader2 size={16} className="animate-spin" /> Testing...</> : 'Test Connection'}
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
              style={{ flex: 1 }}
            >
              {saving ? <><Loader2 size={16} className="animate-spin" /> Saving...</> : 'Save & Introspect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
