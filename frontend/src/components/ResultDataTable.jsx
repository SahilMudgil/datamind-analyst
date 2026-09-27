import React, { useState, useMemo } from 'react';
import { 
  ArrowUpDown, ArrowUp, ArrowDown, Download, Search, 
  ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, FileSpreadsheet
} from 'lucide-react';

export default function ResultDataTable({ data = [], columns = [] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc'); // 'asc' | 'desc'
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Derive column keys if not explicitly provided
  const derivedColumns = useMemo(() => {
    if (columns && columns.length > 0) return columns;
    if (data && data.length > 0) return Object.keys(data[0]);
    return [];
  }, [columns, data]);

  // Handle Sort Toggle
  const handleSort = (col) => {
    if (sortColumn === col) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else {
        setSortColumn(null);
        setSortDirection('asc');
      }
    } else {
      setSortColumn(col);
      setSortDirection('asc');
    }
  };

  // Filtered and Sorted Data
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    let filtered = data;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = data.filter(row => 
        Object.values(row).some(val => 
          String(val ?? '').toLowerCase().includes(term)
        )
      );
    }

    if (sortColumn) {
      filtered = [...filtered].sort((a, b) => {
        const valA = a[sortColumn];
        const valB = b[sortColumn];

        if (valA === valB) return 0;
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;

        if (typeof valA === 'number' && typeof valB === 'number') {
          return sortDirection === 'asc' ? valA - valB : valB - valA;
        }

        const strA = String(valA).toLowerCase();
        const strB = String(valB).toLowerCase();
        return sortDirection === 'asc' 
          ? strA.localeCompare(strB) 
          : strB.localeCompare(strA);
      });
    }

    return filtered;
  }, [data, searchTerm, sortColumn, sortDirection]);

  // Pagination slicing
  const totalRows = processedData.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedData = processedData.slice(startIndex, startIndex + pageSize);

  // CSV Export
  const handleExportCSV = () => {
    if (!data || data.length === 0) return;
    const headerRow = derivedColumns.join(',');
    const rows = processedData.map(row => 
      derivedColumns.map(col => {
        const val = row[col] ?? '';
        const escaped = String(val).replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',')
    );
    const csvContent = "data:text/csv;charset=utf-8," + [headerRow, ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `query_result_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!data || data.length === 0) {
    return (
      <div style={{
        padding: '24px 16px',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: '0.85rem',
        background: 'rgba(0, 0, 0, 0.15)',
        borderRadius: 'var(--radius-sm)',
        border: '1px dashed var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px'
      }}>
        <FileSpreadsheet size={24} style={{ opacity: 0.4 }} />
        <span>No rows returned for this query</span>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      width: '100%'
    }}>
      {/* Table Controls Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px',
        padding: '6px 0'
      }}>
        {/* Search Input */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px 10px',
          minWidth: '200px'
        }}>
          <Search size={13} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search rows..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: '0.78rem',
              outline: 'none',
              width: '100%'
            }}
          />
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {totalRows} {totalRows === 1 ? 'row' : 'rows'} {searchTerm && `(filtered from ${data.length})`}
          </span>

          <button
            onClick={handleExportCSV}
            title="Download CSV spreadsheet"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontSize: '0.725rem',
              fontWeight: '600',
              padding: '4px 8px',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer'
            }}
            onMouseOver={(e) => e.currentTarget.style.color = '#38bdf8'}
            onMouseOut={(e) => e.currentTarget.style.color = 'var(--text-secondary)'}
          >
            <Download size={12} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Table Container */}
      <div style={{
        overflowX: 'auto',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        background: 'rgba(10, 15, 29, 0.6)'
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '0.8rem',
          textAlign: 'left'
        }}>
          <thead>
            <tr style={{
              background: 'rgba(255, 255, 255, 0.03)',
              borderBottom: '1px solid var(--border-medium)'
            }}>
              {derivedColumns.map(col => {
                const isSorted = sortColumn === col;
                return (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    style={{
                      padding: '9px 12px',
                      color: isSorted ? '#818cf8' : 'var(--text-secondary)',
                      fontWeight: '700',
                      cursor: 'pointer',
                      userSelect: 'none',
                      whiteSpace: 'nowrap',
                      transition: 'color 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>{col.replace(/_/g, ' ').toUpperCase()}</span>
                      {isSorted ? (
                        sortDirection === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                      ) : (
                        <ArrowUpDown size={11} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length > 0 ? (
              paginatedData.map((row, idx) => (
                <tr
                  key={idx}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.015)',
                    transition: 'background 0.12s ease'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.06)'}
                  onMouseOut={(e) => e.currentTarget.style.background = idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.015)'}
                >
                  {derivedColumns.map((col, cIdx) => {
                    const val = row[col];
                    const isNum = typeof val === 'number';
                    return (
                      <td
                        key={cIdx}
                        style={{
                          padding: '8px 12px',
                          color: 'var(--text-primary)',
                          fontFamily: isNum ? 'var(--font-mono)' : 'inherit',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        {val === null || val === undefined 
                          ? <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>null</span>
                          : isNum ? val.toLocaleString() : String(val)
                        }
                      </td>
                    );
                  })}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={derivedColumns.length}
                  style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}
                >
                  No matching records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '4px 2px',
          fontSize: '0.75rem',
          color: 'var(--text-muted)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                padding: '2px 6px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.75rem',
                outline: 'none',
                cursor: 'pointer'
              }}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
            <span>Showing {startIndex + 1}-{Math.min(startIndex + pageSize, totalRows)} of {totalRows}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              onClick={() => setPage(1)}
              disabled={currentPage === 1}
              style={{
                padding: '4px',
                background: 'transparent',
                border: 'none',
                color: currentPage === 1 ? 'var(--text-muted)' : 'var(--text-primary)',
                cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                borderRadius: 'var(--radius-sm)'
              }}
              title="First Page"
            >
              <ChevronsLeft size={14} />
            </button>
            <button
              onClick={() => setPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              style={{
                padding: '4px',
                background: 'transparent',
                border: 'none',
                color: currentPage === 1 ? 'var(--text-muted)' : 'var(--text-primary)',
                cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                borderRadius: 'var(--radius-sm)'
              }}
              title="Previous Page"
            >
              <ChevronLeft size={14} />
            </button>

            <span style={{ padding: '0 8px', fontWeight: '600', color: 'var(--text-primary)' }}>
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              style={{
                padding: '4px',
                background: 'transparent',
                border: 'none',
                color: currentPage === totalPages ? 'var(--text-muted)' : 'var(--text-primary)',
                cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                borderRadius: 'var(--radius-sm)'
              }}
              title="Next Page"
            >
              <ChevronRight size={14} />
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={currentPage === totalPages}
              style={{
                padding: '4px',
                background: 'transparent',
                border: 'none',
                color: currentPage === totalPages ? 'var(--text-muted)' : 'var(--text-primary)',
                cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                borderRadius: 'var(--radius-sm)'
              }}
              title="Last Page"
            >
              <ChevronsRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
