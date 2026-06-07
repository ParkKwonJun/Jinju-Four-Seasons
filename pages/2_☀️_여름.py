import sys
from pathlib import Path
import os
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, date, timedelta
from common import get_service_key, fetch_realtime_kma_temp, fetch_past_kma_temp, station_locations

st.set_page_config(page_title="여름 - 폭염·열섬", page_icon="☀️", layout="wide")
st.header("☀️ 여름철 도시 열섬 현상(UHI) 및 실시간 폭염 분석 대시보드")

# ── 사이드바: 데이터 모드 선택 ────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("📂 데이터 모드 선택")
data_mode = st.sidebar.radio(
    "보고 싶은 데이터를 선택하세요:",
    ["📡 실시간 데이터", "📁 과거 데이터"],
    index=0, key="mode_여름"
)
is_realtime = (data_mode == "📡 실시간 데이터")

# ── 초기값 설정 ─────────────────────────────────────────────────────
real_temp, real_humidity, real_feels = 30.0, 55.0, 32.0
feels_trend = None
api_active = False
picked_date_str = ""

# ── 📡 실시간 데이터 모드 ─────────────────────────────────────────
if is_realtime:
    kma_key = get_service_key()
    if kma_key:
        with st.spinner("🌡️ 기상청 실시간 기온 데이터 조회 중..."):
            kma_res = fetch_realtime_kma_temp(kma_key)
            if kma_res:
                real_temp = kma_res["temp"]
                real_humidity = kma_res["humidity"]
                real_feels = kma_res["feels_like"]
                api_active = True
    
    picked_date = datetime.now().date()
    picked_hour = f"{datetime.now().hour:02d}:00"
    picked_date_str = f"{picked_date.strftime('%Y-%m-%d')} {picked_hour}"

# ── 📅 과거 데이터 모드 ───────────────────────────────────────────
else:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 과거 폭염 데이터 조회 (5월~9월)")
    
    today = datetime.now().date()
    three_years_ago = date(today.year - 2, 1, 1)
    
    raw_picked_date = st.sidebar.date_input(
        "조회할 날짜:",
        value=date(2024, 8, 15),
        min_value=three_years_ago,
        max_value=today,
        key="date_picker_여름"
    )
    
    # 5월~9월만 허용
    if raw_picked_date.month < 5:
        picked_date = date(raw_picked_date.year, 5, 1)
        st.sidebar.warning(f"⚠️ 5월~9월만 조회 가능합니다. {picked_date.year}년 05월 01일로 조정됨")
    elif raw_picked_date.month > 9:
        picked_date = date(raw_picked_date.year, 9, 30)
        st.sidebar.warning(f"⚠️ 5월~9월만 조회 가능합니다. {picked_date.year}년 09월 30일로 조정됨")
    else:
        picked_date = raw_picked_date
    
    picked_hour = st.sidebar.selectbox(
        "조회할 시간대:",
        [f"{i:02d}:00" for i in range(24)],
        index=14,
        key="hour_picker_여름"
    )
    
    picked_date_str = f"{picked_date.strftime('%Y-%m-%d')} {picked_hour}"
    
    kma_key = get_service_key()
    if kma_key:
        with st.spinner(f"📊 {picked_date_str} 기상청 관측 데이터 조회 중..."):
            past_res = fetch_past_kma_temp(kma_key, picked_date, picked_hour)
            if past_res:
                real_temp = past_res["temp"]
                real_humidity = past_res["humidity"]
                real_feels = past_res["feels_like"]
                feels_trend = past_res["hourly_trend"]
                api_active = True

# ── 🌡️ 진주시 전체 행정동 열섬 데이터 생성 ───────────────────────
base_feels = real_feels

# 도시 중심도에 따른 열섬 편차 정의
zone_heat_offset = {
    "원도심": 2.0,      # 가장 높은 열섬
    "신도시": 1.5,
    "동부": 0.8,
    "서부": 0.9,
    "북부": -0.5,      # 외곽 지역
    "남부": -0.3,
    "북서": -0.2,
    "남서": -0.4,
    "남동": -0.6
}

heat_rows = []
for dong_name, location_info in station_locations.items():
    zone = location_info.get("zone", "기타")
    heat_offset = zone_heat_offset.get(zone, 0)
    
    # 도시열섬 편차 + 위치별 추가 보정
    heat_value = round(heat_offset + np.random.uniform(-0.3, 0.3), 1)
    feels_temp = round(base_feels + heat_value, 1)
    
    heat_rows.append({
        "행정동": dong_name,
        "위도": location_info["lat"],
        "경도": location_info["lon"],
        "체감온도(℃)": feels_temp,
        "열섬편차(℃)": heat_value,
        "지역": zone,
        "주소": location_info["address"]
    })

heat_data = pd.DataFrame(heat_rows)

# ── 상단 현황판 ──────────────────────────────────────────────────
st.subheader("📊 진주시 행정동별 폭염 분석")

if api_active:
    st.success(f"📡 **기상청 실시간 관측 데이터** (측정시각: {picked_hour})")
