from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import os
import shutil
from datetime import datetime
import secrets
import subprocess
import threading
import queue
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['LOG_FOLDER'] = 'logs'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'py'}
TIMEOUT = 10

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_execution(filename, output, error=None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_filename = os.path.join(app.config['LOG_FOLDER'], 'execution_logs.txt')
    
    with open(log_filename, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Filename: {filename}\n")
        f.write(f"Output:\n{output}\n")
        if error:
            f.write(f"Error:\n{error}\n")
        f.write(f"{'='*60}\n")

def enqueue_output(stream, queue, stream_type):
    try:
        for line in iter(stream.readline, ''):
            if line:
                queue.put((stream_type, line))
        stream.close()
    except:
        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only .py files are allowed'}), 400
    
    secure_filename = f"{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename)
    
    try:
        file.save(filepath)
        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': file.filename,
            'secure_filename': secure_filename
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/execute/<path:filepath>')
def execute_stream(filepath):
    def generate():
        start_time = time.time()
        output_buffer = []
        error_buffer = []
        
        try:
            import sys
            process = subprocess.Popen(
                [sys.executable, filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
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
            
            while True:
                try:
                    stream_type, line = q.get(timeout=0.1)
                    
                    if stream_type == 'stdout':
                        output_buffer.append(line)
                        yield f"data: {{'type': 'stdout', 'content': {repr(line)}}}\n\n"
                    else:
                        error_buffer.append(line)
                        yield f"data: {{'type': 'stderr', 'content': {repr(line)}}}\n\n"
                    
                except queue.Empty:
                    if process.poll() is not None:
                        break
                    
                    if time.time() > timeout_time:
                        process.kill()
                        yield f"data: {{'type': 'error', 'content': 'Execution timeout: Script exceeded {TIMEOUT} seconds'}}\n\n"
                        break
            
            process.wait(timeout=1)
            
            execution_time = round(time.time() - start_time, 3)
            
            complete_output = ''.join(output_buffer)
            complete_error = ''.join(error_buffer)
            
            original_filename = os.path.basename(filepath).split('_', 1)[1] if '_' in os.path.basename(filepath) else os.path.basename(filepath)
            log_execution(original_filename, complete_output, complete_error)
            
            yield f"data: {{'type': 'complete', 'execution_time': {execution_time}}}\n\n"
            
        except Exception as e:
            yield f"data: {{'type': 'error', 'content': {repr(str(e))}}}\n\n"
        
        finally:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/logs')
def view_logs():
    log_filename = os.path.join(app.config['LOG_FOLDER'], 'execution_logs.txt')
    
    if not os.path.exists(log_filename):
        return "No logs available yet."
    
    with open(log_filename, 'r', encoding='utf-8') as f:
        logs = f.read()
    
    return f"<pre>{logs}</pre>"

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
