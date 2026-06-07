import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from common import (
    jinju_station_aliases, jinju_station_search_keywords,
    station_locations, pm10_status, GRADE_MAP,
    fetch_airkorea_pm10, fetch_airkorea_station_list,
    fetch_airkorea_station_realtime, get_service_key,
    HISTORICAL
)

SEASON_KEY = "겨울"
st.set_page_config(page_title="❄️ 겨울 대시보드", page_icon="❄️", layout="wide")

st.sidebar.markdown("---")
st.sidebar.subheader("📂 데이터 모드 선택")
service_key = get_service_key()
default_idx = 0 if service_key else 1
data_mode = st.sidebar.radio(
    "보고 싶은 데이터를 선택하세요:",
    ["📡 실시간 데이터", "📁 과거 기준 데이터"],
    index=default_idx, key="mode_겨울"
)
is_realtime = (data_mode == "📡 실시간 데이터")

api_items, api_error = None, None
jinju_station_metadata, station_list_error = [], None

if is_realtime:
    if not service_key:
        st.sidebar.warning("⚠️ API 키 미설정 → 과거 데이터로 대체합니다.")
        is_realtime = False
    else:
        try:
            station_list = fetch_airkorea_station_list(service_key)
            jinju_station_metadata = [
                s for s in station_list
                if s.get("cityName") == "진주시"
                or any(alias in s.get("stationName", "") or alias in s.get("addr", "")
                       for alias in jinju_station_aliases)
            ]
        except Exception as e:
            station_list_error = str(e)
        if station_list_error:
            st.info("측정소 목록 조회 오류. CSV 업로드로 대체 가능합니다.")
            uploaded = st.file_uploader("진주 측정소 목록 CSV 업로드 (선택)", type=["csv"])
            if uploaded:
                try:
                    jinju_station_metadata = pd.read_csv(uploaded).to_dict(orient="records")
                    station_list_error = None
                    st.success("업로드된 측정소 목록을 사용합니다.")
                except Exception as ee:
                    st.error(f"파일 처리 오류: {ee}")
        try:
            api_items = fetch_airkorea_pm10(service_key)
        except Exception as e:
            api_error = str(e)

def resolve_station_name(alias):
    if not jinju_station_metadata:
        return alias
    keywords = jinju_station_search_keywords.get(alias, [alias])
    for s in jinju_station_metadata:
        sn, addr = s.get("stationName", ""), s.get("addr", "")
        if any(k in sn or k in addr for k in keywords):
            return sn
    return alias

def find_api_item(alias, items):
    if not items:
        return None
    keywords = jinju_station_search_keywords.get(alias, [alias])
    for item in items:
        sn, addr = item.get("stationName", ""), item.get("addr", "")
        if any(k in sn or k in addr for k in keywords):
            return item
    return None

station_rows = []

if is_realtime and service_key:
    st.info("✅ AIRKOREA 실시간 API에서 4개 진주 측정소 데이터를 조회합니다.")
    for alias in jinju_station_aliases:
        station_name = resolve_station_name(alias)
        station_label, data_time = alias, "-"
        pm_value, grade = None, "데이터 없음"
        try:
            rt = fetch_airkorea_station_realtime(service_key, station_name)
            if rt:
                data_time = rt.get("dataTime", "-")
                pm_value  = rt.get("pm10Value")
                grade     = GRADE_MAP.get(str(rt.get("pm10Grade"))) or pm10_status(pm_value)
        except Exception:
            pass
        if (pm_value is None or not str(pm_value).isdigit()) and api_items:
            item = find_api_item(alias, api_items)
            if item:
                data_time    = item.get("dataTime", data_time)
                pm_value     = item.get("pm10Value")
                grade        = GRADE_MAP.get(str(item.get("pm10Grade"))) or pm10_status(pm_value)
                station_name = item.get("stationName", station_name)
        if station_name != alias:
            station_label = f"{alias} ({station_name})"
        station_rows.append({
            "alias": alias, "측정소": station_label,
            "PM10(㎍/㎥)": int(pm_value) if str(pm_value).isdigit() else None,
            "대기질 상태": grade, "측정 시각": data_time
        })
    data_label = "실시간 데이터 (AirKorea)"
else:
    if not is_realtime:
        st.info(f"📁 **과거 기준 데이터** 표시 중 ({HISTORICAL[SEASON_KEY]['year']})")
    else:
        if api_error:
            st.warning(f"실시간 데이터 없음 → 과거 데이터 표시\n원인: {api_error}")
    station_rows = [dict(r) for r in HISTORICAL[SEASON_KEY]["stations"]]
    data_label = f"과거 기준 ({HISTORICAL[SEASON_KEY]['year']})"

