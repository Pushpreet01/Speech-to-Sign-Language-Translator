
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
import boto3
import uuid
import os
import time
from config import Config
from werkzeug.utils import secure_filename

# --- Import text processing logic ---
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
# --- End imports ---
import threading
import io
from botocore.exceptions import ClientError

app = Flask(__name__)
app.config.from_object(Config)

# Initialize AWS clients
s3_client = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
    region_name=app.config['AWS_REGION']
)

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'm4a', 'flac', 'webm', 'ogg'}

# --- Copying text processing and sign mapping logic from local_demo.py ---
SIGN_MAPPING = {
    # Multi-word phrases (these will be matched first due to greedy algorithm)
    'thank you very much': 'https://via.placeholder.com/200x200/4CAF50/white?text=THANK+YOU+VERY+MUCH',
    'how are you': 'https://via.placeholder.com/200x200/2196F3/white?text=HOW+ARE+YOU',
    'nice to meet you': 'https://via.placeholder.com/200x200/9C27B0/white?text=NICE+TO+MEET+YOU',
    'good morning': 'https://via.placeholder.com/200x200/FF9800/white?text=GOOD+MORNING',
    'good afternoon': 'https://via.placeholder.com/200x200/FFC107/black?text=GOOD+AFTERNOON',
    'good evening': 'https://via.placeholder.com/200x200/673AB7/white?text=GOOD+EVENING',
    'good night': 'https://via.placeholder.com/200x200/424242/white?text=GOOD+NIGHT',
    'thank you': 'https://via.placeholder.com/200x200/4CAF50/white?text=THANK+YOU',
    'excuse me': 'https://via.placeholder.com/200x200/FF5722/white?text=EXCUSE+ME',
    'i am': 'https://via.placeholder.com/200x200/607D8B/white?text=I+AM',
    'you are': 'https://via.placeholder.com/200x200/795548/white?text=YOU+ARE',
    'my name': 'https://via.placeholder.com/200x200/009688/white?text=MY+NAME',
    'what is': 'https://via.placeholder.com/200x200/3F51B5/white?text=WHAT+IS',
    'how much': 'https://via.placeholder.com/200x200/E91E63/white?text=HOW+MUCH',
    'where is': 'https://via.placeholder.com/200x200/8BC34A/white?text=WHERE+IS',
    'see you later': 'https://via.placeholder.com/200x200/FF9800/white?text=SEE+YOU+LATER',
    'have a nice day': 'https://via.placeholder.com/200x200/4CAF50/white?text=HAVE+NICE+DAY',
    'very much': 'https://via.placeholder.com/200x200/9E9E9E/white?text=VERY+MUCH',
    'very good': 'https://via.placeholder.com/200x200/4CAF50/white?text=VERY+GOOD',
    'please help': 'https://via.placeholder.com/200x200/FF5722/white?text=PLEASE+HELP',
    'hello world': 'https://via.placeholder.com/200x200/2196F3/white?text=HELLO+WORLD',
    'hello': 'https://via.placeholder.com/200x200/4CAF50/white?text=HELLO',
    'world': 'https://via.placeholder.com/200x200/2196F3/white?text=WORLD',
    'thank': 'https://via.placeholder.com/200x200/FF9800/white?text=THANK',
    'you': 'https://via.placeholder.com/200x200/9C27B0/white?text=YOU',
}
SORTED_SIGN_KEYS = sorted(SIGN_MAPPING.keys(), key=lambda x: len(x.split()), reverse=True)
SIGNBSL_CACHE = {}

