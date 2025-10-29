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
  const [exportMenuOpen, setExportMenuOpen] = useState(false);

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

  // Fail-first ordering: users with failures on top
  const orderedResults = [...filteredResults].sort((a, b) => {
    const af = a.failed_rules > 0 ? 1 : 0;
    const bf = b.failed_rules > 0 ? 1 : 0;
    if (af !== bf) return bf - af; // failed first
    // tie-breaker: more failed rules first
    if (a.failed_rules !== b.failed_rules) return b.failed_rules - a.failed_rules;
    return 0;
  });

  const getUserSummary = (r: EvaluationResult) => {
    const files = r.policy_files?.length || 0;
    const total = r.total_rules || 0;
    const passed = r.passed_rules || 0;
    const failed = r.failed_rules || 0;
    return `${files} files • ${total} rules (${passed} ✓, ${failed} ✗)`;
  };

  const copyUserFailures = (r: EvaluationResult) => {
    const failures: any[] = [];
    r.policy_files.forEach(pf => {
      pf.rules.filter(rr => !rr.passed).forEach(rr => {
        const conds = collectFailedConditions(rr.details || {});
        conds.forEach(c => failures.push({
          user: getUserLabel(r),
          policy_file: pf.policy_file,
          rule_index: rr.rule_index,
          field: c.field,
          operator: c.operator,
          expected: c.expected,
          actual: c.actual,
          error: c.error,
        }));
      });
    });
    const text = JSON.stringify(failures, null, 2);
    navigator.clipboard?.writeText(text).catch(() => {});
  };

  const exportView = (format: 'json' | 'csv') => {
    const ts = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const stamp = `${ts.getFullYear()}${pad(ts.getMonth() + 1)}${pad(ts.getDate())}-${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}`;

    // Use current ordered view (after filter and fail-first sorting)
    const usersOrdered = orderedResults.map(r => {
      const policiesOrdered = [...r.policy_files]
        .sort((a,b) => (b.failed_rules>0?1:0)-(a.failed_rules>0?1:0) || b.failed_rules - a.failed_rules)
        .map(pf => {
          const rulesOrdered = [...pf.rules]
            .sort((a,b) => (a.passed===b.passed?0:(a.passed?1:-1)))
            .map(rr => {
              const failed = collectFailedConditions(rr.details || {});
              return {
                rule_index: rr.rule_index + 1,
                rule_name: getRuleName(rr.rule, rr.rule_index),
                passed: rr.passed,
                failed_conditions: failed,
                rule: rr.rule,
              };
            });
          return {
            policy_file: pf.policy_file,
            total_rules: pf.total_rules,
            passed_rules: pf.passed_rules,
            failed_rules: pf.failed_rules,
            rules: rulesOrdered,
          };
        });
      return {
        user_label: getUserLabel(r),
        summary: {
          files: r.policy_files?.length || 0,
          total_rules: r.total_rules || 0,
          passed_rules: r.passed_rules || 0,
          failed_rules: r.failed_rules || 0,
          all_passed: r.all_passed,
        },
        policy_files: policiesOrdered,
        user_data: r.user_data,
      };
    });

    if (format === 'json') {
      const payload = {
        generated_at: new Date().toISOString(),
        filter,
        total_users: usersOrdered.length,
        results: usersOrdered,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `compliance-view-${filter}-${stamp}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      return;
    }

    // CSV: flatten to one row per rule in the current view
    const headers = ['user','policy_file','rule_index','rule_name','passed','failed_count','failed_conditions'];
    const rows: any[] = [];
    usersOrdered.forEach(u => {
      u.policy_files.forEach(pf => {
        pf.rules.forEach(rr => {
          rows.push({
            user: u.user_label,
            policy_file: pf.policy_file,
            rule_index: rr.rule_index,
            rule_name: rr.rule_name,
            passed: rr.passed,
            failed_count: Array.isArray(rr.failed_conditions) ? rr.failed_conditions.length : 0,
            failed_conditions: rr.failed_conditions && rr.failed_conditions.length > 0 ? JSON.stringify(rr.failed_conditions) : '',
          });
        });
      });
    });

    const escape = (v: any) => {
      const s = typeof v === 'string' ? v : JSON.stringify(v);
      return '"' + (s ?? '').replace(/"/g, '""') + '"';
    };
    const csv = [headers.join(',')].concat(
      rows.map(r => headers.map(h => escape((r as any)[h])).join(','))
    ).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `compliance-view-${filter}-${stamp}.csv`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

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
              <span style={{flex: '1 1 auto'}} />
              <div className="results-actions">
                <div className="btn-split">
                  <button className="btn" onClick={() => exportView('json')}>Export view</button>
                  <button className="btn split-toggle" onClick={() => setExportMenuOpen(!exportMenuOpen)}>▾</button>
                  {exportMenuOpen && (
                    <div className="menu">
                      <button onClick={() => { exportView('json'); setExportMenuOpen(false); }}>Export as JSON</button>
                      <button onClick={() => { exportView('csv'); setExportMenuOpen(false); }}>Export as CSV</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="simple-results-list">
            {orderedResults.map((result, index) => (
              <div
                key={index}
                className={`result-card ${result.all_passed ? 'passed' : 'failed'}`}
              >
                <div className="result-header">
                  <div className="result-info">
                    <span className="result-user">
                      <strong>User:</strong> {getUserLabel(result)}
                    </span>
                    <span className="result-policy" style={{color:'#374151', fontSize:'0.9rem'}}>
                      {getUserSummary(result)}
                    </span>
                    <div className="policy-files-summary">
                      {[...result.policy_files]
                        .sort((a,b) => (b.failed_rules>0?1:0)-(a.failed_rules>0?1:0) || b.failed_rules - a.failed_rules)
                        .map((policyFile, pfIdx) => (
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
                    <button className="btn-details" onClick={() => copyUserFailures(result)}>Copy failures</button>
                  </div>
                </div>

                {expandedRow === index && (
                  <div className="result-details">
                    <div className="details-controls" />
                    <div className="detail-section">
                      <h4>User Data:</h4>
                      <pre>{JSON.stringify(result.user_data, null, 2)}</pre>
                    </div>

                    {[...result.policy_files]
                      .sort((a,b) => (b.failed_rules>0?1:0)-(a.failed_rules>0?1:0) || b.failed_rules - a.failed_rules)
                      .map((policyFile, pfIdx) => {
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
                                {[...policyFile.rules]
                                  .sort((a,b) => (a.passed===b.passed?0:(a.passed?1:-1)))
                                  .map((ruleResult, rIdx) => (
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
