import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import { EvaluationResult, ResultContext, ConditionSummary } from '../types';

export const Results: React.FC = () => {
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [sortField, setSortField] = useState<string>('user_index');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const [policies, setPolicies] = useState<any[]>([]);
  const [userFiles, setUserFiles] = useState<any[]>([]);
  const [selectedPolicies, setSelectedPolicies] = useState<number[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);

  const humanizeKey = (key: string) =>
    key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const formatEntityMeta = (context: ResultContext | undefined, fallback: string) => {
    if (!context) {
      return fallback;
    }

    const parts: string[] = [];
    const source = context.source || fallback;
    if (source) {
      parts.push(source);
    }
    if (context.filename && context.filename !== source) {
      parts.push(context.filename);
    }
    if (typeof context.record_id === 'number') {
      parts.push(`Record ${context.record_id}`);
    }
    if (typeof context.record_position === 'number') {
      parts.push(`Row ${context.record_position + 1}`);
    }
    if (typeof context.section === 'string') {
      parts.push(`Section ${humanizeKey(context.section)}`);
    }
    if (typeof context.position === 'number') {
      parts.push(`Rule ${context.position + 1}`);
    }

    return parts.join(' • ') || fallback;
  };

  const formatEntityLabel = (
    context: ResultContext | undefined,
    fallbackPrefix: string,
    fallbackIndex: number
  ) => {
    if (context?.label) {
      return context.label;
    }
    return `${fallbackPrefix} #${fallbackIndex + 1}`;
  };

  const renderContextDetails = (context?: ResultContext) => {
    if (!context) return null;

    return (
      <ul className="context-list">
        {Object.entries(context).map(([key, value]) => {
          if (value === undefined || value === null) return null;
          return (
            <li key={key}>
              <span className="context-key">{humanizeKey(key)}</span>
              <span className="context-value">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </span>
            </li>
          );
        })}
      </ul>
    );
  };

  const formatConditionValue = (value: any) => {
    if (value === undefined) return 'undefined';
    if (value === null) return 'null';
    if (typeof value === 'string') return value;
    return JSON.stringify(value);
  };

  const renderFailedConditions = (conditions?: ConditionSummary[]) => {
    if (!conditions || conditions.length === 0) {
      return <p className="no-failures-message">All child rules passed.</p>;
    }

    return (
      <ul className="failures-list">
        {conditions.map((condition, index) => (
          <li key={index} className="failure-item">
            <span className="failure-index">#{index + 1}</span>
            <div className="failure-content">
              <div className="failure-line">
                <span className="failure-field">{condition.field || 'Unknown field'}</span>
                {condition.operator && (
                  <span className="failure-operator">{condition.operator}</span>
                )}
              </div>
              <div className="failure-line">
                <span className="failure-expected">
                  Expected: {formatConditionValue(condition.expected)}
                </span>
                <span className="failure-actual">
                  Actual: {formatConditionValue(condition.actual)}
                </span>
              </div>
              {condition.error && (
                <div className="failure-line failure-error">
                  Error: {condition.error}
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    );
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
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
    } finally {
      setLoading(false);
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
      const data = await api.evaluateSelection(selectedUsers, selectedPolicies);
      setResults(data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Evaluation failed');
    } finally {
      setEvaluating(false);
    }
  };

  const filteredResults = useMemo(() => {
    let filtered = results;

    // Apply pass/fail filter
    if (filter === 'passed') {
      filtered = filtered.filter((r) => r.passed);
    } else if (filter === 'failed') {
      filtered = filtered.filter((r) => !r.passed);
    }

    const normalize = (value: any) => {
      if (value === undefined || value === null) return '';
      if (typeof value === 'number') return value;
      if (typeof value === 'boolean') return value ? 1 : 0;
      return String(value).toLowerCase();
    };

    // Apply sorting
    filtered = [...filtered].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      if (sortField === 'user_index' || sortField === 'policy_index') {
        aVal = a[sortField as keyof EvaluationResult];
        bVal = b[sortField as keyof EvaluationResult];
      } else if (sortField === 'passed') {
        aVal = a.passed ? 1 : 0;
        bVal = b.passed ? 1 : 0;
      } else if (sortField === 'failure_count') {
        aVal = a.failed_conditions ? a.failed_conditions.length : 0;
        bVal = b.failed_conditions ? b.failed_conditions.length : 0;
      } else {
        // Sort by user data fields
        aVal = a.user_data[sortField];
        bVal = b.user_data[sortField];
      }

      aVal = normalize(aVal);
      bVal = normalize(bVal);

      if (aVal === bVal) return 0;

      const comparison = aVal > bVal ? 1 : -1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [results, filter, sortField, sortDirection]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const toggleRow = (index: number) => {
    setExpandedRow(expandedRow === index ? null : index);
  };

  // Extract all unique field names from user data
  const userFields = useMemo(() => {
    if (results.length === 0) return [];
    const excludedFields = new Set(['filename', 'users']);
    const fields = new Set<string>();
    results.forEach((r) => {
      Object.keys(r.user_data).forEach((key) => fields.add(key));
    });
    return Array.from(fields).filter((field) => !excludedFields.has(field));
  }, [results]);

  const visibleUserFields = useMemo(() => userFields.slice(0, 3), [userFields]);

  const passedCount = results.filter((r) => r.passed).length;
  const failedCount = results.filter((r) => !r.passed).length;
  const totalFailedConditions = results.reduce(
    (sum, r) => sum + (r.failed_conditions ? r.failed_conditions.length : 0),
    0
  );

  return (
    <div className="results-container">
      <h2>Evaluate Compliance</h2>

      {(policies.length === 0 || userFiles.length === 0) && !loading && (
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
              <span className="stat-label">Visible:</span>
              <span className="stat-value">{filteredResults.length}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Total:</span>
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
            <div className="stat warning">
              <span className="stat-label">Rules Failed:</span>
              <span className="stat-value">{totalFailedConditions}</span>
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

          <div className="table-wrapper">
            <table className="results-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('user_index')}>
                    User {sortField === 'user_index' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('policy_index')}>
                    Policy {sortField === 'policy_index' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('passed')}>
                    Status {sortField === 'passed' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('failure_count')}>
                    Failed Rules {sortField === 'failure_count' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  {visibleUserFields.map((field) => (
                    <th key={field} onClick={() => handleSort(field)}>
                      {humanizeKey(field)} {sortField === field && (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                  ))}
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((result, index) => {
                  const userLabel = formatEntityLabel(result.user_context, 'User', result.user_index);
                  const policyLabel = formatEntityLabel(result.policy_context, 'Policy', result.policy_index);
                  const userMeta = formatEntityMeta(result.user_context, `Entry #${result.user_index + 1}`);
                  const policyMeta = formatEntityMeta(result.policy_context, `Policy #${result.policy_index + 1}`);
                  const failureCount = result.failed_conditions ? result.failed_conditions.length : 0;

                  return (
                    <React.Fragment key={index}>
                      <tr className={result.passed ? 'row-passed' : 'row-failed'}>
                        <td>
                          <div className="entity-cell">
                            <span className="entity-label">{userLabel}</span>
                            {userMeta && <span className="entity-meta">{userMeta}</span>}
                          </div>
                        </td>
                        <td>
                          <div className="entity-cell">
                            <span className="entity-label">{policyLabel}</span>
                            {policyMeta && <span className="entity-meta">{policyMeta}</span>}
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${result.passed ? 'badge-success' : 'badge-error'}`}>
                            {result.passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`failure-count ${failureCount > 0 ? 'has-failures' : 'no-failures'}`}
                          >
                            {failureCount}
                          </span>
                        </td>
                        {visibleUserFields.map((field) => (
                          <td key={field}>
                            {JSON.stringify(result.user_data[field])}
                          </td>
                        ))}
                        <td>
                          <button
                            className="btn-link"
                            onClick={() => toggleRow(index)}
                          >
                            {expandedRow === index ? 'Hide' : 'Show'}
                          </button>
                        </td>
                      </tr>
                      {expandedRow === index && (
                        <tr className="expanded-row">
                          <td colSpan={visibleUserFields.length + 5}>
                            <div className="details-panel">
                              <div className="details-section">
                                <h4>User Data:</h4>
                                <pre>{JSON.stringify(result.user_data, null, 2)}</pre>
                              </div>
                              <div className="details-section">
                                <h4>Policy:</h4>
                                <pre>{JSON.stringify(result.policy, null, 2)}</pre>
                              </div>
                              <div className="details-section">
                                <h4>Evaluation Details:</h4>
                                <pre>{JSON.stringify(result.details, null, 2)}</pre>
                              </div>
                              {result.failed_conditions && result.failed_conditions.length > 0 && (
                                <div className="details-section">
                                  <h4>Failed Rules:</h4>
                                  {renderFailedConditions(result.failed_conditions)}
                                </div>
                              )}
                              {result.user_context && (
                                <div className="details-section">
                                  <h4>User Context:</h4>
                                  {renderContextDetails(result.user_context)}
                                </div>
                              )}
                              {result.policy_context && (
                                <div className="details-section">
                                  <h4>Policy Context:</h4>
                                  {renderContextDetails(result.policy_context)}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
