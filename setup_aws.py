#!/usr/bin/env python3
"""
AWS Setup Script for Speech-to-Sign MVP
This script creates the necessary AWS resources for the application.
"""

import boto3
import json
import zipfile
import os
import time
from config import Config

def create_s3_buckets():
    """Create S3 buckets for upload and processed files"""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION
    )
    
    buckets = [Config.UPLOAD_BUCKET, Config.PROCESSED_BUCKET]
    
    for bucket_name in buckets:
        try:
            # Check if bucket exists
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✓ Bucket {bucket_name} already exists")
        except:
            try:
                # Create bucket
                if Config.AWS_REGION == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': Config.AWS_REGION}
                    )
                
                # Set CORS configuration for upload bucket
                if bucket_name == Config.UPLOAD_BUCKET:
                    cors_configuration = {
                        'CORSRules': [{
                            'AllowedHeaders': ['*'],
                            'AllowedMethods': ['GET', 'PUT', 'POST'],
                            'AllowedOrigins': ['*'],
                            'MaxAgeSeconds': 3000
                        }]
                    }
                    s3_client.put_bucket_cors(
                        Bucket=bucket_name,
                        CORSConfiguration=cors_configuration
                    )
                
                print(f"✓ Created bucket: {bucket_name}")
            except Exception as e:
                print(f"✗ Failed to create bucket {bucket_name}: {str(e)}")

def create_lambda_function():
    """Create and deploy the Lambda function"""
    lambda_client = boto3.client(
        'lambda',
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION
    )
    
    # Create deployment package
    zip_path = create_lambda_zip()
    
    function_name = 'speech-to-sign-processor'
    
    try:
        # Check if function exists
        lambda_client.get_function(FunctionName=function_name)
        
        # Update existing function
        with open(zip_path, 'rb') as zip_file:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
        print(f"✓ Updated Lambda function: {function_name}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        try:
            with open(zip_path, 'rb') as zip_file:
                response = lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.9',
                    Role=f'arn:aws:iam::{get_account_id()}:role/lambda-execution-role',
                    Handler='lambda_function.lambda_handler',
                    Code={'ZipFile': zip_file.read()},
                    Environment={
                        'Variables': {
                            'UPLOAD_BUCKET': Config.UPLOAD_BUCKET,
                            'PROCESSED_BUCKET': Config.PROCESSED_BUCKET
                        }
                    },
                    Timeout=300,
                    MemorySize=512
                )
            print(f"✓ Created Lambda function: {function_name}")
            
            # Add S3 trigger
            add_s3_trigger(function_name)
            
        except Exception as e:
            print(f"✗ Failed to create Lambda function: {str(e)}")
            print("Please ensure you have created the IAM role 'lambda-execution-role' with appropriate permissions")
    
    # Clean up
    os.remove(zip_path)

def create_lambda_zip():
    """Create a ZIP file for Lambda deployment"""
    zip_path = 'lambda_deployment.zip'
    
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        # Add Lambda function
        zip_file.write('lambda_function/lambda_function.py', 'lambda_function.py')
        
        # Note: boto3 is already available in Lambda runtime
    
    return zip_path

def add_s3_trigger(function_name):
    """Add S3 trigger to Lambda function"""
    lambda_client = boto3.client(
        'lambda',
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION
    )
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION
    )
    
    try:
        # Add permission for S3 to invoke Lambda
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='s3-trigger',
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn=f'arn:aws:s3:::{Config.UPLOAD_BUCKET}'
        )
        
        # Configure S3 notification
        notification_config = {
            'LambdaFunctionConfigurations': [{
                'Id': 'speech-to-sign-trigger',
                'LambdaFunctionArn': f'arn:aws:lambda:{Config.AWS_REGION}:{get_account_id()}:function:{function_name}',
                'Events': ['s3:ObjectCreated:*']
            }]
        }
        
        s3_client.put_bucket_notification_configuration(
            Bucket=Config.UPLOAD_BUCKET,
            NotificationConfiguration=notification_config
        )
        
        print(f"✓ Added S3 trigger for bucket: {Config.UPLOAD_BUCKET}")
        
    except Exception as e:
        print(f"✗ Failed to add S3 trigger: {str(e)}")

def get_account_id():
    """Get AWS account ID"""
    sts_client = boto3.client(
        'sts',
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
        region_name=Config.AWS_REGION
    )
    
    return sts_client.get_caller_identity()['Account']

def create_iam_role():
    """Create IAM role for Lambda (manual setup required)"""
    print("\n" + "="*50)
    print("MANUAL SETUP REQUIRED - IAM ROLE")
    print("="*50)
    print("Please create an IAM role named 'lambda-execution-role' with the following policies:")
    print("1. AWSLambdaBasicExecutionRole")
    print("2. AmazonS3FullAccess")
    print("3. AmazonTranscribeFullAccess")
    print("\nOr use this trust policy JSON:")
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    print(json.dumps(trust_policy, indent=2))

def main():
    """Main setup function"""
    print("Setting up AWS resources for Speech-to-Sign MVP...")
    print(f"Region: {Config.AWS_REGION}")
    print(f"Upload Bucket: {Config.UPLOAD_BUCKET}")
    print(f"Processed Bucket: {Config.PROCESSED_BUCKET}")
    print()
    
    # Check AWS credentials
    if not Config.AWS_ACCESS_KEY_ID or not Config.AWS_SECRET_ACCESS_KEY:
        print("✗ AWS credentials not found. Please set them in .env file")
        return
    
    try:
        # Test AWS connection
        sts_client = boto3.client(
            'sts',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        account_id = sts_client.get_caller_identity()['Account']
        print(f"✓ Connected to AWS Account: {account_id}")
        
    except Exception as e:
        print(f"✗ Failed to connect to AWS: {str(e)}")
        return
    
    # Create resources
    create_s3_buckets()
    create_iam_role()
    
    print("\n" + "="*50)
    print("NEXT STEPS:")
    print("="*50)
    print("1. Create the IAM role as described above")
    print("2. Update your .env file with the correct bucket names")
    print("3. Run: python setup_aws.py --lambda  (to deploy Lambda function)")
    print("4. Run: python app.py  (to start the Flask application)")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--lambda':
        create_lambda_function()
    else:
        main()
