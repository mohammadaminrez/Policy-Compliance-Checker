import React, { useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import { EvaluationResult } from '../types';

interface ResultsProps {
  policiesFile: File | null;
  usersFile: File | null;
  triggerEvaluation: boolean;
  onEvaluationComplete: () => void;
}

export const Results: React.FC<ResultsProps> = ({
  policiesFile,
  usersFile,
  triggerEvaluation,
  onEvaluationComplete,
}) => {
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [sortField, setSortField] = useState<string>('user_index');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    if (triggerEvaluation && policiesFile && usersFile) {
      handleEvaluate();
    }
  }, [triggerEvaluation]);

  const handleEvaluate = async () => {
    if (!policiesFile || !usersFile) {
      setError('Please upload both policy and user files first');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await api.evaluate(usersFile, policiesFile);
      setResults(response.results);
      onEvaluationComplete();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Evaluation failed');
    } finally {
      setLoading(false);
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
      } else {
        // Sort by user data fields
        aVal = a.user_data[sortField];
        bVal = b.user_data[sortField];
      }

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
    const fields = new Set<string>();
    results.forEach((r) => {
      Object.keys(r.user_data).forEach((key) => fields.add(key));
    });
    return Array.from(fields);
  }, [results]);

  const passedCount = results.filter((r) => r.passed).length;
  const failedCount = results.filter((r) => !r.passed).length;

  return (
    <div className="results-container">
      <h2>Evaluation Results</h2>

      {!results.length && !loading && !error && (
        <div className="empty-state">
          <p>No results yet. Upload policy and user files, then click "Evaluate".</p>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Evaluating...</p>
        </div>
      )}

      {error && <div className="message error">{error}</div>}

      {results.length > 0 && (
        <>
          <div className="results-summary">
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
                    User # {sortField === 'user_index' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('policy_index')}>
                    Policy # {sortField === 'policy_index' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('passed')}>
                    Status {sortField === 'passed' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  {userFields.slice(0, 3).map((field) => (
                    <th key={field} onClick={() => handleSort(field)}>
                      {field} {sortField === field && (sortDirection === 'asc' ? '↑' : '↓')}
                    </th>
                  ))}
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((result, index) => (
                  <React.Fragment key={index}>
                    <tr className={result.passed ? 'row-passed' : 'row-failed'}>
                      <td>{result.user_index}</td>
                      <td>{result.policy_index}</td>
                      <td>
                        <span className={`badge ${result.passed ? 'badge-success' : 'badge-error'}`}>
                          {result.passed ? 'PASSED' : 'FAILED'}
                        </span>
                      </td>
                      {userFields.slice(0, 3).map((field) => (
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
                        <td colSpan={userFields.length + 4}>
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
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
