import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function Navigation() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [usage, setUsage] = useState(null);
  const [showUsageModal, setShowUsageModal] = useState(false);

  useEffect(() => {
    fetchUsageStats();
    const interval = setInterval(fetchUsageStats, 20000);
    return () => clearInterval(interval);
  }, []);

  const fetchUsageStats = async () => {
    try {
      const data = await api.request('/api/analytics/llm-usage');
      setUsage(data);
    } catch (e) {
      // ignore
    }
  };

  return (
    <>
      <header style={{
        height: '64px',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '28px' }}>
          <div
            onClick={() => navigate('/dashboard')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              cursor: 'pointer',
              userSelect: 'none'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(99, 102, 241, 0.35)',
              fontSize: '18px'
            }}>
              🧠
            </div>
            <div>
              <div style={{
                fontSize: '1.1rem',
                fontWeight: 700,
                letterSpacing: '-0.02em',
                background: 'linear-gradient(135deg, #fff 0%, #cbd5e1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                DataMind
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '-2px' }}>
                Agentic SQL Analyst
              </div>
            </div>
          </div>

          {/* Nav Links */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <NavLink
              to="/dashboard"
              style={({ isActive }) => ({
                padding: '8px 14px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 500,
                textDecoration: 'none',
                transition: 'all 0.2s',
                color: (isActive || window.location.pathname === '/' || window.location.pathname === '/chat') ? '#fff' : 'var(--text-secondary)',
                background: (isActive || window.location.pathname === '/' || window.location.pathname === '/chat') ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                border: (isActive || window.location.pathname === '/' || window.location.pathname === '/chat') ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent'
              })}
            >
              📊 Dashboard
            </NavLink>

            <NavLink
              to="/bookmarks"
              style={({ isActive }) => ({
                padding: '8px 14px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 500,
                textDecoration: 'none',
                transition: 'all 0.2s',
                color: isActive ? '#fff' : 'var(--text-secondary)',
                background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                border: isActive ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent'
              })}
            >
              🔖 Saved Queries
            </NavLink>

            <NavLink
              to="/connections"
              style={({ isActive }) => ({
                padding: '8px 14px',
                borderRadius: '8px',
                fontSize: '0.88rem',
                fontWeight: 500,
                textDecoration: 'none',
                transition: 'all 0.2s',
                color: isActive ? '#fff' : 'var(--text-secondary)',
                background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                border: isActive ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent'
              })}
            >
              🗄️ Databases & CSV
            </NavLink>
          </nav>
        </div>

        {/* Right Section: Usage pill & Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {usage && (
            <button
              onClick={() => setShowUsageModal(true)}
              style={{
                background: 'rgba(30, 41, 59, 0.7)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '20px',
                padding: '6px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                transition: 'border-color 0.2s'
              }}
              title="Click to view full LLM Token & Cost Breakdown"
            >
              <span style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#10b981',
                boxShadow: '0 0 8px #10b981'
              }} />
              <span>⚡ {usage.total_tokens.toLocaleString()} tokens</span>
              <span style={{ color: 'var(--text-muted)' }}>|</span>
              <span style={{ color: '#38bdf8' }}>${usage.total_cost_usd.toFixed(4)}</span>
            </button>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              {user?.email}
            </span>
            <button
              onClick={logout}
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                color: '#f87171',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                fontWeight: 500,
                transition: 'all 0.2s'
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Usage Modal */}
      {showUsageModal && usage && (
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
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '520px',
            padding: '24px',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.4rem' }}>⚡</span>
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-primary)' }}>LLM & Token Accounting</h3>
              </div>
              <button
                onClick={() => setShowUsageModal(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '1.2rem',
                  cursor: 'pointer'
                }}
              >
                ✕
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '12px',
              marginBottom: '20px'
            }}>
              <div style={{
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '14px',
                borderRadius: '10px',
                border: '1px solid var(--border-subtle)'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Invocations</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff', marginTop: '4px' }}>
                  {usage.total_calls} calls
                </div>
              </div>

              <div style={{
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '14px',
                borderRadius: '10px',
                border: '1px solid var(--border-subtle)'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Estimated Spend</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
                  ${usage.total_cost_usd.toFixed(4)}
                </div>
              </div>

              <div style={{
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '14px',
                borderRadius: '10px',
                border: '1px solid var(--border-subtle)'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Prompt Input Tokens</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {usage.total_input_tokens.toLocaleString()}
                </div>
              </div>

              <div style={{
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '14px',
                borderRadius: '10px',
                border: '1px solid var(--border-subtle)'
              }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Output Tokens</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {usage.total_output_tokens.toLocaleString()}
                </div>
              </div>
            </div>

            {usage.by_model && usage.by_model.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Breakdown by Model
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {usage.by_model.map((m, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.8rem',
                        padding: '8px 12px',
                        background: 'rgba(15, 23, 42, 0.4)',
                        borderRadius: '6px'
                      }}
                    >
                      <span style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>{m.model}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{m.tokens.toLocaleString()} tokens (${m.cost_usd.toFixed(4)})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