realtime_df = pd.DataFrame(station_rows)
realtime_df["PM10(㎍/㎥)"] = pd.to_numeric(realtime_df["PM10(㎍/㎥)"], errors="coerce")
realtime_df = realtime_df.sort_values("PM10(㎍/㎥)", ascending=False, na_position="last").reset_index(drop=True)
valid_df  = realtime_df.dropna(subset=["PM10(㎍/㎥)"])
top_value = valid_df["PM10(㎍/㎥)"].max() if not valid_df.empty else float("nan")
avg_value = valid_df["PM10(㎍/㎥)"].mean() if not valid_df.empty else float("nan")
avg_pm10  = avg_value
max_pm10  = top_value

st.header("❄️ 겨울철 대설 발생 시 제설 사각지대 분석")

st.subheader("📊 진주시 행정동별 대기질 현황")
if is_realtime:
    st.success(f"📡 **{data_label}** 표시 중")
if not valid_df.empty:
    top_station_text = " / ".join(valid_df.loc[valid_df["PM10(㎍/㎥)"] == top_value, "측정소"].tolist())
    st.success(f"📡 최고 PM10 측정소: {top_station_text} - {int(top_value)} ㎍/㎥")
else:
    top_station_text = "정보 없음"

col1, col2, col3 = st.columns(3)
col1.metric("🚨 현재 최약 행정동", top_station_text,
            f"최대 {int(top_value)} ㎍/㎥" if not pd.isna(top_value) else "정보 없음")
col2.metric("📉 진주시 평균 농도",
            f"{avg_value:.1f} ㎍/㎥" if not pd.isna(avg_value) else "-", data_label)
col3.metric("📂 데이터 출처", "실시간" if is_realtime else "과거 기준")

st.subheader("📍 진주시 측정소별 미세먼지·황사 심화도 지도")
loc_df = pd.DataFrame.from_dict(station_locations, orient="index").reset_index().rename(columns={"index": "alias"})
map_df = pd.merge(realtime_df, loc_df, on="alias", how="left")
map_df["미세먼지 심도"] = map_df["PM10(㎍/㎥)"].fillna(1.0)
map_df["황사 심화도"]  = map_df["PM10(㎍/㎥)"].apply(lambda x: round(x * 0.85 + 5, 1) if pd.notna(x) else 1.0)

view_mode = st.radio("지도 보기 선택", ["미세먼지", "황사"], horizontal=True)
if view_mode == "미세먼지":
    map_color, map_size, map_title, color_scale = "미세먼지 심도","미세먼지 심도","진주시 측정소별 미세먼지 심도 지도","thermal"
    hover_data = {"PM10(㎍/㎥)":True,"대기질 상태":True,"황사 심화도":True,"alias":False}
else:
    map_color, map_size, map_title, color_scale = "황사 심화도","황사 심화도","진주시 측정소별 황사 심화도 지도","Reds"
    hover_data = {"황사 심화도":True,"PM10(㎍/㎥)":False,"대기질 상태":True,"alias":False}

fig_map = px.scatter_mapbox(
    map_df, lat="lat", lon="lon", size=map_size, color=map_color,
    hover_name="측정소", hover_data=hover_data, size_max=30, zoom=11,
    mapbox_style="open-street-map", title=map_title, color_continuous_scale=color_scale
)
fig_map.update_layout(height=520)
st.plotly_chart(fig_map, use_container_width=True)

fig_pm10 = px.bar(
    realtime_df, x="PM10(㎍/㎥)", y="측정소", orientation="h",
    text="PM10(㎍/㎥)", color="대기질 상태",
    color_discrete_map={"좋음":"#2ca02c","보통":"#ff7f0e","나쁨":"#d62728",
                        "매우 나쁨":"#8c564b","정보 없음":"#7f7f7f","데이터 없음":"#aaaaaa"},
    title="진주시 측정소별 PM10 농도 비교"
)
fig_pm10.update_layout(yaxis={"categoryorder":"total ascending"}, xaxis_title="PM10 (㎍/㎥)", height=500)
fig_pm10.update_traces(textposition="outside")
st.plotly_chart(fig_pm10, use_container_width=True)

realtime_with_dust = realtime_df.copy()
realtime_with_dust["황사 심화도(㎍/㎥)"] = realtime_with_dust["PM10(㎍/㎥)"].apply(
    lambda x: round(x * 0.85 + 5, 1) if pd.notna(x) else None)
st.dataframe(realtime_with_dust.drop(columns=["alias"], errors="ignore"),
             use_container_width=True, hide_index=True)

# ── 겨울 24시간 추이 ──────────────────────────────────────────────
st.subheader("⏰ 겨울철 24시간 대기질 추이 (시간대별)")
col_a, col_b, col_c = st.columns(3)
col_a.metric("PM10 AQI", f"{int(avg_pm10) if not pd.isna(avg_pm10) else '-'}", "실시간" if is_realtime else "과거 기준")
col_b.metric("난방 연소 영향", "높음", "새벽~오전 농도 상승")
col_c.metric("결빙 위험", "12~2월", "제설 사각지대 주의")

