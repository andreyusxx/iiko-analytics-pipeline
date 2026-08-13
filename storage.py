import boto3
import json
import os
from botocore.config import Config

def upload_payroll_report(data, filename):
    """Вивантажує JSON звіт у Cloudflare R2"""
    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv('R2_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(signature_version='s3v4')
    )
    
    s3.put_object(
        Bucket=os.getenv('R2_BUCKET_NAME'),
        Key=f"payroll_reports/{filename}",
        Body=json.dumps(data, ensure_ascii=False, indent=4),
        ContentType='application/json'
    )