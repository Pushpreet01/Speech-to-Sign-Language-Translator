# Speech-to-Sign MVP - Deployment Guide

## 🚀 Quick Start (Choose Your Path)

### Option 1: Local Demo (Recommended for Quick Testing) ⭐

**No AWS setup required! Perfect for immediate demonstration.**

1. **Install Python 3.9+** (if not installed)
2. **Run the quick start script:**
   
   **Windows:**
   ```cmd
   quick_start.bat
   ```
   
   **macOS/Linux:**
   ```bash
   chmod +x quick_start.sh
   ./quick_start.sh
   ```
   
   Choose option "1" for local demo

3. **Open browser:** http://localhost:5000
4. **Upload audio file:** The system will use mock transcription
5. **View results:** See sign language animations

### Option 2: Full AWS Setup (Production-Ready)

**Requires AWS account and credentials setup.**

1. **Set up AWS credentials** in `.env` file:
   ```env
   AWS_ACCESS_KEY_ID=your_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_here
   AWS_REGION=us-east-1
   UPLOAD_BUCKET=your-unique-upload-bucket-name
   PROCESSED_BUCKET=your-unique-processed-bucket-name
   ```

2. **Run setup:**
   ```bash
   python setup_aws.py
   python setup_aws.py --lambda
   ```

3. **Start application:**
   ```bash
   python app.py
   ```

## 📁 What You Get

```
STT/
├── 🌐 Web Application (Flask)
│   ├── app.py              # Main Flask app
│   ├── local_demo.py       # Demo version (no AWS)
│   └── templates/          # HTML templates
├── ☁️ AWS Lambda Function
│   └── lambda_function/    # Serverless processing
├── 🔧 Setup & Config
│   ├── setup_aws.py        # AWS resource setup
│   ├── config.py          # Configuration
│   └── requirements.txt   # Dependencies
└── 📚 Documentation
    ├── README.md          # Detailed guide
    └── DEPLOYMENT_GUIDE.md # This file
```

## 🎯 Features Implemented

✅ **File Upload Interface** - Drag & drop audio files  
✅ **Speech Processing** - Mock transcription (AWS Transcribe ready)  
✅ **Sign Language Mapping** - 20+ common words mapped to visual signs  
✅ **Animated Playback** - Sequential sign language display  
✅ **Responsive UI** - Works on desktop and mobile  
✅ **Serverless Architecture** - AWS Lambda for processing  
✅ **Real-time Status** - Progress tracking and polling  

## 🎬 Demo Workflow

1. **Upload:** Select audio file (WAV, MP3, etc.)
2. **Process:** System converts speech → text → signs
3. **Display:** View transcribed text and sign sequence
4. **Playback:** Watch animated sign language sequence

## 🔧 Technical Architecture

### Local Demo Mode
```
Browser → Flask App → Mock Processing → Sign Display
```

### AWS Production Mode
```
Browser → Flask App → S3 Upload → Lambda Trigger → 
Speech-to-Text → Sign Mapping → S3 Results → Display
```

## 📊 Current Capabilities

- **Audio Formats:** WAV, MP3, MP4, M4A, FLAC
- **Sign Library:** 20+ basic words with placeholder images
- **Processing:** Mock transcription (AWS Transcribe integration ready)
- **UI:** Modern, responsive design with Bootstrap
- **Deployment:** Local demo + AWS serverless options

## 🔮 Production Enhancements

For a full production system, consider:

1. **Real Sign Assets:** Replace placeholder images with actual ASL GIFs
2. **Enhanced Vocabulary:** Expand sign library to 1000+ words
3. **Real Speech Recognition:** Implement AWS Transcribe integration
4. **User Accounts:** Add user registration and history
5. **Video Output:** Generate MP4 videos of sign sequences
6. **Multiple Languages:** Support for different sign languages
7. **Mobile App:** Native iOS/Android applications

## 💰 Cost Estimate (AWS Production)

For 100 files/month:
- S3 Storage: ~$1/month
- Lambda Execution: ~$2/month
- AWS Transcribe: ~$3/month
- **Total: ~$6/month**

## 🆘 Troubleshooting

### Common Issues

1. **Python not found**
   - Install Python 3.9+ from python.org
   - Ensure Python is in your PATH

2. **Virtual environment issues**
   - Delete `venv` folder and recreate
   - Use `python -m venv venv` or `python3 -m venv venv`

3. **Dependencies failing**
   - Upgrade pip: `pip install --upgrade pip`
   - Try: `pip install -r requirements.txt --no-cache-dir`

4. **AWS permission errors**
   - Verify IAM role has correct permissions
   - Check bucket names are globally unique

### Quick Fixes

```bash
# Reset environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Test local demo
python local_demo.py
```

## 📞 Support & Next Steps

1. **Immediate Demo:** Use local demo mode for presentation
2. **AWS Setup:** Follow README.md for full AWS integration
3. **Customization:** Modify sign mappings in lambda_function.py
4. **Scaling:** Consider additional AWS services for production

---

**🎯 MVP Status: READY FOR DEMONSTRATION**

The system is functional and ready for submission. Choose local demo for immediate testing or AWS setup for full serverless experience.
