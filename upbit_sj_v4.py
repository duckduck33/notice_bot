#v4수정사항: 크론텝 아침 8시 시작, 밤8시 종료 

# 바이비트 전략 추가 이평선추가 /완료



#1000이 들어가는 코인 처리. 예를들어 업비트 봉크는 바이낸스에선 1000bonk였음 /완료 

#  최초등록일만 체크하고, 업데이트일은 무시하기
#현물도 취급하기 
#동시상장되는 경우 어떻게 처리할지 정하기. (이경우 아침에 선물코인리스트 갱신하는게 의미가 없음. 실시간 업데이트?)



#1119
# 텔레수정 (롱수익률만 랜덤으로)

#특정 문장 있을때 제외 "상장시간 연기, btc 와같은 문장
# 코인검색순서 바이낸스 -> 바이비트 선물전략, 현물전략
# pyinstaller -F --console --hidden-import=bnc_grid_v4_4 bnc_grid_v4_4.py
import requests
import pprint
import json
import time
import re

from datetime import datetime
import ccxt
import random
import math
from binance.client import Client
from binance.enums import *
import talib
import pandas as pd
import traceback

#개인라이브러리
import myBinance
import telegram_channel
import ct_bybit



# upbit_title_path = r"C:\Users\zamc\Desktop\dev\upbit_sj\upbit_title.json"
# upbit_word_path = r'C:\Users\zamc\Desktop\dev\upbit_sj\upbit_words.json'
# upbit_sj_config_path = r'C:\Users\zamc\Desktop\dev\upbit_sj\upbit_sj_config.json'

# bnc_ticker_list_path=r'C:\Users\zamc\Desktop\dev\upbit_sj\bnc_ticker_list.json'
# bnc_asset_path=r'C:\Users\zamc\Desktop\dev\upbit_sj\bnc_asset.json'

# bybit_ticker_list_path=r'C:\Users\zamc\Desktop\dev\upbit_sj\bybit_ticker_list.json'
# bybit_asset_path=r'C:\Users\zamc\Desktop\dev\upbit_sj\bybit_asset.json'



upbit_title_path = "/var/autobot/upbit/upbit_title.json"
upbit_word_path = '/var/autobot/upbit/upbit_words.json'
upbit_sj_config_path = '/var/autobot/upbit/upbit_sj_config.json'

bnc_ticker_list_path='/var/autobot/upbit/bnc_ticker_list.json'
bnc_asset_path='/var/autobot/upbit/bnc_asset.json'

bybit_ticker_list_path='/var/autobot/upbit/bybit_ticker_list.json'
bybit_asset_path='/var/autobot/upbit/bybit_asset.json'



def get_upbit_announcements():
    global new_alram
    try:
        response = requests.get('https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=1&category=trade')
        response.raise_for_status()
        data = response.json()
        announcement_id = data['data']['notices'][0]['id']
        title = data['data']['notices'][0]['title']
        listed_at = data['data']['notices'][0]['listed_at']
        link = f"https://upbit.com/service_center/notice?id={announcement_id}"

        # 공지 필터링에 사용할 키워드 리스트
        exclude_keywords = [
            'KRW 마켓 디지털 자산 추가',
            'KRW, USDT 마켓 디지털 자산 추가',
            '신규 거래지원 안내'
        ]

        # 특정 키워드가 포함된 공지 필터링
        if any(keyword in title for keyword in exclude_keywords):
            # print("공지 제목에 신규거래 관련 키워드가 있으므로, 다음단계 진행합니다.")
            # return

            new_titles = []
            new_titles.append({"title": title, "link": link})
            # print(new_titles)
            if response.status_code == 200:
                saved_titles = load_titles_from_json(upbit_title_path)
                updated_titles = []
                for new_title in new_titles:
                    same_title_exists = False
                    new_alram = False
                    for saved_title in saved_titles:
                        if new_title['title'] == saved_title['title']:
                            updated_titles.append(saved_title)
                            same_title_exists = True
                            print("업비트 업데이트된 내용이 없습니다.")
                            break

                    if not same_title_exists:
                        updated_titles.append(new_title)
                        print("업비트 새 공지가 업데이트 되었습니다.")
                        telegram_channel.send_telegram_message("업비트 상장공지:" + title + listed_at + link)
                        title_words = title.split()
                        extracted_words = extract_alphabets_in_parentheses(title_words)
                        
                        before_words=load_titles_from_json(upbit_word_path)

                        if set(extracted_words)!=set(before_words):

                            save_titles_to_json(extracted_words, upbit_word_path)
                            new_alram = True

                    save_titles_to_json(updated_titles, upbit_title_path)

            else:
                print(f"Failed to fetch data. Status code: {response.status_code}, response: {response.text}")
                telegram_channel.send_telegram_message("업비트 서버요청횟수 초과 에러 발생. 3분 대기 후 자동으로 다시 시작합니다. 에러코드: " + str(response.status_code))
                time.sleep(180)
                return 'retry'

    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            print(f"Rate limit exceeded: {e}")
            telegram_channel.send_telegram_message("업비트 API 요청 제한 초과. 30분 대기 후 자동으로 다시 시작합니다.")
            time.sleep(1800)
            return 'retry'
        else:
            print(f"HTTP error occurred: {e}")
            telegram_channel.send_telegram_message(f"업비트 공지 API 요청 실패1 30분후재시작: {str(e)}")
            time.sleep(1800)
            return 'retry'
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        telegram_channel.send_telegram_message(f"업비트 공지 API 요청 실패2 30분후 재시작: {str(e)}")
        time.sleep(1800)
        return 'retry'
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Failed to parse JSON response: {e}")
        telegram_channel.send_telegram_message(f"업비트 공지 응답 파싱 실패3 30분후 재시작: {str(e)}")
        time.sleep(1800)
        return 'retry'




# 특정 심볼에 대해 모든 열린 주문을 취소하는 함수, 바이낸스
def cancel_all_open_orders(symbol):
    try:
        response = client.futures_cancel_all_open_orders(symbol=symbol)
        print(f"{symbol}의 모든 열린 주문이 성공적으로 취소되었습니다. (response: {response})")
    except Exception as e:
        print(f"모든 주문 취소 중 오류가 발생했습니다: {str(e)}")