def fetch_signbsl_video_url(word_or_phrase):
    cache_key = word_or_phrase.lower().replace(' ', '-')
    if cache_key in SIGNBSL_CACHE:
        return SIGNBSL_CACHE[cache_key]
    try:
        formatted_word = word_or_phrase.lower().replace(' ', '-')
        signbsl_url = f"https://www.signbsl.com/sign/{formatted_word}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(signbsl_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            video_tag = soup.find('video')
            if video_tag:
                source = video_tag.find('source')
                video_url = urljoin(signbsl_url, source['src'] if source else video_tag['src'])
                SIGNBSL_CACHE[cache_key] = video_url
                return video_url
        SIGNBSL_CACHE[cache_key] = None
        return None
    except Exception:
        SIGNBSL_CACHE[cache_key] = None
        return None

def create_text_fallback(word_or_phrase):
    """Create a text-based fallback for words/phrases without sign videos"""
    return f"{word_or_phrase.upper()} - NOT FOUND (Textual Representation)"

def get_sign_url(word_or_phrase):
    signbsl_url = fetch_signbsl_video_url(word_or_phrase)
    if signbsl_url:
        return signbsl_url
    
    # Fallback: return simple text
    return create_text_fallback(word_or_phrase)

def map_text_to_signs_greedy(text):
    words = text.lower().split()
    sign_sequence = []
    i = 0
    while i < len(words):
        # Process each word individually - no phrase matching
        clean_word = ''.join(char for char in words[i] if char.isalnum())
        sign_url = get_sign_url(clean_word)
        
        # Determine source based on whether it's a real BSL video or text fallback
        if 'signbsl.com' in sign_url:
            source = 'signbsl'
        else:
            source = 'text_fallback'
        
        sign_sequence.append({
            'word': clean_word, 
            'image_url': sign_url, 
            'phrase_length': 1,
            'source': source
        })
        i += 1
    return sign_sequence
# --- End of copied logic ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- Helper: Check if processed result exists in S3 ---
def processed_result_exists(job_id: str) -> bool:
    processed_key = f"{job_id}_result.json"
    try:
        s3_client.head_object(Bucket=app.config['PROCESSED_BUCKET'], Key=processed_key)
        return True
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code')
        if code in ('404', 'NoSuchKey', 'NotFound'):
            return False
        # Other errors: log and assume not found
        print(f"[status-check] Unexpected S3 error for {processed_key}: {e}")
        return False


# --- Fallback: Local transcription with faster-whisper ---
def transcribe_with_local_engine(audio_bytes: bytes, content_type: str = None):
    """Local offline fallback using Vosk. Uses ffmpeg to decode (m4a/mp3) to WAV before recognition."""
    try:
        from vosk import Model, KaldiRecognizer
        import tempfile
        import subprocess
        import wave as _wave

        # Write original bytes to temp input file
        with tempfile.NamedTemporaryFile(suffix='.input', delete=False) as in_f:
            in_f.write(audio_bytes)
            in_path = in_f.name

        # Transcode to mono 16kHz WAV using ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as out_f:
            out_path = out_f.name

        ffmpeg_cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-i', in_path,
            '-ac', '1', '-ar', '16000', out_path
        ]
        try:
            subprocess.run(ffmpeg_cmd, check=True)
        except Exception as e:
            print(f"[fallback-local] ffmpeg not found or failed to transcode: {e}. If newly installed, restart the server.")
            return None

        # Read WAV via stdlib
        try:
            with _wave.open(out_path, 'rb') as wf:
                sr = wf.getframerate()
                nframes = wf.getnframes()
                sampwidth = wf.getsampwidth()
                frames = wf.readframes(nframes)
                if sampwidth != 2:
                    print(f"[fallback-local] Unexpected sample width: {sampwidth}")
                    return None
        except Exception as e:
            print(f"[fallback-local] Failed to read transcoded WAV: {e}")
            return None

        # Load Vosk model
        model_path = os.getenv('VOSK_MODEL_PATH', 'vosk-model-small-en-us-0.15')
        if not os.path.isdir(model_path):
            print(f"[fallback-local] Vosk model not found at '{model_path}'. Download and set VOSK_MODEL_PATH.")
            return None

        model = Model(model_path)
        rec = KaldiRecognizer(model, sr)
        rec.SetWords(True)

        # Stream PCM chunks to recognizer (16-bit little-endian)
        bytes_per_sample = 2  # sampwidth ensured above
        samples_per_chunk = 4000
        step_bytes = samples_per_chunk * bytes_per_sample
        for i in range(0, len(frames), step_bytes):
            chunk = frames[i:i+step_bytes]
            rec.AcceptWaveform(chunk)

        final = rec.FinalResult()
        import json as _json
        text = _json.loads(final).get('text', '').strip()
        print(f"[fallback-local] Vosk transcription length={len(text)} chars")
        return text or None
    except Exception as e:
        print(f"[fallback-local] Exception during Vosk transcription: {e}")
        return None


