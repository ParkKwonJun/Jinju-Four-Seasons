# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

### AirKorea API 키 설정

실시간 봄철 미세먼지 데이터를 사용하려면 `AIRKOREA_SERVICE_KEY`를 설정해야 합니다.

1. `.streamlit/secrets.toml` 파일을 열어 아래처럼 입력하세요.

   ```toml
   AIRKOREA_SERVICE_KEY = "여기에_실제_API_KEY를_입력하세요"
   ```

2. 또는 환경 변수로 설정할 수도 있습니다.

   ```bash
   export AIRKOREA_SERVICE_KEY="여기에_실제_API_KEY"
   ```

3. 입력 후 다시 앱을 실행하면 실시간 진주시 PM10 데이터 호출을 시도합니다.
