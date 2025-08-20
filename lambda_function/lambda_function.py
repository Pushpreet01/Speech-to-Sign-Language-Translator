import json
import boto3
import urllib.parse
import os
from typing import List, Dict
import time # Added for polling

# Initialize AWS clients
s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')

# Configuration
PROCESSED_BUCKET = os.environ.get('PROCESSED_BUCKET', 'stt-processed-bucket')
TRANSCRIBE_BUCKET = os.environ.get('UPLOAD_BUCKET', 'stt-upload-bucket')

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
    'see you later': 'https://via.placeholder.com/200x200/FF9800/white?text=SEE+YOU+LATER',
    'have a nice day': 'https://via.placeholder.com/200x200/4CAF50/white?text=HAVE+NICE+DAY',
    'my name': 'https://via.placeholder.com/200x200/009688/white?text=MY+NAME',
    'what is': 'https://via.placeholder.com/200x200/3F51B5/white?text=WHAT+IS',
    'where is': 'https://via.placeholder.com/200x200/8BC34A/white?text=WHERE+IS',
    
    # Two-word combinations
    'very much': 'https://via.placeholder.com/200x200/9E9E9E/white?text=VERY+MUCH',
    'hello world': 'https://via.placeholder.com/200x200/2196F3/white?text=HELLO+WORLD',
    'please help': 'https://via.placeholder.com/200x200/FF5722/white?text=PLEASE+HELP',
    
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
    'nice': 'https://via.placeholder.com/200x200/4CAF50/white?text=NICE',
    'meet': 'https://via.placeholder.com/200x200/FF9800/white?text=MEET',
    'see': 'https://via.placeholder.com/200x200/2196F3/white?text=SEE',
    'later': 'https://via.placeholder.com/200x200/607D8B/white?text=LATER',
    'day': 'https://via.placeholder.com/200x200/FFEB3B/black?text=DAY',
    'have': 'https://via.placeholder.com/200x200/9C27B0/white?text=HAVE',
    'is': 'https://via.placeholder.com/200x200/795548/white?text=IS',
    'my': 'https://via.placeholder.com/200x200/FF5722/white?text=MY',
    'me': 'https://via.placeholder.com/200x200/673AB7/white?text=ME',
    'excuse': 'https://via.placeholder.com/200x200/FF5722/white?text=EXCUSE'
}

# Pre-sorted keys for efficient phrase-first matching
SORTED_SIGN_KEYS = sorted(SIGN_MAPPING.keys(), key=lambda x: len(x.split()), reverse=True)

def lambda_handler(event, context):
    """
    AWS Lambda handler for processing audio files uploaded to S3
    """
    try:
        # Parse S3 event
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
            
            print(f"Processing file: {key} from bucket: {bucket}")
            
            # Start transcription job
            job_name = key.split('.')[0]  # Remove file extension
            transcription_text = start_transcription_job(bucket, key, job_name)
            
            if transcription_text:
                # Map text to sign language
                sign_sequence = map_text_to_signs(transcription_text)
                
                # Save results to processed bucket
                save_results(job_name, transcription_text, sign_sequence)
                
                print(f"Successfully processed {key}")
            else:
                print(f"Failed to transcribe {key}")
                save_error_result(job_name, "Failed to transcribe audio")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Processing completed successfully')
        }
        
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def start_transcription_job(bucket: str, key: str, job_name: str) -> str:
    """
    Start AWS Transcribe job and wait for completion
    """
    try:
        # Generate S3 URI for the audio file
        s3_uri = f"s3://{bucket}/{key}"
        
        # Start the transcription job
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat=key.split('.')[-1],  # Infer format from file extension
            LanguageCode='en-US',
            OutputBucketName=PROCESSED_BUCKET, # Store transcribe output in processed bucket
            OutputKey=f"transcripts/{job_name}.json"
        )

        print(f"Started transcription job: {job_name}")

        # Poll for job completion
        while True:
            status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            
            if job_status in ['COMPLETED', 'FAILED']:
                print(f"Transcription job {job_name} finished with status: {job_status}")
                break
            
            print(f"Job {job_name} is still {job_status}... waiting.")
            time.sleep(5) # Wait for 5 seconds before checking again

        if job_status == 'COMPLETED':
            # Get the transcript content
            transcript_key = f"transcripts/{job_name}.json"
            transcript_object = s3_client.get_object(Bucket=PROCESSED_BUCKET, Key=transcript_key)
            transcript_content = json.loads(transcript_object['Body'].read().decode('utf-8'))
            
            # Extract the transcribed text
            transcription_text = transcript_content['results']['transcripts'][0]['transcript']
            return transcription_text
        else:
            print(f"Transcription job {job_name} failed.")
            return None
        
    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return None

def map_text_to_signs(text: str) -> List[Dict]:
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
                    sign_sequence.append({
                        'word': phrase_key,
                        'original_words': text_slice,
                        'image_url': SIGN_MAPPING[phrase_key],
                        'phrase_length': phrase_length
                    })
                    i += phrase_length  # Skip ahead by the length of the matched phrase
                    matched = True
                    break
        
        if not matched:
            # No phrase matched, treat as unknown word
            unknown_word = words[i]
            clean_word = ''.join(char for char in unknown_word if char.isalnum())
            sign_sequence.append({
                'word': clean_word,
                'original_words': [unknown_word],
                'image_url': 'https://via.placeholder.com/200x200/9E9E9E/white?text=?',
                'phrase_length': 1
            })
            i += 1  # Move to next word
    
    return sign_sequence

def save_results(job_name: str, transcribed_text: str, sign_sequence: List[Dict]):
    """
    Save processing results to S3
    """
    try:
        result = {
            'job_id': job_name,
            'transcribed_text': transcribed_text,
            'sign_sequence': sign_sequence,
            'timestamp': context.aws_request_id if 'context' in globals() else 'test',
            'status': 'completed'
        }
        
        # Upload result to processed bucket
        s3_client.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=f"{job_name}_result.json",
            Body=json.dumps(result),
            ContentType='application/json'
        )
        
        print(f"Results saved for job: {job_name}")
        
    except Exception as e:
        print(f"Error saving results: {str(e)}")
        save_error_result(job_name, str(e))

def save_error_result(job_name: str, error_message: str):
    """
    Save error result to S3
    """
    try:
        result = {
            'job_id': job_name,
            'status': 'error',
            'error_message': error_message,
            'timestamp': context.aws_request_id if 'context' in globals() else 'test'
        }
        
        s3_client.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=f"{job_name}_result.json",
            Body=json.dumps(result),
            ContentType='application/json'
        )
        
    except Exception as e:
        print(f"Error saving error result: {str(e)}")

# For local testing
if __name__ == "__main__":
    # Test the function locally
    test_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'test_hello.wav'}
            }
        }]
    }
    
    result = lambda_handler(test_event, None)
    print(result)
