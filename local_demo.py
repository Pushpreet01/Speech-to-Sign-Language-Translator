#!/usr/bin/env python3
"""
Local Demo Version - Speech-to-Sign MVP
This version runs without AWS for quick testing and demonstration
"""

from flask import Flask, request, render_template, jsonify
import os
import uuid
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'demo-secret-key'

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'demo_results'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'm4a', 'flac'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Enhanced sign language mapping with phrases and individual words
# Inspired by signbsl.com structure - phrases take priority over individual words
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
    
    # Two-word combinations
    'very much': 'https://via.placeholder.com/200x200/9E9E9E/white?text=VERY+MUCH',
    'very good': 'https://via.placeholder.com/200x200/4CAF50/white?text=VERY+GOOD',
    'please help': 'https://via.placeholder.com/200x200/FF5722/white?text=PLEASE+HELP',
    'hello world': 'https://via.placeholder.com/200x200/2196F3/white?text=HELLO+WORLD',
    
    # Individual words (fallback when no phrases match)
    'hello': 'https://via.placeholder.com/200x200/4CAF50/white?text=HELLO',
    'world': 'https://via.placeholder.com/200x200/2196F3/white?text=WORLD',
    'thank': 'https://via.placeholder.com/200x200/FF9800/white?text=THANK',
    'you': 'https://via.placeholder.com/200x200/9C27B0/white?text=YOU',
    'please': 'https://via.placeholder.com/200x200/607D8B/white?text=PLEASE',
    'sorry': 'https://via.placeholder.com/200x200/F44336/white?text=SORRY',
    'yes': 'https://via.placeholder.com/200x200/4CAF50/white?text=YES',
    'no': 'https://via.placeholder.com/200x200/F44336/white?text=NO',
    'good': 'https://via.placeholder.com/200x200/4CAF50/white?text=GOOD',
    'morning': 'https://via.placeholder.com/200x200/FF9800/white?text=MORNING',
    'afternoon': 'https://via.placeholder.com/200x200/FFC107/black?text=AFTERNOON',
    'evening': 'https://via.placeholder.com/200x200/673AB7/white?text=EVENING',
    'night': 'https://via.placeholder.com/200x200/424242/white?text=NIGHT',
    'help': 'https://via.placeholder.com/200x200/FF5722/white?text=HELP',
    'water': 'https://via.placeholder.com/200x200/2196F3/white?text=WATER',
    'food': 'https://via.placeholder.com/200x200/FF9800/white?text=FOOD',
    'home': 'https://via.placeholder.com/200x200/795548/white?text=HOME',
    'work': 'https://via.placeholder.com/200x200/607D8B/white?text=WORK',
    'family': 'https://via.placeholder.com/200x200/E91E63/white?text=FAMILY',
    'friend': 'https://via.placeholder.com/200x200/9C27B0/white?text=FRIEND',
    'love': 'https://via.placeholder.com/200x200/E91E63/white?text=LOVE',
    'happy': 'https://via.placeholder.com/200x200/FFEB3B/black?text=HAPPY',
    'sad': 'https://via.placeholder.com/200x200/3F51B5/white?text=SAD',
    'name': 'https://via.placeholder.com/200x200/009688/white?text=NAME',
    'time': 'https://via.placeholder.com/200x200/795548/white?text=TIME',
    'today': 'https://via.placeholder.com/200x200/4CAF50/white?text=TODAY',
    'tomorrow': 'https://via.placeholder.com/200x200/2196F3/white?text=TOMORROW',
    'yesterday': 'https://via.placeholder.com/200x200/9E9E9E/white?text=YESTERDAY',
    'very': 'https://via.placeholder.com/200x200/795548/white?text=VERY',
    'much': 'https://via.placeholder.com/200x200/607D8B/white?text=MUCH',
    'how': 'https://via.placeholder.com/200x200/FF9800/white?text=HOW',
    'what': 'https://via.placeholder.com/200x200/9C27B0/white?text=WHAT',
    'where': 'https://via.placeholder.com/200x200/4CAF50/white?text=WHERE',
    'when': 'https://via.placeholder.com/200x200/2196F3/white?text=WHEN',
    'why': 'https://via.placeholder.com/200x200/F44336/white?text=WHY',
    'nice': 'https://via.placeholder.com/200x200/4CAF50/white?text=NICE',
    'meet': 'https://via.placeholder.com/200x200/FF9800/white?text=MEET',
    'see': 'https://via.placeholder.com/200x200/2196F3/white?text=SEE',
    'later': 'https://via.placeholder.com/200x200/607D8B/white?text=LATER',
    'day': 'https://via.placeholder.com/200x200/FFEB3B/black?text=DAY',
    'have': 'https://via.placeholder.com/200x200/9C27B0/white?text=HAVE',
    'is': 'https://via.placeholder.com/200x200/795548/white?text=IS',
    'am': 'https://via.placeholder.com/200x200/4CAF50/white?text=AM',
    'are': 'https://via.placeholder.com/200x200/2196F3/white?text=ARE',
    'my': 'https://via.placeholder.com/200x200/FF5722/white?text=MY',
    'your': 'https://via.placeholder.com/200x200/9E9E9E/white?text=YOUR',
    'i': 'https://via.placeholder.com/200x200/E91E63/white?text=I',
    'me': 'https://via.placeholder.com/200x200/673AB7/white?text=ME',
    'we': 'https://via.placeholder.com/200x200/3F51B5/white?text=WE',
    'they': 'https://via.placeholder.com/200x200/009688/white?text=THEY'
}

