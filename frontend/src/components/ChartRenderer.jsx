import React, { useState } from 'react';
import { 
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, Legend, CartesianGrid 
} from 'recharts';
import { BarChart3, Table as TableIcon, Sparkles, TrendingUp, TrendingDown } from 'lucide-react';
import ResultDataTable from './ResultDataTable';

const DEFAULT_COLORS = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#3b82f6"];

const formatYTick = (val) => {
  if (typeof val !== 'number') return val;
  const abs = Math.abs(val);
  if (abs >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(val / 1_000).toFixed(0)}k`;
  return val.toLocaleString();
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'rgba(15, 23, 42, 0.95)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: 'var(--radius-md)',
        padding: '10px 14px',
        boxShadow: 'var(--shadow-md)',
        backdropFilter: 'blur(10px)',
        fontSize: '0.8rem'
      }}>
        {label && <div style={{ fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>{label}</div>}
        {payload.map((entry, index) => (
          <div key={`item-${index}`} style={{ display: 'flex', alignItems: 'center', gap: '6px', color: entry.color || '#38bdf8' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: entry.color || '#38bdf8' }} />
            <span style={{ color: 'var(--text-secondary)' }}>{entry.name}:</span>
            <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
              {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function ChartRenderer({ chartType, chartConfig, data = [] }) {
  const [viewMode, setViewMode] = useState('chart'); // 'chart' | 'table'

  if (!data || data.length === 0) return null;

  // 1. Stat Card Render
  if (chartType === 'stat_card') {
    const title = chartConfig?.title || 'Result';
    const rawVal = chartConfig?.value || (data[0] ? Object.values(data[0])[0] : '0');
    const formattedVal = typeof rawVal === 'number' ? rawVal.toLocaleString() : String(rawVal);
    const trend = chartConfig?.trend; // Optional { direction: 'up' | 'down', percentage: 12.5 }

    return (
      <div style={{
        margin: '14px 0',
        padding: '24px 28px',
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(6, 182, 212, 0.06) 100%)',
        border: '1px solid var(--border-focus)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 0 24px var(--primary-glow)',
        textAlign: 'center',
        position: 'relative'
      }}>
        <div style={{
          fontSize: '0.825rem',
          fontWeight: '700',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
          letterSpacing: '0.06em',
          marginBottom: '8px'
        }}>
          {title}
        </div>
        <div style={{
          fontSize: '2.6rem',
          fontWeight: '800',
          color: '#ffffff',
          letterSpacing: '-0.02em',
          lineHeight: 1.1
        }}>
          {formattedVal}
        </div>

        {trend && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            marginTop: '10px',
            fontSize: '0.8rem',
            fontWeight: '600',
            padding: '3px 10px',
            borderRadius: 'var(--radius-sm)',
            background: trend.direction === 'up' ? 'var(--success-bg)' : 'var(--danger-bg)',
            color: trend.direction === 'up' ? '#10b981' : '#f87171'
          }}>
            {trend.direction === 'up' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            <span>{trend.percentage > 0 ? `+${trend.percentage}%` : `${trend.percentage}%`} period-over-period</span>
          </div>
        )}
      </div>
    );
  }

  const colors = chartConfig?.colors || DEFAULT_COLORS;
  
  // Intelligently resolve the category/dimension (X axis) and metric/measure (Y axis)
  const resolvedXKey = chartConfig?.xKey || chartConfig?.xAxis || chartConfig?.nameKey || (
    Object.keys(data[0] || {}).find(k => typeof data[0][k] === 'string') || Object.keys(data[0] || {})[0]
  );

  let resolvedYKeys = chartConfig?.yKeys || (chartConfig?.yAxis ? [chartConfig.yAxis] : (chartConfig?.dataKey ? [chartConfig.dataKey] : null));
  if (!resolvedYKeys || resolvedYKeys.length === 0) {
    const numericKeys = Object.keys(data[0] || {}).filter(k => k !== resolvedXKey && typeof data[0][k] === 'number');
    resolvedYKeys = numericKeys.length > 0 
      ? numericKeys 
      : [Object.keys(data[0] || {}).find(k => k !== resolvedXKey) || Object.keys(data[0] || {})[1] || Object.keys(data[0] || {})[0]];
  }

  return (
    <div style={{
      margin: '14px 0',
      padding: '16px',
      background: 'rgba(0, 0, 0, 0.25)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)'
    }}>
      {/* Chart Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
        paddingBottom: '10px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div style={{ fontSize: '0.875rem', fontWeight: '700', color: 'var(--text-primary)' }}>
          {chartConfig?.title || 'Data Visualization'}
        </div>

        <div style={{ display: 'flex', gap: '4px', background: 'rgba(0, 0, 0, 0.3)', padding: '3px', borderRadius: 'var(--radius-sm)' }}>
          <button
            onClick={() => setViewMode('chart')}
            style={{
              padding: '4px 10px',
              border: 'none',
              background: viewMode === 'chart' ? 'var(--primary)' : 'transparent',
              color: viewMode === 'chart' ? '#ffffff' : 'var(--text-muted)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.75rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              transition: 'all 0.15s ease'
            }}
          >
            <BarChart3 size={13} /> Visual Chart
          </button>
          <button
            onClick={() => setViewMode('table')}
            style={{
              padding: '4px 10px',
              border: 'none',
              background: viewMode === 'table' ? 'var(--primary)' : 'transparent',
              color: viewMode === 'table' ? '#ffffff' : 'var(--text-muted)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.75rem',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              transition: 'all 0.15s ease'
            }}
          >
            <TableIcon size={13} /> Data Table ({data.length})
          </button>
        </div>
      </div>

      {/* View Mode: Interactive Data Table */}
      {viewMode === 'table' ? (
        <ResultDataTable data={data} />
      ) : (
        /* View Mode: Interactive Recharts */
        <div style={{ width: '100%', height: 290 }}>
          {chartType === 'line' ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 12, right: 24, left: 16, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
                <XAxis dataKey={resolvedXKey} stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={formatYTick} width={64} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                {resolvedYKeys.map((key, i) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={colors[i % colors.length]}
                    strokeWidth={2.5}
                    dot={{ fill: colors[i % colors.length], r: 3 }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : chartType === 'area' ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 12, right: 24, left: 16, bottom: 8 }}>
                <defs>
                  {resolvedYKeys.map((key, i) => (
                    <linearGradient key={`grad-${key}`} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={colors[i % colors.length]} stopOpacity={0.5} />
                      <stop offset="95%" stopColor={colors[i % colors.length]} stopOpacity={0.02} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
                <XAxis dataKey={resolvedXKey} stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={formatYTick} width={64} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                {resolvedYKeys.map((key, i) => (
                  <Area
                    key={key}
                    type="monotone"
                    dataKey={key}
                    stroke={colors[i % colors.length]}
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill={`url(#grad-${key})`}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          ) : chartType === 'pie' ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 10, bottom: 10 }}>
                <Tooltip content={<CustomTooltip />} />
                <Legend 
                  wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
                  formatter={(val) => <span style={{ color: 'var(--text-secondary)' }}>{val}</span>} 
                />
                <Pie
                  data={data}
                  nameKey={resolvedXKey}
                  dataKey={resolvedYKeys[0]}
                  cx="50%"
                  cy="45%"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={4}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  labelLine={true}
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          ) : (
            /* Bar Chart Default */
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 12, right: 24, left: 16, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
                <XAxis dataKey={resolvedXKey} stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={formatYTick} width={64} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                {resolvedYKeys.map((key, i) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    fill={colors[i % colors.length]}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  );
}
