import os
import json
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import random

# ====== 텔레그램 정보 ======
TELEGRAM_BOT_TOKEN = "7578590641:AAEiftqs1sHKPS2FMNUpODSRkXC_6Yr51Wc"
TELEGRAM_CHAT_ID = "-1002204342572"       # 상장 공지 알림 채널
ADMIN_CHAT_ID = "1748799133"              # duck Kim 님의 user_id

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
LAST_NOTICE_PATH = os.path.join(os.path.dirname(__file__), 'last_notice.json')

default_config = {
    "min_interval": 3,
    "max_interval": 10,
    "listing_keywords": [
        "신규 거래지원 안내",
        "디지털 자산 추가"
    ],
    "krw_only_for_add": True
}

if not os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

def send_telegram_message(msg, bot_token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        res = requests.post(url, data={
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=5)
        return res.ok
    except Exception as e:
        print("[텔레그램 전송 오류]", e)
        return False

def load_last_notice(path=LAST_NOTICE_PATH):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        msg = f"[로드 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
        return None

def save_last_notice(notice, path=LAST_NOTICE_PATH):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(notice, f, ensure_ascii=False, indent=2)
    except Exception as e:
        msg = f"[저장 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)

def html_to_text(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        msg = f"[HTML 파싱 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
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
        msg = f"[표 파싱 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
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
        msg = f"[코인명 추출 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
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
        msg = f"[시간 리스트 추출 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
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
        try:
            return datetime.fromisoformat(trade_time_clean.replace(" ", "T"))
        except:
            pass
    except Exception as e:
        msg = f"[상장시각 파싱 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
    return None

def to_naive(dt):
    try:
        if dt is None:
            return None
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    except Exception as e:
        msg = f"[datetime 변환 예외] {e}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
        return dt

def is_listing_notice(title, config):
    # 키워드 포함 여부만 체크 (신규 상장 공지만 True)
    return any(kw in title for kw in config["listing_keywords"])

def process_notice_by_id(notice_id):
    last_notice = load_last_notice()
    detail_url = f'https://api-manager.upbit.com/api/v1/announcements/{notice_id}'
    detail_res = requests.get(detail_url)
    if detail_res.status_code != 200:
        msg = f"공지 상세 API 오류: {detail_res.status_code}\n업비트 API가 변경되었을 가능성이 있습니다. 최대한 빨리 조치할게요."
        print(msg)
        send_telegram_message(msg, chat_id=ADMIN_CHAT_ID)
        return
    detail_data = detail_res.json()
    notice = detail_data.get('data', {})
    title = notice.get('title', "")
    listed_at = notice.get('listed_at', "")
    first_listed_at = notice.get('first_listed_at', "")
    details = notice.get('body', "")

    # =========== 상장공지 필터링 ==============
    if not is_listing_notice(title, config):
        print(f"\n[비상장공지 스킵] {title}")
        return  # 아무것도 하지 않음!
    # =========================================

    if (
        last_notice and
        str(notice_id) == str(last_notice.get("id")) and
        listed_at == last_notice.get("listed_at")
    ):
        print("\n신규 공지 없음 (기존 데이터와 동일)")
        return

    if listed_at == first_listed_at:
        pattern_type = 1
    elif listed_at != first_listed_at and '거래지원 개시 시점 안내' in title:
        pattern_type = 2
    elif listed_at != first_listed_at and '거래지원 개시 시점 연기 안내' in title:
        pattern_type = 3
    else:
        print("[경고] 업비트 공지 패턴 분류에서 벗어남 (API 변경 가능성 있음)")
        pattern_type = 1

    text = html_to_text(details)
    trade_times = extract_trade_times(text, details, pattern_type, title)

    # 메시지 생성 (콘솔+텔레그램용)
    msg_lines = []
    msg_lines.append("🚨 <b>[상장공지 감지]</b>")
    msg_lines.append(f"<b>제목:</b> {title}")
    msg_lines.append(f"<b>공지 시각:</b> {listed_at}")
    link_url = f"https://upbit.com/service_center/notice?id={notice_id}"

    msg_lines.append("--- [코인별 상장정보] ---")
    if trade_times:
        listed_dt = datetime.fromisoformat(listed_at.replace(" ", "T"))
        listed_dt = to_naive(listed_dt)
        for t in trade_times:
            line = f"<b>{t['asset']}</b>: {t['trade_time']}"
            trade_dt = parse_trade_time(t['trade_time'])
            trade_dt = to_naive(trade_dt)
            if trade_dt:
                delta = trade_dt - listed_dt
                minutes = int(delta.total_seconds() // 60)
                hours, mins = divmod(minutes, 60)
                line += f"  ⏳ 거래까지 남은시간: {hours}시간 {mins}분"
            else:
                line += "  (상장시각 파싱 오류, 원본만 출력)"
            msg_lines.append(line)
    else:
        msg_lines.append("거래지원 개시 시점 정보 없음")

    msg_lines.append(f"\n🔗 <a href='{link_url}'>공지 바로가기</a>")

    # 콘솔 출력
    print("\n=== [단일 공지 테스트 결과] ===")
    for l in msg_lines:
        print(l)
    # 텔레그램 전송 (공지 채널로)
    send_telegram_message("\n".join(msg_lines))

    # 저장
    new_notice = {
        "id": notice_id,
        "title": title,
        "listed_at": listed_at,
        "first_listed_at": first_listed_at,
        "assets": trade_times
    }
    save_last_notice(new_notice)
    print("\n(last_notice.json 파일이 해당 공지로 갱신됨)")






if __name__ == "__main__":
    notice_id = input("테스트할 공지 id 입력: ").strip()
    if notice_id.isdigit():
        process_notice_by_id(notice_id)
    else:
        print("id(숫자)를 입력하세요.")