# Pre-sorted keys for efficient phrase-first matching
SORTED_SIGN_KEYS = sorted(SIGN_MAPPING.keys(), key=lambda x: len(x.split()), reverse=True)

# Cache for SignBSL.com video URLs to avoid repeated requests
SIGNBSL_CACHE = {}

def fetch_signbsl_video_url(word_or_phrase):
    """
    Fetch real sign language video URL from SignBSL.com
    """
    # Check cache first
    cache_key = word_or_phrase.lower().replace(' ', '-')
    if cache_key in SIGNBSL_CACHE:
        return SIGNBSL_CACHE[cache_key]
    
    try:
        # Construct URL for SignBSL.com
        # Replace spaces with hyphens for URL format
        formatted_word = word_or_phrase.lower().replace(' ', '-')
        signbsl_url = f"https://www.signbsl.com/sign/{formatted_word}"
        
        # Set headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Make request with timeout
        response = requests.get(signbsl_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for video elements in various formats
            video_url = None
            
            # Try to find video tags
            video_tag = soup.find('video')
            if video_tag:
                source = video_tag.find('source')
                if source and source.get('src'):
                    video_url = urljoin(signbsl_url, source.get('src'))
                elif video_tag.get('src'):
                    video_url = urljoin(signbsl_url, video_tag.get('src'))
            
            # Try to find iframe embeds (YouTube, Vimeo, etc.)
            if not video_url:
                iframe = soup.find('iframe')
                if iframe and iframe.get('src'):
                    iframe_src = iframe.get('src')
                    # Check if it's a video embed
                    if any(domain in iframe_src for domain in ['youtube.com', 'vimeo.com', 'player.vimeo.com']):
                        video_url = iframe_src
            
            # Try to find any media elements with video-related URLs
            if not video_url:
                # Look for any links or sources that might contain video URLs
                for element in soup.find_all(['a', 'source', 'embed']):
                    href_or_src = element.get('href') or element.get('src')
                    if href_or_src and any(ext in href_or_src.lower() for ext in ['.mp4', '.webm', '.ogv', 'video']):
                        video_url = urljoin(signbsl_url, href_or_src)
                        break
            
            # If we found a video URL, cache and return it
            if video_url:
                SIGNBSL_CACHE[cache_key] = video_url
                print(f"✅ Found SignBSL video for '{word_or_phrase}': {video_url}")
                return video_url
            else:
                # No video found, cache the failure
                print(f"⚠️ No video found for '{word_or_phrase}' on SignBSL.com")
                SIGNBSL_CACHE[cache_key] = None
                return None
        else:
            print(f"⚠️ SignBSL.com returned status {response.status_code} for '{word_or_phrase}'")
            SIGNBSL_CACHE[cache_key] = None
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching from SignBSL.com for '{word_or_phrase}': {str(e)}")
        SIGNBSL_CACHE[cache_key] = None
        return None
    except Exception as e:
        print(f"❌ Unexpected error for '{word_or_phrase}': {str(e)}")
        SIGNBSL_CACHE[cache_key] = None
        return None

def get_sign_url(word_or_phrase):
    """
    Get sign URL - first try SignBSL.com, then fall back to our static mapping
    """
    # First try to get real sign from SignBSL.com
    signbsl_url = fetch_signbsl_video_url(word_or_phrase)
    if signbsl_url:
        return signbsl_url
    
    # Fall back to our placeholder mapping
    if word_or_phrase in SIGN_MAPPING:
        return SIGN_MAPPING[word_or_phrase]
    
    # Default fallback
    return 'https://via.placeholder.com/200x200/9E9E9E/white?text=?'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def mock_transcription(filename):
    """Mock transcription based on filename - designed to showcase phrase-first matching"""
    filename_lower = filename.lower()
    
    # Demo transcriptions that demonstrate phrase-first matching
    if 'hello' in filename_lower:
        return "hello world thank you very much"
    elif 'good' in filename_lower or 'morning' in filename_lower:
        return "good morning how are you today have a nice day"
    elif 'help' in filename_lower:
        return "excuse me please help where is my name"
    elif 'test' in filename_lower:
        return "this is a test thank you very much see you later"
    elif 'meet' in filename_lower:
        return "hello nice to meet you what is your name"
    elif 'phrase' in filename_lower:
        return "thank you very much good morning how are you nice to meet you"
    else:
        return "hello world good morning thank you very much how are you"

def map_text_to_signs_greedy(text):
    """
    Advanced greedy phrase-first mapping algorithm
    Matches the longest possible phrases first, then falls back to individual words
    """
    words = text.lower().split()
    sign_sequence = []
    i = 0
    
    while i < len(words):
        matched = False
        
        # Try to match phrases starting from current position
        # SORTED_SIGN_KEYS is already sorted by length (longest first)
        for phrase_key in SORTED_SIGN_KEYS:
            phrase_words = phrase_key.split()
            phrase_length = len(phrase_words)
            
            # Check if we have enough words left to match this phrase
            if i + phrase_length <= len(words):
                # Check if the words match the phrase
                text_slice = words[i:i + phrase_length]
                if text_slice == phrase_words:
                    # Found a match!
                    sign_url = get_sign_url(phrase_key)
                    sign_sequence.append({
                        'word': phrase_key,
                        'original_words': text_slice,
                        'image_url': sign_url,
                        'phrase_length': phrase_length,
                        'source': 'signbsl' if 'signbsl.com' in sign_url else 'placeholder'
                    })
                    i += phrase_length  # Skip ahead by the length of the matched phrase
                    matched = True
                    break
        
        if not matched:
            # No phrase matched, try individual word
            unknown_word = words[i]
            clean_word = ''.join(char for char in unknown_word if char.isalnum())
            sign_url = get_sign_url(clean_word)
            
            sign_sequence.append({
                'word': clean_word,
                'original_words': [unknown_word],
                'image_url': sign_url,
                'phrase_length': 1,
                'source': 'signbsl' if 'signbsl.com' in sign_url else 'placeholder'
            })
            i += 1  # Move to next word
    
    return sign_sequence

def process_audio_mock(job_id, filename):
    """Mock audio processing with enhanced phrase-first mapping"""
    # Simulate processing delay
    time.sleep(2)
    
    # Mock transcription
    transcribed_text = mock_transcription(filename)
    
    # Map to signs using greedy phrase-first algorithm
    sign_sequence = map_text_to_signs_greedy(transcribed_text)
    
    # Save results
    result = {
        'job_id': job_id,
        'transcribed_text': transcribed_text,
        'sign_sequence': sign_sequence,
        'status': 'completed',
        'algorithm': 'greedy_phrase_first'
    }
    
    with open(os.path.join(RESULTS_FOLDER, f"{job_id}_result.json"), 'w') as f:
        json.dump(result, f)

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
            return jsonify({
                'success': False,
                'message': 'No text provided'
            })
        
        # Generate job ID
        job_id = uuid.uuid4().hex
        
        # Process text directly using our algorithm
        sign_sequence = map_text_to_signs_greedy(text)
        
        # Save results immediately (no delay needed for text processing)
        result = {
            'job_id': job_id,
            'transcribed_text': text,
            'sign_sequence': sign_sequence,
            'status': 'completed',
            'algorithm': 'greedy_phrase_first',
            'source': 'text_input'
        }
        
        with open(os.path.join(RESULTS_FOLDER, f"{job_id}_result.json"), 'w') as f:
            json.dump(result, f)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Text processed successfully'
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
        unique_filename = f"{job_id}_{filename}"
        
        # Save file locally
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Start background processing (in a real app, use Celery or similar)
        import threading
        thread = threading.Thread(target=process_audio_mock, args=(job_id, filename))
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'File uploaded successfully. Processing...'
        })
    
    return jsonify({
        'success': False,
        'message': 'Invalid file type. Please upload audio files only.'
    })

@app.route('/status/<job_id>')
def check_status(job_id):
    result_file = os.path.join(RESULTS_FOLDER, f"{job_id}_result.json")
    
    if os.path.exists(result_file):
        with open(result_file, 'r') as f:
            result = json.load(f)
        return jsonify({
            'status': 'completed',
            'result': result
        })
    else:
        return jsonify({
            'status': 'processing',
            'message': 'Your audio is being processed...'
        })

@app.route('/results/<job_id>')
def show_results(job_id):
    return render_template('results.html', job_id=job_id)

if __name__ == '__main__':
    print("🤟 Speech-to-Sign Demo Mode")
    print("=" * 40)
    print("Running in LOCAL DEMO mode (no AWS required)")
    print("This version uses mock transcription for demonstration")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
