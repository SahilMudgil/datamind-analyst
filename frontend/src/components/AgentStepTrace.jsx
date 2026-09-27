import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, Clock, AlertTriangle, XCircle, 
  ChevronDown, ChevronRight, Cpu, ShieldCheck, 
  Sparkles, Database, Terminal, BarChart2, RefreshCw, Zap
} from 'lucide-react';

const STEP_METADATA = {
  intent_check: { label: "1. Intent Check & Context Resolution", icon: Sparkles, color: "#818cf8" },
  schema_linker: { label: "2. Vector Schema Linking (Top-K)", icon: Database, color: "#38bdf8" },
  sql_generator: { label: "3. SQL Generation (Structured)", icon: Terminal, color: "#c084fc" },
  safety_validator: { label: "4. AST Safety & Guardrail Check", icon: ShieldCheck, color: "#10b981" },
  execution: { label: "5. Sandboxed Target DB Execution", icon: Cpu, color: "#f59e0b" },
  self_correction: { label: "6. Autonomous Error Reflection", icon: RefreshCw, color: "#ef4444" },
  data_analysis: { label: "7. Trend & Statistical Analysis", icon: BarChart2, color: "#06b6d4" },
  result_explainer: { label: "8. Executive Insight Synthesis", icon: Sparkles, color: "#10b981" }
};

export default function AgentStepTrace({ steps = [], isLive = false }) {
  const [isOpen, setIsOpen] = useState(isLive);
  const [expandedStep, setExpandedStep] = useState(null);

  // Keep open when streaming live
  useEffect(() => {
    if (isLive) setIsOpen(true);
  }, [isLive]);

  if (!steps || steps.length === 0) return null;

  const totalDuration = steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0);

  return (
    <div style={{
      marginTop: '12px',
      background: 'rgba(5, 10, 24, 0.5)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      boxShadow: '0 2px 10px rgba(0, 0, 0, 0.2)'
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
          background: isOpen ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
          userSelect: 'none',
          transition: 'background 0.15s ease'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={14} color="#818cf8" />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-secondary)' }}>
            Agent Reasoning Pipeline ({steps.length} {steps.length === 1 ? 'step' : 'steps'})
          </span>

          {isLive && (
            <span className="badge badge-primary" style={{ fontSize: '0.65rem', padding: '1px 8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{
                display: 'inline-block',
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: '#38bdf8',
                boxShadow: '0 0 8px #38bdf8'
              }} />
              Streaming Live
            </span>
          )}

          {!isLive && totalDuration > 0 && (
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              ({Math.round(totalDuration)}ms total)
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
          <span style={{ fontSize: '0.725rem' }}>{isOpen ? 'Collapse' : 'Expand trace'}</span>
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </div>

      {/* Step items list */}
      {isOpen && (
        <div style={{ padding: '8px 12px 12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {steps.map((step, idx) => {
            const rawName = step.step_name || "";
            const meta = STEP_METADATA[rawName] || { label: rawName, icon: Cpu, color: "#94a3b8" };
            const Icon = meta.icon;
            const isExpanded = expandedStep === idx;
            const duration = step.duration_ms ? `${Math.round(step.duration_ms)}ms` : "";

            return (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden'
                }}
              >
                <div
                  onClick={() => setExpandedStep(isExpanded ? null : idx)}
                  style={{
                    padding: '7px 10px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    transition: 'background 0.12s ease'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {step.status === 'completed' ? (
                      <CheckCircle2 size={13} color="#10b981" />
                    ) : step.status === 'failed' ? (
                      <XCircle size={13} color="#ef4444" />
                    ) : (
                      <Clock size={13} color="#f59e0b" />
                    )}
                    <Icon size={13} color={meta.color} />
                    <span style={{ fontSize: '0.775rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {meta.label}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {duration && (
                      <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {duration}
                      </span>
                    )}
                    {isExpanded ? <ChevronDown size={12} color="var(--text-muted)" /> : <ChevronRight size={12} color="var(--text-muted)" />}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && step.details && (
                  <div style={{
                    padding: '8px 12px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.04)',
                    background: 'rgba(0, 0, 0, 0.35)',
                    fontSize: '0.725rem',
                    fontFamily: 'var(--font-mono)',
                    color: '#94a3b8',
                    overflowX: 'auto'
                  }}>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>
                      {typeof step.details === 'string' ? step.details : JSON.stringify(step.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
