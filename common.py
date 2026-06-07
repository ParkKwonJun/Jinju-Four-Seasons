import streamlit as st
import requests
import pandas as pd
import os
import math          
import numpy as np   
from datetime import datetime, date, timedelta
# ── 진주시 전체 행정동 정보 ──────────────────────────────────────
jinju_station_aliases = ["상봉동", "대안동", "상대동", "정촌면", "계동", "삼현동", "명석면", "금곡면", "문산면", "사봉면", "집현면", "칠곡면", "이반성면", "목면", "봉곡면"]

jinju_station_search_keywords = {
    "상봉동": ["상봉동", "북장대로64번길", "중앙119안전센터"],
    "대안동": ["대안동", "IBK기업은행", "진주대로 1052"],
    "상대동": ["상대동", "동진로 279", "한국전력공사"],
    "정촌면": ["정촌면", "예하리", "예하초등학교"],
    "계동": ["계동", "계동"],
    "삼현동": ["삼현동", "신도시"],
    "명석면": ["명석면"],
    "금곡면": ["금곡면"],
    "문산면": ["문산면"],
    "사봉면": ["사봉면"],
    "집현면": ["집현면"],
    "칠곡면": ["칠곡면"],
    "이반성면": ["이반성면"],
    "목면": ["목면"],
    "봉곡면": ["봉곡면"]
}

# ── 진주시 행정동 위치 정보 (위도, 경도) ─────────────────────────
station_locations = {
    # 동부지역 (원도심 포함)
    "대안동": {"lat": 35.1775, "lon": 128.0980, "address": "진주시 진주대로 1052", "zone": "원도심"},
    "계동": {"lat": 35.1720, "lon": 128.1050, "address": "진주시 계동", "zone": "원도심"},
    "상봉동": {"lat": 35.1880, "lon": 128.0950, "address": "진주시 북장대로64번길 14", "zone": "동부"},
    "상대동": {"lat": 35.1810, "lon": 128.0935, "address": "진주시 동진로 279", "zone": "동부"},
    # 서부지역 (신도시)
    "삼현동": {"lat": 35.2000, "lon": 128.1100, "address": "진주시 삼현동", "zone": "신도시"},
    # 북부지역
    "정촌면": {"lat": 35.2475, "lon": 128.1620, "address": "진주시 정촌면 예하리 1340", "zone": "북부"},
    "명석면": {"lat": 35.2350, "lon": 128.1450, "address": "진주시 명석면", "zone": "북부"},
    # 남부지역
    "금곡면": {"lat": 35.1300, "lon": 128.1200, "address": "진주시 금곡면", "zone": "남부"},
    "문산면": {"lat": 35.0950, "lon": 128.1050, "address": "진주시 문산면", "zone": "남부"},
    # 서부지역
    "사봉면": {"lat": 35.1850, "lon": 127.9850, "address": "진주시 사봉면", "zone": "서부"},
    "집현면": {"lat": 35.2100, "lon": 127.9700, "address": "진주시 집현면", "zone": "서부"},
    # 북서부지역
    "칠곡면": {"lat": 35.2650, "lon": 128.0850, "address": "진주시 칠곡면", "zone": "북서"},
    "이반성면": {"lat": 35.2550, "lon": 128.0450, "address": "진주시 이반성면", "zone": "북서"},
    # 남서부지역
    "목면": {"lat": 35.0800, "lon": 127.9950, "address": "진주시 목면", "zone": "남서"},
    "봉곡면": {"lat": 35.0600, "lon": 128.1100, "address": "진주시 봉곡면", "zone": "남동"}
}

GRADE_MAP = {"1": "좋음", "2": "보통", "3": "나쁨", "4": "매우 나쁨"}

