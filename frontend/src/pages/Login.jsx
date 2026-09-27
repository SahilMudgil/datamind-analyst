import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Database, ShieldCheck, Cpu, Terminal, ArrowRight, Sparkles } from 'lucide-react';

export default function Login() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isRegister) {
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background Decorative Ambient Gradients */}
      <div style={{
        position: 'absolute',
        top: '-15%',
        left: '20%',
        width: '500px',
        height: '500px',
        background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
        borderRadius: '50%',
        pointerEvents: 'none',
        filter: 'blur(40px)'
      }} />
      <div style={{
        position: 'absolute',
        bottom: '-15%',
        right: '15%',
        width: '600px',
        height: '600px',
        background: 'radial-gradient(circle, rgba(6, 182, 212, 0.12) 0%, transparent 70%)',
        borderRadius: '50%',
        pointerEvents: 'none',
        filter: 'blur(50px)'
      }} />

      <div style={{
        width: '100%',
        maxWidth: '440px',
        zIndex: 1
      }}>
        {/* Logo & Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '64px',
            height: '64px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(139,92,246,0.2) 100%)',
            border: '1px solid rgba(99,102,241,0.4)',
            boxShadow: '0 0 24px rgba(99,102,241,0.25)',
            marginBottom: '16px'
          }}>
            <Database size={32} color="#818cf8" />
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: '800', letterSpacing: '-0.02em', marginBottom: '8px' }}>
            Data<span style={{ color: '#818cf8' }}>Mind</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Agentic Text-to-SQL Data Analyst
          </p>
        </div>

        {/* Auth Glass Card */}
        <div className="glass-panel glow-card" style={{ padding: '32px' }}>
          {/* Tabs */}
          <div style={{
            display: 'flex',
            background: 'rgba(0, 0, 0, 0.3)',
            padding: '4px',
            borderRadius: 'var(--radius-md)',
            marginBottom: '24px',
            border: '1px solid var(--border-subtle)'
          }}>
            <button
              type="button"
              onClick={() => { setIsRegister(false); setError(''); }}
              style={{
                flex: 1,
                padding: '8px 12px',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                background: !isRegister ? 'var(--primary)' : 'transparent',
                color: !isRegister ? '#ffffff' : 'var(--text-secondary)',
                fontWeight: '600',
                fontSize: '0.875rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsRegister(true); setError(''); }}
              style={{
                flex: 1,
                padding: '8px 12px',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                background: isRegister ? 'var(--primary)' : 'transparent',
                color: isRegister ? '#ffffff' : 'var(--text-secondary)',
                fontWeight: '600',
                fontSize: '0.875rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div style={{
              background: 'var(--danger-bg)',
              color: '#fca5a5',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.875rem',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              marginBottom: '18px'
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {isRegister && (
              <div className="input-group">
                <label className="input-label">Full Name</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Alex Mercer"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required={isRegister}
                />
              </div>
            )}

            <div className="input-group">
              <label className="input-label">Email Address</label>
              <input
                type="email"
                className="input-field"
                placeholder="analyst@enterprise.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="input-group" style={{ marginBottom: '24px' }}>
              <label className="input-label">Password</label>
              <input
                type="password"
                className="input-field"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px' }}
              disabled={loading}
            >
              {loading ? 'Authenticating...' : (
                <>
                  {isRegister ? 'Get Started' : 'Enter Workspace'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* System Capabilities Pill Badges */}
          <div style={{
            marginTop: '28px',
            paddingTop: '20px',
            borderTop: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <ShieldCheck size={16} color="#10b981" />
              <span>AST Safety Parsing with Read-Only Sandboxing</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <Cpu size={16} color="#6366f1" />
              <span>LangGraph Self-Correcting Execution Engine</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
