import uuid
import json
import boto3
import logging
from flask import Flask, request, jsonify
from .transcript_extractor import YoutubeTranscriptExtractor
import threading

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# S3 클라이언트 설정
s3_client = boto3.client('s3')
BUCKET_NAME = 'aiclude.jp.file'
S3_PREFIX = 'youtube-transcript/'

def upload_to_s3(task_id: str, data: dict):
    """S3에 JSON 파일 업로드"""
    file_name = f"{S3_PREFIX}{task_id}.json"
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json; charset=utf-8'
        )
        logging.info(f"Successfully uploaded {file_name} to S3.")
    except Exception as e:
        logging.error(f"Failed to upload {file_name} to S3: {str(e)}")

def extract_transcript_sync(url: str, lang: str, task_id: str):
    """자막 추출을 동기적으로 처리하는 함수"""
    try:
        with YoutubeTranscriptExtractor(lang=lang) as extractor:
            transcript = extractor.extract_transcript(url)
            result = {
                'success': True,
                'transcript': transcript
            }
            logging.debug(f"Transcript extracted for task {task_id}: {transcript[:100]}...")
    except Exception as e:
        result = {
            'success': False,
            'error': str(e)
        }
        logging.error(f"Error extracting transcript for task {task_id}: {str(e)}")
    
    # S3에 결과 업로드할 때 ensure_ascii=False 설정
    upload_to_s3(task_id, result)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'youtube-transcript'
    }), 200

@app.route('/youtube-transcript', methods=['POST'])
def get_transcript():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            logging.warning("URL is missing in request body")
            return jsonify({
                'success': False,
                'error': 'URL is required in request body'
            }), 400

        url = data['url']
        lang = data.get('lang', 'ko')

        # 클래스 메서드로 URL 유효성 검사
        try:
            url = YoutubeTranscriptExtractor.validate_youtube_url(url)
            logging.debug(f"Validated URL: {url}")
        except Exception as e:
            logging.error(f"Invalid YouTube URL: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Invalid YouTube URL: {str(e)}'
            }), 400

        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        logging.info(f"Starting transcript extraction for task {task_id}")
        # 비동기 작업 시작
        thread = threading.Thread(target=extract_transcript_sync, args=(url, lang, task_id))
        thread.start()
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '비동기 처리 중...'
        }), 202
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5172)