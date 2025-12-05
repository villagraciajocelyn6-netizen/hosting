import subprocess
import sys
import os
import time
import tempfile
import shutil

TIMEOUT = 10  # seconds
ALLOWED_IMPORTS = {'time', 'math', 'json', 'random', 'datetime', 'collections', 'itertools', 're'}

DANGEROUS_KEYWORDS = [
    'os.system',
    'subprocess',
    'eval(',
    'exec(',
    'compile(',
    '__import__',
    'open(',
    'file(',
    'input(',
    'raw_input(',
    'execfile(',
    'reload(',
    'import os',
    'from os',
    'import subprocess',
    'from subprocess',
    'import sys',
    'import shutil',
    'from shutil',
    'import socket',
    'from socket',
    'import requests',
    'import urllib',
    'from urllib',
    'rm -',
    'sudo ',
    'curl ',
    'wget ',
]

def check_dangerous_code(filepath):
    """Check if the script contains dangerous code patterns"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content_lower = content.lower()
        
        for keyword in DANGEROUS_KEYWORDS:
            if keyword.lower() in content_lower:
                return False, f"Dangerous code detected: {keyword}"
        
        return True, None
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def execute_sandbox(filepath):
    """Execute Python script in a restricted environment"""
    start_time = time.time()
    
    # Check for dangerous code
    is_safe, danger_msg = check_dangerous_code(filepath)
    if not is_safe:
        return "", danger_msg, 0
    
    # Create temporary directory for execution
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Copy script to temp directory
        temp_script = os.path.join(temp_dir, 'script.py')
        shutil.copy2(filepath, temp_script)
        
        # Execute with restricted environment
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=temp_dir,
            env=env
        )
        
        execution_time = round(time.time() - start_time, 3)
        
        output = result.stdout
        error = result.stderr
        
        if result.returncode != 0 and not error:
            error = f"Process exited with code {result.returncode}"
        
        return output, error, execution_time
    
    except subprocess.TimeoutExpired:
        execution_time = round(time.time() - start_time, 3)
        return "", f"Execution timeout: Script exceeded {TIMEOUT} seconds", execution_time
    
    except Exception as e:
        execution_time = round(time.time() - start_time, 3)
        return "", f"Execution error: {str(e)}", execution_time
    
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except:
            pass