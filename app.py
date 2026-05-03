import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 디자인 설정 (코랩 감성 + 버튼 중앙 정렬) ---
st.set_page_config(page_title="JTV 뉴스 분석기", layout="centered")
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }
        .header-box {
            border: 3px solid #000000; padding: 30px; border-radius: 15px; 
            text-align: center; margin-bottom: 25px;
        }
        .header-text { color: #000000; font-size: 28px; font-weight: bold; }
        .stButton { display: flex; justify-content: center; }
        div.stButton > button {
            background-color: #000000 !important; color: #ffffff !important;
            font-weight: bold !important; border-radius: 5px !important;
            height: 55px !important; width: 300px !important;
            border: none !important; font-size: 18px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안: 비밀번호 체크 ---
if "login_success" not in st.session_state:
    st.session_state["login_success"] = False

if not st.session_state["login_success"]:
    st.markdown("<div class='header-box'><div class='header-text'>🔐 비밀번호를 입력하세요</div></div>", unsafe_allow_html=True)
    pwd = st.text_input("PASSWORD", type="password")
    _, login_col, _ = st.columns([1, 1, 1])
    with login_col:
        if st.button("접속하기"):
            if pwd == "0985":
                st.session_state["login_success"] = True
                st.rerun()
            else: st.error("❌ 틀렸습니다.")
    st.stop()

# --- 3. 메인 화면 ---
st.markdown("<div class='header-box'><div class='header-text'>📊 JTV 뉴스 채널 분석기</div></div>", unsafe_allow_html=True)

# 여기에 JTV 뉴스 채널 ID를 직접 미리 넣어둡니다.
# (ID 찾는 법을 모르신다면 일단 아래 형식을 유지하세요)
DEFAULT_CHANNEL_ID = "UCo_m-qY4D-oHhE-j_D8S08A" # jtvnews2021의 예상 ID

api_key = st.secrets.get("YOUTUBE_API_KEY", "")

# 채널 ID가 이미 있으므로 주소창은 '안내용'으로만 둡니다.
st.info(f"📍 현재 분석 대상: **JTV 뉴스 (@jtvnews2021)**")

c1, c2, c3 = st.columns(3)
with c1: start_date = st.date_input("📅 시작", datetime.now() - timedelta(days=30))
with c2: end_date = st.date_input("📅 종료", datetime.now())
with c3: min_views = st.number_input("📈 최소 조회수", value=1000, step=1000)

st.write("") 

btn_col1, btn_col2, btn_col3 = st.columns([1, 2, 1])
with btn_col2:
    submit_btn = st.button("🚀 분석 시작")

if submit_btn:
    if not api_key: st.error("API 키 설정을 확인해주세요.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            with st.spinner('데이터 수집 중...'):
                # 채널 정보를 가져올 때 검색 과정을 거치지 않고 바로 ID로 조회 (점수 절약)
                ch_res = youtube.channels().list(part='snippet,contentDetails', id=DEFAULT_CHANNEL_ID).execute()
                
                if not ch_res.get('items'):
                    st.error("❌ 채널 ID가 올바르지 않습니다. 정확한 ID로 수정해주세요.")
                    st.stop()
                
                channel_name = ch_res['items'][0]['snippet']['title']
                uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                videos = []
                next_page_token = None
                s_dt = datetime.combine(start_date, datetime.min.time())
                e_dt = datetime.combine(end_date, datetime.max.time())

                while True:
                    res = youtube.playlistItems().list(part='snippet,contentDetails', playlistId=uploads_id, maxResults=50, pageToken=next_page_token).execute()
                    for item in res['items']:
                        pub_dt = datetime.strptime(item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=9)
                        if s_dt <= pub_dt <= e_dt:
                            v_id = item['contentDetails']['videoId']
                            v_stats = youtube.videos().list(part='statistics', id=v_id).execute()
                            views = int(v_stats['items'][0]['statistics'].get('viewCount', 0))
                            if views >= min_views:
                                videos.append({
                                    '썸네일': item['snippet']['thumbnails']['medium']['url'],
                                    '제목': item['snippet']['title'],
                                    '날짜': pub_dt.strftime("%Y-%m-%d %H:%M"),
                                    '조회수': f"{views:,}회",
                                    '링크': f"https://www.youtube.com/watch?v={v_id}"
                                })
                        elif pub_dt < s_dt:
                            next_page_token = None; break
                    next_page_token = res.get('nextPageToken')
                    if not next_page_token or pub_dt < s_dt: break

                if videos:
                    st.success(f"✅ {channel_name} 분석 완료! ({len(videos)}개)")
                    st.dataframe(pd.DataFrame(videos), 
                                 column_config={"썸네일": st.column_config.ImageColumn(), "링크": st.column_config.LinkColumn()}, 
                                 hide_index=True, use_container_width=True)
                else:
                    st.warning("🧐 조건에 맞는 영상이 없습니다.")
                    
        except Exception as e:
            if "quotaExceeded" in str(e):
                st.error("🚨 사용량 초과! 오늘 오후 4시 이후에 다시 가능합니다.")
            else: st.error(f"⚠️ 오류: {e}")
