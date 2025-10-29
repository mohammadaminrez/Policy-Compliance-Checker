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
              <button
                className="btn-delete"
                onClick={() => handleDelete(policy.id)}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
