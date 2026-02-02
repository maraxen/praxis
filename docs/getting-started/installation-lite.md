# Lite Mode Installation

Lite Mode provides a lightweight local development environment using the FastAPI backend but replacing heavy infrastructure like PostgreSQL and Redis with local SQLite and in-memory stores.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**

## Setup Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/maraxen/praxis.git
   cd praxis
   ```

2. **Install Dependencies**

   ```bash
   uv sync
   cd praxis/web-client
   bun install
   ```

3. **Configure Lite Mode**
   Edit `praxis.ini` (or set environment variables):

   ```ini
   [praxis]
   storage_backend = sqlite
   db_url = sqlite+aiosqlite:///praxis.db
   ```

4. **Run Backend**

   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

5. **Run Frontend**

   ```bash
   cd praxis/web-client
   bun start
   ```

## Key Features

- **No Docker Required**: Run everything as native processes.
- **Full API Support**: Unlike Browser Mode, you have access to the full Python backend.
- **Zero-Config State**: State is persisted to a local `praxis.db` file.
- **Speed**: Optimized for rapid development and testing cycles.

## Troubleshooting

If you encounter database locked errors, ensure only one instance of the backend is running, as SQLite has limited concurrency support.
