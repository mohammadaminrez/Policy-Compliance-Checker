import { useState } from 'react';
import { PolicyUpload } from './components/PolicyUpload';
import { UserUpload } from './components/UserUpload';
import { Results } from './components/Results';
import './App.css';

type Tab = 'policy' | 'users' | 'results';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('policy');
  const [policiesFile, setPoliciesFile] = useState<File | null>(null);
  const [usersFile, setUsersFile] = useState<File | null>(null);
  const [triggerEvaluation, setTriggerEvaluation] = useState(false);

  const handlePolicyUploadSuccess = (file: File) => {
    setPoliciesFile(file);
  };

  const handleUserUploadSuccess = (file: File) => {
    setUsersFile(file);
  };

  const handleEvaluate = () => {
    setActiveTab('results');
    setTriggerEvaluation(true);
  };

  const handleEvaluationComplete = () => {
    setTriggerEvaluation(false);
  };

  const canEvaluate = policiesFile !== null && usersFile !== null;

  return (
    <div className="app">
      <header className="header">
        <h1>Policy Compliance Checker</h1>
        <p className="subtitle">Schema-Agnostic Policy Evaluation Engine</p>
      </header>

      <div className="status-bar">
        <div className="status-item">
          <span className="status-label">Policy:</span>
          <span className={`status-value ${policiesFile ? 'uploaded' : ''}`}>
            {policiesFile ? policiesFile.name : 'Not uploaded'}
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Users:</span>
          <span className={`status-value ${usersFile ? 'uploaded' : ''}`}>
            {usersFile ? usersFile.name : 'Not uploaded'}
          </span>
        </div>
        <button
          className="btn-evaluate"
          onClick={handleEvaluate}
          disabled={!canEvaluate}
        >
          Evaluate
        </button>
      </div>

      <nav className="tabs">
        <button
          className={`tab ${activeTab === 'policy' ? 'active' : ''}`}
          onClick={() => setActiveTab('policy')}
        >
          1. Upload Policy
        </button>
        <button
          className={`tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          2. Upload Users
        </button>
        <button
          className={`tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          3. View Results
        </button>
      </nav>

      <main className="content">
        {activeTab === 'policy' && (
          <PolicyUpload onUploadSuccess={handlePolicyUploadSuccess} />
        )}
        {activeTab === 'users' && (
          <UserUpload onUploadSuccess={handleUserUploadSuccess} />
        )}
        {activeTab === 'results' && (
          <Results
            policiesFile={policiesFile}
            usersFile={usersFile}
            triggerEvaluation={triggerEvaluation}
            onEvaluationComplete={handleEvaluationComplete}
          />
        )}
      </main>

      <footer className="footer">
        <p>
          Dynamic policy evaluation - supports any JSON structure | Built with FastAPI + React
        </p>
      </footer>
    </div>
  );
}

export default App;
