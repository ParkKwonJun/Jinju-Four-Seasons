import sys
from pathlib import Path
import os
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, date, timedelta
import random
from common import (
    get_service_key, get_season_by_date, fetch_realtime_kma_temp, fetch_past_kma_temp
)

SEASON_KEY = "여름"
st.set_page_config(page_title="여름 - 폭염·열섬", page_icon="☀️", layout="wide")
st.header("☀️ 여름철 도시 열섬 현상(UHI) 및 실시간 폭염 분석 대시보드")

# ── 사이드바: 데이터 모드 선택 ────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("📂 데이터 모드 선택")
service_key = get_service_key() # 기존 실시간용 에어코리아 키
default_idx = 0 if service_key else 1
data_mode = st.sidebar.radio(
    "보고 싶은 데이터를 선택하세요:",
    ["📡 실시간 데이터", "📁 과거 기준 데이터"],
    index=default_idx, key="mode_여름"
)
is_realtime = (data_mode == "📡 실시간 데이터")

picked_date_str = ""
kma_api_active = False
past_api_active = False
real_temp, real_humidity, real_feels = 33.0, 60.0, 34.2
feels_trend = []

# ── 📡 실시간 데이터 모드 ─────────────────────────────────────────
if is_realtime:
    if service_key:
        with st.spinner("기상청에서 실시간 진주시 날씨를 조회하는 중..."):
            kma_res = fetch_realtime_kma_temp(service_key)
            if kma_res:
                real_temp = kma_res["temp"]
                real_humidity = kma_res["humidity"]
                real_feels = kma_res["feels_like"]
                kma_api_active = True
    
    picked_date = datetime.now().date()
    picked_hour = f"{datetime.now().hour:02d}:00"
    picked_date_str = f"{picked_date.strftime('%Y-%m-%d')} {picked_hour}"

# ── 📅 과거 기준 데이터 모드 (진짜 과거 기상청 데이터 연동) ──────────────
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 과거 폭염 데이터 날짜 선택 (근 3개년)")
    
    today = datetime.now().date()
    three_years_ago_start = date(today.year - 2, 1, 1)
    
    raw_picked_date = st.sidebar.date_input(
        "조회할 날짜를 선택하세요 (과거 3개년 내 5월~9월):",
        value=date(2024, 8, 21), # 디폴트 날짜 세팅
        min_value=three_years_ago_start,
        max_value=today,
        key="date_picker_raw_여름"
    )
    
    if raw_picked_date.month < 5:
        picked_date = date(raw_picked_date.year, 5, 1)
        st.sidebar.warning(f"⚠️ 5월~9월 제한으로 인해 **{picked_date.year}년 05월 01일**로 자동 조정되었습니다.")
    elif raw_picked_date.month > 9:
        picked_date = date(raw_picked_date.year, 9, 30)
        st.sidebar.warning(f"⚠️ 5월~9월 제한으로 인해 **{picked_date.year}년 09월 30일**로 자동 조정되었습니다.")
    else:
        picked_date = raw_picked_date
        
    picked_hour = st.sidebar.selectbox(
        "조회할 시간대를 선택하세요:",
        [f"{i:02d}:00" for i in range(24)],
        index=14,
        key="hour_picker_여름"
    )
    
    picked_date_str = f"{picked_date.strftime('%Y-%m-%d')} {picked_hour}"
    
    # 🔑 secrets.toml에 새로 추가한 기상청 전용 독립 키 가져오기
    kma_past_key = st.secrets.get("KMA_SERVICE_KEY") if hasattr(st, "secrets") else os.getenv("KMA_SERVICE_KEY")
    
    # 💥 진짜 과거 기상청 데이터 호출 (분리된 전용 키 전달)
    if kma_past_key:
        with st.spinner(f"기상청에서 {picked_date_str} 실제 관측 데이터를 조회하는 중..."):
            past_res = fetch_past_kma_temp(kma_past_key, picked_date, picked_hour)
            if past_res:
                real_temp = past_res["temp"]
                real_humidity = past_res["humidity"]
                real_feels = past_res["feels_like"]
                feels_trend = past_res["hourly_trend"] # 진짜 그날의 24시간 데이터
                past_api_active = True

