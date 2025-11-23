# ISE — Course Special Edition (Windows / PyCharm Compatible)

This project is a specialized edition for course assignments (Option C), designed to be clear, deliverable, and runnable directly on Windows and PyCharm. It covers all key requirements: intelligent source selection, local RAG, advanced reranking, workflow engine, multimodal support, and domain-specific tools.

## Features

- Intelligent source selection and local Retrieval-Augmented Generation (RAG)
- Advanced reranking and multimodal support
- Workflow engine and domain-specific agents (finance, traffic, weather, etc.)
- LLM-powered Q&A, context management, translation
- Full-stack integration: FastAPI backend + React frontend

## Directory Structure

```
NLP-ISE-code/
├── main.py                # CLI/backend entry point
├── app.py                 # FastAPI backend (API + static file serving)
├── requirements.txt       # Python dependencies
├── rag/                   # RAG builder and upload
├── agents/                # Domain agents
├── tools/                 # Domain tools
├── utils/                 # Utilities and reranker
├── static/                # Frontend static files (index.html)
├── config/                # Configuration files
├── dataset/               # Dataset and metadata
└── test/                  # Test scripts
```

## Quick Start

### 1. Environment Setup

```bash
pip install -r requirements.txt
```

### 2. Build RAG (First Run Only)

```bash
python rag/rag_builder.py
```

### 3. Start the System

#### CLI Mode

```bash
python main.py
```

#### Web Mode (Recommended)

```bash
python app.py
```
Visit [http://localhost:5000](http://localhost:5000) for the frontend interface.

## API Endpoints

- `/api/chat` : POST, parameter `question`, returns intelligent answer
- `/api/upload` : Upload documents for local retrieval
- `/api/clear_history` : Clear conversation context

## Frontend Usage

- Access the root path to enter the React SPA interface
- Supports Markdown output for rich, readable answers

## FAQ

- **Port conflict**: If port 5000 is occupied, change it in `app.py`
- **Dependency issues**: Ensure Python >= 3.8, use a virtual environment if possible
- **Slow RAG build**: First run processes data; subsequent runs are faster