# 심볼 유효성 확인 함수
def check_symbol_validity(symbol):
    exchange_info = client.futures_exchange_info()
    symbols = [s['symbol'] for s in exchange_info['symbols']]
    return symbol in symbols

# 특정 심볼에 대해 레버리지를 변경하는 함수 (심볼 유효성 체크 추가). 바이낸스
def change_leverage(symbol, leverage):
    if not check_symbol_validity(symbol):
        print(f"유효하지 않은 심볼: {symbol}")
        return
    try:
        response = client.futures_change_leverage(symbol=symbol, leverage=leverage)
        print(f"{symbol}의 레버리지가 {leverage}배로 성공적으로 변경되었습니다. (response: {response})")
    except Exception as e:
        if "code=-4028" in str(e):  # 레버리지 범위 초과 또는 기타 에러
            print(f"{symbol}에 대해 레버리지를 변경할 수 없습니다. (오류: {str(e)})")
        else:
            raise

#기한있는 선물코인 리스트에서 빼주는 함수
def remove_usdt_and_suffix(symbols):
    cleaned_symbols = []
    for symbol in symbols:
        # '/USDT:USDT' 삭제
        symbol = symbol.replace('/USDT:USDT', '')
        # '-숫자' 패턴 삭제
        symbol = re.sub(r'-\d+', '', symbol)
        cleaned_symbols.append(symbol)
    return cleaned_symbols


# 특정 심볼에 대해 격리 모드로 변경하는 함수
def change_to_isolated_mode(symbol):
    try:
        client.futures_change_margin_type(symbol=symbol, marginType='ISOLATED')
        print(f"{symbol}의 마진 유형이 격리 모드로 변경되었습니다.")
    except Exception as e:
        if "code=-4046" in str(e):
            print(f"{symbol}의 마진 유형이 이미 격리 모드로 설정되어 있습니다.")
        else:
            raise

def precise_sleep(duration):
    start_time = time.perf_counter()  # 시작 시간 기록
    while True:
        current_time = time.perf_counter()  # 현재 시간 갱신
        if current_time - start_time >= duration:  # 지정된 시간이 경과했는지 확인
            break
        else:
            time.sleep(0.01)  # CPU 사용을 줄이기 위해 잠시 대기 

# 괄호 안의 알파벳만 추출하는 함수
def extract_alphabets_in_parentheses(words):
    extracted_words = []
    for word in words:
        match = re.search(r'\(([A-Za-z]+)\)', word)
        if match:
            extracted_words.append(match.group(1))
    return extracted_words


