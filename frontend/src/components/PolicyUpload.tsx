import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface Policy {
  id: number;
  name: string;
  created_at: string;
  raw: any;
}

interface PolicyUploadProps {
  onUploadSuccess: (file: File) => void;
}

export const PolicyUpload: React.FC<PolicyUploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null);
  const [editName, setEditName] = useState('');
  const [editJsonText, setEditJsonText] = useState('');
  const [saving, setSaving] = useState(false);
  const [jsonValid, setJsonValid] = useState(true);
  const [jsonError, setJsonError] = useState('');
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    setLoading(true);
    try {
      const data = await api.getPolicies();
      setPolicies(data);
    } catch (err) {
      console.error('Failed to load policies', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.json')) {
        setError('Please select a JSON file');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError('');
      setMessage('');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError('');
    setMessage('');

    try {
      const response = await api.uploadPolicy(file);
      setMessage(`Success: ${response.message}`);
      setFile(null);
      onUploadSuccess(file);
      loadPolicies();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload policy');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this policy?')) return;

    try {
      await api.deletePolicy(id);
      loadPolicies();
    } catch (err) {
      setError('Failed to delete policy');
    }
  };

  const openEditor = (policy: Policy) => {
    setEditingPolicy(policy);
    setEditName(policy.name);
    setEditJsonText(JSON.stringify(policy.raw, null, 2));
    setError('');
    setMessage('');
    setEditorOpen(true);
    setJsonValid(true);
    setJsonError('');
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setEditingPolicy(null);
    setEditName('');
    setEditJsonText('');
  };

  const handleSave = async () => {
    if (!editingPolicy) return;
    setSaving(true);
    setError('');
    setMessage('');
    try {
      let parsed: any = null;
      try {
        parsed = JSON.parse(editJsonText);
      } catch (e: any) {
        const msg = 'Invalid JSON: ' + (e?.message || 'Parse error');
        setError(msg);
        setJsonValid(false);
        setJsonError(msg);
        setSaving(false);
        return;
      }

      await api.updatePolicy(editingPolicy.id, { name: editName, raw: parsed });
      setMessage('Policy updated successfully');
      closeEditor();
      loadPolicies();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update policy');
    } finally {
      setSaving(false);
    }
  };

  const handleFormat = () => {
    try {
      const obj = JSON.parse(editJsonText);
      const pretty = JSON.stringify(obj, null, 2);
      setEditJsonText(pretty);
      setJsonValid(true);
      setJsonError('');
    } catch (e: any) {
      setJsonValid(false);
      setJsonError(e?.message || 'Invalid JSON');
    }
  };

  const handleMinify = () => {
    try {
      const obj = JSON.parse(editJsonText);
      const compact = JSON.stringify(obj);
      setEditJsonText(compact);
      setJsonValid(true);
      setJsonError('');
    } catch (e: any) {
      setJsonValid(false);
      setJsonError(e?.message || 'Invalid JSON');
    }
  };

  const handleDownload = () => {
    try {
      const blob = new Blob([editJsonText], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = (editName?.trim() || 'policy') + '.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {}
  };

  const handleLoadFromFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || '');
      setEditJsonText(text);
      try {
        JSON.parse(text);
        setJsonValid(true);
        setJsonError('');
      } catch (err: any) {
        setJsonValid(false);
        setJsonError(err?.message || 'Invalid JSON');
      }
    };
    reader.readAsText(f);
    // reset input value so the same file can be reselected
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!editorOpen) return;
      if (e.key === 'Escape') {
        e.preventDefault();
        closeEditor();
      }
      const isSave = (e.key === 's' || e.key === 'S') && (e.metaKey || e.ctrlKey);
      if (isSave) {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [editorOpen, editJsonText, editName, editingPolicy]);

  return (
    <div className="upload-container">
      <h2>Upload Policy JSON</h2>
      <p className="description">
        Upload a policy file in JSON format. The structure is completely flexible -
        the system will evaluate any valid policy format dynamically.
      </p>

      <div className="file-input-wrapper">
        <input
          type="file"
          accept=".json"
          onChange={handleFileChange}
          disabled={uploading}
          id="policy-file-input"
        />
        <label htmlFor="policy-file-input" className="file-input-label">
          {file ? file.name : 'Choose JSON file'}
        </label>
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="btn-primary"
      >
        {uploading ? 'Uploading...' : 'Upload Policy'}
      </button>

      {message && <div className="message success">{message}</div>}
      {error && <div className="message error">{error}</div>}

      {policies.length > 0 && (
        <div className="policies-list">
          <h3>Uploaded Policies</h3>
          {policies.map((policy) => (
            <div key={policy.id} className="policy-item">
              <div className="policy-info">
                <span className="policy-name">{policy.name}</span>
                <span className="policy-date">
                  {new Date(policy.created_at).toLocaleString()}
                </span>
              </div>
              <div className="policy-actions">
                <button
                  className="btn-secondary"
                  onClick={() => openEditor(policy)}
                >
                  Edit
                </button>
                <button
                  className="btn-delete"
                  onClick={() => handleDelete(policy.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {editorOpen && (
        <div className="modal-backdrop">
          <div className="modal modal-lg">
            <div className="modal-header">
              <h3>Edit Policy</h3>
              <button className="modal-close" onClick={closeEditor}>&times;</button>
            </div>
            <div className="modal-body">
              <label className="input-label">Name</label>
              <input
                type="text"
                className="input-text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
              <label className="input-label">JSON</label>
              <div className="editor-toolbar">
                <div className="left">
                  <button className="btn-secondary" onClick={handleFormat} title="Format (pretty-print)">Format</button>
                  <button className="btn-secondary" onClick={handleMinify} title="Minify JSON">Minify</button>
                  <button className="btn-secondary" onClick={() => fileInputRef.current?.click()} title="Load from file">Load</button>
                  <input ref={fileInputRef} type="file" accept=".json" style={{display:'none'}} onChange={handleLoadFromFile} />
                  <button className="btn-secondary" onClick={handleDownload} title="Download JSON">Download</button>
                </div>
                <div className={`validity ${jsonValid ? 'ok' : 'err'}`}>
                  {jsonValid ? 'JSON valid' : `Invalid JSON: ${jsonError}`}
                </div>
              </div>
              <textarea
                className={`input-textarea code editor-area ${jsonValid ? '' : 'has-error'}`}
                rows={22}
                value={editJsonText}
                onChange={(e) => setEditJsonText(e.target.value)}
              />
              {error && <div className="message error">{error}</div>}
              {message && <div className="message success">{message}</div>}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={closeEditor} disabled={saving}>Cancel</button>
              <button className="btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
