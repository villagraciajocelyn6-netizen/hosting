from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import os
import shutil
from datetime import datetime
import secrets
import subprocess
import threading
import queue
import time
import sys

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'py'}
TIMEOUT = 10

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_to_console(message, level="INFO"):
    """Log messages directly to console/terminal with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    log_message = f"[{timestamp}] [{level}] {message}"
    print(log_message, flush=True)
    sys.stdout.flush()

@app.route('/')
def index():
    log_to_console("Index page accessed")
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    log_to_console("=" * 80)
    log_to_console("FILE UPLOAD REQUEST RECEIVED")
    
    if 'file' not in request.files:
        log_to_console("No file provided in request", "ERROR")
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        log_to_console("Empty filename received", "ERROR")
        return jsonify({'error': 'No file selected'}), 400
    
    log_to_console(f"Original filename: {file.filename}")
    
    if not allowed_file(file.filename):
        log_to_console(f"Invalid file type: {file.filename}", "ERROR")
        return jsonify({'error': 'Only .py files are allowed'}), 400
    
    secure_filename = f"{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename)
    
    try:
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        log_to_console(f"File saved successfully: {secure_filename}")
        log_to_console(f"File size: {file_size} bytes")
        log_to_console(f"File path: {filepath}")
        log_to_console("=" * 80)
        
        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': file.filename,
            'secure_filename': secure_filename
        })
    except Exception as e:
        log_to_console(f"File save error: {str(e)}", "ERROR")
        log_to_console("=" * 80)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def enqueue_output(stream, queue, stream_type):
    try:
        for line in iter(stream.readline, ''):
            if line:
                queue.put((stream_type, line))
        stream.close()
    except Exception as e:
        log_to_console(f"Stream reading error ({stream_type}): {str(e)}", "ERROR")

@app.route('/execute/<path:filepath>')
def execute_stream(filepath):
    def generate():
        log_to_console("=" * 80)
        log_to_console("SCRIPT EXECUTION STARTED")
        log_to_console(f"File path: {filepath}")
        
        start_time = time.time()
        output_buffer = []
        error_buffer = []
        
        try:
            # Validate filepath exists
            if not os.path.exists(filepath):
                error_msg = f"File not found: {filepath}"
                log_to_console(error_msg, "ERROR")
                yield f"data: {{'type': 'error', 'content': {repr(error_msg)}}}\n\n"
                return
            
            log_to_console(f"Executing Python script: {os.path.basename(filepath)}")
            log_to_console(f"Python interpreter: {sys.executable}")
            
            process = subprocess.Popen(
                [sys.executable, filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            log_to_console(f"Process started with PID: {process.pid}")
            
            q = queue.Queue()
            
            stdout_thread = threading.Thread(
                target=enqueue_output,
                args=(process.stdout, q, 'stdout')
            )
            stderr_thread = threading.Thread(
                target=enqueue_output,
                args=(process.stderr, q, 'stderr')
            )
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            timeout_time = start_time + TIMEOUT
            line_count = 0
            
            while True:
                try:
                    stream_type, line = q.get(timeout=0.1)
                    line_count += 1
                    
                    if stream_type == 'stdout':
                        output_buffer.append(line)
                        log_to_console(f"[STDOUT] {line.rstrip()}", "OUTPUT")
                        yield f"data: {{'type': 'stdout', 'content': {repr(line)}}}\n\n"
                    else:
                        error_buffer.append(line)
                        log_to_console(f"[STDERR] {line.rstrip()}", "ERROR")
                        yield f"data: {{'type': 'stderr', 'content': {repr(line)}}}\n\n"
                    
                except queue.Empty:
                    if process.poll() is not None:
                        log_to_console(f"Process completed with return code: {process.returncode}")
                        break
                    
                    if time.time() > timeout_time:
                        log_to_console(f"TIMEOUT: Killing process (exceeded {TIMEOUT} seconds)", "WARNING")
                        process.kill()
                        timeout_msg = f"Execution timeout: Script exceeded {TIMEOUT} seconds"
                        yield f"data: {{'type': 'error', 'content': {repr(timeout_msg)}}}\n\n"
                        break
            
            process.wait(timeout=1)
            
            execution_time = round(time.time() - start_time, 3)
            
            complete_output = ''.join(output_buffer)
            complete_error = ''.join(error_buffer)
            
            original_filename = os.path.basename(filepath).split('_', 1)[1] if '_' in os.path.basename(filepath) else os.path.basename(filepath)
            
            # Log execution summary to console
            log_to_console("-" * 80)
            log_to_console("EXECUTION SUMMARY")
            log_to_console(f"Filename: {original_filename}")
            log_to_console(f"Execution time: {execution_time} seconds")
            log_to_console(f"Lines of output: {line_count}")
            log_to_console(f"Return code: {process.returncode}")
            log_to_console(f"Output length: {len(complete_output)} characters")
            log_to_console(f"Error length: {len(complete_error)} characters")
            
            if complete_output:
                log_to_console("-" * 40)
                log_to_console("COMPLETE STDOUT:")
                for line in complete_output.splitlines():
                    log_to_console(f"  {line}", "OUTPUT")
            
            if complete_error:
                log_to_console("-" * 40)
                log_to_console("COMPLETE STDERR:")
                for line in complete_error.splitlines():
                    log_to_console(f"  {line}", "ERROR")
            
            log_to_console("=" * 80)
            
            yield f"data: {{'type': 'complete', 'execution_time': {execution_time}}}\n\n"
            
        except Exception as e:
            error_msg = f"Execution exception: {str(e)}"
            log_to_console(error_msg, "ERROR")
            log_to_console("=" * 80)
            yield f"data: {{'type': 'error', 'content': {repr(error_msg)}}}\n\n"
        
        finally:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    log_to_console(f"File deleted: {filepath}", "CLEANUP")
                except Exception as e:
                    log_to_console(f"File deletion failed: {str(e)}", "ERROR")
            log_to_console("Execution stream closed")
            log_to_console("=" * 80 + "\n")
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/logs')
def view_logs():
    """Info page explaining console logging"""
    log_to_console("/logs endpoint accessed")
    return """
    <html>
    <head>
        <title>Console Logging Information</title>
        <style>
            body {
                font-family: 'Courier New', monospace;
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 40px;
                line-height: 1.6;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: #252526;
                padding: 30px;
                border-radius: 8px;
            }
            h1 { color: #4ec9b0; }
            h2 { color: #569cd6; margin-top: 30px; }
            .info { background: #2d2d30; padding: 15px; border-left: 4px solid #4ec9b0; margin: 20px 0; }
            code { background: #1e1e1e; padding: 2px 6px; border-radius: 3px; color: #ce9178; }
            ul { margin-left: 20px; }
            a { color: #569cd6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Console Logging Information</h1>
            
            <div class="info">
                <strong>ℹ️ All execution logs are now displayed in the terminal/console in real-time!</strong>
            </div>
            
            <h2>Where to View Logs</h2>
            <p>All logs are printed directly to <code>stdout</code> and can be viewed in:</p>
            <ul>
                <li><strong>Development:</strong> Your terminal where you run <code>python main.py</code></li>
                <li><strong>Production (Gunicorn):</strong> Server logs or stdout redirection</li>
                <li><strong>Docker/Container:</strong> <code>docker logs [container-name]</code></li>
                <li><strong>Render.com:</strong> View logs in the Render dashboard under "Logs" tab</li>
            </ul>
            
            <h2>Log Format</h2>
            <p>Each log entry includes:</p>
            <ul>
                <li><strong>Timestamp:</strong> [YYYY-MM-DD HH:MM:SS.mmm]</li>
                <li><strong>Level:</strong> [INFO|ERROR|WARNING|OUTPUT|CLEANUP]</li>
                <li><strong>Message:</strong> Detailed information about the event</li>
            </ul>
            
            <h2>What Gets Logged</h2>
            <ul>
                <li>✓ File upload events</li>
                <li>✓ File validation and security checks</li>
                <li>✓ Script execution start/end</li>
                <li>✓ Every line of stdout (script output)</li>
                <li>✓ Every line of stderr (errors/warnings)</li>
                <li>✓ Process information (PID, return code)</li>
                <li>✓ Execution time and performance metrics</li>
                <li>✓ File cleanup operations</li>
                <li>✓ Errors and exceptions</li>
            </ul>
            
            <h2>Example Log Output</h2>
            <pre style="background: #1e1e1e; padding: 15px; border-radius: 4px; overflow-x: auto;">
[2025-12-04 19:59:23.456] [INFO] ================================================================================
[2025-12-04 19:59:23.457] [INFO] FILE UPLOAD REQUEST RECEIVED
[2025-12-04 19:59:23.458] [INFO] Original filename: test_script.py
[2025-12-04 19:59:23.459] [INFO] File saved successfully: a1b2c3d4_test_script.py
[2025-12-04 19:59:23.460] [INFO] File size: 1234 bytes
[2025-12-04 19:59:23.461] [INFO] ================================================================================
[2025-12-04 19:59:23.500] [INFO] SCRIPT EXECUTION STARTED
[2025-12-04 19:59:23.501] [INFO] Process started with PID: 12345
[2025-12-04 19:59:23.502] [OUTPUT] [STDOUT] Hello, World!
[2025-12-04 19:59:23.503] [INFO] Process completed with return code: 0
[2025-12-04 19:59:23.504] [INFO] Execution time: 0.125 seconds
[2025-12-04 19:59:23.505] [CLEANUP] File deleted: uploads/a1b2c3d4_test_script.py</pre>
            
            <h2>Viewing Logs on Render.com</h2>
            <ol>
                <li>Go to your Render dashboard</li>
                <li>Select your service</li>
                <li>Click on the "Logs" tab</li>
                <li>View real-time logs streaming</li>
            </ol>
            
            <div class="info" style="border-left-color: #569cd6;">
                <strong>💡 Tip:</strong> Logs are printed with <code>flush=True</code> to ensure immediate visibility, 
                even when buffering is enabled.
            </div>
            
            <p style="margin-top: 40px;">
                <a href="/">← Back to Executor</a>
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    log_to_console("Health check performed")
    return jsonify({'status': 'healthy', 'logging': 'console'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    log_to_console("=" * 80)
    log_to_console("PYTHON SCRIPT EXECUTOR - STARTING")
    log_to_console(f"Port: {port}")
    log_to_console(f"Python version: {sys.version}")
    log_to_console(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    log_to_console(f"Max file size: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)}MB")
    log_to_console(f"Execution timeout: {TIMEOUT} seconds")
    log_to_console("Logging mode: CONSOLE OUTPUT (Real-time)")
    log_to_console("=" * 80)
    app.run(host='0.0.0.0', port=port, debug=False)
