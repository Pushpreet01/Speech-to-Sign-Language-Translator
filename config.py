import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # S3 Bucket Names
    UPLOAD_BUCKET = os.getenv('UPLOAD_BUCKET', 'stt-upload-bucket')
    PROCESSED_BUCKET = os.getenv('PROCESSED_BUCKET', 'stt-processed-bucket')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Hugging Face Fallback Configuration
    HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')
    HUGGINGFACE_ASR_MODEL = os.getenv('HUGGINGFACE_ASR_MODEL', 'distil-whisper/distil-small.en')

    # Orchestrator wait time for AWS results before falling back (seconds)
    try:
        AWS_RESULT_WAIT_SECS = int(os.getenv('AWS_RESULT_WAIT_SECS', '60'))
    except ValueError:
        AWS_RESULT_WAIT_SECS = 60