else:
    st.warning(f"⚠️ 기상청 API 조회 불가 - 샘플 데이터 표시 중")

st.caption(f"진주시 기온: {real_temp}℃ / 습도: {real_humidity}% → 체감온도: {real_feels}℃")

max_temp_row = heat_data.loc[heat_data["체감온도(℃)"].idxmax()]
min_temp_row = heat_data.loc[heat_data["체감온도(℃)"].idxmin()]
avg_feels_like = heat_data["체감온도(℃)"].mean()
avg_uhi = heat_data["열섬편차(℃)"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("🚨 최고 폭염 지역", f"{max_temp_row['행정동']}", f"{max_temp_row['체감온도(℃)']} ℃")
col2.metric("❄️ 최저 기온 지역", f"{min_temp_row['행정동']}", f"{min_temp_row['체감온도(℃)']} ℃")
col3.metric("📉 진주시 평균", f"{avg_feels_like:.1f} ℃", f"")
col4.metric("🌡️ 온도차", f"{max_temp_row['체감온도(℃)'] - min_temp_row['체감온도(℃)']:.1f} ℃", "최고-최저")

# ── 시각화 차트 ──────────────────────────────────────────────────
st.subheader("📊 행정동별 열섬 시각화")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    # 체감온도 순정렬 (높은순)
    heat_sorted = heat_data.sort_values("체감온도(℃)", ascending=False)
    fig_t = px.bar(heat_sorted, x="체감온도(℃)", y="행정동", orientation="h", 
                   color="체감온도(℃)", color_continuous_scale="Reds",
                   title="🔥 행정동별 체감온도 (내림차순)")
    fig_t.update_layout(yaxis={'categoryorder': 'total ascending'}, height=600)
    st.plotly_chart(fig_t, use_container_width=True)

with col_chart2:
    # 지역별 열섬 편차
    fig_u = px.box(heat_data, x="지역", y="열섬편차(℃)", color="지역",
                   title="🏙️ 지역별 도시열섬(UHI) 편차 분포")
    st.plotly_chart(fig_u, use_container_width=True)

# ── 📍 진주시 폭염 지수 지도 시각화 ────────────────────────────────
st.subheader("📍 진주시 행정동별 폭염 지수 지도")

fig_map = px.scatter_mapbox(
    heat_data,
    lat='위도',
    lon='경도',
    size=heat_data['열섬편차(℃)'].abs() + 1,  # 절댓값 사용 + 최소 크기(1) 보정
    color='체감온도(℃)',
    hover_name='행정동',
    hover_data={'체감온도(℃)':True, '열섬편차(℃)':True, '지역':True, '주소':False},
    size_max=25,
    zoom=10.8,
    mapbox_style='open-street-map',
    title='🗺️ 진주시 실시간 폭염 지수 분포도',
    color_continuous_scale='RdYlBu_r'
)
fig_map.update_layout(height=600, margin=dict(l=0, r=0, t=50, b=0))

st.plotly_chart(fig_map, use_container_width=True)

# ── 📊 상세 데이터 테이블 ──────────────────────────────────────────
st.subheader("📋 전체 행정동 상세 데이터")

display_columns = ['행정동', '체감온도(℃)', '열섬편차(℃)', '지역', '주소']
display_data = heat_data[display_columns].copy()
display_data = display_data.sort_values('체감온도(℃)', ascending=False).reset_index(drop=True)
display_data.index = display_data.index + 1

st.dataframe(display_data, use_container_width=True)

# ── 24시간 추이 (실제 데이터 트렌드) ──────────────────────────────────
st.subheader("⏰ 24시간 체감온도 및 열지수 변동 추이")

time_hours = [f"{i:02d}:00" for i in range(24)]

if feels_trend and len(feels_trend) == 24:
    # 실제 API 데이터 사용
    heat_trend = [round(v * 0.92, 1) for v in feels_trend]
    df_h = pd.DataFrame({"시간": time_hours, "체감온도(℃)": feels_trend, "열지수(℃)": heat_trend})
    chart_title = "⏰ 하루 시간대별 실제 관측 온도 변화 추이" if api_active else "⏰ 샘플 기반 온도 변화 추이"
else:
    # API 데이터 없을 때: 현재 기온 기반 표준 곡선 생성
    base_cycle = [28, 27, 26, 26, 27, 28, 30, 33, 35, 37, 38, 39, 39, 38, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29]
    offset = real_feels - 37.0
    feels_trend = [round(v + offset, 1) for v in base_cycle]
    heat_trend = [round(v * 0.92, 1) for v in feels_trend]
    df_h = pd.DataFrame({"시간": time_hours, "체감온도(℃)": feels_trend, "열지수(℃)": heat_trend})
    chart_title = "⏰ 표준 여름철 온도 변화 추이 (샘플)"

df_h_melt = df_h.melt(id_vars=["시간"], var_name="항목", value_name="값")

fig_ht = px.line(df_h_melt, x="시간", y="값", color="항목", markers=True,
    title=chart_title,
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