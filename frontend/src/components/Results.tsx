import { useState, useEffect } from 'react';
import { api } from '../services/api';

interface PolicyFileGroup {
  policy_file: string;
  policy_id: number;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  rules: Array<{
    rule: any;
    rule_index: number;
    passed: boolean;
    details: any;
  }>;
}

interface EvaluationResult {
  user_data: any;
  all_passed: boolean;
  total_rules: number;
  passed_rules: number;
  failed_rules: number;
  policy_files: PolicyFileGroup[];
  failed_conditions?: Array<{
    field: string;
    operator: string;
    expected: any;
    actual: any;
  }>;
}

export const Results = () => {
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [expandedPolicies, setExpandedPolicies] = useState<Record<number, Record<string, boolean>>>({});

  const togglePolicyExpand = (rowIndex: number, policyKey: string) => {
    setExpandedPolicies(prev => {
      const row = prev[rowIndex] || {};
      return {
        ...prev,
        [rowIndex]: {
          ...row,
          [policyKey]: !row[policyKey]
        }
      };
    });
  };

  const collectFailedConditions = (details: any): Array<{field: string | null; operator: string | null; expected: any; actual: any; error?: string | null;}> => {
    const failures: Array<{field: string | null; operator: string | null; expected: any; actual: any; error?: string | null;}> = [];
    const walk = (node: any) => {
      if (Array.isArray(node)) {
        node.forEach(walk);
        return;
      }
      if (node && typeof node === 'object') {
        const t = node.type;
        if (t === 'condition') {
          if (!node.passed) {
            failures.push({
              field: node.field ?? null,
              operator: node.operator ?? null,
              expected: node.expected,
              actual: node.actual,
              error: node.error ?? null,
            });
          }
          return;
        }
        if ('conditions' in node) walk(node.conditions);
        if ('condition' in node) walk(node.condition);
      }
    };
    walk(details);
    return failures;
  };

  const [policies, setPolicies] = useState<any[]>([]);
  const [userFiles, setUserFiles] = useState<any[]>([]);
  const [selectedPolicies, setSelectedPolicies] = useState<number[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [policiesData, usersData] = await Promise.all([
        api.getPolicies(),
        api.getUsers()
      ]);
      setPolicies(policiesData);
      setUserFiles(usersData);
      setSelectedPolicies(policiesData.map((p: any) => p.id));
      setSelectedUsers(usersData.map((u: any) => u.id));
    } catch (err) {
      console.error('Failed to load data', err);
    }
  };

  const handlePolicyToggle = (id: number) => {
    setSelectedPolicies(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const handleUserToggle = (id: number) => {
    setSelectedUsers(prev =>
      prev.includes(id) ? prev.filter(u => u !== id) : [...prev, id]
    );
  };

  const handleSelectAllPolicies = () => {
    setSelectedPolicies(selectedPolicies.length === policies.length ? [] : policies.map(p => p.id));
  };

  const handleSelectAllUsers = () => {
    setSelectedUsers(selectedUsers.length === userFiles.length ? [] : userFiles.map(u => u.id));
  };

  const handleEvaluate = async () => {
    if (selectedPolicies.length === 0 || selectedUsers.length === 0) {
      setError('Please select at least one policy and one user file');
      return;
    }

    setEvaluating(true);
    setError('');
    setResults([]);

    try {
      const data = await api.evaluateByIds(selectedPolicies, selectedUsers);
      setResults(data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Evaluation failed');
    } finally {
      setEvaluating(false);
    }
  };

  const getUserLabel = (result: EvaluationResult) => {
    const userData = result.user_data;
    return userData.user_id || userData.id || userData.email || userData.name || 'User';
  };

  const getRuleName = (rule: any, index: number) => {
    return rule.name || rule.title || rule.validation_name || rule.policy_name || `Rule #${index + 1}`;
  };

  const filteredResults = results.filter(r => {
    if (filter === 'passed') return r.all_passed;
    if (filter === 'failed') return !r.all_passed;
    return true;
  });

  const passedCount = results.filter(r => r.all_passed).length;
  const failedCount = results.filter(r => !r.all_passed).length;

  return (
    <div className="results-container">
      <h2>Evaluate Compliance</h2>

      {(policies.length === 0 || userFiles.length === 0) && (
        <div className="empty-state">
          <p>Please upload policies and user data first.</p>
        </div>
      )}

      {policies.length > 0 && userFiles.length > 0 && (
        <div className="selection-section">
          <div className="selection-column">
            <div className="selection-header">
              <h3>Select Policies</h3>
              <button className="btn-select-all" onClick={handleSelectAllPolicies}>
                {selectedPolicies.length === policies.length ? 'Deselect All' : 'Select All'}
              </button>
            </div>
            <div className="selection-list">
              {policies.map(policy => (
                <label key={policy.id} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedPolicies.includes(policy.id)}
                    onChange={() => handlePolicyToggle(policy.id)}
                  />
                  <span>{policy.name}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="selection-column">
            <div className="selection-header">
              <h3>Select User Files</h3>
              <button className="btn-select-all" onClick={handleSelectAllUsers}>
                {selectedUsers.length === userFiles.length ? 'Deselect All' : 'Select All'}
              </button>
            </div>
            <div className="selection-list">
              {userFiles.map(userFile => (
                <label key={userFile.id} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedUsers.includes(userFile.id)}
                    onChange={() => handleUserToggle(userFile.id)}
                  />
                  <span>{userFile.filename} ({userFile.count} users)</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {policies.length > 0 && userFiles.length > 0 && (
        <button
          className="btn-evaluate-large"
          onClick={handleEvaluate}
          disabled={evaluating || selectedPolicies.length === 0 || selectedUsers.length === 0}
        >
          {evaluating ? 'Evaluating...' : 'Evaluate'}
        </button>
      )}

      {error && <div className="message error">{error}</div>}

      {results.length > 0 && (
        <>
          <div className="results-summary">
            <div className="stat">
              <span className="stat-label">Total Users:</span>
              <span className="stat-value">{results.length}</span>
            </div>
            <div className="stat success">
              <span className="stat-label">Passed:</span>
              <span className="stat-value">{passedCount}</span>
            </div>
            <div className="stat error">
              <span className="stat-label">Failed:</span>
              <span className="stat-value">{failedCount}</span>
            </div>
          </div>

          <div className="controls">
            <div className="filter-group">
              <label>Filter:</label>
              <button
                className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                All
              </button>
              <button
                className={`filter-btn ${filter === 'passed' ? 'active' : ''}`}
                onClick={() => setFilter('passed')}
              >
                Passed
              </button>
              <button
                className={`filter-btn ${filter === 'failed' ? 'active' : ''}`}
                onClick={() => setFilter('failed')}
              >
                Failed
              </button>
            </div>
          </div>

          <div className="simple-results-list">
            {filteredResults.map((result, index) => (
              <div
                key={index}
                className={`result-card ${result.all_passed ? 'passed' : 'failed'}`}
              >
                <div className="result-header">
                  <div className="result-info">
                    <span className="result-user">
                      <strong>User:</strong> {getUserLabel(result)}
                    </span>
                    <div className="policy-files-summary">
                      {result.policy_files.map((policyFile, pfIdx) => (
                        <span key={pfIdx} className="policy-file-summary">
                          <strong>{policyFile.policy_file}:</strong> {policyFile.total_rules} rules
                          {' '}({policyFile.passed_rules} passed, {policyFile.failed_rules} failed)
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="result-status-container">
                    <span className={`result-status ${result.all_passed ? 'passed' : 'failed'}`}>
                      {result.all_passed ? '✓ ALL PASSED' : '✗ FAILED'}
                    </span>
                    <button
                      className="btn-details"
                      onClick={() => setExpandedRow(expandedRow === index ? null : index)}
                    >
                      {expandedRow === index ? 'Hide Details' : 'Show Details'}
                    </button>
                  </div>
                </div>

                {expandedRow === index && (
                  <div className="result-details">
                    <div className="details-controls" />
                    <div className="detail-section">
                      <h4>User Data:</h4>
                      <pre>{JSON.stringify(result.user_data, null, 2)}</pre>
                    </div>

                    {result.policy_files.map((policyFile, pfIdx) => {
                        const policyKey = `${policyFile.policy_file}-${pfIdx}`;
                        const isOpen = !!(expandedPolicies[index] && expandedPolicies[index][policyKey]);
                        return (
                          <div key={pfIdx} className="detail-section policy-group">
                            <div
                              className="policy-group-header"
                              onClick={() => togglePolicyExpand(index, policyKey)}
                            >
                              <span className={`caret ${isOpen ? 'open' : ''}`}>▸</span>
                              <span className="policy-file-name">{policyFile.policy_file}</span>
                              <span className="policy-file-counts">
                                {policyFile.total_rules} rules · {policyFile.passed_rules} ✓ · {policyFile.failed_rules} ✗
                              </span>
                            </div>
                            {isOpen && (
                              <div className="policy-group-body">
                                {policyFile.rules.map((ruleResult, rIdx) => (
                                  <div key={rIdx} className={`policy-result ${ruleResult.passed ? 'passed' : 'failed'}`}>
                                    <div className="policy-result-header">
                                      <strong>Rule #{ruleResult.rule_index + 1}:</strong> {getRuleName(ruleResult.rule, ruleResult.rule_index)}
                                      <span className={`policy-status ${ruleResult.passed ? 'passed' : 'failed'}`}>
                                        {ruleResult.passed ? '✓' : '✗'}
                                      </span>
                                    </div>
                                    {(() => {
                                      const failed = collectFailedConditions(ruleResult.details || {});
                                      return failed.length > 0 ? (
                                        <div className="detail-section">
                                          <h4>Failed Conditions ({failed.length}):</h4>
                                          <ul>
                                            {failed.map((cond, i) => (
                                              <li key={i}>
                                                <code>{cond.field}</code> {cond.operator} <code>{JSON.stringify(cond.expected)}</code>
                                                {' '}(actual: <code>{JSON.stringify(cond.actual)}</code>)
                                              </li>
                                            ))}
                                          </ul>
                                        </div>
                                      ) : null;
                                    })()}
                                    <pre>{JSON.stringify(ruleResult.rule, null, 2)}</pre>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
