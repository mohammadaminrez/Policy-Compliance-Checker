import React, { useState } from 'react';
import { api } from '../services/api';

interface PolicyUploadProps {
  onUploadSuccess: (file: File) => void;
}

export const PolicyUpload: React.FC<PolicyUploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

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
      onUploadSuccess(file);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload policy');
    } finally {
      setUploading(false);
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
    </div>
  );
};
