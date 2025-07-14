import os
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import random
import cloudscraper

# ====== 텔레그램 정보 ======
TELEGRAM_BOT_TOKEN = "7578590641:AAEiftqs1sHKPS2FMNUpODSRkXC_6Yr51Wc"
TELEGRAM_CHAT_ID = "-1002204342572"
ADMIN_CHAT_ID = "1748799133"

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
LAST_NOTICE_PATH = os.path.join(os.path.dirname(__file__), 'last_notice.json')

# ====== 기본 설정 ======
default_config = {
    "min_interval": 3,
    "max_interval": 10,
    "listing_keywords": ["신규 거래지원 안내", "디지털 자산 추가"],
    "krw_only_for_add": True
}

default_last_notice = {
    "id": "5183",
    "title": "라이브피어(LPT)(KRW, USDT 마켓), 포켓네트워크(POKT)(KRW 마켓) 디지털 자산 추가",
    "listed_at": "2025-05-30T12:15:00+09:00",
    "first_listed_at": "2025-05-30T12:15:00+09:00",
    "assets": [
        {"asset": "LPT", "trade_time": "5월 30일 17시 예정"},
        {"asset": "POKT", "trade_time": "5월 30일 19시 예정"}
    ]
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)

if not os.path.exists(LAST_NOTICE_PATH):
    with open(LAST_NOTICE_PATH, 'w', encoding='utf-8') as f:
        json.dump(default_last_notice, f, ensure_ascii=False, indent=2)

with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

# ====== 에러 알림 쿨다운 처리 ======
last_error_messages = {}
ERROR_COOLDOWN_SECONDS = 3600

def send_error_once(key, message):
    now = time.time()
    print(f"[에러 로그] {message}")
    if key not in last_error_messages or (now - last_error_messages[key]) > ERROR_COOLDOWN_SECONDS:
        send_telegram_message(message, chat_id=ADMIN_CHAT_ID)
        last_error_messages[key] = now

# ====== 요청 함수 (403 대응 포함) ======
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
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
        send_error_once("요청실패", f"[요청 예외] {e}")
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
        send_error_once("로드", f"[로드 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")
        return None

def save_last_notice(notice, path=LAST_NOTICE_PATH):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(notice, f, ensure_ascii=False, indent=2)
    except Exception as e:
        send_error_once("저장", f"[저장 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")

