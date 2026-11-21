import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from './config.js';
import SummaryTab from './SummaryTab';
import KeyInfoTab from './KeyInfoTab';
import RiskTab from './RiskTab';
import ChatTab from './ChatTab';

export default function App() {
  // Metadata & Notices
  const [meta, setMeta] = useState(null);
  const [metaError, setMetaError] = useState(null);

  // Upload State
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [docId, setDocId] = useState(null);
  const [isCached, setIsCached] = useState(false);

  // Ingestion Status & Polling
  const [docStatus, setDocStatus] = useState(null);
  const [takingLonger, setTakingLonger] = useState(false);
  const pollTimerRef = useRef(null);
  const pollStartRef = useRef(null);

  // Page Viewer State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageData, setPageData] = useState(null);
  const [loadingPage, setLoadingPage] = useState(false);
  const [pageError, setPageError] = useState(null);

  // Placeholder Tabs State
  const [activeTab, setActiveTab] = useState('summary');

  // 1. Fetch metadata on mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/meta`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setMeta(data);
      })
      .catch((err) => {
        setMetaError(err.message);
      });
  }, []);

  // Cleanup polling timer on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  // 2. Client-side validation & upload
  const handleFileChange = (e) => {
    setUploadError(null);
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadError('Please select a file to upload.');
      return;
    }

    const maxMb = meta?.max_upload_mb || 25;
    const maxBytes = maxMb * 1024 * 1024;
    if (file.size > maxBytes) {
      setUploadError(`File exceeds maximum size of ${maxMb} MB.`);
      return;
    }

    const allowed = meta?.allowed_types || ['pdf', 'html', 'txt'];
    const lowerName = file.name.toLowerCase();
    const hasValidExt = allowed.some((ext) => {
      if (ext === 'html') {
        return lowerName.endsWith('.html') || lowerName.endsWith('.htm');
      }
      return lowerName.endsWith(`.${ext}`);
    });

    if (!hasValidExt) {
      setUploadError(`Invalid file type. Allowed: ${allowed.join(', ')}`);
      return;
    }

    setUploading(true);
    setUploadError(null);
    setDocId(null);
    setIsCached(false);
    setDocStatus(null);
    setTakingLonger(false);
    setPageData(null);
    setCurrentPage(1);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE_URL}/api/documents`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `Upload failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      setDocId(data.doc_id);
      setIsCached(Boolean(data.cached));
      startPolling(data.doc_id);
    } catch (err) {
      setUploadError(err.message);
      setUploading(false);
    }
  };

  // 3. Status Polling every 1.5s
  const startPolling = (targetDocId) => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }
    pollStartRef.current = Date.now();
    setTakingLonger(false);

    const checkStatus = async () => {
      // Check 120s threshold without stopping polling
      if (pollStartRef.current && Date.now() - pollStartRef.current > 120000) {
        setTakingLonger(true);
      }

      try {
        const res = await fetch(`${API_BASE_URL}/api/documents/${targetDocId}/status`);
        if (!res.ok) {
          throw new Error(`Status check HTTP ${res.status}`);
        }
        const data = await res.json();
        setDocStatus(data);

        if (data.state === 'ready') {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          setUploading(false);
          loadPage(targetDocId, 1);
        } else if (data.state === 'failed') {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          setUploading(false);
        }
      } catch (err) {
        // Continue polling on transient network glitches
      }
    };

    checkStatus();
    pollTimerRef.current = setInterval(checkStatus, 1500);
  };

  // 4. Page Viewer Fetcher
  const loadPage = async (targetDocId, pageNum) => {
    setLoadingPage(true);
    setPageError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/documents/${targetDocId}/pages/${pageNum}`);
      if (!res.ok) {
        throw new Error(`Failed to load page ${pageNum}`);
      }
      const data = await res.json();
      setPageData(data);
      setCurrentPage(pageNum);
    } catch (err) {
      setPageError(err.message);
    } finally {
      setLoadingPage(false);
    }
  };

  const handlePrevPage = () => {
    if (docId && currentPage > 1) {
      loadPage(docId, currentPage - 1);
    }
  };

  const handleNextPage = () => {
    const total = docStatus?.pages_total || 1;
    if (docId && currentPage < total) {
      loadPage(docId, currentPage + 1);
    }
  };

  const handleJumpToPage = (pageNum) => {
    if (docId && pageNum) {
      loadPage(docId, pageNum);
      const viewer = document.getElementById('page-viewer');
      if (viewer) {
        viewer.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  const totalPages = docStatus?.pages_total || 0;
  const pagesDone = docStatus?.pages_done || 0;
  const progressPct = totalPages > 0 ? Math.min(100, Math.round((pagesDone / totalPages) * 100)) : 0;

  return (
    <div className="app-container">
      {/* Header & Notices */}
      <header className="header">
        <h1>AI Loan Agreement Analysis</h1>
        <div className="notices-banner">
          {meta ? (
            <>
              <p className="notice-item notice-privacy">
                <strong>Notice:</strong> {meta.upload_notice}
              </p>
              <p className="notice-item notice-legal">
                <strong>Disclaimer:</strong> {meta.disclaimer}
              </p>
            </>
          ) : (
            <div className="notice-fallback">
              {metaError && <p className="notice-error">Error connecting to API: {metaError}</p>}
              <p className="notice-item notice-privacy">
                Upload only public documents. Information, not legal or financial advice.
              </p>
            </div>
          )}
        </div>
      </header>

      {/* Upload Section */}
      <section className="card upload-section">
        <h2>Upload Document</h2>
        <form onSubmit={handleUpload} className="upload-form">
          <div className="file-input-wrapper">
            <input
              type="file"
              id="file-input"
              onChange={handleFileChange}
              disabled={uploading}
            />
            <span className="file-hint">
              Allowed: {meta ? meta.allowed_types.join(', ') : 'pdf, html, txt'} (Max {meta ? meta.max_upload_mb : 25} MB)
            </span>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={uploading || !file}
          >
            {uploading ? 'Processing...' : 'Upload & Analyze'}
          </button>
        </form>

        {uploadError && (
          <div className="alert alert-error">
            <strong>Upload Error:</strong> {uploadError}
          </div>
        )}
      </section>

      {/* Progress Section */}
      {docStatus && (
        <section className="card progress-section">
          <div className="progress-header">
            <h3>Ingestion Status: <span className={`badge state-${docStatus.state}`}>{docStatus.state}</span></h3>
            {isCached && <span className="badge badge-cached">Already processed</span>}
          </div>

          <div className="progress-bar-container">
            <div
              className="progress-bar-fill"
              style={{ width: `${progressPct}%` }}
            ></div>
          </div>

          <div className="progress-details">
            <span>Stage: {docStatus.stage || 'queued'}</span>
            <span>Pages: {pagesDone} / {totalPages} ({progressPct}%)</span>
          </div>

          {takingLonger && docStatus.state === 'processing' && (
            <div className="alert alert-warning">
              Processing is taking longer than usual (OCR running for complex scans). Still working...
            </div>
          )}

          {docStatus.state === 'failed' && (
            <div className="alert alert-error">
              <strong>Processing Failed:</strong> {docStatus.error || 'Unknown ingestion failure.'}
            </div>
          )}
        </section>
      )}

      {/* Ready View: Page Viewer & Document Info */}
      {docStatus?.state === 'ready' && docId && (
        <section id="page-viewer" className="card document-viewer-section">
          <div className="doc-meta-bar">
            <span><strong>Doc ID:</strong> <code>{docId}</code></span>
            <span><strong>Total Pages:</strong> {totalPages}</span>
            {isCached && <span className="badge badge-cached">Loaded from cache</span>}
          </div>

          <div className="page-viewer">
            <div className="page-viewer-controls">
              <button
                className="btn btn-secondary"
                onClick={handlePrevPage}
                disabled={currentPage <= 1 || loadingPage}
              >
                &larr; Previous Page
              </button>
              <span className="page-counter">
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn btn-secondary"
                onClick={handleNextPage}
                disabled={currentPage >= totalPages || loadingPage}
              >
                Next Page &rarr;
              </button>
            </div>

            {loadingPage && <div className="loading-indicator">Loading page text...</div>}

            {pageError && (
              <div className="alert alert-error">
                Failed to load page: {pageError}
              </div>
            )}

            {pageData && !loadingPage && (
              <div className="page-content-box">
                <div className="page-badges">
                  <span className={`badge quality-${pageData.quality}`}>
                    Quality: {pageData.quality}
                  </span>
                  <span className="badge badge-source">
                    Source: {pageData.source}
                  </span>
                </div>
                <pre className="page-text-preview">{pageData.text || '(Empty page text)'}</pre>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Analysis Tabs */}
      <section className="card tabs-section">
        <div className="tabs-header">
          <button
            className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
            onClick={() => setActiveTab('summary')}
          >
            Summary <span className="tab-pill">automated output</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'keyinfo' ? 'active' : ''}`}
            onClick={() => setActiveTab('keyinfo')}
          >
            Key Info <span className="tab-pill">automated output</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
          >
            Risk Analysis <span className="tab-pill">automated output</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat <span className="tab-pill">automated output</span>
          </button>
        </div>

        <div className="tab-body">
          {activeTab === 'summary' && (
            <SummaryTab docId={docId} onJumpPage={handleJumpToPage} />
          )}
          {activeTab === 'keyinfo' && (
            <KeyInfoTab docId={docId} onJumpPage={handleJumpToPage} />
          )}
          {activeTab === 'risk' && (
            <RiskTab docId={docId} onJumpPage={handleJumpToPage} />
          )}
          {activeTab === 'chat' && (
            <ChatTab docId={docId} onJumpPage={handleJumpToPage} />
          )}
        </div>
      </section>
    </div>
  );
}
