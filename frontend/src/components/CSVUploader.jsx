import React, { useState, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function CSVUploader({ isOpen, onClose, onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [customTableName, setCustomTableName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const selected = e.dataTransfer.files[0];
      if (selected.name.toLowerCase().endsWith('.csv')) {
        setFile(selected);
        setCustomTableName(selected.name.replace(/\.[^/.]+$/, '').toLowerCase().replace(/[^a-z0-9]/g, '_'));
        setError('');
      } else {
        setError('Please drop a valid .csv spreadsheet file.');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0];
      setFile(selected);
      setCustomTableName(selected.name.replace(/\.[^/.]+$/, '').toLowerCase().replace(/[^a-z0-9]/g, '_'));
      setError('');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a CSV file first.');
      return;
    }

    setUploading(true);
    setError('');
    setUploadResult(null);

    try {
      const res = await api.uploadCSV(file, customTableName);
      setUploadResult(res);
      if (onUploadComplete) {
        onUploadComplete(res);
      }
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err.message || 'CSV upload failed.');
    } finally {
      setUploading(false);
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
        maxWidth: '480px',
        width: '100%',
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
            background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <FileSpreadsheet size={22} color="#ffffff" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '800' }}>Import CSV Spreadsheet</h2>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
              Automatically convert any spreadsheet into a queryable SQL table
            </p>
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

        {uploadResult && (
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
            <span>Imported {uploadResult.row_count} rows across {uploadResult.column_count} columns into table '{uploadResult.table_name}'!</span>
          </div>
        )}

        <form onSubmit={handleUpload}>
          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '2px dashed var(--border-medium)',
              borderRadius: 'var(--radius-md)',
              padding: '32px 20px',
              textAlign: 'center',
              cursor: 'pointer',
              background: file ? 'rgba(99, 102, 241, 0.05)' : 'rgba(0, 0, 0, 0.2)',
              borderColor: file ? 'var(--primary)' : 'var(--border-medium)',
              marginBottom: '20px',
              transition: 'all 0.2s ease'
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".csv"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <UploadCloud size={36} color={file ? '#818cf8' : 'var(--text-muted)'} style={{ margin: '0 auto 10px' }} />
            {file ? (
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                  {file.name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {(file.size / 1024).toFixed(1)} KB — Click to change file
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--text-primary)' }}>
                  Click to browse or drop CSV here
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Supports comma-separated values (.csv)
                </div>
              </div>
            )}
          </div>

          {file && (
            <div className="input-group">
              <label className="input-label">Custom SQL Table Name (Optional)</label>
              <input
                type="text"
                className="input-field"
                value={customTableName}
                onChange={(e) => setCustomTableName(e.target.value)}
                placeholder="e.g. sales_transactions"
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={!file || uploading}
            style={{ width: '100%', padding: '12px', marginTop: '12px' }}
          >
            {uploading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Parsing & Creating Table...
              </>
            ) : (
              'Import & Introspect CSV'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
