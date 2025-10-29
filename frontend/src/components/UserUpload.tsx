import React, { useState } from 'react';
import { api } from '../services/api';

interface UserUploadProps {
  onUploadSuccess: (file: File) => void;
}

export const UserUpload: React.FC<UserUploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const isValid =
        selectedFile.name.endsWith('.csv') ||
        selectedFile.name.endsWith('.json');

      if (!isValid) {
        setError('Please select a CSV or JSON file');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError('');
      setMessage('');
      setPreview(null);
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
      const response = await api.uploadUsers(file);
      setMessage(`Success: Parsed ${response.count} user records`);
      setPreview(response.users.slice(0, 5)); // Show first 5 users
      onUploadSuccess(file);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload users');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <h2>Upload User Data</h2>
      <p className="description">
        Upload user data in CSV or JSON format. Any structure is supported -
        the system will match fields dynamically against policy rules.
      </p>

      <div className="file-input-wrapper">
        <input
          type="file"
          accept=".csv,.json"
          onChange={handleFileChange}
          disabled={uploading}
          id="users-file-input"
        />
        <label htmlFor="users-file-input" className="file-input-label">
          {file ? file.name : 'Choose CSV or JSON file'}
        </label>
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="btn-primary"
      >
        {uploading ? 'Uploading...' : 'Upload Users'}
      </button>

      {message && <div className="message success">{message}</div>}
      {error && <div className="message error">{error}</div>}

      {preview && (
        <div className="preview-box">
          <h3>Preview (first 5 records):</h3>
          <pre>{JSON.stringify(preview, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