def html_to_text(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        send_error_once("HTML파싱", f"[HTML 파싱 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")
        return html if html else ""

def extract_all_trade_times_table(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return []
        thead = table.find("thead")
        ths = [th.get_text().strip() for th in thead.find_all("th")]
        asset_idx = None
        time_idx = None
        for i, th in enumerate(ths):
            if "디지털 자산" in th:
                asset_idx = i
            if "거래지원 개시 시점" in th:
                time_idx = i
        if asset_idx is None or time_idx is None:
            return []
        result = []
        tbody = table.find("tbody")
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) > max(asset_idx, time_idx):
                asset = tds[asset_idx].get_text(strip=True)
                trade_time = tds[time_idx].get_text(strip=True)
                result.append({"asset": asset, "trade_time": trade_time})
        return result
    except Exception as e:
        send_error_once("표파싱", f"[표 파싱 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")
        return []

def extract_coin_name_from_title(title):
    try:
        match = re.match(r'([^(]+)\(', title)
        if match:
            return match.group(1).strip()
        match2 = re.match(r'(.+?)\s*신규 거래지원 안내', title)
        if match2:
            return match2.group(1).strip()
        if ',' in title:
            return title.split(',')[0].split('(')[0].strip()
        return "상장코인"
    except Exception as e:
        send_error_once("코인명", f"[코인명 추출 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")
        return "상장코인"

def extract_trade_times(text, html, pattern_type, title="상장코인"):
    try:
        if pattern_type == 1:
            times = extract_all_trade_times_table(html)
            if times:
                return times
            pattern = r"거래지원\s*개시\s*시점\s*[:：\-]\s*([^\n]+)"
            match = re.search(pattern, text)
            if match:
                return [{"asset": extract_coin_name_from_title(title), "trade_time": match.group(1).strip()}]
            return []
        elif pattern_type == 2:
            pattern = r"거래지원\s*개시\s*시점\s*[:：\-]\s*([^\n]+)"
            match = re.search(pattern, text)
            if match:
                return [{"asset": extract_coin_name_from_title(title), "trade_time": match.group(1).strip()}]
            return []
        elif pattern_type == 3:
            pattern = r"연기된\s*거래지원\s*개시\s*시점\s*[:：\-]\s*([^\n]+)"
            match = re.search(pattern, text)
            if match:
                return [{"asset": extract_coin_name_from_title(title), "trade_time": match.group(1).strip()}]
            return []
        return []
    except Exception as e:
        send_error_once("시간추출", f"[시간 리스트 추출 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")
        return []

def parse_trade_time(trade_time_str):
    now = datetime.now()
    try:
        hangul_match = re.search(r'(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2})시', trade_time_str)
        if hangul_match:
            month = int(hangul_match.group(1))
            day = int(hangul_match.group(2))
            hour = int(hangul_match.group(3))
            return datetime(now.year, month, day, hour, 0)
        trade_time_clean = trade_time_str.replace("KST", "").replace("UTC", "").replace("예정", "").strip()
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(trade_time_clean, fmt)
            except:
                continue
        return datetime.fromisoformat(trade_time_clean.replace(" ", "T"))
    except Exception as e:
        send_error_once("시간파싱", f"[상장시각 파싱 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다.")
    return None

def to_naive(dt):
    try:
        if dt is None:
            return None
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    except Exception as e:
        send_error_once("datetime변환", f"[datetime 변환 예외] {e}")
        return dt

def is_listing_notice(title, config):
    return any(kw in title for kw in config["listing_keywords"])

def process_notice_by_id(notice_id):
    last_notice = load_last_notice()
    detail_url = f'https://api-manager.upbit.com/api/v1/announcements/{notice_id}'
    detail_res = get_with_fallback(detail_url)
    if not detail_res or detail_res.status_code != 200:
        send_error_once("공지상세", f"공지 상세 API 오류: {detail_res.status_code if detail_res else '응답 없음'}")
        return

    detail_data = detail_res.json()
    notice = detail_data.get('data', {})
    title = notice.get('title', "")
    listed_at = notice.get('listed_at', "")
    first_listed_at = notice.get('first_listed_at', "")
    details = notice.get('body', "")

    if not is_listing_notice(title, config):
        print(f"\n[비상장공지 스킵] {title}")
        return

    if last_notice and str(notice_id) == str(last_notice.get("id")) and listed_at == last_notice.get("listed_at"):
        print("\n신규 공지 없음 (기존 데이터와 동일)")
        return

    pattern_type = 1
    if listed_at != first_listed_at:
        if '거래지원 개시 시점 안내' in title:
            pattern_type = 2
        elif '거래지원 개시 시점 연기 안내' in title:
            pattern_type = 3
        else:
            print("[경고] 공지 패턴 미정의")

    text = html_to_text(details)
    trade_times = extract_trade_times(text, details, pattern_type, title)

    msg_lines = [
        "🚨 <b>[상장공지 감지]</b>",
        f"<b>제목:</b> {title}",
        f"<b>공지 시각:</b> {listed_at}",
        "--- [코인별 상장정보] ---"
    ]
    link_url = f"https://upbit.com/service_center/notice?id={notice_id}"

    if trade_times:
        listed_dt = to_naive(datetime.fromisoformat(listed_at.replace(" ", "T")))
        for t in trade_times:
            line = f"<b>{t['asset']}</b>: {t['trade_time']}"
            trade_dt = to_naive(parse_trade_time(t['trade_time']))
            if trade_dt:
                delta = trade_dt - listed_dt
                minutes = int(delta.total_seconds() // 60)
                hours, mins = divmod(minutes, 60)
                line += f"  ⏳ 거래까지 남은시간: {hours}시간 {mins}분"
            msg_lines.append(line)
    else:
        msg_lines.append("거래지원 개시 시점 정보 없음")

    msg_lines.append(f"\n🔗 <a href='{link_url}'>공지 바로가기</a>")
    print("\n=== [단일 공지 테스트 결과] ===")
    for l in msg_lines:
        print(l)
    send_telegram_message("\n".join(msg_lines))

    save_last_notice({
        "id": notice_id,
        "title": title,
        "listed_at": listed_at,
        "first_listed_at": first_listed_at,
        "assets": trade_times
    })
    print("\n(last_notice.json 파일이 해당 공지로 갱신됨)")



# #ID로 테스트 루프
# if __name__ == "__main__":
#     notice_id = input("테스트할 공지 id 입력: ").strip()
#     if notice_id.isdigit():
#         process_notice_by_id(notice_id)
#     else:
#         print("id(숫자)를 입력하세요.")


# ====== 메인 루프 ======
if __name__ == "__main__":
    while True:
        try:
            url = 'https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=1&category=trade'
            res = get_with_fallback(url)
            if res and res.status_code == 200:
                data = res.json()
                notices = data['data']['notices']
                if notices:
                    notice = notices[0]
                    notice_id = str(notice['id'])
                    if is_listing_notice(notice['title'], config):
                        process_notice_by_id(notice_id)
                    else:
                        print(f"[비상장공지 무시] {notice['title']}")
            else:
                send_error_once("업비트API", f"[업비트 리스트 API 오류] {res.status_code if res else '응답 없음'}")
        except Exception as e:
            send_error_once("감시루프", f"[감시루프 예외] {e}")
        interval = random.uniform(config["min_interval"], config["max_interval"])
        time.sleep(interval)

