import gspread
from google.oauth2.service_account import Credentials
import requests
from datetime import datetime, timedelta
import pandas as pd
import os
import json

# GitHub Actions에서 제공한 환경 변수로 인증 설정
credentials_json = os.getenv('GOOGLE_CREDENTIALS')  # GitHub Secrets에 저장된 JSON 내용

# 환경변수 값 출력 (디버깅용)
if credentials_json is None or credentials_json.strip() == "":
    raise ValueError("GOOGLE_CREDENTIALS 환경변수가 비어 있거나 올바르지 않습니다!")

print("GOOGLE_CREDENTIALS:", credentials_json)  # 디버깅용

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# JSON 문자열을 파싱하여 인증 정보 객체 생성
credentials_info = json.loads(credentials_json)
credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

# Google Sheets 인증
gc = gspread.authorize(credentials)

# Google Sheets 열기
spreadsheet_url = "https://docs.google.com/spreadsheets/d/13BYN_0ipYjnPblROvXgvjqnQ7G41dMkghB6mTJOczx0"
sh = gc.open_by_url(spreadsheet_url)
worksheet_rawdata = sh.worksheet('rawdata')  # 'rawdata' 탭 선택
worksheet_dollar = sh.worksheet('dollar')  # 'dollar' 탭 선택

# 환율 API 호출
api_url = "https://v6.exchangerate-api.com/v6/6e77f5cd17d9cb2a7b8d5978/latest/USD"  # 실제 API URL
response = requests.get(api_url)

# 응답이 정상적이면 환율 데이터를 사용
if response.status_code == 200:
    data = response.json()
    today_rate = data['conversion_rates']['KRW']  # USD to KRW 환율
else:
    today_rate = 0  # API 호출 실패 시 처리

# 'rawdata'에서 날짜와 환율 데이터 가져오기
data = worksheet_rawdata.get_all_records()  # 모든 데이터 가져오기
df = pd.DataFrame(data)  # pandas DataFrame으로 변환

# 날짜 형식을 datetime으로 변환
df['Date'] = pd.to_datetime(df['Date'])

# 오늘 날짜 기준으로 3년 전 날짜 계산
today_date = datetime.now()
three_years_ago = today_date - timedelta(days=365*3)

# 3년 범위 내의 데이터 필터링
df_filtered = df[df['Date'] >= three_years_ago]

# 3년 평균 환율 계산
three_year_avg_rate = df_filtered['dollar'].mean()

# 분석 결과 계산
difference = today_rate - three_year_avg_rate
if today_rate > three_year_avg_rate:
    suggestion = f"기다리세요. {difference:.2f}원 높습니다. 오늘 가격: {today_rate:.2f}원, 3년 평균: {three_year_avg_rate:.2f}원"
else:
    suggestion = f"투자하세요. {abs(difference):.2f}원 낮습니다. 오늘 가격: {today_rate:.2f}원, 3년 평균: {three_year_avg_rate:.2f}원"

# 오늘 날짜와 결과
today_date_str = today_date.strftime("%Y-%m-%d")
data_row = [today_date_str, f"{today_rate:.2f}", f"{three_year_avg_rate:.2f}", suggestion]

# 'dollar' 탭에 결과 추가
worksheet_dollar.append_row(data_row)

# 'rawdata' 탭에도 오늘 날짜와 환율 추가
rawdata_row = [today_date_str, f"{today_rate:.2f}"]
worksheet_rawdata.append_row(rawdata_row)

print("데이터 업데이트 완료:", data_row)
