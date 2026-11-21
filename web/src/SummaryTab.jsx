import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from './config';
import { renderCitations } from './citationUtils';

export default function SummaryTab({ docId, onJumpPage }) {
  const [taskState, setTaskState] = useState('not_started'); // 'not_started' | 'running' | 'done' | 'failed' | 'quota_blocked' | 'partial'
  const [result, setResult] = useState(null);
  const [notice, setNotice] = useState(null);
  const [errorText, setErrorText] = useState(null);
  const [clientElapsed, setClientElapsed] = useState(0);

  const [selectedLang, setSelectedLang] = useState('en');
  const [transResult, setTransResult] = useState(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [transElapsed, setTransElapsed] = useState(0);
  const [transError, setTransError] = useState(null);

  const pollTimerRef = useRef(null);
  const elapsedTimerRef = useRef(null);
  const pollStartRef = useRef(null);

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    };
  }, []);

  // Reset translation when docId changes
  useEffect(() => {
    setSelectedLang('en');
    setTransResult(null);
    setTransError(null);
    setIsTranslating(false);
  }, [docId]);

  // Fetch translation when language is non-English and summary result is ready
  useEffect(() => {
    if (selectedLang === 'en' || !docId || !result?.short) {
      setTransResult(null);
      setTransError(null);
      setIsTranslating(false);
      return;
    }

    let isCancelled = false;
    setIsTranslating(true);
    setTransError(null);
    setTransElapsed(0);

    const startT = Date.now();
    const timer = setInterval(() => {
      setTransElapsed(Math.floor((Date.now() - startT) / 1000));
    }, 1000);

    fetch(`${API_BASE_URL}/api/documents/${docId}/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source: 'summary', language: selectedLang }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(txt || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        if (!isCancelled) {
          setTransResult(data);
          setIsTranslating(false);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          setTransError(err.message || 'Translation failed.');
          setIsTranslating(false);
        }
      })
      .finally(() => {
        clearInterval(timer);
      });

    return () => {
      isCancelled = true;
      clearInterval(timer);
    };
  }, [selectedLang, docId, result?.short]);

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
      const postRes = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/summary`, {
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
        setErrorText(postData.error || 'Summary task failed.');
        setTaskState('failed');
        return;
      }

      // Poll every 2 s
      pollTimerRef.current = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_BASE_URL}/api/documents/${docId}/tasks/summary`);
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
            setErrorText(pollData.error || 'Summary task failed.');
            setTaskState('failed');
          } else if (pollData.state === 'partial') {
            stopAllTimers();
            setResult(pollData.result);
            setTaskState('partial');
          }
        } catch {
          // Keep polling on transient network drops
        }
      }, 2000);
    } catch (err) {
      stopAllTimers();
      setErrorText(err.message || 'Failed to start summary task.');
      setTaskState('failed');
    }
  };

  // Parse markdown detailed text into structured sections
  const parseDetailedSections = (detailedStr) => {
    if (!detailedStr) return [];
    const parts = detailedStr.split(/\n\n## /);
    const sections = [];

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!part.trim()) continue;
      const clean = part.startsWith('## ') ? part.slice(3) : part;
      const firstNewline = clean.indexOf('\n');
      if (firstNewline !== -1) {
        const title = clean.slice(0, firstNewline).trim();
        const content = clean.slice(firstNewline + 1).trim();
        sections.push({ title, content });
      } else {
        sections.push({ title: clean.trim(), content: '' });
      }
    }
    return sections;
  };

  const detailedSections = result?.detailed ? parseDetailedSections(result.detailed) : [];

  return (
    <div className="task-tab-container">
      <div className="tab-title-row">
        <h3>
          Summary <span className="tab-pill">automated output</span>
        </h3>
        <div className="summary-controls-top">
          <div className="summary-lang-picker">
            <label htmlFor="summary-lang-select" className="lang-label">
              Language:
            </label>
            <select
              id="summary-lang-select"
              value={selectedLang}
              onChange={(e) => setSelectedLang(e.target.value)}
              className="lang-select"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="ta">Tamil</option>
              <option value="bn">Bengali</option>
              <option value="pa">Punjabi</option>
              <option value="ml">Malayalam</option>
            </select>
          </div>
          {taskState !== 'running' && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleRun}
              disabled={!docId}
            >
              {taskState === 'done' ? 'Show saved result' : 'Run Summary'}
            </button>
          )}
        </div>
      </div>

      {/* Task Output Notice */}
      {notice && (
        <div className="notice-box">
          <p>
            <strong>Notice:</strong> {notice}
          </p>
        </div>
      )}

      {/* Not Started State */}
      {taskState === 'not_started' && (
        <div className="card task-intro-card">
          <p className="placeholder-text">
            Click "Run Summary" to extract concise and detailed summaries with clause citations.
          </p>
        </div>
      )}

      {/* Running State */}
      {taskState === 'running' && (
        <div className="card task-running-card">
          <div className="spinner-wrapper">
            <div className="spinner" />
            <p className="running-text">
              Generating grounded summary... ({clientElapsed}s)
            </p>
          </div>
          {clientElapsed > 120 && (
            <div className="alert alert-warning">
              Taking longer than usual. Key info and OCR can take over a minute.
            </div>
          )}
        </div>
      )}

      {/* Quota Blocked State */}
      {taskState === 'quota_blocked' && (
        <div className="alert alert-warning">
          <strong>Notice:</strong> Today's free Gemini limit is used up, so this task did not run. Try again after the daily reset.
        </div>
      )}

      {/* Failed State */}
      {taskState === 'failed' && (
        <div className="alert alert-error">
          <strong>Error:</strong> {errorText || 'Summary generation failed.'}
        </div>
      )}

      {/* Done or Partial State */}
      {(taskState === 'done' || taskState === 'partial') && result && (
        <div className="summary-results">
          {/* Short Summary Card */}
          <section className="card summary-card">
            <h4>Short Summary</h4>
            {selectedLang === 'en' ? (
              <div className="summary-text-block">
                <p>{renderCitations(result.short, onJumpPage)}</p>
              </div>
            ) : isTranslating ? (
              <div className="translation-loading-block">
                <div className="spinner-wrapper">
                  <div className="spinner" />
                  <p className="running-text">
                    Translating summary... ({transElapsed}s)
                  </p>
                </div>
                {transElapsed >= 60 && (
                  <div className="alert alert-warning">
                    Translation is taking longer than usual (over 60 seconds).
                  </div>
                )}
              </div>
            ) : transResult?.status === 'ok' ? (
              <div className="translated-summary-block">
                <div className="translation-badge-row">
                  <span className="badge badge-translation">
                    Machine translation. Check against the original English.
                  </span>
                </div>
                <div className="summary-text-block">
                  <p>{renderCitations(transResult.translated_text, onJumpPage)}</p>
                </div>
                <div className="original-english-box">
                  <span className="original-label">Original English:</span>
                  <div className="summary-text-block">
                    <p>{renderCitations(result.short, onJumpPage)}</p>
                  </div>
                </div>
              </div>
            ) : transResult?.status === 'number_check_failed' ? (
              <div className="translated-summary-fallback">
                <div className="alert alert-warning">
                  Number check failed between translation and original text. Showing original English.
                </div>
                <div className="summary-text-block">
                  <p>{renderCitations(result.short, onJumpPage)}</p>
                </div>
              </div>
            ) : transResult?.status === 'quota_blocked' ? (
              <div className="translated-summary-fallback">
                <div className="alert alert-warning">
                  Today's free Gemini limit is used up, so translation did not run. Try again after the daily reset.
                </div>
                <div className="summary-text-block">
                  <p>{renderCitations(result.short, onJumpPage)}</p>
                </div>
              </div>
            ) : (
              <div className="translated-summary-fallback">
                <div className="alert alert-error">
                  Translation failed. Showing original English.
                </div>
                <div className="summary-text-block">
                  <p>{renderCitations(result.short, onJumpPage)}</p>
                </div>
              </div>
            )}
          </section>

          {/* Detailed Summary Sections */}
          {detailedSections.map((sec, idx) => {
            const isNotFoundSection = sec.title.toLowerCase().includes('not found') || sec.title.toLowerCase().includes('defined elsewhere');
            const lines = sec.content.split('\n').filter((l) => l.trim().length > 0);

            return (
              <section key={`sec-${idx}`} className={`card summary-section-card ${isNotFoundSection ? 'section-not-found' : ''}`}>
                <h4>{sec.title}</h4>
                {isNotFoundSection ? (
                  <ul className="not-found-list">
                    {lines.map((line, lineIdx) => {
                      const cleanLine = line.replace(/^-\s*/, '');
                      return (
                        <li key={`nf-${lineIdx}`}>
                          {renderCitations(cleanLine, onJumpPage)}
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="summary-text-block">
                    {lines.map((line, lineIdx) => (
                      <p key={`p-${lineIdx}`}>
                        {renderCitations(line, onJumpPage)}
                      </p>
                    ))}
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
