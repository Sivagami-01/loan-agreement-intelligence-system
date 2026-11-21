import React from 'react';

/**
 * Parses bracketed page citations like [p. 1] or [p. 1, p. 2] into interactive jump buttons.
 *
 * @param {string} text - Raw sentence or paragraph containing [p. N] markers.
 * @param {function} onJumpPage - Callback invoked with the integer page number.
 * @returns {React.ReactNode[]} Array of text snippets and button elements.
 */
export function renderCitations(text, onJumpPage) {
  if (!text || typeof text !== 'string') {
    return text || null;
  }

  const citePattern = /\[p\.\s*\d+(?:\s*,\s*(?:p\.\s*)?\d+)*\]/gi;
  const elements = [];
  let lastIndex = 0;
  let match;

  while ((match = citePattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      elements.push(text.slice(lastIndex, match.index));
    }

    const matchStr = match[0];
    const pageNumbers = (matchStr.match(/\d+/g) || []).map(Number);

    elements.push(
      <span key={`cite-${match.index}`} className="cite-wrapper">
        [
        {pageNumbers.map((page, idx) => (
          <React.Fragment key={`page-${match.index}-${idx}`}>
            {idx > 0 && ', '}
            <button
              type="button"
              className="cite-btn"
              onClick={() => onJumpPage && onJumpPage(page)}
              title={`Jump to page ${page}`}
            >
              p.{page}
            </button>
          </React.Fragment>
        ))}
        ]
      </span>
    );

    lastIndex = citePattern.lastIndex;
  }

  if (lastIndex < text.length) {
    elements.push(text.slice(lastIndex));
  }

  return elements;
}
