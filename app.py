
from flask import Flask, request, render_template, jsonify
import uuid
import os
import io
import json
import tempfile
import subprocess
import wave as _wave
import threading
from config import Config
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Import text processing logic ---
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
# --- End imports ---

app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'm4a', 'flac', 'webm', 'ogg'}
VOSK_MODEL = None

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
SIGNBSL_CACHE = {}
SIGNBSL_HTTP_META = {}
SIGNBSL_LOCK = threading.Lock()
REQUESTS_SESSION = None
MAX_PARALLEL_FETCHES = 6
PHRASE_KEYS = {k for k in SIGN_MAPPING.keys() if " " in k}
MAX_PHRASE_LEN = max((len(k.split()) for k in PHRASE_KEYS), default=1)


def get_requests_session():
    """Create a pooled HTTP session once and reuse it."""
    global REQUESTS_SESSION
    if REQUESTS_SESSION is not None:
        return REQUESTS_SESSION

    session = requests.Session()
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        backoff_factor=0.1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    REQUESTS_SESSION = session
    return REQUESTS_SESSION


def normalize_word(word: str) -> str:
    return ''.join(char for char in word.lower() if char.isalnum())


def phrase_first_tokens(text: str):
    """Greedy phrase-first tokenization, then fallback to single words."""
    raw_words = text.lower().split()
    words = [normalize_word(w) for w in raw_words]
    words = [w for w in words if w]
    tokens = []
    i = 0

    while i < len(words):
        matched = None
        max_len = min(MAX_PHRASE_LEN, len(words) - i)
        for length in range(max_len, 1, -1):
            candidate = " ".join(words[i:i + length])
            if candidate in PHRASE_KEYS:
                matched = candidate
                break

        if matched:
            tokens.append((matched, len(matched.split())))
            i += len(matched.split())
        else:
            tokens.append((words[i], 1))
            i += 1

    return tokens

def fetch_signbsl_video_url(word_or_phrase):
    normalized = word_or_phrase.lower().strip()
    cache_key = normalized.replace(' ', '-')
    session = get_requests_session()
    headers = {'User-Agent': 'Mozilla/5.0'}

    with SIGNBSL_LOCK:
        meta = SIGNBSL_HTTP_META.get(cache_key, {})
        if meta.get('etag'):
            headers['If-None-Match'] = meta['etag']
        if meta.get('last_modified'):
            headers['If-Modified-Since'] = meta['last_modified']

    signbsl_url = f"https://www.signbsl.com/sign/{cache_key}"
    try:
        response = session.get(signbsl_url, headers=headers, timeout=(2, 5))
        if response.status_code == 304:
            with SIGNBSL_LOCK:
                return SIGNBSL_CACHE.get(cache_key)

        with SIGNBSL_LOCK:
            SIGNBSL_HTTP_META[cache_key] = {
                'etag': response.headers.get('ETag'),
                'last_modified': response.headers.get('Last-Modified'),
            }

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            video_tag = soup.find('video')
            if video_tag:
                source = video_tag.find('source')
                video_url = urljoin(signbsl_url, source['src'] if source else video_tag['src'])
                with SIGNBSL_LOCK:
                    SIGNBSL_CACHE[cache_key] = video_url
                return video_url

        with SIGNBSL_LOCK:
            SIGNBSL_CACHE[cache_key] = None
        return None
    except Exception:
        # If request failed but we have a previous value, reuse it.
        with SIGNBSL_LOCK:
            if cache_key in SIGNBSL_CACHE:
                return SIGNBSL_CACHE[cache_key]
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
    tokens = phrase_first_tokens(text)
    sign_sequence = []
    unique_terms = {}
    for token, _phrase_len in tokens:
        unique_terms[token] = None

    if unique_terms:
        worker_count = min(MAX_PARALLEL_FETCHES, len(unique_terms))
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            future_map = {pool.submit(get_sign_url, term): term for term in unique_terms}
            for future in as_completed(future_map):
                term = future_map[future]
                try:
                    unique_terms[term] = future.result()
                except Exception:
                    unique_terms[term] = create_text_fallback(term)

    for token, phrase_len in tokens:
        sign_url = unique_terms.get(token) or create_text_fallback(token)
        source = 'signbsl' if ('signbsl.com' in sign_url) else 'text_fallback'
        sign_sequence.append({
            'word': token,
            'image_url': sign_url,
            'phrase_length': phrase_len,
            'source': source
        })

    return sign_sequence
