import os
import json
import requests
import re
from datetime import datetime, timedelta
import time
import random
import cloudscraper
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

# ====== 텔레그램 정보 ======
TELEGRAM_BOT_TOKEN = "7578590641:AAEiftqs1sHKPS2FMNUpODSRkXC_6Yr51Wc"
TELEGRAM_CHAT_ID = "-1002204342572"
ADMIN_CHAT_ID = "1748799133"

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config_warn.json')
LAST_NOTICE_PATH = os.path.join(os.path.dirname(__file__), 'last_notice_warn.json')

default_config = {
    "min_interval": 3,
    "max_interval": 10,
    "warn_keywords": ["거래 유의 종목"],
}

default_last_notice = {
    "id": "9999",
    "title": "세럼(SRM) 거래 유의 종목 지정 안내",
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)

if not os.path.exists(LAST_NOTICE_PATH):
    with open(LAST_NOTICE_PATH, 'w', encoding='utf-8') as f:
        json.dump(default_last_notice, f, ensure_ascii=False, indent=2)

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

last_error_messages = {}
ERROR_COOLDOWN_SECONDS = 300

def send_error_once(key, message):
    now = time.time()
    print(f"[에러 로그] {message}")
    if key not in last_error_messages or (now - last_error_messages[key]) > ERROR_COOLDOWN_SECONDS:
        send_telegram_message(message, chat_id=ADMIN_CHAT_ID)
        last_error_messages[key] = now

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://upbit.com"
})

def get_with_fallback(url):
    try:
        res = session.get(url, timeout=5)
        if res.status_code == 403:
            print("[403 감지] cloudscraper로 재시도 중...")
            scraper = cloudscraper.create_scraper()
            res = scraper.get(url, timeout=5)
        return res
    except Exception as e:
        send_error_once("요청실패", f"[요청 예외] {type(e).__name__}: {e}")
        return None

def send_telegram_message(msg, bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        res = requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=5)
        return res.ok
    except Exception as e:
        print("[텔레그램 전송 오류]", e)
        return False

def load_last_notice(path=LAST_NOTICE_PATH):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        send_error_once("로드", f"[로드 예외] {e}")
        return None

def save_last_notice(notice, path=LAST_NOTICE_PATH):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(notice, f, ensure_ascii=False, indent=2)
    except Exception as e:
        send_error_once("저장", f"[저장 예외] {e}")

def is_warn_notice(title, config):
    return any(kw in title for kw in config["warn_keywords"])


def extract_asset_from_title(title):
    # 예시: "세럼(SRM) 거래 유의 종목 지정 안내"
    match = re.match(r'([^(]+)\(', title)
    if match:
        return match.group(1).strip()
    return title.split('거래 유의 종목')[0].strip()

def process_notice_by_id(notice_id):
    last_notice = load_last_notice()
    detail_url = f'https://api-manager.upbit.com/api/v1/announcements/{notice_id}'
    detail_res = session.get(detail_url, timeout=5)
    if detail_res.status_code == 403:
        print("[403 감지] cloudscraper로 재시도 중...")
        scraper = cloudscraper.create_scraper()
        detail_res = scraper.get(detail_url, timeout=5)
    if detail_res.status_code != 200:
        msg = f"공지 상세 API 오류: {detail_res.status_code}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
        return
    detail_data = detail_res.json()
    notice = detail_data.get('data', {})
    title = notice.get('title', "")
    asset = extract_asset_from_title(title)

    if not is_warn_notice(title, config):
        print(f"\n[비유의공지 스킵] {title}")
        return

    if last_notice and str(notice_id) == str(last_notice.get("id")):
        print("\n신규 유의 공지 없음 (기존 데이터와 동일)")
        return

    # 텔레그램 알림, 콘솔 출력
    link_url = f"https://upbit.com/service_center/notice?id={notice_id}"
    msg_lines = [
        "⚠️ <b>[거래 유의 종목 감지]</b>",
        f"<b>제목:</b> {title}",
        f"\n🔗 <a href='{link_url}'>공지 바로가기</a>"
    ]
    send_telegram_message("\n".join(msg_lines))
    print("\n".join(msg_lines))

    save_last_notice({
        "id": notice_id,
        "title": title,
        "asset": asset,
    })

# ====== FastAPI 서버 ======
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/latest_notice")
def latest_notice():
    try:
        with open("last_notice_warn.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": str(e)}

def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=run_api, daemon=True).start()
    send_telegram_message("⚠️ <b>업비트 거래유의공지알림 시작합니다</b>", chat_id=ADMIN_CHAT_ID)

    last_health_check_time = datetime.now()
    while True:
        try:
            current_time = datetime.now()
            print(f"\n--- [ {current_time.strftime('%Y-%m-%d %H:%M:%S')} ] 루프 시작 ---")

            if current_time - last_health_check_time >= timedelta(hours=1):
                send_telegram_message("✅ <b>거래유의 감시봇이 정상 작동 중입니다.</b>", chat_id=ADMIN_CHAT_ID)
                last_health_check_time = current_time

            url = 'https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=1&category=trade'
            res = get_with_fallback(url)
            if res:
                if res.status_code == 200:
                    data = res.json()
                    notices = data['data']['notices']
                    if notices:
                        notice = notices[0]
                        notice_id = str(notice['id'])
                        process_notice_by_id(notice_id)
                    else:
                        print("[정보] 카테고리에 최신 공지가 없습니다.")
                else:
                    send_error_once("업비트API", f"[업비트 리스트 API 오류] 상태 코드: {res.status_code}")
            else:
                send_error_once("업비트API", "[업비트 리스트 API 오류] 응답 없음 (네트워크 문제 또는 차단)")
        except Exception as e:
            send_error_once("감시루프", f"[감시루프 예외] {e}")

        interval = random.uniform(config["min_interval"], config["max_interval"])
        print(f"--- [ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ] {interval:.2f}초 대기 ---")
        time.sleep(interval)