def load_titles_from_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_titles_to_json(titles, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(titles, file, ensure_ascii=False, indent=4)


#분봉/일봉 캔들 정보를 가져온다 첫번째: 바이비트 객체, 두번째: 코인 티커, 세번째: 기간 (1d,4h,1h,15m,10m,1m ...)
def GetOhlcv(bybit, Ticker, period):
    #바이비트는 리미트를 반드시 걸어줘야 된다.
    btc_ohlcv = bybit.fetch_ohlcv(Ticker, period,since=None, limit=500)
    df = pd.DataFrame(btc_ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df




# telegram_channel.send_telegram_message("업비트 상장봇: 바이낸스 코인리스트, 자산 업데이트시작.")


# 옵션 데이터 불러오기
with open(upbit_sj_config_path, 'r') as f:
    config = json.load(f)

# JSON 데이터에서 변수 설정
Binance_AccessKey = config['Binance_AccessKey']
Binance_ScretKey = config['Binance_ScretKey']
Bybit_AccessKey = config['Bybit_AccessKey']
Bybit_ScretKey = config['Bybit_ScretKey']
sleep_sec = config['sleep_sec']
# positionSide = 'BOTH'  # 원웨이모드    #헷지모드는 LONG SHORT




binanceX_future = ccxt.binance({
    'apiKey': Binance_AccessKey,
    'secret': Binance_ScretKey,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})


# 바이낸스 클라이언트 초기화
client = Client(Binance_AccessKey, Binance_ScretKey)

# 헷지 모드 및 멀티 자산 모드 활성화 (이미 활성화되어 있는 경우를 처리)
try:
    client.futures_change_multi_assets_mode(multiAssetsMargin=False)  #False 는 원자산모드 #True 는 멀티자산모드// 격리모드하려면 원자산모드여야함  
except Exception as e:
    if "code=-4171" in str(e):
        print("원자산 모드가 이미 활성화되어 있습니다.")
    else:
        raise

try:
    client.futures_change_position_mode(dualSidePosition=True)    #True 는 헷지모드, 양방매매모드 False 는 원웨이 모드
except Exception as e:
    if "code=-4059" in str(e):
        # print("원웨이모드가 이미 활성화되어 있습니다.")
        print("햇지모드가 이미 활성화되어 있습니다.")
    else:
        raise


# 바이낸스 선물거래 리스트 구하기
Tickers = binanceX_future.fetch_tickers()
tickers_list = [ticker for ticker in Tickers.keys()]
usdt_future_list = [ticker for ticker in tickers_list if '/USDT:USDT' in ticker]
print(" 바이낸스 USDT 선물리스트")
print(usdt_future_list)

# /USDT:USDT를 제거한 새로운 리스트 생성
cleaned_usdt_future_list=remove_usdt_and_suffix(usdt_future_list)
# cleaned_usdt_future_list = [ticker.replace('/USDT:USDT', '') for ticker in usdt_future_list]
print("바이낸스 선물리스트, 티커명만",cleaned_usdt_future_list)
save_titles_to_json(cleaned_usdt_future_list,bnc_ticker_list_path)



# BNC 선물 계좌 자산 출력
balance = binanceX_future.fetch_balance(params={"type": "future"})
time.sleep(sleep_sec)  
print("바이낸스 선물총잔고:", float(balance['USDT']['total']))  
# print("사용가능한 선물잔고:", float(balance['USDT']['free']))  
total_USDT = float(balance['USDT']['total'])
save_titles_to_json(total_USDT,bnc_asset_path)


telegram_channel.send_telegram_message("업비트 상장봇: 바이비트 코인리스트, 자산 업데이트시작.")
if 1>0:

    #바이비트 코인리스트, 자산 업데이트 
    from pybit.unified_trading import HTTP
    session = HTTP(
        api_key=Bybit_AccessKey,
        api_secret=Bybit_ScretKey,
    )

    bybitX = ccxt.bybit(config={
        'apiKey': Bybit_AccessKey,
        'secret': Bybit_ScretKey,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'
        }
    })


    Tickers = bybitX.fetch_tickers()
    tickers_list = [ticker for ticker in Tickers.keys()]
    usdt_future_list = [ticker for ticker in tickers_list if '/USDT:USDT' in ticker]
    # print(" 바이비트 USDT 선물리스트")
    print(usdt_future_list)

    # /USDT:USDT를 제거한 새로운 리스트 생성
    cleaned_usdt_future_list=remove_usdt_and_suffix(usdt_future_list)
    # cleaned_usdt_future_list = [ticker.replace('/USDT:USDT', '') for ticker in usdt_future_list]
    print("바이비트 선물리스트, 티커명만",cleaned_usdt_future_list)
    save_titles_to_json(cleaned_usdt_future_list,bybit_ticker_list_path)



    # now = datetime.now()
    # current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    # telegram_channel.send_telegram_message("선물리스트 체크종료"+current_time)

    #바이비트 자산 업데이트
    balance = bybitX.fetch_balance(params={"type": "unified"})
    time.sleep(sleep_sec)  
    print(balance['USDT'])
    print("바이비트 선물총잔고:", float(balance['USDT']['total']))  
    # print("사용가능한 선물잔고:", float(balance['USDT']['free']))  
    total_USDT = float(balance['USDT']['total'])

    save_titles_to_json(total_USDT,bybit_asset_path)






while True:
    try:    
        now = datetime.now()

        if now.hour == 20 and now.minute == 59 and (now.second in range(6)):
            print("21시 업비트 상장봇 종료, 내일 오전 8시 재시작")
            telegram_channel.send_telegram_message("업비트 상장봇 종료, 내일 오전 8시 재시작")

            break


        new_alram = False  # 새 공지 없음 디폴트
        # result = get_bit_announcements()
        result = get_upbit_announcements()

        if result == 'retry':
            continue  # 루프의 시작으로 돌아가서 다시 시도

        # print("뉴알람값", new_alram)  # 새 공지가 뜨면 True

        if new_alram:
            # 업비트 상장 코인이 바이낸스 선물 리스트에 있는지 찾기
            cleaned_usdt_future_list=load_titles_from_json(bnc_ticker_list_path)
            bnc_able_list = []
            new_word = load_titles_from_json(upbit_word_path)
            for item in cleaned_usdt_future_list:
                if item in new_word:
                    bnc_able_list.append(item)

            # print(able_list)
            print("상장뉴스와 일치하는 바이낸스 코인 개수", len(bnc_able_list))



        # if 1 >0 :
            bnc_able_list = [] #############################바이낸스는 건너 뛴다 당분간 
            if len(bnc_able_list) > 0:  
                # 옵션 데이터 불러오기
                with open(upbit_sj_config_path, 'r') as f:
                    config = json.load(f)

                # JSON 데이터에서 변수 설정
                stop_loss_percent = config['stop_loss_percent'] / 100
                callbackRate = config['callbackRate']
                activationPriceRate = config['activationPriceRate'] / 100
                investUsdt = config['investUsdt']
                lev = config['lev']

                Binance_AccessKey = config['Binance_AccessKey']
                Binance_ScretKey = config['Binance_ScretKey']
                sleep_sec = config['sleep_sec']


                # 바이낸스 클라이언트 초기화
                client = Client(Binance_AccessKey, Binance_ScretKey)

                binanceX_future = ccxt.binance({
                    'apiKey': Binance_AccessKey,
                    'secret': Binance_ScretKey,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future'
                    }
                })



                # 매수금액 정하기
                buy_usdt = investUsdt
                # print("매수금액 usdt", buy_usdt)

                # for ticker in able_list:
                ticker = bnc_able_list[0]
                print("업비트 상장코인",ticker)


                ticker_future = ticker + '/USDT:USDT'
                ticker_mode = ticker + 'USDT'
                # print("바이낸스 선물 티커명", ticker_future)


                #레버리지 변경
                change_leverage(ticker_mode,lev)
                # time.sleep(30)



                # 코인 선물 가격
                nowPrice_future = myBinance.GetCoinNowPrice(binanceX_future, ticker_future)
                # print("바이낸스 선물 코인 가격", nowPrice_future)
                
                # 코인가격 소수점 자릿수 계산
                price_str = str(nowPrice_future)

                if '.' in price_str:
                    decimal_places = len(price_str.split('.')[1])
                else:
                    decimal_places = 0

                # print("바이낸스 선물 코인 가격의 소수점 자릿수:", decimal_places)



                # 선물 가격에 따른 매수 수량 조정 함수
                def amt_clean(price, amt_swap):
                    if price >= 100:
                        amt = round(amt_swap, 3)
                    elif 100 > price >= 10:
                        amt = round(amt_swap, 2)
                    elif 10 > price >= 1:
                        amt = round(amt_swap, 1)
                    elif 1 > price >= 0.1:
                        amt = math.floor(amt_swap / 10) * 10
                    elif 0.1 > price >= 0.01:
                        amt = math.floor(amt_swap / 100) * 100
                    elif 0.01 > price:
                        amt = math.floor(amt_swap / 1000) * 1000
                    return amt

                amt = buy_usdt / nowPrice_future
                amt = amt_clean(nowPrice_future, amt)






                #롱 진입 
                params = {'positionSide': 'LONG'}
                open_order = binanceX_future.create_order(ticker_future, 'market', 'buy', amt, None, params)
                print("롱 진입정보", open_order)
                now = datetime.now()
                current_time = now.strftime("%Y-%m-%d %H:%M:%S")
                telegram_channel.send_telegram_message("바이낸스 롱 진입완료:" + current_time)



                ##익절값 구하기 : 1시간봉 직전캔들 종가와 현재가격의 길이의 3배, 절반

                #1시간봉 직전캔들 종가 구하기 
                timecandle='1h'
                #대상시간봉
                ohlcv=GetOhlcv(binanceX_future,ticker_future,timecandle)
                # print(ohlcv)
                # 'close' 값 가져오기
                close_prices = ohlcv['close'].astype(float).values
                close_price_before_origin=close_prices[-2]
                print('1시간봉 직전캔들 종가',close_price_before_origin)

                price_length=float(abs(nowPrice_future-close_price_before_origin))
                print('현재가격-직전가격',price_length)



                #지정익절값
                # 롱 진입 수량 체크
                entryPrice_b = 0
                amt_b = 0
                leverage = 0

                # 잔고 정보를 읽어온다.
                balance = binanceX_future.fetch_balance(params={"type": "future"})
                # 매수 코인의 진입 가격, 수량, 레버리지를 불러온다
                for posi in balance['info']['positions']:
                    try:
                        if posi['symbol'] == ticker + 'USDT':
                            if posi['positionSide'] == 'LONG':
                                entryPrice_b = float(posi['entryPrice'])
                                amt_b = float(posi['positionAmt'])
                                leverage = float(posi['leverage'])
                                print("선물 티커명", ticker_future)
                                print("롱 진입 가격", entryPrice_b)
                                print("롱 진입 수량", amt_b)
                                print("롱 레버리지", leverage)
                                # time.sleep(sleep_sec)
                    except Exception as e:
                        print("Exception:", e)


                #익절주문
                tp_price = entryPrice_b +3*float(price_length)
                limit_price = round(tp_price, decimal_places) 

                params = {'positionSide': 'LONG'
                            }
                limit_order=binanceX_future.create_order(ticker_future, 'limit', 'sell', abs(amt_b)*0.5, 
                limit_price, params)
                print("롱 포지션 지정가익절주문",limit_order)

                # 롱 트레일링 주문
                activationPrice = entryPrice_b +price_length
                activationPrice = round(activationPrice, decimal_places)
                print("롱 트레일링 실행 가격", activationPrice)

                params_trailing_stop = {
                    'positionSide': 'LONG',
                    'callbackRate': callbackRate,
                    'activationPrice': activationPrice
                }

                try:
                    trailing_stop_order = binanceX_future.create_order(ticker_future, 'TRAILING_STOP_MARKET', 'sell', abs(amt_b), None, params_trailing_stop)

                    print("롱 트레일링 주문 실행", trailing_stop_order)
                    # telegram_channel.send_telegram_message("바이낸스 선물 상폐숏 주문 완료:" + ticker_future)
                            
                except ccxt.errors.BadRequest as e:
                    print("에러가 발생했습니다:", e)

                


                while True:
                    print("롱포지션 종료및 숏포지션 진입조건 1분마다 찾기")
                    #대상시간봉
                    timecandle='1m'
                    ohlcv_1m=GetOhlcv(binanceX_future,ticker_future,timecandle)
                    # print(ohlcv)

                    #1분마다 데드크로스 찾기
                    ema_50=talib.EMA(ohlcv_1m["close"],50)                        
                    ema_7=talib.EMA(ohlcv_1m["close"],7)                        
                    # ema_50_now = ema_50.iloc[-1]  # 현재 캔들의 EMA 값
                    
                    ema_50_before = ema_50.iloc[-2]  # 직전 캔들의 50 EMA 값
                    ema_50_before2 = ema_50.iloc[-3]  # 전전 캔들의 50 EMA 값

                    ema_7_before = ema_7.iloc[-2]  # 직전 캔들의 7 EMA 값
                    ema_7_before2 = ema_7.iloc[-3]  # 전전 캔들의 7 EMA 값

                    print('50ema 전값 ',ema_50_before)
                    print('50ema 전전값 ',ema_50_before2)
                    print('7ema 전값',ema_7_before)
                    print('7ema 전전값',ema_7_before2)
                    if ema_50_before2 <= ema_7_before2 and ema_50_before >= ema_7_before :
                        print("데드크로스 달성 롱포지션 종료하고 숏포지션 진입")

                        break 

                    # print("1분후 데드크로스 다시 감시")
                    time.sleep(60)



                #롱주문 정리 

                # 롱 진입 수량 체크
                entryPrice_b = 0
                amt_b = 0
                leverage = 0

                # 잔고 정보를 읽어온다.
                balance = binanceX_future.fetch_balance(params={"type": "future"})
                # 매수 코인의 진입 가격, 수량, 레버리지를 불러온다
                for posi in balance['info']['positions']:
                    try:
                        if posi['symbol'] == ticker + 'USDT':
                            if posi['positionSide'] == 'LONG':
                                entryPrice_b = float(posi['entryPrice'])
                                amt_b = float(posi['positionAmt'])
                                leverage = float(posi['leverage'])
                                print("선물 티커명", ticker_future)
                                print("롱 진입 가격", entryPrice_b)
                                print("롱 진입 수량", amt_b)
                                print("롱 레버리지", leverage)
                                # time.sleep(sleep_sec)
                    except Exception as e:
                        print("Exception:", e)


                if amt_b != 0 :
                #포지션이 남아있다면 현재가 종료 
                    params = {'positionSide': 'LONG'}
                    open_order = binanceX_future.create_order(ticker_future, 'market', 'sell', abs(amt_b), None, params)
                
                cancel_all_open_orders(ticker_mode)
                print("모든 남은 주문 취소")

                time.sleep(1.0)
                #숏주문 넣기
                params = {'positionSide': 'SHORT'}
                open_order = binanceX_future.create_order(ticker_future, 'market', 'sell', amt, None, params)
                # print("선물 숏 진입", open_order)


                # 선물 숏 진입 수량 체크
                entryPrice_s = 0
                amt_s = 0
                leverage = 0

                # 잔고 정보를 읽어온다.
                balance = binanceX_future.fetch_balance(params={"type": "future"})
                # 매수 코인의 진입 가격, 수량, 레버리지를 불러온다
                for posi in balance['info']['positions']:
                    try:
                        if posi['symbol'] == ticker + 'USDT':
                            if posi['positionSide'] == 'SHORT':
                                entryPrice_s = float(posi['entryPrice'])
                                amt_s = float(posi['positionAmt'])
                                leverage = float(posi['leverage'])
                                print("선물 티커명", ticker_future)
                                print("숏 진입 가격", entryPrice_s)
                                print("숏 진입 수량", amt_s)
                                print("숏 레버리지", leverage)
                                time.sleep(sleep_sec)
                    except Exception as e:
                        print("Exception:", e)

                #숏익절값 구하기: 상장공지 전 가격과 현재가격의 절반 

                #숏 지정가 익절주문
                tp_price = close_price_before_origin + (entryPrice_s - close_price_before_origin)*0.5

                limit_price = round(tp_price, decimal_places) 
                params = {'positionSide': 'SHORT'
                            }
                limit_order=binanceX_future.create_order(ticker_future, 'limit', 'buy', abs(amt_s)*0.5, 
                limit_price, params)
                print(limit_order)

                #숏 트레일링 주문  
                activationPrice = entryPrice_s * (1-activationPriceRate)
                activationPrice = round(activationPrice, decimal_places)
                print("숏 트레일링 실행 가격", activationPrice)

                params_trailing_stop = {
                    'positionSide': 'SHORT',
                    'callbackRate': callbackRate,
                    'activationPrice': activationPrice
                }

                try:
                    trailing_stop_order = binanceX_future.create_order(ticker_future, 'TRAILING_STOP_MARKET', 'buy', abs(amt_s), None, params_trailing_stop)

                    print("숏 트레일링 주문 실행", trailing_stop_order)
                    # telegram_channel.send_telegram_message("바이낸스 선물 상폐숏 주문 완료:" + ticker_future)
                            
                except ccxt.errors.BadRequest as e:
                    print("에러가 발생했습니다:", e)

                
                #숏포지션 종료조건 1분봉 골든크로스 


                while True:
                    print("숏포지션 종료조건 1분마다 찾기")
                    #대상시간봉
                    timecandle='1m'
                    ohlcv_1m=GetOhlcv(binanceX_future,ticker_future,timecandle)
                    # print(ohlcv)

                    #1분마다 데드크로스 찾기
                    ema_50=talib.EMA(ohlcv_1m["close"],50)                        
                    ema_7=talib.EMA(ohlcv_1m["close"],7)                        
                    # ema_50_now = ema_50.iloc[-1]  # 현재 캔들의 EMA 값
                    
                    ema_50_before = ema_50.iloc[-2]  # 직전 캔들의 50 EMA 값
                    ema_50_before2 = ema_50.iloc[-3]  # 전전 캔들의 50 EMA 값

                    ema_7_before = ema_7.iloc[-2]  # 직전 캔들의 7 EMA 값
                    ema_7_before2 = ema_7.iloc[-3]  # 전전 캔들의 7 EMA 값

                    print('50ema 전값 ',ema_50_before)
                    print('50ema 전전값 ',ema_50_before2)
                    print('7ema 전값',ema_7_before)
                    print('7ema 전전값',ema_7_before2)
                    if ema_50_before2 >= ema_7_before2 and ema_50_before <= ema_7_before :
                        print("골드크로스 달성 숏포지션 종료")

                        break 

                    time.sleep(60)



                # 선물 숏 진입 수량 체크
                entryPrice_s = 0
                amt_s = 0
                leverage = 0

                # 잔고 정보를 읽어온다.
                balance = binanceX_future.fetch_balance(params={"type": "future"})
                # 매수 코인의 진입 가격, 수량, 레버리지를 불러온다
                for posi in balance['info']['positions']:
                    try:
                        if posi['symbol'] == ticker + 'USDT':
                            if posi['positionSide'] == 'SHORT':
                                entryPrice_s = float(posi['entryPrice'])
                                amt_s = float(posi['positionAmt'])
                                leverage = float(posi['leverage'])
                                print("선물 티커명", ticker_future)
                                print("숏 진입 가격", entryPrice_s)
                                print("숏 진입 수량", amt_s)
                                print("숏 레버리지", leverage)
                                time.sleep(sleep_sec)
                    except Exception as e:
                        print("Exception:", e)



                if amt_s != 0 :
                #포지션이 남아있다면 현재가 종료 
                    
                    params = {'positionSide': 'SHORT'}
                    open_order = binanceX_future.create_order(ticker_future, 'market', 'buy', abs(amt_s), None, params)


                cancel_all_open_orders(ticker_mode)
                print("모든 주문 취소")

                #수익률 계산
                #초기자산 불러오기
                total_USDT = load_titles_from_json(bnc_asset_path)

                balance = binanceX_future.fetch_balance(params={"type": "future"})
                time.sleep(sleep_sec)  

                total_USDT_after = float(balance['USDT']['total'])

                profit = round((total_USDT_after-total_USDT)/total_USDT * 100,1) 

                random_delay=2       
                random_pt = random_delay + random.uniform(0, 30)  # 랜덤 지연 시간 추가 
                random_pt =round(random_pt,1)
                # telegram_channel.send_telegram_message("상장코인 감시봇 수익률 %"+str(random_pt))    
                telegram_channel.send_telegram_message("상장코인 감시봇 수익률 %"+str(profit+100))    



            #바이비트 연결
            else:
                # 업비트 상장 코인이 바이비트 선물 리스트에 있는지 찾기
                cleaned_usdt_future_list=load_titles_from_json(bybit_ticker_list_path)
                bybit_able_list = []
                new_word = load_titles_from_json(upbit_word_path)
                for item in cleaned_usdt_future_list:
                    #코인앞에 붙은 숫자를 빼고 비교 
                    cleaned_item = re.sub(r'\d+', '', item)
                    if cleaned_item in new_word:
                        #원래 코인명으로 리스트에 추가
                        bybit_able_list.append(item)





                # bybit_able_list = ['TRX']
                if len(bybit_able_list) > 0:
                    # print("업비트 상장공지 바이비트에서 발견. 롱진입 시작")
                    # 옵션 데이터 불러오기
                    with open(upbit_sj_config_path, 'r') as f:
                        config = json.load(f)

                    # JSON 데이터에서 변수 설정
                    stop_loss_percent = config['stop_loss_percent'] / 100
                    tp_rate = config['tp_rate'] / 100
                    callbackRate = config['callbackRate']
                    activationPriceRate = config['activationPriceRate'] / 100
                    investUsdt = config['investUsdt']
                    lev = config['lev']


                    Bybit_AccessKey = config['Bybit_AccessKey']
                    Bybit_ScretKey = config['Bybit_ScretKey']
                    sleep_sec = config['sleep_sec']

                    # positionSide = 'BOTH'  # 원웨이모드

                    from pybit.unified_trading import HTTP
                    session = HTTP(
                        api_key=Bybit_AccessKey,
                        api_secret=Bybit_ScretKey,
                    )

                    bybitX = ccxt.bybit(config={
                        'apiKey': Bybit_AccessKey,
                        'secret': Bybit_ScretKey,
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future'
                        }
                    })

    

                    # # 헷지모드,양방방 모드로 설정// 코드 나중에 찾자




                    # for ticker in able_list:
                    ticker = bybit_able_list[0]

                    ticker_future = ticker + '/USDT:USDT'
                    # print("바이비트 선물 티커명", ticker_future)

                    Target_Coin_Symbol = ticker_future.replace("/", "").replace(":USDT", "")

                    nowPrice_future = ct_bybit.GetCoinNowPrice(bybitX, ticker_future)
                    print('바이비트 선물 코인 현재가격', nowPrice_future)


                    able_amt = investUsdt / nowPrice_future
                    print('매수가능수량', able_amt)

                    minimun_amount = ct_bybit.GetMinimumAmount(bybitX, Target_Coin_Symbol)
                    print("--- 바이비트 타겟코인:", ticker_future, " 최소수량 : ", minimun_amount)

                    if able_amt < minimun_amount:
                        able_amt = minimun_amount

                    Buy_Amt_Precision = float(bybitX.amount_to_precision(ticker_future, able_amt))
                    print("바이비트 정확도 조정후 1회매수수량", Buy_Amt_Precision)

                    print("------")

                    balances2 = bybitX.fetch_positions(None, {"type": "unified"})
                    amt_b = 0
                    amt_s = 0
                    entryPrice_b = 0
                    entryPrice_s = 0
                    leverage = 0
                    for posi in balances2:
                        if posi['info']['symbol'] == Target_Coin_Symbol and posi['info']['side'] == "Buy":
                            amt_b = float(posi['info']['size'])
                            entryPrice_b = float(posi['info']['avgPrice'])
                            leverage = float(posi['info']['leverage'])
                            break
                    print("--- 바이비트 선물 코인명:", Target_Coin_Symbol, "--- 롱잔고:", amt_b, " 롱진입가격 : ", entryPrice_b, " 롱 레버리지 : ", leverage)

                    for posi in balances2:
                        if posi['info']['symbol'] == Target_Coin_Symbol and posi['info']['side'] == "Sell":
                            amt_s = float(posi['info']['size'])
                            entryPrice_s = float(posi['info']['avgPrice'])
                            leverage = float(posi['info']['leverage'])
                            break
                    print("--- 바이비트 선물 코인명:", Target_Coin_Symbol, "--- 숏잔고:", amt_s, " 숏진입가격 : ", entryPrice_s, " 숏 레버리지 : ", leverage)

                    price_str = str(nowPrice_future)
                    if '.' in price_str:
                        decimal_places = len(price_str.split('.')[1])
                    else:
                        decimal_places = 0

                    print("바이비트 선물 코인 가격의 소수점 자릿수:", decimal_places)

                    def amt_clean(price, amt_swap):
                        if price >= 100:
                            amt = round(amt_swap, 3)
                        elif 100 > price >= 10:
                            amt = round(amt_swap, 2)
                        elif 10 > price >= 1:
                            amt = round(amt_swap, 1)
                        elif 1 > price >= 0.1:
                            amt = math.floor(amt_swap / 10) * 10
                        elif 0.1 > price >= 0.01:
                            amt = math.floor(amt_swap / 100) * 100
                        elif 0.01 > price:
                            amt = math.floor(amt_swap / 1000) * 1000
                        return amt

                    # time.sleep(sleep_sec)
                    # time.sleep(120)

                    # params = {'reduce_only': False, 'close_on_trigger': False, 'positionSide': 'LONG'}
                    params = {
                        'reduce_only': False, 
                        'close_on_trigger': False, 
                        'positionIdx': 1  # 롱 포지션
                    }

                    bybitX.create_market_buy_order(ticker_future, Buy_Amt_Precision, params)
                    # time.sleep(sleep_sec)
                    telegram_channel.send_telegram_message("업비트 상장 봇: 바이비트 롱 진입 완료."+ticker_future)


                    ##익절값 구하기 : 1시간봉 직전캔들 종가와 현재가격의 길이의 3배, 절반

                    #1시간봉 직전캔들 종가 구하기 
                    timecandle='1h'
                    #대상시간봉
                    ohlcv=GetOhlcv(bybitX,ticker_future,timecandle)
                    # print(ohlcv)
                    # 'close' 값 가져오기
                    close_prices = ohlcv['close'].astype(float).values
                    close_price_before_origin=close_prices[-2]
                    print('1시간봉 직전캔들 종가',close_price_before_origin)

                    price_length=float(abs(nowPrice_future-close_price_before_origin))
                    print('현재가격-직전가격',price_length)


                    #지정가 익절주문 넣기



                    #체결주문 정보
                    balances2 = bybitX.fetch_positions(None, {"type": "unified"})
                    amt_b = 0
                    entryPrice_b = 0
                    leverage = 0
                    for posi in balances2:
                        try:
                            if posi['info']['symbol'] == Target_Coin_Symbol and posi['info']['side'] == "Buy":
                                amt_b = float(posi['info']['size'])
                                entryPrice_b = float(posi['info']['avgPrice'])
                                leverage = float(posi['info']['leverage'])
                                print("바이비트 롱진입가격", entryPrice_b)
                                print("바이비트 롱수량", amt_b)
                                time.sleep(sleep_sec)
                                #익절주문
                                tp_price = entryPrice_b +3*float(price_length)
                                limit_price = round(tp_price, decimal_places) 
                                amt_first = float(bybitX.amount_to_precision(ticker_future, amt_b * 0.5))
                                print("정확도 조정후 1차 익절주문수량", amt_first)

                                # params = {'reduce_only': True, 'close_on_trigger': True, 'positionSide': 'LONG'}
                                

                                params = {'reduce_only': True, 'close_on_trigger': True, 'positionIdx': 1 }

                                print(bybitX.create_order(ticker_future, 'limit', 'sell', abs(amt_first), limit_price, params))
                        except Exception as e:
                            print("Exception:", e)




                    #롱 트레일링  #바이비트는 바이낸스와 달리 트리거값을 설정못하고, 현재가격이 트리거 값이 된다. 
                    tp_long = entryPrice_b * (1 + tp_rate)
                    stop_loss_long = entryPrice_b * (1 - stop_loss_percent)
                    trailing_Stop = str(entryPrice_b * float(callbackRate)*0.01)
                    print("올익절값,손절값,추적값", tp_long, stop_loss_long, trailing_Stop)
                    # print("트레일링스탑 콜백레이트 거리", trailing_Stop)

                    print(session.set_trading_stop(
                        category="linear",
                        symbol=Target_Coin_Symbol,
                        takeProfit=tp_long,
                        stopLoss=stop_loss_long,
                        slTriggerB="IndexPrice", #트리거값 
                        # slTriggerB=3, #트리거값 
                        tpslMode="Full",
                        slOrderType="market",
                        trailingStop=trailing_Stop,
                        positionIdx=1,    #0 원웨이 1 헷지 롱포지션, 2 햇지 숏포지션
                    ))

                    while True:
                            print("바이비트 롱포지션 종료및 숏포지션 진입조건 1분마다 찾기")
                            #대상시간봉
                            timecandle='1m'
                            ohlcv_1m=GetOhlcv(bybitX,ticker_future,timecandle)
                            # print(ohlcv)

                            #1분마다 데드크로스 찾기
                            ema_50=talib.EMA(ohlcv_1m["close"],50)                        
                            ema_7=talib.EMA(ohlcv_1m["close"],7)                        
                            # ema_50_now = ema_50.iloc[-1]  # 현재 캔들의 EMA 값
                            
                            ema_50_before = ema_50.iloc[-2]  # 직전 캔들의 50 EMA 값
                            ema_50_before2 = ema_50.iloc[-3]  # 전전 캔들의 50 EMA 값

                            ema_7_before = ema_7.iloc[-2]  # 직전 캔들의 7 EMA 값
                            ema_7_before2 = ema_7.iloc[-3]  # 전전 캔들의 7 EMA 값

                            print('50ema 전값 ',ema_50_before)
                            print('50ema 전전값 ',ema_50_before2)
                            print('7ema 전값',ema_7_before)
                            print('7ema 전전값',ema_7_before2)

                            if ema_50_before2 <= ema_7_before2 and ema_50_before >= ema_7_before :
                                print("데드크로스 달성 롱포지션 종료하고 숏포지션 진입")
                            # if 1> 0:
                                break 

                            # print("1분후 데드크로스 다시 감시")
                            time.sleep(60)
                    # time.sleep(60)
                    #롱주문 정리

                    balances2 = bybitX.fetch_positions(None, {"type": "unified"})
                    amt_b = 0
                    entryPrice_b = 0
                    leverage = 0
                    for posi in balances2:
                        try:
                            if posi['info']['symbol'] == Target_Coin_Symbol and posi['info']['side'] == "Buy":
                                amt_b = float(posi['info']['size'])
                                entryPrice_b = float(posi['info']['avgPrice'])
                                leverage = float(posi['info']['leverage'])
                                print("바이비트 롱진입가격", entryPrice_b)
                                print("바이비트 롱수량", amt_b)

                        except Exception as e:
                            print("Exception:", e)
                    
                    if amt_b != 0 :
                        #롱포지션 종료
                        # params = {'reduce_only': False, 'close_on_trigger': False, 'positionSide': 'LONG'}

                        params = {
                                'reduce_only': True, 
                                'close_on_trigger': True, 
                                'positionIdx': 1  # 롱 포지션
                            }
                        print(bybitX.create_market_sell_order(ticker_future, amt_b, params))

                    # #남은주문 취소하기 
                    # ct_bybit.CancelAllOrder(bybitX,ticker_future)
                    # print("바이비트 남은 주문 취소")

                    time.sleep(1.0)
                    #숏포지션 진입
                    # params = {'reduce_only': False, 'close_on_trigger': False, 'positionSide': 'SHORT'}
                    params = {
                        'reduce_only': False, 
                        'close_on_trigger': False, 
                        'positionIdx': 2  # 헷지숏 포지션
                    }
                    print(bybitX.create_market_sell_order(ticker_future, Buy_Amt_Precision, params))

                    telegram_channel.send_telegram_message("업비트 상장봇: 바이비트 숏 포지션 진입"+ticker_future)                    
                        
                    #포지션정보
                    balances2 = bybitX.fetch_positions(None, {"type": "unified"})
                    amt_s = 0
                    entryPrice_s = 0
                    leverage = 0
                    for posi in balances2:
                        try:
                            if posi['info']['symbol'] == Target_Coin_Symbol and posi['info']['side'] == "Sell":
                                amt_s = float(posi['info']['size'])
                                entryPrice_s = float(posi['info']['avgPrice'])
                                leverage = float(posi['info']['leverage'])
                                print("바이비트  숏진입가격", entryPrice_s)
                                print("바이비트 숏수량", amt_s)
                                time.sleep(sleep_sec)


                        except Exception as e:
                            print("Exception:", e)


                    #숏익절값 구하기: 상장공지 전 가격과 현재가격의 절반 
                    #숏 지정가 익절주문
                    tp_price = close_price_before_origin + (entryPrice_s - close_price_before_origin)*0.5

                    limit_price = round(tp_price, decimal_places) 

                    # params = {'reduce_only': True, 'close_on_trigger': True, 'positionSide': 'SHORT'}
                    params = {
                        'reduce_only': True, 
                        'close_on_trigger': True, 
                        'positionIdx': 2  # 헷지숏 포지션
                    }
                    print(bybitX.create_order(ticker_future, 'limit', 'buy', abs(amt_s), limit_price, params))

                    #숏 트레일링 주문

                    tp_short = entryPrice_s * (1 - tp_rate)
                    stop_loss_short = entryPrice_s * (1 + stop_loss_percent)
                    trailing_Stop = str(entryPrice_s * float(callbackRate)*0.01)
                    print("올익절값,손절값,추적값", tp_short, stop_loss_short, trailing_Stop)
                    # print("트레일링스탑 콜백레이트 거리", trailing_Stop)

                    print(session.set_trading_stop(
                        category="linear",
                        symbol=Target_Coin_Symbol,
                        takeProfit=tp_short,
                        stopLoss=stop_loss_short,
                        slTriggerB="IndexPrice",
                        tpslMode="Full",
                        slOrderType="market",
                        trailingStop=trailing_Stop,
                        positionIdx=2,    #0 원웨이 1 헷지 롱포지션, 2 햇지 숏포지션
                    ))

                    #숏포지션 종료조건 1분봉 골든크로스 
                    while True:
                        print("바이비트 숏포지션 종료조건 1분마다 찾기")
                        #대상시간봉
                        timecandle='1m'
                        ohlcv_1m=GetOhlcv(bybitX,ticker_future,timecandle)
                        # print(ohlcv)

                        #1분마다 데드크로스 찾기
                        ema_50=talib.EMA(ohlcv_1m["close"],50)                        
                        ema_7=talib.EMA(ohlcv_1m["close"],7)                        
                        # ema_50_now = ema_50.iloc[-1]  # 현재 캔들의 EMA 값
                        
                        ema_50_before = ema_50.iloc[-2]  # 직전 캔들의 50 EMA 값
                        ema_50_before2 = ema_50.iloc[-3]  # 전전 캔들의 50 EMA 값

                        ema_7_before = ema_7.iloc[-2]  # 직전 캔들의 7 EMA 값
                        ema_7_before2 = ema_7.iloc[-3]  # 전전 캔들의 7 EMA 값

                        print('50ema 전값 ',ema_50_before)
                        print('50ema 전전값 ',ema_50_before2)
                        print('7ema 전값',ema_7_before)
                        print('7ema 전전값',ema_7_before2)
                        if ema_50_before2 >= ema_7_before2 and ema_50_before <= ema_7_before :
                            print("골드크로스 달성 숏포지션 종료")
                        # if 1 >0 :
                            break 

                        time.sleep(60)


                    # time.sleep(60)
                    #포지션정보
                    balances2 = bybitX.fetch_positions(None, {"type": "unified"})
                    amt_s = 0
                    entryPrice_s = 0
                    leverage = 0
                    for posi in balances2:
                        try:
                            if posi['info']['symbol'] == Target_Coin_Symbol and posi['info']['side'] == "Sell":
                                amt_s = float(posi['info']['size'])
                                entryPrice_s = float(posi['info']['avgPrice'])
                                leverage = float(posi['info']['leverage'])
                                print("바이비트  숏진입가격", entryPrice_s)
                                print("바이비트 숏수량", amt_s)
                                time.sleep(sleep_sec)


                        except Exception as e:
                            print("Exception:", e)

                    if abs(amt_s) >0 :
                        # params = {'reduce_only': True, 'close_on_trigger': True, 'positionSide': 'SHORT'}
                        params = {
                            'reduce_only': True, 
                            'close_on_trigger': True, 
                            'positionIdx': 2  # 헷지숏 포지션
                        }
                        print(bybitX.create_market_buy_order(ticker_future,  abs(amt_s), params))

                    # #모든 바이비트 주문 취소
                    # ct_bybit.CancelAllOrder(bybitX,ticker_future)
                    #수익률 계산
                    #초기자산 불러오기
                    total_USDT = load_titles_from_json(bybit_asset_path)

                    #현재자산 불러오기 
                    balance = bybitX.fetch_balance(params={"type": "unified"})
                    time.sleep(sleep_sec)

                    print(balance['USDT'])
                    print("바이비트 선물총잔고:", float(balance['USDT']['total']))  
                    print("사용가능한 선물잔고:", float(balance['USDT']['free']))  
                    total_USDT_after = float(balance['USDT']['total'])

                    profit = round((total_USDT_after-total_USDT)/total_USDT* 100,1) 

                    # random_delay=2       
                    # random_pt = random_delay + random.uniform(0, 30)  # 랜덤 수익률  
                    # random_pt =round(random_pt,1)
                    # telegram_channel.send_telegram_message("데우스 바이비트 숏 종료후 수익률 %"+str(random_pt))   

                    telegram_channel.send_telegram_message("업비트 상장봇 최종 수익률%"+str(profit+100))   

        
                else:
                    print("---------")
                    print("---------")
                    print("---------")
                    print("업비트 상장공지 뉴스와 일치하는 바이낸스, 바이비트 선물 거래 코인이 없으므로, 매매를 하지 않습니다.")
                    telegram_channel.send_telegram_message("업비트 상장공지 뉴스와 일치하는 바이낸스, 바이비트 선물 거래 코인이 없으므로, 매매를 하지 않습니다.")



        else:
            print("업비트 상장공지 아직 없음")
            # telegram_channel.send_telegram_message("새공지아직없음.")
            random_delay=3       
            sleep_time = random_delay + random.uniform(1, 3)  # 랜덤 지연 시간 추가 
            print(sleep_time)
            time.sleep(sleep_time)  # 3초로 지연 시간 증가

    except Exception as e:
        # 에러 메시지와 스택 트레이스를 텔레그램에 전송
        error_message = f"에러 발생: {str(e)}\n{traceback.format_exc()}"
        print(error_message)  # 디버깅을 위해 콘솔에도 출력
        telegram_channel.send_telegram_message(f"업비트 상장봇 오류 발생:\n{error_message}")
        
        # 일정 시간 대기 후 재시작
        time.sleep(60)