# --- End of copied logic ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_vosk_model():
    """Load Vosk model once per process and reuse it across requests."""
    global VOSK_MODEL
    if VOSK_MODEL is not None:
        return VOSK_MODEL

    try:
        from vosk import Model
    except Exception as e:
        print(f"[fallback-local] Failed to import vosk: {e}")
        return None

    model_path = os.getenv('VOSK_MODEL_PATH', 'vosk-model-small-en-us-0.15')
    if not os.path.isdir(model_path):
        print(f"[fallback-local] Vosk model not found at '{model_path}'. Download and set VOSK_MODEL_PATH.")
        return None

    try:
        VOSK_MODEL = Model(model_path)
        print(f"[fallback-local] Vosk model loaded from: {model_path}")
        return VOSK_MODEL
    except Exception as e:
        print(f"[fallback-local] Failed to load Vosk model: {e}")
        return None


# --- Local transcription with Vosk ---
def transcribe_with_local_engine(audio_bytes: bytes, content_type: str = None):
    """Local offline transcription with a WAV fast-path and ffmpeg fallback."""
    in_path = None
    out_path = None
    try:
        from vosk import KaldiRecognizer
        model = get_vosk_model()
        if model is None:
            return None

        frames = None
        sr = None

        # Fast-path: if input is already mono PCM16 WAV at 16kHz, skip ffmpeg.
        try:
            with _wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                is_pcm16_mono_16k = (
                    wf.getnchannels() == 1
                    and wf.getsampwidth() == 2
                    and wf.getframerate() == 16000
                    and wf.getcomptype() == 'NONE'
                )
                if is_pcm16_mono_16k:
                    sr = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
        except Exception:
            # Not a compatible WAV; will transcode below.
            pass

        if frames is None:
            # Transcode unsupported formats to mono 16kHz WAV using ffmpeg.
            with tempfile.NamedTemporaryFile(suffix='.input', delete=False) as in_f:
                in_f.write(audio_bytes)
                in_path = in_f.name

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

            with _wave.open(out_path, 'rb') as wf:
                sr = wf.getframerate()
                nframes = wf.getnframes()
                sampwidth = wf.getsampwidth()
                frames = wf.readframes(nframes)
                if sampwidth != 2:
                    print(f"[fallback-local] Unexpected sample width: {sampwidth}")
                    return None

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
        text = json.loads(final).get('text', '').strip()
        print(f"[fallback-local] Vosk transcription length={len(text)} chars")
        return text or None
    except Exception as e:
        print(f"[fallback-local] Exception during Vosk transcription: {e}")
        return None
    finally:
        # Ensure temporary files are removed after every request.
        for path in (in_path, out_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    """Process text input directly without file upload"""
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'message': 'No text provided'})
        
        job_id = uuid.uuid4().hex
        sign_sequence = map_text_to_signs_greedy(text)
        
        result = {
            'job_id': job_id,
            'transcribed_text': text,
            'sign_sequence': sign_sequence,
            'status': 'completed',
            'source': 'text_input'
        }

        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Text processing failed: {str(e)}'
        })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'})
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        job_id = uuid.uuid4().hex
        
        try:
            file.seek(0)
            audio_bytes = file.read()
            transcription_text = transcribe_with_local_engine(audio_bytes, file.content_type)
            if not transcription_text:
                return jsonify({
                    'success': False,
                    'message': 'Could not transcribe audio. Please upload a clear, short clip.'
                })

            sign_sequence = map_text_to_signs_greedy(transcription_text)
            result = {
                'job_id': job_id,
                'transcribed_text': transcription_text,
                'sign_sequence': sign_sequence,
                'status': 'completed',
                'source': 'local_vosk',
                'original_filename': filename,
            }
            return jsonify({
                'success': True,
                'result': result
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

@app.route('/results')
def show_results():
    return render_template('results.html')

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=True, host='0.0.0.0', port=port)
