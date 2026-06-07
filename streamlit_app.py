import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_current_season, HISTORICAL

st.set_page_config(page_title="진주시 사계절 환경·재난 대시보드", page_icon="🌆", layout="wide")
st.title("🌆 진주시 사계절 환경·재난 취약지 분석 대시보드")
st.markdown("---")

current_season = get_current_season()
emoji = {"봄":"🌸","여름":"☀️","가을":"🍂","겨울":"❄️"}
st.info(f"📅 현재 계절: **{emoji[current_season]} {current_season}** — 각 페이지 사이드바에서 📡 실시간 / 📁 과거 데이터를 선택할 수 있습니다!")
st.markdown("""
| 계절 | 분석 주제 |
|------|-----------|
| 🌸 봄 | 미세먼지 · 황사 실시간 취약성 + 마스크 가이드 |
| ☀️ 여름 | 도시 열섬 현상(UHI) + 폭염 행동 요령 |
| 🍂 가을 | 봄/가을 미세먼지,황사 비교 + 대기 정체 분석 |
| ❄️ 겨울 | 제설 사각지대 + 월별 대설 통계 |

> 👈 왼쪽 사이드바에서 계절을 선택하세요.  
> 각 계절 페이지 사이드바에서 **📡 실시간 / 📁 과거 기준 데이터**를 자유롭게 전환할 수 있어요!
""")
st.sidebar.markdown("""
**프로젝트 멤버:** 박권준, 이승윤  
**데이터 출처:**  
- 에어코리아 실시간 대기질  
- 기상청 공공데이터 포털  
- 진주시 개방 데이터  
""")
