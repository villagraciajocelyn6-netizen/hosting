# 🐍 Python Script Executor - Live Terminal

A web application for executing Python scripts with real-time streaming output.

## Features

- Upload Python (.py) files through web interface
- Live streaming terminal output as scripts execute
- Real-time display of stdout and stderr
- No code restrictions or filtering
- 10-second execution timeout
- Automatic file cleanup after execution
- Execution logging
- Terminal-style output display

## Technology Stack

- **Backend**: Flask, Python 3.11+
- **Process Management**: subprocess.Popen with streaming
- **Real-time Communication**: Server-Sent Events (SSE)
- **Web Server**: Gunicorn
- **Frontend**: HTML, CSS, Vanilla JavaScript

## Local Installation

### Prerequisites

- Python 3.11 or higher
- pip

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd python-executor
