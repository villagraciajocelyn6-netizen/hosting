from flask import Flask, render_template, request, jsonify
import os
import shutil
from datetime import datetime
from sandbox import execute_sandbox
import secrets

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['LOG_FOLDER'] = 'logs'

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'py'}

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
    
    # Generate secure random filename
    secure_filename = f"{secrets.token_hex(8)}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename)
    
    try:
        # Save the file
        file.save(filepath)
        
        # Execute in sandbox
        output, error, execution_time = execute_sandbox(filepath)
        
        # Log execution
        log_execution(secure_filename, output, error)
        
        # Delete the file after execution
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({
            'success': True,
            'output': output,
            'error': error,
            'execution_time': execution_time,
            'filename': file.filename
        })
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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