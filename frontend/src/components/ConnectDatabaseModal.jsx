import React, { useState } from 'react';
import { Database, ShieldCheck, CheckCircle2, AlertCircle, X, Loader2, Sparkles, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

const isCloud = typeof window !== 'undefined' && 
  !window.location.hostname.includes('localhost') && 
  !window.location.hostname.includes('127.0.0.1');

const DEMO_CLOUD_CONFIG = {
  display_name: 'E-commerce Cloud Store (PostgreSQL)',
  host: 'ep-small-darkness-b4sn8qbx.c-6.us-east-2.aws.neon.tech',
  port: 5432,
  db_name: 'neondb',
  username: 'neondb_owner',
  password: 'npg_vxaIl9DM8tYy',
  db_type: 'postgresql'
};

const LOCAL_SANDBOX_CONFIG = {
  display_name: 'E-commerce Sandbox (Local)',
  host: 'localhost',
  port: 5433,
  db_name: 'ecommerce_db',
  username: 'readonly_agent',
  password: 'readonly_secure_pass',
  db_type: 'postgresql'
};

export default function ConnectDatabaseModal({ isOpen, onClose, onConnectionCreated }) {
  const [formData, setFormData] = useState(isCloud ? DEMO_CLOUD_CONFIG : LOCAL_SANDBOX_CONFIG);
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

  const handleFillDemo = () => {
    setFormData(DEMO_CLOUD_CONFIG);
    setTestResult(null);
    setError('');
  };

  const handleClear = () => {
    setFormData({
      display_name: '',
      host: '',
      port: 5432,
      db_name: '',
      username: '',
      password: '',
      db_type: 'postgresql'
    });
    setTestResult(null);
    setError('');
  };

  const handleTestConnection = async () => {
    if (isCloud && (formData.host === 'localhost' || formData.host === '127.0.0.1')) {
      setError('Notice: "localhost" points to your personal PC. Since you are using the live cloud website, please click "Load Cloud Demo DB" above to test our live sample database, or enter your remote cloud database host (AWS RDS, Neon, Supabase, Aiven).');
      return;
    }
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
    if (isCloud && (formData.host === 'localhost' || formData.host === '127.0.0.1')) {
      setError('Notice: "localhost" points to your personal PC. Since you are using the live cloud website, please click "Load Cloud Demo DB" above or enter a cloud database host.');
      return;
    }
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
        maxWidth: '540px',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
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
              Connect a PostgreSQL or MySQL relational database for AI analytics
            </p>
          </div>
        </div>

        {/* 1-Click Demo DB Banner for Cloud Mode */}
        {isCloud && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(168, 85, 247, 0.12))',
            border: '1px solid rgba(139, 92, 246, 0.35)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px'
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                <Sparkles size={16} color="#c084fc" />
                <span style={{ fontSize: '0.84rem', fontWeight: '700', color: '#e9d5ff' }}>
                  1-Click Sample Cloud Database
                </span>
              </div>
              <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.35 }}>
                Testing the live demo? Pre-fill our 5-table E-Commerce PostgreSQL database with one click.
              </p>
            </div>
            <button
              type="button"
              onClick={handleFillDemo}
              className="btn btn-secondary"
              style={{
                padding: '6px 12px',
                fontSize: '0.78rem',
                whiteSpace: 'nowrap',
                background: 'rgba(139, 92, 246, 0.25)',
                border: '1px solid rgba(168, 85, 247, 0.5)',
                color: '#ffffff',
                cursor: 'pointer'
              }}
            >
              Fill Demo DB
            </button>
          </div>
        )}

        {/* Security Notice */}
        <div style={{
          background: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          borderRadius: 'var(--radius-md)',
          padding: '10px 12px',
          marginBottom: '16px',
          display: 'flex',
          gap: '10px'
        }}>
          <ShieldCheck size={18} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '0.76rem', color: '#a7f3d0', lineHeight: 1.35 }}>
            <strong>Security Guardrail:</strong> Dedicated read-only role recommended. Destructive queries (DROP, INSERT, UPDATE, DELETE) are AST-blocked automatically.
          </div>
        </div>

        {error && (
          <div style={{
            background: 'var(--danger-bg)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            padding: '12px',
            borderRadius: 'var(--radius-md)',
            color: '#fca5a5',
            fontSize: '0.8rem',
            marginBottom: '16px',
            lineHeight: 1.4
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
            <span>Connection verified successfully! Ready to introspect schema.</span>
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
                placeholder="e.g. Sales Database"
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
                placeholder={isCloud ? "e.g. ep-xyz.aws.neon.tech or aws-rds.com" : "localhost"}
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
                placeholder={formData.db_type === 'mysql' ? '3306' : '5432'}
                required
              />
            </div>
          </div>

          {isCloud && (formData.host === 'localhost' || formData.host === '127.0.0.1') && (
            <div style={{
              fontSize: '0.75rem',
              color: '#93c5fd',
              marginBottom: '14px',
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              padding: '8px 12px',
              borderRadius: 'var(--radius-md)',
              lineHeight: 1.4
            }}>
              💡 <strong>Want to connect a local PC database (MySQL / Postgres)?</strong><br />
              • To connect <code>localhost</code> directly, run DataMind locally on your PC (double-click <code>start_local.bat</code> and open <code>http://localhost:3000</code>).<br />
              • Or click <strong>Fill Demo DB</strong> above to test our live sample database right now!
            </div>
          )}

          {!isCloud && (
            <div style={{
              fontSize: '0.75rem',
              color: '#6ee7b7',
              marginBottom: '14px',
              lineHeight: 1.4
            }}>
              ⚡ <strong>Local mode active:</strong> You can connect directly to your local PC's MySQL (<code>localhost:3306</code>) or PostgreSQL (<code>localhost:5432 / 5433</code>).
            </div>
          )}

          <div className="input-group">
            <label className="input-label">Database Name</label>
            <input
              type="text"
              name="db_name"
              className="input-field"
              value={formData.db_name}
              onChange={handleChange}
              placeholder="e.g. neondb or ecommerce_db"
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
                placeholder="e.g. postgres or root"
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

          <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
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
              {saving ? <><Loader2 size={16} className="animate-spin" /> Saving & Introspecting...</> : 'Save & Introspect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
