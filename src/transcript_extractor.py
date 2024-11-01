import logging
from playwright.sync_api import sync_playwright
import time
from typing import Optional, Dict
import json
import sys
import argparse
from urllib.parse import urlparse, parse_qs
import random

# 로깅 설정
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class YoutubeTranscriptExtractor:
    @staticmethod
    def validate_youtube_url(url: str) -> str:
        """YouTube URL의 유효성을 검사하고 표준 형식으로 변환"""
        try:
            parsed = urlparse(url)
            if 'youtube.com' not in parsed.netloc and 'youtu.be' not in parsed.netloc:
                raise ValueError("올바른 YouTube URL이 아닙니다.")
            
            # youtu.be 형식의 URL 처리
            if 'youtu.be' in parsed.netloc:
                video_id = parsed.path[1:]
                return f"https://www.youtube.com/watch?v={video_id}"
            
            # youtube.com 형식의 URL 처리
            if parsed.path == '/watch':
                query = parse_qs(parsed.query)
                if 'v' in query:
                    return f"https://www.youtube.com/watch?v={query['v'][0]}"
                
            raise ValueError("올바른 YouTube URL이 아닙니다.")
        except Exception:
            raise ValueError("올바른 URL 형식이 아닙니다.")
    
    @staticmethod
    def get_random_ip():
        """임의의 IP 주소 생성"""
        ip_ranges = [
            "52.194.", # AWS 도쿄
            "34.85.",  # GCP 도쿄
            "13.115.", # AWS 오사카
            "211.45.", # 한국
            "203.104.", # 일본
            "157.7.",   # 라쿠텐
            "219.100.", # KDDI
            "210.153.", # NTT
            "27.114.",  # SK브로드밴드
            "211.234."  # KT
        ]
        prefix = random.choice(ip_ranges)
        return f"{prefix}{random.randint(0,255)}.{random.randint(1,255)}"

    def __init__(self, lang: str = 'ko'):
        self.lang = lang
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        self.languages = {
            'ko': '한국어',
            'en': 'English',
            'ja': '日本語',
            'zh': '中文',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch',
            'ru': 'Русский',
            'pt': 'Português',
            'ar': 'العربية'
        }
    
    def __enter__(self):
        self.playwright = sync_playwright().start()
        
        # 다양한 User-Agent 목록
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/81.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/85.0.564.51"
        ]

        # 랜덤하게 User-Agent 선택
        selected_user_agent = random.choice(user_agents)
        logging.debug(f"Selected User-Agent: {selected_user_agent}")

        # 랜덤 IP 생성
        random_ip = self.get_random_ip()
        logging.debug(f"Using IP address: {random_ip}")

        # 브라우저 컨텍스트 설정
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        self.context = self.browser.new_context(
            locale=self.lang,
            extra_http_headers={
                "Accept-Language": f"{self.lang},en;q=0.9",
                "User-Agent": selected_user_agent,
                "Referer": "https://www.google.com/",
                "DNT": "1",  # Do Not Track 요청
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                "X-Forwarded-For": random_ip,
                "X-Real-IP": random_ip,
                "Via": f"{random_ip} Playwright/1.0",
                "Client-IP": random_ip
            }
        )
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                logging.error(f"Exception occurred: {exc_val}")
        finally:
            self.close()
    
    def close(self):
        """브라우저 및 Playwright 인스턴스 종료"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logging.info("Playwright and browser closed.")

    def extract_transcript(self, url: str) -> Optional[str]:
        """YouTube 동영상의 자막을 추출"""
        try:
            logging.debug(f"Navigating to URL: {url}")
            # 페이지 로드
            self.page.goto(url, timeout=60000)  # 타임아웃을 60초로 증가
            self.page.wait_for_load_state('networkidle')
            time.sleep(2)  # 추가 대기 시간

            # 더보기 버튼 클릭
            more_button = self.page.locator('tp-yt-paper-button#expand').first
            if more_button.is_visible():
                more_button.click()
                time.sleep(1)

            # 스크립트 버튼 찾기 및 클릭
            transcript_button = None
            
            # 방법 1: 클래스로 찾기
            button = self.page.locator('button.yt-spec-button-shape-next.yt-spec-button-shape-next--outline')
            if button.count() > 0:
                transcript_button = button.first
            
            # 방법 2: 메뉴 아이템으로 찾기
            if not transcript_button:
                menu_items = self.page.locator('ytd-menu-service-item-renderer')
                for i in range(menu_items.count()):
                    item = menu_items.nth(i)
                    text = item.inner_text()
                    if '스크립트' in text.lower() or 'transcript' in text.lower():
                        transcript_button = item
                        break

            if not transcript_button:
                logging.warning("스크립트 버튼을 찾을 수 없습니다.")
                return None

            transcript_button.click()
            time.sleep(2)  # 자막 로딩 대기

            # 자막 세그먼트 수집
            segments = []
            transcript_segments = self.page.locator('ytd-transcript-segment-renderer')
            
            for i in range(transcript_segments.count()):
                segment = transcript_segments.nth(i)
                timestamp = segment.locator('.segment-timestamp').inner_text()
                text = segment.locator('.segment-text').inner_text()
                segments.append(f"[{timestamp.strip()}] {text.strip()}")

            if not segments:
                logging.warning("자막을 찾을 수 없습니다.")
                return None

            logging.info(f"Extracted {len(segments)} transcript segments.")
            return '\n'.join(segments)

        except Exception as e:
            logging.error(f"자막 추출 중 오류 발생: {str(e)}")
            return None