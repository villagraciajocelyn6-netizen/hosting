# 🐍 Python Script Executor

A secure web application that allows users to upload and execute Python scripts in a sandboxed environment.

## Features

- ✅ Upload Python (.py) files through web interface
- ✅ Automatic execution in sandboxed environment
- ✅ 10-second timeout protection
- ✅ Security filters for dangerous code
- ✅ Real-time output display
- ✅ Execution logging
- ✅ Automatic file cleanup after execution
- ✅ Responsive web design

## Security Features

- Blocks dangerous operations (os.system, subprocess, eval, exec)
- Restricted import system (only safe modules allowed)
- File size limit (5MB)
- Execution timeout (10 seconds)
- Temporary isolated execution environment
- Automatic file deletion after execution

## Technology Stack

- **Backend**: Flask, Python 3.11+
- **Process Management**: subprocess with timeout
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