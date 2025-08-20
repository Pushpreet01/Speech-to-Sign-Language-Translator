# Speech-to-Sign MVP Using AWS Lambda

A serverless web application that converts speech audio files to sign language animations using AWS Lambda, S3, and Transcribe services.

## Features

- 🎤 Audio file upload (WAV, MP3, MP4, M4A, FLAC)
- 🔊 Speech-to-text conversion
- 🤟 Text-to-sign language mapping
- 🎬 Animated sign language sequence playback
- ☁️ Serverless architecture using AWS Lambda
- 📱 Responsive web interface

## Quick Start (2-Hour Setup)

### Prerequisites

- Python 3.9+
- AWS Account with programmatic access
- AWS CLI configured (optional but recommended)

### 1. Environment Setup

```bash
# Clone or download the project
cd STT

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. AWS Configuration

Create `.env` file in the project root:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Bucket Names (must be globally unique)
UPLOAD_BUCKET=your-unique-upload-bucket-name
PROCESSED_BUCKET=your-unique-processed-bucket-name

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

### 3. AWS Resources Setup

```bash
# Setup S3 buckets and IAM role
python setup_aws.py
```

**Important:** Follow the IAM role creation instructions printed by the setup script.

### 4. Deploy Lambda Function

```bash
# Deploy the Lambda function
python setup_aws.py --lambda
```

### 5. Run the Application

```bash
# Start the Flask web server
python app.py
```

Visit `http://localhost:5000` to use the application.

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Flask Web App  │────│  S3 Upload   │────│  Lambda Function│
│                 │    │   Bucket     │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                                           │
         │              ┌──────────────┐            │
         └──────────────│ S3 Processed │────────────┘
                        │   Bucket     │
                        └──────────────┘
```

### Component Breakdown

1. **Flask Web App**: User interface for file upload and results display
2. **S3 Upload Bucket**: Stores uploaded audio files, triggers Lambda
3. **AWS Lambda**: Processes audio, converts speech to text, maps to signs
4. **S3 Processed Bucket**: Stores processing results and sign mappings

## File Structure

```
STT/
├── app.py                 # Flask web application
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
├── setup_aws.py         # AWS resource setup script
├── lambda_function/     
│   ├── lambda_function.py # AWS Lambda function code
│   └── requirements.txt  # Lambda dependencies
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   └── results.html
└── static/             # CSS and static files
    └── style.css
```

## Usage

1. **Upload Audio**: Select an audio file containing speech
2. **Processing**: The system will automatically:
   - Upload file to S3
   - Trigger Lambda function
   - Convert speech to text
   - Map words to sign language animations
3. **View Results**: See the transcribed text and sign sequence
4. **Playback**: Use controls to play the sign language sequence

## Customization

### Adding More Sign Language Words

Edit `lambda_function/lambda_function.py` and update the `SIGN_MAPPING` dictionary:

```python
SIGN_MAPPING = {
    'your_word': 'https://your-sign-gif-url.com/sign.gif',
    # Add more mappings...
}
```

### Using Real AWS Transcribe

Replace the mock transcription in the Lambda function with actual AWS Transcribe:

```python
def start_transcription_job(bucket: str, key: str, job_name: str) -> str:
    # Use AWS Transcribe service
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': f's3://{bucket}/{key}'},
        MediaFormat='mp3',  # or appropriate format
        LanguageCode='en-US'
    )
    # Wait for completion and get results
    # Implementation details...
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify `.env` file has correct AWS credentials
   - Check IAM user has necessary permissions

2. **S3 Bucket Already Exists**
   - Bucket names must be globally unique
   - Update bucket names in `.env` file

3. **Lambda Function Not Triggered**
   - Verify S3 event notification is configured
   - Check Lambda function permissions

4. **Processing Stuck**
   - Check Lambda function logs in AWS CloudWatch
   - Verify bucket permissions

### Logs and Monitoring

- **Flask Logs**: Check terminal output where `python app.py` is running
- **Lambda Logs**: AWS CloudWatch Logs
- **S3 Events**: AWS CloudTrail (if enabled)

## Production Considerations

For production deployment, consider:

1. **Security**: Use IAM roles instead of access keys
2. **Scalability**: Configure Lambda concurrency limits
3. **Monitoring**: Set up CloudWatch alarms
4. **Error Handling**: Implement dead letter queues
5. **CORS**: Configure proper CORS policies for production domains
6. **Real Sign Assets**: Replace placeholder images with actual sign language GIFs

## Cost Estimation

For moderate usage (100 files/month):
- **S3 Storage**: ~$1-2/month
- **Lambda Execution**: ~$1-3/month
- **AWS Transcribe**: ~$2-5/month
- **Total**: ~$5-10/month

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review AWS CloudWatch logs
3. Verify all setup steps were completed
4. Check AWS service status

## License

This project is for educational/demo purposes. Please ensure compliance with AWS terms of service and applicable laws when using speech recognition and sign language content.