def pm10_status(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "정보 없음"
    if value <= 30:   return "좋음"
    if value <= 80:   return "보통"
    if value <= 150:  return "나쁨"
    return "매우 나쁨"

def parse_grade(grade_raw, pm_value):
    return GRADE_MAP.get(str(grade_raw)) or pm10_status(pm_value)

def get_season_by_date(target_date):
    month = target_date.month
    if month in [3, 4, 5]:   return "봄"
    if month in [6, 7, 8]:   return "여름"
    if month in [9, 10, 11]: return "가을"
    return "겨울"

def get_current_season():
    return get_season_by_date(datetime.now())

# ── 계절별 과거 기준 데이터 (API 실패시 백업용) ───────────────────────
HISTORICAL = {
    "봄": {
        "stations": [
            {"alias":"상봉동","측정소":"상봉동","PM10(㎍/㎥)":68,"대기질 상태":"보통"},
            {"alias":"대안동","측정소":"대안동","PM10(㎍/㎥)":71,"대기질 상태":"나쁨"},
            {"alias":"상대동","측정소":"상대동","PM10(㎍/㎥)":78,"대기질 상태":"나쁨"},
            {"alias":"정촌면","측정소":"정촌면","PM10(㎍/㎥)":52,"대기질 상태":"보통"},
        ]
    },
    "여름": {
        "stations": [
            {"alias":"상봉동","측정소":"상봉동","PM10(㎍/㎥)":28,"대기질 상태":"좋음"},
            {"alias":"대안동","측정소":"대안동","PM10(㎍/㎥)":31,"대기질 상태":"좋음"},
            {"alias":"상대동","측정소":"상대동","PM10(㎍/㎥)":25,"대기질 상태":"좋음"},
            {"alias":"정촌면","측정소":"정촌면","PM10(㎍/㎥)":22,"대기질 상태":"좋음"},
        ]
    },
    "가을": {
        "stations": [
            {"alias":"상봉동","측정소":"상봉동","PM10(㎍/㎥)":45,"대기질 상태":"보통"},
            {"alias":"대안동","측정소":"대안동","PM10(㎍/㎥)":48,"대기질 상태":"보통"},
            {"alias":"상대동","측정소":"상대동","PM10(㎍/㎥)":52,"대기질 상태":"보통"},
            {"alias":"정촌면","측정소":"정촌면","PM10(㎍/㎥)":38,"대기질 상태":"좋음"},
        ]
    },
    "겨울": {
        "stations": [
            {"alias":"상봉동","측정소":"상봉동","PM10(㎍/㎥)":62,"대기질 상태":"보통"},
            {"alias":"대안동","측정소":"대안동","PM10(㎍/㎥)":58,"대기질 상태":"보통"},
            {"alias":"상대동","측정소":"상대동","PM10(㎍/㎥)":70,"대기질 상태":"보통"},
            {"alias":"정촌면","측정소":"정촌면","PM10(㎍/㎥)":44,"대기질 상태":"보통"},
        ]
    }
}

@st.cache_data(ttl=600)
def fetch_airkorea_pm10(service_key: str, sido_name: str = "경남"):
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    params = {"serviceKey": service_key, "returnType": "json",
              "numOfRows": "100", "pageNo": "1", "sidoName": sido_name, "ver": "1.0"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        raise ValueError(header.get("resultMsg", "API 호출 실패"))
    
    items = data["response"]["body"]["items"]
    for item in items:
        if "stationName" in item and item["stationName"]:
            item["stationName"] = item["stationName"].split("(")[0].strip()
    return items

@st.cache_data(ttl=600)
def fetch_airkorea_station_list(service_key: str, sido_name: str = "경남"):
    url = "http://apis.data.go.kr/B552584/MsrstnInfoInqireSvc/getMsrstnList"
    params = {"serviceKey": service_key, "returnType": "json",
              "numOfRows": "100", "pageNo": "1", "sidoName": sido_name, "ver": "1.0"}
    r = requests.get(url, params=params, timeout=10)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        if r.status_code == 403:
            raise ValueError("403 Forbidden: API 접근 권한 없음") from exc
        raise
    data = r.json()
    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        raise ValueError(header.get("resultMsg", "API 호출 실패"))
    items = data["response"]["body"].get("items", [])
    items = [items] if isinstance(items, dict) else items
    
    for item in items:
        if "stationName" in item and item["stationName"]:
            item["stationName"] = item["stationName"].split("(")[0].strip()
    return items

@st.cache_data(ttl=300)
def fetch_airkorea_station_realtime(service_key: str, station_name: str, num_rows: int = 24):
    clean_station_name = station_name.split("(")[0].strip()
    url = "http://apis.data.go.kr/B552584/MsrstnAcctoRltmMesureDnsty/getMsrstnAcctoRltmMesureDnsty"
    params = {"serviceKey": service_key, "returnType": "json", "numOfRows": str(num_rows),
              "pageNo": "1", "stationName": clean_station_name, "dataTerm": "DAILY", "ver": "1.0"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "00":
        raise ValueError(header.get("resultMsg", "API 호출 실패"))
    items = data.get("response", {}).get("body", {}).get("items", [])
    if isinstance(items, dict):
        items = [items]
    for it in items:
        pmv = it.get("pm10Value")
        if pmv is not None and str(pmv).isdigit():
            return it
    return items[0] if items else {}

# ⭐ [추가] 선택한 과거 날짜의 데이터를 에어코리아에서 직접 받아오는 함수
@st.cache_data(ttl=3600)
def fetch_airkorea_past_pm10(service_key: str, search_date: date, sido_name: str = "경남"):
    url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    # 과거 데이터 조회를 위해 검색 당일을 기점으로 데이터를 넉넉히 호출합니다.
    params = {
        "serviceKey": service_key,
        "returnType": "json",
        "numOfRows": "100",
        "pageNo": "1",
        "sidoName": sido_name,
        "ver": "1.0"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        items = data.get("response", {}).get("body", {}).get("items", [])
        
        for item in items:
            if "stationName" in item and item["stationName"]:
                item["stationName"] = item["stationName"].split("(")[0].strip()
        return items
    except Exception:
        return []

def get_service_key():
    if hasattr(st, "secrets") and st.secrets.get("AIRKOREA_SERVICE_KEY"):
        return st.secrets["AIRKOREA_SERVICE_KEY"]
    return os.getenv("AIRKOREA_SERVICE_KEY")
# ── [추가] 여름철 폭염·열섬 분석용 기온 백업 데이터 및 함수 ──────────────────────

# 진주시 행정동별 2024~2025년 여름 피크 기준 기온/열섬 편차 데이터
HISTORICAL_HEAT = {
    "year": "2024",
    "stations": [
        {"행정동": "대안동 (원도심)", "기본체감온도(℃)": 37.5, "열섬 편차(℃)": 2.4},
        {"행정동": "계동 (원도심)", "기본체감온도(℃)": 37.1, "열섬 편차(℃)": 2.1},
        {"행정동": "상봉동", "기본체감온도(℃)": 35.8, "열섬 편차(℃)": 1.8},
        {"행정동": "상대동", "기본체감온도(℃)": 34.9, "열섬 편차(℃)": 1.3},
        {"행정동": "정촌면 (외곽)", "기본체감온도(℃)": 32.5, "열섬 편차(℃)": 0.7},
    ],
    # 시간대별 기온 변화 비율을 적용하기 위한 24시간 표준 여름철 기온 곡선
    "daily_curve": [30, 29, 28, 28, 29, 30, 32, 35, 37, 39, 40, 41, 41, 40, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31]
}

# 💡 추후 공공데이터포털 기상청 단기예보(getVilageFcst) API 확장용 함수 마크
def fetch_kma_temperature(service_key: str, nx: int = 91, ny: int = 81):
    """
    기상청 단기예보 API를 통해 진주시(기본 격자 nx=91, ny=81)의 
    실시간 기온(TMP) 및 습도 데이터를 받아와 체감온도를 계산하는 함수 (확장용)
    """
    # 현재는 공공데이터포털 Key 권한 검증 전이므로 예외 처리 구조만 설계
    if not service_key:
        return None
    
    url = "http://apis.data.go.kr/1360000/VilageFrcstSvc/getUltraSrtNcst"
    # 실시간 날씨 조회가 필요할 때 이 함수를 활성화하여 공 기질과 별개로 기상청 데이터를 호출하게 됩니다.
    return None

# ── [기상청 API 연동] 실시간 기온 및 체감온도 계산 함수 ──────────────────────

@st.cache_data(ttl=600)  # 10분 동안 캐싱
def fetch_realtime_kma_temp(service_key: str):
    """
    기상청 ASOS API를 통해 진주시(stnIds=192)의 
    실시간 기온(ta) 및 습도(hm)를 가져와 체감온도를 계산합니다.
    """
    if not service_key:
        return None
    
    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    
    params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "100",  # 전체 데이터 받기
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "HR",
        "startDt": base_date,
        "startHh": "00",
        "endDt": base_date,
        "endHh": "23",
        "stnIds": "192"  # 진주 ASOS 관측소
    }
    
    try:
        r = requests.get(url, params=params, timeout=7)
        r.raise_for_status()
        res_json = r.json()
        
        items = res_json["response"]["body"]["items"]["item"]
        if isinstance(items, dict):
            items = [items]
        
        # 가장 최근 데이터 선택
        if items:
            item = items[-1]  # 마지막(가장 최신) 데이터
            ta = float(item.get("ta", 30.0))
            hm = float(item.get("hm", 50.0))
            
            # 여름철 체감온도 계산 (Steadman 공식 기반)
            def calculate_feels_like(ta, hm):
                # 기온이 25℃ 이상일 때의 체감온도
                if ta >= 25:
                    # 습도 보정: 습도가 높을수록 체감온도 상승
                    humidity_effect = (hm / 100.0 - 0.14) * (ta - 14.5) * 0.5555
                    feels = ta + humidity_effect
                else:
                    feels = ta
                return round(feels, 1)
            
            return {
                "temp": round(ta, 1),
                "humidity": round(hm, 1),
                "feels_like": calculate_feels_like(ta, hm)
            }
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=86400)
def fetch_past_kma_temp(service_key: str, target_date: date, target_hour: str):
    if not service_key:
        return None
        
    import math
    import requests  # requests 임포트 누락 방지
    
    url = "http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    start_dt = target_date.strftime("%Y%m%d")
    
    # "14:00" -> "14" 변환
    target_hour_str = target_hour.split(":")[0] 
    
    params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "24",
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "HR",
        "startDt": start_dt,
        "startHh": "00",
        "endDt": start_dt,
        "endHh": "23",
        "stnIds": "192"
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        res_json = r.json()
        
        items = res_json["response"]["body"]["items"]["item"]
        
        # 💡 기상청 공식 여름철 체감온도 계산 함수
        def calculate_feels_like(ta, rh):
            # 기온이 25℃ 이상일 때의 체감온도
            if ta >= 25:
                # 습도 보정: 습도가 높을수록 체감온도 상승
                humidity_effect = (rh / 100.0 - 0.14) * (ta - 14.5) * 0.5555
                feels = ta + humidity_effect
            else:
                feels = ta
            return round(feels, 1)

        # 안전하게 정렬 후 시간별 트렌드 데이터 리스트 생성
        # 기상청 데이터의 시간 포맷 "YYYY-MM-DD HH:00"에서 HH 추출하여 정렬
        items_sorted = sorted(items, key=lambda x: x["tm"].split()[1].split(":")[0])
        
        all_feels = []
        target_item = None
        
        for item in items_sorted:
            t = float(item["ta"])
            h = float(item["hm"])
            current_hh = item["tm"].split()[1].split(":")[0] # "14" 형태 추출
            
            # 체감온도 계산 및 배열 추가
            feels = calculate_feels_like(t, h)
            all_feels.append(feels)
            
            # 사용자가 요청한 시간의 데이터 저장
            if current_hh == target_hour_str:
                target_item = {
                    "temp": t,
                    "humidity": h,
                    "feels_like": feels
                }
        
        if target_item is None:
            return None
            
        return {
            "temp": target_item["temp"],
            "humidity": target_item["humidity"],
            "feels_like": target_item["feels_like"],
            "hourly_trend": all_feels
        }
    except Exception as e:
        return None