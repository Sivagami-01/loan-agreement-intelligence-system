import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from './config';

const FIELD_LABELS = {
  document_title: 'Document Title',
  agreement_date: 'Agreement Date',
  borrowers: 'Borrowers',
  lenders: 'Lenders',
  agents: 'Agents',
  loan_or_commitment_amount: 'Loan / Commitment Amount',
  interest_rate: 'Interest Rate',
  repayment_terms: 'Repayment Terms',
  maturity_termination_date: 'Maturity / Termination Date',
  fees: 'Fees',
  late_payment_or_default_interest: 'Late Payment / Default Interest',
  prepayment_terms: 'Prepayment Terms',
  collateral_security: 'Collateral / Security',
  guarantees: 'Guarantees',
  events_of_default: 'Events of Default',
  governing_law: 'Governing Law',
};

export default function KeyInfoTab({ docId, onJumpPage }) {
  const [taskState, setTaskState] = useState('not_started'); // 'not_started' | 'running' | 'done' | 'failed' | 'quota_blocked' | 'partial'
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
      const postRes = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/keyinfo`, {
        method: 'POST',
      });
      const postData = await postRes.json();

      if (postData.notice) {
        setNotice(postData.notice);
      }

      if (postData.state === 'done') {
        stopAllTimers();
        setResult(postData.result);
        setTaskState('done');
        return;
      }

      if (postData.state === 'quota_blocked') {
        stopAllTimers();
        setTaskState('quota_blocked');
        return;
      }

      if (postData.state === 'failed') {
        stopAllTimers();
        setErrorText(postData.error || 'Key Info task failed.');
        setTaskState('failed');
        return;
      }

      pollTimerRef.current = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/keyinfo`);
          if (!pollRes.ok) return;
          const pollData = await pollRes.json();

          if (pollData.notice) {
            setNotice(pollData.notice);
          }

          if (pollData.state === 'done') {
            stopAllTimers();
            setResult(pollData.result);
            setTaskState('done');
          } else if (pollData.state === 'quota_blocked') {
            stopAllTimers();
            setTaskState('quota_blocked');
          } else if (pollData.state === 'failed') {
            stopAllTimers();
            setErrorText(pollData.error || 'Key Info task failed.');
            setTaskState('failed');
          } else if (pollData.state === 'partial') {
            stopAllTimers();
            setResult(pollData.result);
            setTaskState('partial');
          }
        } catch {
          // Continue polling on transient errors
        }
      }, 2000);
    } catch (err) {
      stopAllTimers();
      setErrorText(err.message || 'Failed to start key info extraction.');
      setTaskState('failed');
    }
  };

  const fields = result?.fields || [];

  return (
    <div className="task-tab-container">
      <div className="tab-title-row">
        <h3>
          Key Information <span className="tab-pill">automated output</span>
        </h3>
        {taskState !== 'running' && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleRun}
            disabled={!docId}
          >
            {taskState === 'done' ? 'Show saved result' : 'Run Key Info'}
          </button>
        )}
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
            Click "Run Key Info" to extract all 16 grounded loan parameters with verbatim evidence quotes and verification status.
          </p>
        </div>
      )}

      {taskState === 'running' && (
        <div className="card task-running-card">
          <div className="spinner-wrapper">
            <div className="spinner" />
            <p className="running-text">
              Extracting key fields and verifying quotes... ({clientElapsed}s)
            </p>
          </div>
          {clientElapsed > 120 && (
            <div className="alert alert-warning">
              Taking longer than usual. Key info and OCR can take over a minute.
            </div>
          )}
        </div>
      )}

      {taskState === 'quota_blocked' && (
        <div className="alert alert-warning">
          <strong>Notice:</strong> Today's free Gemini limit is used up, so this task did not run. Try again after the daily reset.
        </div>
      )}

      {taskState === 'failed' && (
        <div className="alert alert-error">
          <strong>Error:</strong> {errorText || 'Key info extraction failed.'}
        </div>
      )}

      {(taskState === 'done' || taskState === 'partial') && result && (
        <div className="keyinfo-results">
          <div className="card keyinfo-table-card">
            <div className="table-responsive">
              <table className="keyinfo-table">
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Status</th>
                    <th>Value</th>
                    <th>Verbatim Quote</th>
                    <th>Page</th>
                  </tr>
                </thead>
                <tbody>
                  {fields.map((f, idx) => {
                    const fieldStatus = f.status || 'not_found';
                    const friendlyName = FIELD_LABELS[f.field] || f.field;
                    const quoteText = f.evidence?.[0]?.quote || (f.quotes && f.quotes[0]) || '';
                    const pageNum = f.page != null ? f.page : (f.evidence?.[0]?.page != null ? f.evidence[0].page : null);
                    const notIndep = f.verifier_independent === false;

                    return (
                      <tr key={`field-${idx}`} className={`row-status-${fieldStatus}`}>
                        <td className="field-name-cell">
                          <strong>{friendlyName}</strong>
                          <span className="field-raw-name">{f.field}</span>
                        </td>
                        <td className="field-status-cell">
                          {fieldStatus === 'verified' && (
                            <span className="badge badge-verified">verified</span>
                          )}
                          {fieldStatus === 'needs_review' && (
                            <span className="badge badge-needs-review">needs review</span>
                          )}
                          {fieldStatus === 'not_found' && (
                            <span className="badge badge-not-found">not found</span>
                          )}
                          {fieldStatus === 'deferred_to_other_document' && (
                            <span className="badge badge-deferred">
                              defined in another document
                            </span>
                          )}
                          {fieldStatus === 'unverified' && (
                            <span className="badge badge-unverified">unverified</span>
                          )}
                          {notIndep && (
                            <span className="badge badge-not-indep">
                              not independently verified
                            </span>
                          )}
                        </td>
                        <td className="field-value-cell">
                          {fieldStatus === 'unverified' && (
                            <span className="text-muted">no verified quote</span>
                          )}
                          {fieldStatus === 'not_found' && (
                            <span className="text-muted">Not found in this document</span>
                          )}
                          {fieldStatus === 'deferred_to_other_document' && (
                            <span className="text-deferred">
                              {f.defers_to ? `Defined in: ${f.defers_to}` : (f.value || 'Defined in another document')}
                            </span>
                          )}
                          {fieldStatus !== 'unverified' && fieldStatus !== 'not_found' && fieldStatus !== 'deferred_to_other_document' && (
                            <span>{f.value || '—'}</span>
                          )}
                        </td>
                        <td className="field-quote-cell">
                          {quoteText ? (
                            <blockquote className="verbatim-quote">
                              "{quoteText}"
                            </blockquote>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                        <td className="field-page-cell">
                          {pageNum != null ? (
                            <button
                              type="button"
                              className="cite-btn"
                              onClick={() => onJumpPage && onJumpPage(pageNum)}
                              title={`Jump to page ${pageNum}`}
                            >
                              p.{pageNum}
                            </button>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
