import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from './config';
import { renderCitations } from './citationUtils';

export default function ChatTab({ docId, onJumpPage }) {
  const [turns, setTurns] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState(null);

  const [inputQuestion, setInputQuestion] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState(null);
  const [clientElapsed, setClientElapsed] = useState(0);
  const [chatError, setChatError] = useState(null);

  const [selectedLang, setSelectedLang] = useState('en');
  const [translations, setTranslations] = useState({});
  const [translatingTurns, setTranslatingTurns] = useState({});

  const translationsRef = useRef({});
  translationsRef.current = translations;
  const translatingRef = useRef({});
  translatingRef.current = translatingTurns;

  const elapsedTimerRef = useRef(null);
  const elapsedStartRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Clear translation cache when docId changes
  useEffect(() => {
    setTranslations({});
    setTranslatingTurns({});
    setSelectedLang('en');
  }, [docId]);

  // Update timer for in-flight translations
  useEffect(() => {
    const keys = Object.keys(translatingTurns);
    if (keys.length === 0) return;

    const interval = setInterval(() => {
      setTranslatingTurns((prev) => {
        let changed = false;
        const now = Date.now();
        const next = { ...prev };
        for (const k of Object.keys(next)) {
          if (next[k]?.startTime) {
            const el = Math.floor((now - next[k].startTime) / 1000);
            if (next[k].elapsed !== el) {
              next[k] = { ...next[k], elapsed: el };
              changed = true;
            }
          }
        }
        return changed ? next : prev;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [Object.keys(translatingTurns).length]);

  const fetchTurnTranslation = async (turnIdx, lang) => {
    const key = `${turnIdx}_${lang}`;
    setTranslatingTurns((prev) => ({
      ...prev,
      [key]: { elapsed: 0, startTime: Date.now() },
    }));

    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'chat',
          turn_index: turnIdx,
          language: lang,
        }),
      });

      if (!res.ok) {
        const errTxt = await res.text();
        throw new Error(errTxt || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setTranslations((prev) => ({
        ...prev,
        [key]: data,
      }));
    } catch (err) {
      setTranslations((prev) => ({
        ...prev,
        [key]: {
          status: 'failed',
          error: err.message || 'Translation failed.',
        },
      }));
    } finally {
      setTranslatingTurns((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  useEffect(() => {
    if (selectedLang === 'en' || !docId || turns.length === 0) {
      return;
    }

    turns.forEach((turn, idx) => {
      const key = `${idx}_${selectedLang}`;
      if (translationsRef.current[key] || translatingRef.current[key]) {
        return;
      }

      const isAdvice =
        turn.category === 'advice' ||
        turn.status === 'refused' ||
        (Array.isArray(turn.flags) && turn.flags.includes('advice_refused'));
      const hasAnswer = typeof turn.answer === 'string' && turn.answer.trim().length > 0;
      const isBlockedOrNotFound =
        turn.status === 'quota_blocked' ||
        turn.status === 'unverified' ||
        turn.status === 'not_found';

      if (!isAdvice && (!hasAnswer || isBlockedOrNotFound)) {
        return;
      }

      fetchTurnTranslation(idx, selectedLang);
    });
  }, [selectedLang, docId, turns]);

  // Auto-scroll to bottom of chat when turns change
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [turns, pendingQuestion]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (elapsedTimerRef.current) {
        clearInterval(elapsedTimerRef.current);
        elapsedTimerRef.current = null;
      }
    };
  }, []);

  // Fetch chat history on mount or when docId changes
  useEffect(() => {
    if (!docId) {
      setTurns([]);
      setHistoryError(null);
      return;
    }

    let cancelled = false;
    setLoadingHistory(true);
    setHistoryError(null);

    fetch(`${API_BASE_URL}/api/documents/${docId}/chat`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load chat history (HTTP ${res.status})`);
        }
        return res.json();
      })
      .then((data) => {
        if (!cancelled) {
          setTurns(Array.isArray(data.turns) ? data.turns : []);
          setLoadingHistory(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setHistoryError(err.message);
          setLoadingHistory(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [docId]);

  const handleSend = async (e) => {
    e.preventDefault();
    const cleanQ = inputQuestion.trim();
    if (!cleanQ || isSubmitting || !docId) {
      return;
    }

    setInputQuestion('');
    setChatError(null);
    setPendingQuestion(cleanQ);
    setIsSubmitting(true);
    setClientElapsed(0);
    elapsedStartRef.current = Date.now();

    elapsedTimerRef.current = setInterval(() => {
      if (elapsedStartRef.current) {
        setClientElapsed(Math.floor((Date.now() - elapsedStartRef.current) / 1000));
      }
    }, 1000);

    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: cleanQ }),
      });

      if (res.status === 429) {
        throw new Error('A question is already being answered. Please wait.');
      }
      if (res.status === 422) {
        throw new Error('Question cannot be empty.');
      }
      if (res.status === 404) {
        throw new Error('Document not found.');
      }
      if (res.status === 409) {
        throw new Error('Document is not ready for chat.');
      }
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `Request failed with HTTP ${res.status}`);
      }

      const turnData = await res.json();
      const completeTurn = {
        question: cleanQ,
        timestamp: new Date().toISOString(),
        ...turnData,
      };

      setTurns((prev) => [...prev, completeTurn]);
    } catch (err) {
      setChatError(err.message || 'Error sending question.');
    } finally {
      if (elapsedTimerRef.current) {
        clearInterval(elapsedTimerRef.current);
        elapsedTimerRef.current = null;
      }
      setIsSubmitting(false);
      setPendingQuestion(null);
    }
  };

  const renderTurnEvidence = (evidenceList) => {
    if (!Array.isArray(evidenceList) || evidenceList.length === 0) {
      return null;
    }
    return (
      <div className="chat-evidence-list">
        <h5 className="chat-evidence-title">Verified Document Evidence:</h5>
        {evidenceList.map((ev, evIdx) => (
          <div key={`ev-${evIdx}`} className="chat-evidence-item">
            <blockquote className="chat-quote">"{ev.quote}"</blockquote>
            {ev.page != null && (
              <button
                type="button"
                className="cite-btn"
                onClick={() => onJumpPage && onJumpPage(ev.page)}
                title={`Jump to page ${ev.page}`}
              >
                p.{ev.page}
              </button>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderCalculationBody = (turn) => {
    const isNeedsInputs =
      turn.status === 'needs_inputs' ||
      turn.needs_inputs === true ||
      (Array.isArray(turn.missing) && turn.missing.length > 0) ||
      (turn.missing && typeof turn.missing === 'object' && Object.keys(turn.missing).length > 0);

    const missingList = Array.isArray(turn.missing)
      ? turn.missing
      : turn.missing && typeof turn.missing === 'object'
      ? Object.keys(turn.missing)
      : [];

    return (
      <div className="chat-calculation-block">
        {isNeedsInputs && (
          <div className="alert alert-warning">
            <strong>Missing inputs needed:</strong>{' '}
            {missingList.length > 0
              ? missingList.join(', ')
              : 'Additional parameters required for calculation.'}
          </div>
        )}

        {/* Inputs Table */}
        {turn.inputs && typeof turn.inputs === 'object' && Object.keys(turn.inputs).length > 0 && (
          <div className="calc-inputs-wrapper">
            <h5 className="calc-section-title">Inputs &amp; Sources:</h5>
            <table className="calc-inputs-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Source</th>
                  <th>Document Citation</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(turn.inputs).map(([k, item]) => {
                  const isObj = item && typeof item === 'object';
                  const val = isObj ? String(item.value ?? '') : String(item ?? '');
                  const src = isObj ? item.source || 'user' : 'user';
                  const quote = isObj ? item.quote : null;
                  const page = isObj ? item.page : null;
                  return (
                    <tr key={k}>
                      <td><code>{k}</code></td>
                      <td><strong>{val}</strong></td>
                      <td><span className="badge badge-source">{src}</span></td>
                      <td>
                        {quote && <span className="calc-input-quote">"{quote}"</span>}
                        {page != null && (
                          <button
                            type="button"
                            className="cite-btn"
                            onClick={() => onJumpPage && onJumpPage(page)}
                            title={`Jump to page ${page}`}
                          >
                            p.{page}
                          </button>
                        )}
                        {!quote && page == null && <span className="text-muted">—</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Steps */}
        {Array.isArray(turn.steps) && turn.steps.length > 0 && (
          <div className="calc-steps-wrapper">
            <h5 className="calc-section-title">Formula Steps:</h5>
            <ol className="calc-steps-list">
              {turn.steps.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {/* Result */}
        {turn.result != null && (
          <div className="calc-result-box">
            <span className="calc-result-label">Estimated Result:</span>
            <span className="calc-result-value">
              {turn.currency ? `${turn.currency} ` : ''}
              {turn.result}
            </span>
          </div>
        )}

        {/* Estimate-only notice */}
        <div className="calc-notice-box">
          {Array.isArray(turn.assumptions) && turn.assumptions.length > 0 && (
            <p className="calc-assumptions">{turn.assumptions.join(' ')}</p>
          )}
          <p className="calc-disclaimer">
            Estimate only: your lender's schedule may differ because of rounding, day-count, fees and taxes. Not financial advice.
          </p>
        </div>
      </div>
    );
  };

  const renderTranslatedProse = (turn, turnIndex, originalContent) => {
    if (selectedLang === 'en' || turnIndex == null) {
      return originalContent;
    }

    const transKey = `${turnIndex}_${selectedLang}`;
    const trans = translations[transKey];
    const transState = translatingTurns[transKey];

    if (transState) {
      return (
        <div className="chat-translating-block">
          <div className="spinner-wrapper">
            <div className="spinner" />
            <span className="running-text">Translating answer... ({transState.elapsed || 0}s)</span>
          </div>
          {(transState.elapsed || 0) >= 60 && (
            <div className="alert alert-warning">
              Translation is taking longer than usual (over 60 seconds).
            </div>
          )}
        </div>
      );
    }

    if (trans) {
      if (trans.status === 'ok') {
        return (
          <div className="chat-translated-block">
            <div className="translation-badge-row">
              <span className="badge badge-translation">
                Machine translation. Check against the original English.
              </span>
            </div>
            <div className="chat-answer-text">
              {renderCitations(trans.translated_text, onJumpPage)}
            </div>
            <div className="original-english-box">
              <span className="original-label">Original English:</span>
              <div className="chat-answer-text">
                {originalContent}
              </div>
            </div>
          </div>
        );
      }
      if (trans.status === 'number_check_failed') {
        return (
          <div className="chat-translated-fallback">
            <div className="alert alert-warning">
              Number check failed between translation and original text. Showing original English.
            </div>
            {originalContent}
          </div>
        );
      }
      if (trans.status === 'quota_blocked') {
        return (
          <div className="chat-translated-fallback">
            <div className="alert alert-warning">
              Today's free Gemini limit is used up, so translation did not run. Try again after the daily reset.
            </div>
            {originalContent}
          </div>
        );
      }
      return (
        <div className="chat-translated-fallback">
          <div className="alert alert-error">
            Translation failed. Showing original English.
          </div>
          {originalContent}
        </div>
      );
    }

    return originalContent;
  };

  const renderTurnContent = (turn, turnIndex) => {
    const status = turn.status;
    const category = turn.category;
    const flags = Array.isArray(turn.flags) ? turn.flags : [];

    // Quota blocked
    if (status === 'quota_blocked' || turn.state === 'quota_blocked' || flags.includes('quota_blocked')) {
      return (
        <div className="chat-status-message chat-quota-blocked">
          Today's free Gemini limit is used up, so this question did not run. Try again after the daily reset.
        </div>
      );
    }

    // Unverified
    if (status === 'unverified' || flags.includes('evidence_unverified_server')) {
      return (
        <div className="chat-status-message chat-unverified">
          I could not verify this answer against the document, so it is not shown.
        </div>
      );
    }

    // Not found
    if (status === 'not_found') {
      return (
        <div className="chat-status-message chat-not-found">
          Not found in this document.
        </div>
      );
    }

    // Advice / refused
    if (category === 'advice' || status === 'refused' || flags.includes('advice_refused')) {
      const neutralAdviceText =
        'This system gives document information only. It does not give legal or financial advice, so it cannot say whether to sign or accept this agreement. It can show the risks, fees, penalties or foreclosure clauses stated in the document.';
      const originalElem = <p className="chat-answer-text">{neutralAdviceText}</p>;
      return (
        <div className="chat-advice-box">
          {renderTranslatedProse(turn, turnIndex, originalElem)}
        </div>
      );
    }

    // Off topic
    if (category === 'off_topic' || status === 'off_topic' || flags.includes('off_topic_refused')) {
      const originalElem = <p className="chat-answer-text">{turn.answer}</p>;
      return (
        <div className="chat-off-topic-box">
          {renderTranslatedProse(turn, turnIndex, originalElem)}
        </div>
      );
    }

    // Explain term
    if (category === 'explain_term') {
      const originalElem = (
        <div className="chat-answer-text">
          {renderCitations(turn.answer, onJumpPage)}
        </div>
      );
      return (
        <div className="chat-explain-term-block">
          <div className="explain-term-label">
            General explanation, not from your document
          </div>
          {renderTranslatedProse(turn, turnIndex, originalElem)}
          {renderTurnEvidence(turn.evidence)}
        </div>
      );
    }

    // Calculation
    if (category === 'calculation') {
      return renderCalculationBody(turn);
    }

    // Needs retrieval or failed
    if (status === 'needs_retrieval' || status === 'failed' || flags.includes('chat_budget_reached')) {
      return (
        <div className="alert alert-error">
          {turn.answer || turn.detail || 'The system was unable to retrieve or verify information for this question.'}
        </div>
      );
    }

    // Fact query or standard ok status
    if (category === 'fact' || status === 'ok') {
      const originalElem = (
        <div className="chat-answer-text">
          {renderCitations(turn.answer, onJumpPage)}
        </div>
      );
      return (
        <div className="chat-fact-block">
          {renderTranslatedProse(turn, turnIndex, originalElem)}
          {renderTurnEvidence(turn.evidence)}
        </div>
      );
    }

    // Default fallback display
    const fallbackElem = (
      <div className="chat-answer-text">
        {renderCitations(turn.answer, onJumpPage)}
      </div>
    );
    return (
      <div className="chat-fact-block">
        {renderTranslatedProse(turn, turnIndex, fallbackElem)}
        {renderTurnEvidence(turn.evidence)}
      </div>
    );
  };

  const isNotIndependentlyVerified = (turn) => {
    return (
      turn.verifier_independent === false ||
      turn.fallback_used === true ||
      (Array.isArray(turn.flags) && turn.flags.includes('model_fallback'))
    );
  };

  return (
    <div className="task-tab-container chat-tab-container">
      {/* Title & Controls Bar */}
      <div className="tab-title-row chat-header-row">
        <h3>
          Chat <span className="tab-pill">automated output</span>
        </h3>
        <div className="chat-controls-top">
          <div className="chat-lang-picker">
            <label htmlFor="chat-lang-select" className="lang-label">
              Language:
            </label>
            <select
              id="chat-lang-select"
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
        </div>
      </div>

      {!docId && (
        <div className="card task-intro-card">
          <p className="placeholder-text">
            Please upload and process a loan agreement first to ask questions about it.
          </p>
        </div>
      )}

      {historyError && (
        <div className="alert alert-error">
          <strong>Chat History Error:</strong> {historyError}
        </div>
      )}

      {/* Chat History View */}
      {docId && (
        <div className="chat-history-container">
          {loadingHistory && turns.length === 0 && (
            <div className="chat-loading-history">
              <span>Loading saved chat history...</span>
            </div>
          )}

          {!loadingHistory && turns.length === 0 && !pendingQuestion && (
            <div className="chat-empty-state">
              <p>No questions asked yet for this document.</p>
              <span className="file-hint">
                Ask about loan terms, repayment, interest rates, EMI calculations, or general definitions.
              </span>
            </div>
          )}

          {turns.map((turn, index) => {
            const notVerified = isNotIndependentlyVerified(turn);
            const needsReview = turn.final_check === 'needs_review';

            return (
              <div key={`turn-${index}`} className="chat-turn-wrapper">
                {/* User Message Bubble */}
                <div className="chat-bubble chat-bubble-user">
                  <div className="bubble-header">
                    <span className="bubble-author">You</span>
                    {turn.timestamp && (
                      <span className="bubble-time">
                        {new Date(turn.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    )}
                  </div>
                  <div className="bubble-content">{turn.question}</div>
                </div>

                {/* Assistant Message Bubble */}
                <div className="chat-bubble chat-bubble-assistant">
                  <div className="bubble-header">
                    <div className="bubble-header-left">
                      <span className="bubble-author">Assistant</span>
                      <span className="tab-pill">automated output</span>
                      {turn.category && (
                        <span className="badge badge-category">{turn.category}</span>
                      )}
                      {notVerified && (
                        <span className="badge badge-fallback">
                          not independently verified
                        </span>
                      )}
                      {needsReview && (
                        <span className="badge badge-review">needs review</span>
                      )}
                    </div>
                  </div>

                  {turn.notice && (
                    <div className="chat-turn-notice">
                      <small>{turn.notice}</small>
                    </div>
                  )}

                  <div className="bubble-body">{renderTurnContent(turn, index)}</div>
                </div>
              </div>
            );
          })}

          {/* Pending In-Flight Question Bubble */}
          {pendingQuestion && (
            <div className="chat-turn-wrapper">
              <div className="chat-bubble chat-bubble-user">
                <div className="bubble-header">
                  <span className="bubble-author">You</span>
                </div>
                <div className="bubble-content">{pendingQuestion}</div>
              </div>

              <div className="chat-bubble chat-bubble-assistant chat-bubble-waiting">
                <div className="waiting-spinner-row">
                  <span className="spinner"></span>
                  <span>Thinking... ({clientElapsed}s)</span>
                </div>
                {clientElapsed >= 120 && (
                  <div className="alert alert-warning chat-delay-warning">
                    Taking longer than usual. OCR or complex clause analysis in progress...
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Chat Error Banner */}
      {chatError && (
        <div className="alert alert-error chat-error-banner">
          <strong>Error:</strong> {chatError}
        </div>
      )}

      {/* Input Form */}
      {docId && (
        <form onSubmit={handleSend} className="chat-input-form">
          <div className="chat-input-wrapper">
            <input
              type="text"
              className="chat-text-input"
              placeholder="Ask a question about this document..."
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              disabled={isSubmitting || !docId}
            />
            <button
              type="submit"
              className="btn btn-primary chat-send-btn"
              disabled={isSubmitting || !inputQuestion.trim() || !docId}
            >
              {isSubmitting ? `Sending (${clientElapsed}s)...` : 'Send'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
