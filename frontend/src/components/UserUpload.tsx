import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface UserFile {
  id: number;
  filename: string;
  count: number;
  uploaded_at: string;
}

interface UserUploadProps {
  onUploadSuccess: (file: File) => void;
}

export const UserUpload: React.FC<UserUploadProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [userFiles, setUserFiles] = useState<UserFile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadUserFiles();
  }, []);

  const loadUserFiles = async () => {
    setLoading(true);
    try {
      const data = await api.getUsers();
      setUserFiles(data);
    } catch (err) {
      console.error('Failed to load user files', err);
    } finally {
      setLoading(false);
    }
  };

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
      setMessage(`Success: ${response.count} users uploaded`);
      setFile(null);
      onUploadSuccess(file);
      loadUserFiles();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload users');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this user data?')) return;

    try {
      await api.deleteUser(id);
      loadUserFiles();
    } catch (err) {
      setError('Failed to delete user data');
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

      {userFiles.length > 0 && (
        <div className="policies-list">
          <h3>Uploaded User Files</h3>
          {userFiles.map((userFile) => (
            <div key={userFile.id} className="policy-item">
              <div className="policy-info">
                <span className="policy-name">{userFile.filename}</span>
                <span className="policy-date">
                  {userFile.count} users • {new Date(userFile.uploaded_at).toLocaleString()}
                </span>
              </div>
              <button
                className="btn-delete"
                onClick={() => handleDelete(userFile.id)}
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
