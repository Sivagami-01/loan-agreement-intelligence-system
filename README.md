# Loan Agreement Intelligence System

## Project Overview

The Loan Agreement Intelligence System is an AI-powered application designed to help users understand and analyze loan agreement documents.

Loan agreements often contain complex legal and financial terminology that can be difficult for borrowers to understand. This project aims to simplify the process by extracting important information, generating summaries, answering questions about document content, and identifying potential risks in loan clauses.

## Problem Statement

Borrowers may find it difficult to understand lengthy loan agreements, especially when important terms and conditions are written in complex legal language. Missing or misunderstanding these clauses can lead to confusion about interest rates, repayment conditions, penalties, and other contractual obligations.

This project aims to make loan agreement analysis easier through automated document processing and AI-assisted analysis.

## Key Features

- **Document Processing:** Accepts loan agreement documents for analysis.
- **Text Extraction:** Extracts text from documents, including scanned documents through OCR support.
- **Key Information Extraction:** Identifies configured important information from loan agreements.
- **Clause Analysis:** Identifies and analyzes relevant contractual clauses.
- **Document Summarization:** Generates concise summaries of loan agreement content.
- **Question Answering:** Allows users to ask questions about the uploaded agreement.
- **Risk Assessment:** Evaluates identified clauses using configured risk categories and severity rules.
- **Translation Support:** Provides translation functionality for better accessibility.

## Technology Stack

| Component | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React 18, Vite |
| Document Processing | PyMuPDF, Tesseract OCR, BeautifulSoup |
| Retrieval | BM25 |
| AI Integration | Gemini |
| Testing | Python unittest / project tests |

## Project Architecture

The application consists of three major parts:

1. **Frontend:** React-based user interface for document uploads and interacting with analysis results.
2. **Backend:** FastAPI application that handles requests and coordinates document analysis.
3. **Core Processing Modules:** Python modules for extraction, retrieval, summarization, question answering, risk assessment, and translation.

## Project Structure

- `app/` – FastAPI backend
- `src/` – Core processing and AI modules
- `web/` – React frontend
- `config/` – Application and risk configuration
- `scripts/` – Utility, ingestion, and evaluation scripts
- `tests/` – Python tests
- `tools/` – Review tools
- `docs/` – Project documentation
- `models/` – Model-related files
- `notebooks/` – Jupyter notebooks
- `results/` – Evaluation results

## Future Enhancements

- Improve extraction accuracy for different loan agreement formats.
- Expand clause coverage and risk analysis.
- Improve multilingual document understanding.
- Enhance the user interface and reporting capabilities.

## Note

This repository contains the application source code and supporting project files. Large datasets, downloaded archives, local uploads, caches, and private documents are excluded from version control.

## Author

Sivagami G & Madhumitha S