# ── 🌡️ 데이터 동적 매핑 (도시 열섬 편차 계산) ───────────────────────
if (is_realtime and kma_api_active) or (not is_realtime and past_api_active):
    base_feels = real_feels
else:
    # API 연동 실패 혹은 미연동 시에만 작동하는 백업용 시뮬레이션 로직
    date_seed = int(picked_date.strftime("%Y%m%d")) + int(picked_hour.split(":")[0])
    random.seed(date_seed)
    month_offset = -3.0 if picked_date.month in [5, 9] else 0
    temp_factor = random.uniform(-2.5, 3.5) + month_offset
    base_feels = round(34.5 + temp_factor, 1)

heat_rows = [
    {"행정동": "대안동 (원도심)", "체감온도(℃)": round(base_feels + 1.2, 1), "열섬 편차(℃)": 2.4},
    {"행정동": "계동 (원도심)", "체감온도(℃)": round(base_feels + 0.9, 1), "열섬 편차(℃)": 2.1},
    {"행정동": "상봉동", "체감온도(℃)": round(base_feels + 0.3, 1), "열섬 편차(℃)": 1.8},
    {"행정동": "상대동", "체감온도(℃)": round(base_feels - 0.2, 1), "열섬 편차(℃)": 1.3},
    {"행정동": "정촌면 (외곽)", "체감온도(℃)": round(base_feels - 1.0, 1), "열섬 편차(℃)": 0.7},
]
heat_data = pd.DataFrame(heat_rows)

# ── 상단 현황판 ──────────────────────────────────────────────────
st.subheader("📊 진주시 행정동별 폭염 분석")

if is_realtime and kma_api_active:
    st.success(f"📡 **기상청 실시간 관측 데이터** 반영 중 (측정시각: {picked_hour})")
    st.caption(f"현재 진주 기온: {real_temp}℃ / 습도: {real_humidity}% -> 체감온도: {real_feels}℃")
elif not is_realtime and past_api_active:
    st.success(f"📜 **기상청 실제 과거 관측 데이터** 반영 중 ({picked_date_str})")
    st.caption(f"당시 실제 진주 기온: {real_temp}℃ / 습도: {real_humidity}% -> 실제 체감온도: {real_feels}℃")
else:
    st.info(f"📂 **시뮬레이션 가상 데이터**를 기반으로 분석한 결과입니다. (기상청 API 키 확인 필요)")

