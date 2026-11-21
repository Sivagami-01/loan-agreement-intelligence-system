import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from './config';

const SEVERITY_ORDER = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
};

export default function RiskTab({ docId, onJumpPage }) {
  const [taskState, setTaskState] = useState('not_started'); // 'not_started' | 'running' | 'done' | 'failed' | 'quota_blocked' | 'needs_retrieval' | 'partial'
  const [result, setResult] = useState(null);
  const [notice, setNotice] = useState(null);
  const [errorText, setErrorText] = useState(null);
  const [clientElapsed, setClientElapsed] = useState(0);

  const pollTimerRef = useRef(null);
  const elapsedTimerRef = useRef(null);
  const pollStartRef = useRef(null);

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    };
  }, []);

  const stopAllTimers = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (elapsedTimerRef.current) {
      clearInterval(elapsedTimerRef.current);
      elapsedTimerRef.current = null;
    }
  };

  const processResponsePayload = (data) => {
    if (data.notice) {
      setNotice(data.notice);
    }

    if (data.state === 'quota_blocked') {
      stopAllTimers();
      setTaskState('quota_blocked');
      return;
    }

    if (data.state === 'failed') {
      stopAllTimers();
      setErrorText(data.error || 'Risk analysis failed.');
      setTaskState('failed');
      return;
    }

    const res = data.result;
    if (res && res.status === 'needs_retrieval') {
      stopAllTimers();
      setResult(res);
      setTaskState('needs_retrieval');
      return;
    }

    if (res && res.status === 'scan_failed') {
      stopAllTimers();
      setErrorText('Risk scan failed due to API or network error.');
      setTaskState('failed');
      return;
    }

    if (data.state === 'done' || (res && res.status === 'ok')) {
      stopAllTimers();
      setResult(res);
      setTaskState('done');
      return;
    }

    if (data.state === 'partial') {
      stopAllTimers();
      setResult(res);
      setTaskState('partial');
    }
  };

  const handleRun = async () => {
    if (!docId) return;
    stopAllTimers();
    setTaskState('running');
    setErrorText(null);
    setClientElapsed(0);
    pollStartRef.current = Date.now();

    elapsedTimerRef.current = setInterval(() => {
      if (pollStartRef.current) {
        setClientElapsed(Math.floor((Date.now() - pollStartRef.current) / 1000));
      }
    }, 1000);

    try {
      const postRes = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/risk`, {
        method: 'POST',
      });
      const postData = await postRes.json();
      processResponsePayload(postData);

      if (postData.state === 'done' || postData.state === 'quota_blocked' || postData.state === 'failed') {
        return;
      }

      pollTimerRef.current = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/risk`);
          if (!pollRes.ok) return;
          const pollData = await pollRes.json();
          processResponsePayload(pollData);
        } catch {
          // Continue polling on transient connection drops
        }
      }, 2000);
    } catch (err) {
      stopAllTimers();
      setErrorText(err.message || 'Failed to start risk analysis.');
      setTaskState('failed');
    }
  };

  const handleShowSaved = async () => {
    if (!docId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/risk`);
      if (res.ok) {
        const data = await res.json();
        processResponsePayload(data);
      }
    } catch {
      // Retain current state if re-fetch fails
    }
  };

  // Determine evidence limited badge: check if no category reaches 'strong' evidence (i.e. 'limited' or 'none')
  const isEvidenceLimited = result?.evidence_strength
    ? !Object.values(result.evidence_strength).some((strength) => strength === 'strong') ||
      Object.values(result.evidence_strength).every((strength) => strength === 'limited' || strength === 'none')
    : false;

  // Sort flagged clauses by severity (Critical -> High -> Medium -> Low), then page ascending
  const sortedFlaggedClauses = result?.flagged_clauses
    ? [...result.flagged_clauses].sort((a, b) => {
        const rankA = SEVERITY_ORDER[a.severity] ?? 99;
        const rankB = SEVERITY_ORDER[b.severity] ?? 99;
        if (rankA !== rankB) return rankA - rankB;
        const pA = parseInt(a.page, 10) || 0;
        const pB = parseInt(b.page, 10) || 0;
        return pA - pB;
      })
    : [];

  const categories = result?.categories || [];
  const topDrivers = result?.top_driver_per_category || [];
  const criticalClauses = result?.critical_clauses || [];

  return (
    <div className="task-tab-container">
      <div className="tab-title-row">
        <h3>
          Risk Analysis <span className="tab-pill">automated output</span>
        </h3>
        {taskState === 'done' ? (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleShowSaved}
          >
            Show saved result
          </button>
        ) : taskState !== 'running' ? (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleRun}
            disabled={!docId}
          >
            Run Risk Analysis
          </button>
        ) : null}
      </div>

      {notice && (
        <div className="notice-box">
          <p>
            <strong>Notice:</strong> {notice}
          </p>
        </div>
      )}

      {taskState === 'not_started' && (
        <div className="card task-intro-card">
          <p className="placeholder-text">
            Click "Run Risk Analysis" to scan clauses across all 7 categories and compute the explainable risk score.
          </p>
        </div>
      )}

      {taskState === 'running' && (
        <div className="card task-running-card">
          <div className="spinner-wrapper">
            <div className="spinner" />
            <p className="running-text">
              Scanning clauses and computing risk score... ({clientElapsed}s)
            </p>
          </div>
          {clientElapsed > 120 && (
            <div className="alert alert-warning">
              Taking longer than usual.
            </div>
          )}
        </div>
      )}

      {taskState === 'quota_blocked' && (
        <div className="alert alert-warning">
          <strong>Notice:</strong> Today's free Gemini limit is used up, so this task did not run. Try again after the daily reset.
        </div>
      )}

      {taskState === 'needs_retrieval' && (
        <div className="alert alert-warning">
          <strong>Notice:</strong> This document is too long for the risk scan in this version.
        </div>
      )}

      {taskState === 'failed' && (
        <div className="alert alert-error">
          <strong>Error:</strong> {errorText || 'Risk analysis failed.'}
        </div>
      )}

      {taskState === 'partial' && (
        <div className="alert alert-warning">
          <strong>Notice:</strong> Risk analysis results are partial.
        </div>
      )}

      {(taskState === 'done' || taskState === 'partial') && result && result.status !== 'needs_retrieval' && (
        <div className="risk-results">
          {/* Main Score & Gauge Card */}
          <section className="card risk-score-card">
            <h4>Overall Risk Assessment</h4>
            <div className="score-summary-row">
              <div className="score-number-box">
                <span className="score-val">{result.score != null ? result.score.toFixed(1) : '—'}</span>
                <span className="score-scale">/ 100</span>
              </div>
              <div className="score-badges-col">
                <div className="badge-row">
                  <span className={`badge badge-risk-${(result.level || 'low').toLowerCase()}`}>
                    Level: {result.level || 'Low'}
                  </span>
                  <span className="badge badge-auto-estimate">automated estimate</span>
                  {isEvidenceLimited && (
                    <span className="badge badge-evidence-limited">evidence limited</span>
                  )}
                  {result.verifier_independent === false && (
                    <span className="badge badge-not-indep">not independently verified</span>
                  )}
                </div>
                {result.level_explanation && (
                  <p className="level-explanation-text">
                    {result.level_explanation}
                  </p>
                )}
              </div>
            </div>

            {/* Gauge Bar */}
            <div className="gauge-container">
              <div className="gauge-track">
                <div
                  className={`gauge-fill fill-${(result.level || 'low').toLowerCase()}`}
                  style={{ width: `${Math.min(100, Math.max(0, result.score || 0))}%` }}
                />
                <div className="gauge-marker marker-25" style={{ left: '25%' }} />
                <div className="gauge-marker marker-50" style={{ left: '50%' }} />
                <div className="gauge-marker marker-75" style={{ left: '75%' }} />
              </div>
              <div className="gauge-labels">
                <span className="gauge-label-col left">0 (Low)</span>
                <span className="gauge-label-col pos-25">25 (Moderate)</span>
                <span className="gauge-label-col pos-50">50 (High)</span>
                <span className="gauge-label-col pos-75">75 (Critical)</span>
                <span className="gauge-label-col right">100</span>
              </div>
            </div>

            {/* Sample Range Plain Note */}
            <div className="sample-range-note">
              <p>
                <strong>Sample Range:</strong> {result.sample_range || '41.2-51.7'}. Range seen in the 13 labeled sample documents. Bands are not calibrated.
              </p>
            </div>
          </section>

          {/* Category Breakdown Card */}
          <section className="card risk-categories-card">
            <h4>Category Breakdown</h4>
            <div className="table-responsive">
              <table className="risk-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Weight</th>
                    <th>Risk</th>
                    <th>Clauses</th>
                    <th>Evidence Strength</th>
                    <th>Top Driver</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((cat, idx) => {
                    const driver = topDrivers.find((d) => d.category === cat.name);
                    const hasClauses = cat.n_clauses > 0;
                    const driverPageNum = driver?.page ? parseInt(driver.page, 10) : null;

                    return (
                      <tr key={`cat-${idx}`} className={`cat-row-${cat.evidence_strength || 'none'}`}>
                        <td className="cat-name-cell">
                          <strong>{cat.name}</strong>
                        </td>
                        <td className="cat-weight-cell">
                          {cat.weight != null ? `${Math.round(cat.weight * 100)}%` : '—'}
                        </td>
                        <td className="cat-risk-cell">
                          {cat.risk != null ? (cat.risk * 100).toFixed(1) + '%' : '0.0%'}
                        </td>
                        <td className="cat-clauses-cell">
                          {hasClauses ? (
                            <span>{cat.n_clauses}</span>
                          ) : (
                            <span className="text-muted">No clause found in this document</span>
                          )}
                        </td>
                        <td className="cat-evidence-cell">
                          <span className={`badge badge-ev-${cat.evidence_strength || 'none'}`}>
                            {cat.evidence_strength === 'strong' ? 'strong' : cat.evidence_strength === 'limited' ? 'limited' : 'none'}
                          </span>
                        </td>
                        <td className="cat-driver-cell">
                          {hasClauses && driver && driver.clause_id ? (
                            <div className="driver-info">
                              <span className={`badge badge-sev-${(driver.severity || 'low').toLowerCase()}`}>
                                {driver.severity}
                              </span>
                              <span className="driver-quote">"{driver.quote}"</span>
                              {driverPageNum != null && !isNaN(driverPageNum) && (
                                <button
                                  type="button"
                                  className="cite-btn"
                                  onClick={() => onJumpPage && onJumpPage(driverPageNum)}
                                  title={`Jump to page ${driverPageNum}`}
                                >
                                  p.{driverPageNum}
                                </button>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted">No clause found in this document</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* Critical Clauses Card */}
          <section className="card risk-critical-card">
            <h4>Critical Clauses</h4>
            {criticalClauses.length === 0 ? (
              <div className="empty-message-box">
                <p>No Critical clauses found.</p>
              </div>
            ) : (
              <div className="critical-clauses-list">
                {criticalClauses.map((clause, idx) => {
                  const pageNum = parseInt(clause.page, 10);
                  return (
                    <div key={`crit-${idx}`} className="critical-clause-item">
                      <div className="clause-header-row">
                        <span className="badge badge-sev-critical">Critical</span>
                        <span className="clause-type-tag">{clause.clause_type || 'unspecified'}</span>
                        <span className="clause-category-tag">{clause.category}</span>
                        {clause.verifier_independent === false && (
                          <span className="badge badge-not-indep">not independently verified</span>
                        )}
                        {!isNaN(pageNum) && (
                          <button
                            type="button"
                            className="cite-btn"
                            onClick={() => onJumpPage && onJumpPage(pageNum)}
                            title={`Jump to page ${pageNum}`}
                          >
                            p.{pageNum}
                          </button>
                        )}
                      </div>
                      <p className="clause-explain-text">
                        <strong>Severity Explanation:</strong> {clause.explain || clause.severity_explanation || 'Critical risk condition detected.'}
                      </p>
                      <blockquote className="verbatim-quote">
                        "{clause.quote}"
                      </blockquote>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Flagged Clauses Card */}
          <section className="card risk-flagged-card">
            <h4>Flagged Clauses ({sortedFlaggedClauses.length})</h4>
            {sortedFlaggedClauses.length === 0 ? (
              <div className="empty-message-box">
                <p>No clauses flagged for risk in this document.</p>
              </div>
            ) : (
              <div className="flagged-clauses-list">
                {sortedFlaggedClauses.map((clause, idx) => {
                  const pageNum = parseInt(clause.page, 10);
                  const sevLower = (clause.severity || 'low').toLowerCase();

                  return (
                    <div key={`flagged-${idx}`} className={`flagged-clause-item item-sev-${sevLower}`}>
                      <div className="clause-header-row">
                        <span className={`badge badge-sev-${sevLower}`}>
                          {clause.severity}
                        </span>
                        <span className="badge badge-auto-estimate">automated estimate</span>
                        <span className="clause-category-tag">{clause.category}</span>
                        {clause.clause_type && (
                          <span className="clause-type-tag">{clause.clause_type}</span>
                        )}
                        {clause.verifier_independent === false && (
                          <span className="badge badge-not-indep">not independently verified</span>
                        )}
                        {!isNaN(pageNum) && (
                          <button
                            type="button"
                            className="cite-btn"
                            onClick={() => onJumpPage && onJumpPage(pageNum)}
                            title={`Jump to page ${pageNum}`}
                          >
                            p.{pageNum}
                          </button>
                        )}
                      </div>
                      <p className="clause-explain-text">
                        {clause.explain || clause.severity_explanation || `Severity ${clause.severity} clause.`}
                      </p>
                      <blockquote className="verbatim-quote">
                        "{clause.quote}"
                      </blockquote>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