time_hours  = [f"{i:02d}:00" for i in range(24)]
pm10_trend  = [72,75,78,80,82,85,88,82,76,70,65,62,60,58,57,58,62,68,74,78,76,74,73,72]
pm25_trend  = [45,47,50,52,54,56,58,53,49,44,41,38,37,36,35,36,39,43,47,50,48,46,45,45]
chart_data  = pd.DataFrame({"시간":time_hours,"PM10(㎍/㎥)":pm10_trend,"PM2.5(㎍/㎥)":pm25_trend})
chart_data  = chart_data.melt(id_vars=["시간"], var_name="항목", value_name="값")
fig_hourly = px.line(chart_data, x="시간", y="값", color="항목", markers=True,
    title="⏰ 겨울철 24시간 대기질 추이: PM10 + PM2.5",
    color_discrete_map={"PM10(㎍/㎥)":"#1f77b4","PM2.5(㎍/㎥)":"#d62728"})
fig_hourly.update_layout(xaxis_title="시간", yaxis_title="농도 (㎍/㎥)", height=520,
    xaxis=dict(tickmode="array",tickvals=time_hours[::3],ticktext=time_hours[::3]))
fig_hourly.update_traces(line=dict(width=3))
st.plotly_chart(fig_hourly, use_container_width=True)

# ── 제설 사각지대 분석 ─────────────────────────────────────────────
st.markdown("---")
st.subheader("🗺️ 진주시 결빙 위험 사각지대 분석")
st.info("📌 아래는 2024년 겨울 기준 제설 사각지대 데이터입니다.")

df_snow = pd.DataFrame([
    {"지역":"명석면 고갯길","결빙 위험도":5,"제설함 거리(m)":820,"취약 사유":"급경사 + 제설함 부재"},
    {"지역":"집현면 이면도로","결빙 위험도":4,"제설함 거리(m)":650,"취약 사유":"좁은 이면도로"},
    {"지역":"내동면 산복도로","결빙 위험도":4,"제설함 거리(m)":710,"취약 사유":"산악 지형"},
    {"지역":"이반성면 농로","결빙 위험도":3,"제설함 거리(m)":580,"취약 사유":"농로 미관리"},
    {"지역":"수곡면 경사로","결빙 위험도":3,"제설함 거리(m)":540,"취약 사유":"경사 + 음지"},
])

col1, col2 = st.columns(2)
with col1:
    st.metric("제설함 반경 500m 사각지대", "명석면 고갯길 / 집현면 이면도로")
    st.metric("총 위험 지점", f"{len(df_snow)}개소", delta="500m 이내 제설함 없음")
with col2:
    st.metric("최고 위험도 지점", df_snow.loc[df_snow["결빙 위험도"].idxmax(), "지역"], delta="위험도 5점")

col3, col4 = st.columns(2)
with col3:
    fig_sn = px.bar(df_snow, x="지역", y="결빙 위험도", color="결빙 위험도",
        color_continuous_scale="Blues", title="결빙 위험도", text="결빙 위험도")
    fig_sn.update_traces(textposition="outside"); fig_sn.update_layout(height=380)
    st.plotly_chart(fig_sn, use_container_width=True)
with col4:
    fig_dist = px.bar(df_snow, x="지역", y="제설함 거리(m)", color="제설함 거리(m)",
        color_continuous_scale="Purples", title="제설함까지 거리", text="제설함 거리(m)")
    fig_dist.update_traces(textposition="outside"); fig_dist.update_layout(height=380)
    st.plotly_chart(fig_dist, use_container_width=True)

st.dataframe(df_snow, use_container_width=True, hide_index=True)

st.subheader("❄️ 월별 대설·결빙 발생 현황 (2024년 기준)")
df_m = pd.DataFrame({
    "월": ["12월","1월","2월"],
    "대설 발생 일수": [3, 5, 4],
    "결빙 신고 건수": [12, 21, 16],
    "제설 출동 횟수": [8, 14, 11]
})
fig_m = px.bar(df_m, x="월", y=["대설 발생 일수","결빙 신고 건수","제설 출동 횟수"],
    barmode="group", title="월별 대설·결빙 통계")
fig_m.update_layout(height=420)
st.plotly_chart(fig_m, use_container_width=True)

st.markdown("---")
st.subheader("🧊 겨울 외출 대기질 가이드")
avg_val = avg_pm10 if not pd.isna(avg_pm10) else 0
if avg_val <= 30:    safe, must = "종일 자유","특별한 마스크 불필요"
elif avg_val <= 80:  safe, must = "10:00 ~ 18:00","출퇴근 KF80 권장"
elif avg_val <= 150: safe, must = "없음","종일 KF94 권장"
else:                safe, must = "없음","종일 KF94 필수"
c1, c2 = st.columns(2)
c1.success(f"🟢 마스크 완화 가능 시간대\n\n**{safe}**")
c2.error(f"🛑 마스크 착용 권장\n\n**{must}**")