max_temp_row = heat_data.loc[heat_data["체감온도(℃)"].idxmax()]
avg_feels_like = heat_data["체감온도(℃)"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("🚨 최고 폭염 지역", f"{max_temp_row['행정동']}", f"{max_temp_row['체감온도(℃)']} ℃")
col2.metric("📉 진주시 평균 체감온도", f"{avg_feels_like:.1f} ℃", f"열섬 평균 편차 +{heat_data['열섬 편차(℃)'].mean():.1f}℃")
col3.metric("🔥 열섬 중심 구역", "대안동·계동", "+2.4 ℃ (주변 대비)")

# ── 시각화 차트 ──────────────────────────────────────────────────
col_chart1, col_chart2 = st.columns(2)
with col_chart1:
    fig_t = px.bar(heat_data, x="행정동", y="체감온도(℃)", color="체감온도(℃)",
                   color_continuous_scale="Reds", title="🔥 행정동별 체감온도 비교", text="체감온도(℃)")
    fig_t.update_traces(textposition="outside")
    st.plotly_chart(fig_t, use_container_width=True)
with col_chart2:
    fig_u = px.bar(heat_data, x="행정동", y="열섬 편차(℃)", color="열섬 편차(℃)",
                   color_continuous_scale="Oranges", title="🏙️ 인근 교외 대비 도시 열섬(UHI) 편차", text="열섬 편차(℃)")
    fig_u.update_traces(textposition="outside")
    st.plotly_chart(fig_u, use_container_width=True)

# ── 24시간 추이 (진짜 데이터 트렌드) ──────────────────────────────────
st.subheader("⏰ 24시간 체감온도 및 열지수 변동 추이")

time_hours = [f"{i:02d}:00" for i in range(24)]

if not feels_trend: # API가 안 돌았을 때의 백업 추이 로직
    base_cycle = [30,29,28,28,29,30,32,35,37,39,40,41,41,40,40,39,38,37,36,35,34,33,32,31]
    offset = base_feels - 38.0 
    feels_trend = [round(v + offset, 1) for v in base_cycle]

heat_trend = [round(v * 0.92, 1) for v in feels_trend]

df_h = pd.DataFrame({"시간": time_hours, "체감온도(℃)": feels_trend, "열지수(℃)": heat_trend})
df_h_melt = df_h.melt(id_vars=["시간"], var_name="항목", value_name="값")

fig_ht = px.line(df_h_melt, x="시간", y="값", color="항목", markers=True,
    title="⏰ 하루 시간대별 실제 관측 온도 변화 추이" if (kma_api_active or past_api_active) else "⏰ 시뮬레이션 온도 변화 추이",
    color_discrete_map={"열지수(℃)": "#ff7f0e", "체감온도(℃)": "#d62728"})
fig_ht.update_layout(xaxis_title="시간", yaxis_title="온도 (℃)", height=450,
    xaxis=dict(tickmode="array", tickvals=time_hours[::3], ticktext=time_hours[::3]))
fig_ht.update_traces(line=dict(width=3))
st.plotly_chart(fig_ht, use_container_width=True)

# ── 🆘 폭염 행동 요령 ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("🆘 진주시 맞춤형 폭염 대비 가이드")

danger_threshold = 35.5
danger_hours = [h for h, val in enumerate(feels_trend) if val >= danger_threshold]
if not danger_hours:
    danger_hours = list(np.argsort(feels_trend)[-4:])
danger_hours.sort()

def group_hours(hour_list):
    if not hour_list: return "없음"
    ranges, start, prev = [], hour_list[0], hour_list[0]
    for h in hour_list[1:]:
        if h == prev + 1: prev = h
        else:
            ranges.append((start, prev))
            start = h; prev = h
    ranges.append((start, prev))
    return " / ".join([f"{r[0]:02d}:00" if r[0]==r[1] else f"{r[0]:02d}:00 ~ {r[1]+1:02d}:00" for r in ranges])

danger_period = group_hours(danger_hours)
cool_hours = list(np.argsort(feels_trend)[:4])
cool_hours.sort()
cool_period = group_hours(cool_hours)

st.write(f"- 선택한 날의 **최고 체감온도**: **{max(feels_trend)} ℃** (원도심 기준)")
st.write(f"- 선택한 날의 **최저 체감온도**: **{min(feels_trend)} ℃**")

c1, c2, c3 = st.columns(3)
with c1:
    st.error(f"🛑 **위험: 야외 활동 자제 시간**\n\n**{danger_period}**")
    st.write("- 기상청 관측 기준, 체감온도가 가장 높았던 위험 구간입니다.")
with c2:
    st.warning("⚠️ **지속적인 수분 보충**\n\n**매 20~30분마다**")
    st.write("- 탈수 예방을 위해 무조건 시원한 물 보충이 필수적입니다.")
with c3:
    st.success(f"✅ **안전: 외출 권장 시간대**\n\n**{cool_period}**")
    st.write("- 하루 중 지표면 열기가 식어 상대적으로 안전한 시간대입니다.")