# --- Background orchestrator: wait for AWS result, else fallback to HF and write result ---
def orchestrate_processing(job_id: str, audio_bytes: bytes, content_type: str, original_filename: str) -> None:
    try:
        # Prefer configured value
        total_wait_seconds = app.config.get('AWS_RESULT_WAIT_SECS') or int(os.getenv('AWS_RESULT_WAIT_SECS', '60'))
        interval_secs = 3
        waited = 0
        print(f"[orchestrator] Waiting up to {total_wait_seconds}s for AWS result for job_id={job_id}")
        while waited < total_wait_seconds:
            if processed_result_exists(job_id):
                # Inspect the existing result; if it's an error, attempt HF fallback
                processed_key = f"{job_id}_result.json"
                try:
                    obj = s3_client.get_object(Bucket=app.config['PROCESSED_BUCKET'], Key=processed_key)
                    payload = obj['Body'].read().decode('utf-8')
                    current = json.loads(payload)
                except Exception as e:
                    print(f"[orchestrator] Failed to read existing result for job_id={job_id}: {e}")
                    current = None

                if isinstance(current, dict) and current.get('status') == 'error':
                    print(f"[orchestrator] AWS result indicates error for job_id={job_id}; proceeding with local fallback")
                    break  # exit wait loop to fallback

                print(f"[orchestrator] AWS result detected for job_id={job_id}")
                return
            time.sleep(interval_secs)
            waited += interval_secs

        print(f"[orchestrator] AWS result not found in {total_wait_seconds}s. Falling back to local engine (Vosk) for job_id={job_id}")
        transcription_text = transcribe_with_local_engine(audio_bytes, content_type)
        if not transcription_text:
            print(f"[orchestrator] Local fallback failed or returned empty transcription for job_id={job_id}")
            return

        sign_sequence = map_text_to_signs_greedy(transcription_text)
        result = {
            'job_id': job_id,
            'transcribed_text': transcription_text,
            'sign_sequence': sign_sequence,
            'status': 'completed',
            'source': 'local_vosk',
            'original_filename': original_filename,
        }
        processed_key = f"{job_id}_result.json"
        s3_client.put_object(
            Bucket=app.config['PROCESSED_BUCKET'],
            Key=processed_key,
            Body=json.dumps(result),
            ContentType='application/json'
        )
        print(f"[orchestrator] HF fallback result uploaded to s3://{app.config['PROCESSED_BUCKET']}/{processed_key}")
    except Exception as e:
        print(f"[orchestrator] Exception in fallback orchestrator for job_id={job_id}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    """Process text input directly without file upload"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'})
        
        job_id = uuid.uuid4().hex
        sign_sequence = map_text_to_signs_greedy(text)
        
        result = {
            'job_id': job_id,
            'transcribed_text': text,
            'sign_sequence': sign_sequence,
            'status': 'completed'
        }
        
        # Since this is text-based, we can "store" the result directly in a way
        # the frontend can fetch it. For simplicity in the AWS version, we'll
        # upload this small JSON to the processed bucket, just like the Lambda.
        s3_client.put_object(
            Bucket=app.config['PROCESSED_BUCKET'],
            Key=f"{job_id}_result.json",
            Body=json.dumps(result),
            ContentType='application/json'
        )
        
        return jsonify({
            'success': True,
            'job_id': job_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Text processing failed: {str(e)}'
        })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['audio_file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        try:
            # Read bytes once so we can both upload to S3 and keep for potential fallback
            file.seek(0)
            audio_bytes = file.read()
            content_type = file.content_type or 'application/octet-stream'

            # Upload to S3 (use BytesIO since we already consumed the stream)
            s3_client.upload_fileobj(
                io.BytesIO(audio_bytes),
                app.config['UPLOAD_BUCKET'],
                unique_filename,
                ExtraArgs={'ContentType': content_type}
            )

            # Start background watcher to fallback if AWS doesn't produce a result in time
            job_id = unique_filename.split('.')[0]
            thread = threading.Thread(
                target=orchestrate_processing,
                args=(job_id, audio_bytes, content_type, filename),
                daemon=True,
            )
            thread.start()

            # Optionally wait synchronously until result is available, then return redirect info
            wait_param = (request.args.get('wait') or '').lower() in ('1', 'true', 'yes')
            if wait_param:
                # Wait long enough for AWS to respond and, if needed, for local fallback to overwrite
                max_wait = (app.config.get('AWS_RESULT_WAIT_SECS') or 60) + 120
                waited = 0
                interval = 2
                # Update progress message on server logs while we wait
                while waited < max_wait:
                    if processed_result_exists(job_id):
                        # Inspect the file to ensure it is not an AWS error; if error, keep waiting for Vosk overwrite
                        processed_key = f"{job_id}_result.json"
                        try:
                            obj = s3_client.get_object(Bucket=app.config['PROCESSED_BUCKET'], Key=processed_key)
                            payload = obj['Body'].read().decode('utf-8')
                            current = json.loads(payload)
                            status_val = (current or {}).get('status')
                            # If status is not 'error', we can redirect now (covers AWS success or local_vosk success)
                            if status_val and status_val.lower() != 'error':
                                return jsonify({
                                    'success': True,
                                    'job_id': job_id,
                                    'ready': True,
                                    'redirect_url': url_for('show_results', job_id=job_id)
                                })
                            # Else keep waiting for local overwrite
                        except Exception:
                            # If we fail to read/parse, keep waiting
                            pass
                    time.sleep(interval)
                    waited += interval
                # Timed out waiting; fall back to client-side polling
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    'ready': False,
                    'message': 'Processing... you can continue polling for status.'
                })

            # Default: immediate response for client-side polling
            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': 'File uploaded successfully. Processing...'
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Upload failed: {str(e)}'
            })
    
    return jsonify({
        'success': False,
        'message': 'Invalid file type. Please upload audio files only.'
    })

@app.route('/status/<job_id>')
def check_status(job_id):
    try:
        # Check if processed file exists
        processed_key = f"{job_id}_result.json"
        
        try:
            response = s3_client.get_object(
                Bucket=app.config['PROCESSED_BUCKET'],
                Key=processed_key
            )
            
            # File exists, processing is complete
            import json
            result = json.loads(response['Body'].read().decode('utf-8'))
            # If AWS wrote an error result, signal 'processing' so client continues waiting for local overwrite
            if isinstance(result, dict) and result.get('status') and str(result.get('status')).lower() == 'error':
                return jsonify({
                    'status': 'processing',
                    'message': 'AWS processing error detected. Retrying locally...'
                })
            return jsonify({
                'status': 'completed',
                'result': result
            })
        
        except s3_client.exceptions.NoSuchKey:
            # File doesn't exist yet, still processing
            return jsonify({
                'status': 'processing',
                'message': 'Your audio is being processed...'
            })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error checking status: {str(e)}'
        })

@app.route('/results/<job_id>')
def show_results(job_id):
    return render_template('results.html', job_id=job_id)

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=True, host='0.0.0.0', port=port)
