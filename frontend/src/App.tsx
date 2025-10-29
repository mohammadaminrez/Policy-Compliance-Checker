import { useState } from 'react';
import { PolicyUpload } from './components/PolicyUpload';
import { UserUpload } from './components/UserUpload';
import { Results } from './components/Results';
import './App.css';

type Tab = 'policy' | 'users' | 'results';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('policy');

  return (
    <div className="app">
      <header className="header">
        <h1>Policy Compliance Checker</h1>
        <p className="subtitle">Schema-Agnostic Policy Evaluation Engine</p>
      </header>

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
          <PolicyUpload onUploadSuccess={() => {}} />
        )}
        {activeTab === 'users' && (
          <UserUpload onUploadSuccess={() => {}} />
        )}
        {activeTab === 'results' && (
          <Results />
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
