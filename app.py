import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 디자인 설정 (중앙 정렬 + 블랙 포인트) ---
st.set_page_config(page_title="유튜브 정밀 분석기", layout="centered")
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }
        .header-box {
            border: 3px solid #000000; padding: 30px; border-radius: 15px; 
            text-align: center; margin-bottom: 25px;
        }
        .header-text { color: #000000; font-size: 28px; font-weight: bold; }
        div.stButton > button {
            background-color: #000000 !important; color: #ffffff !important;
            font-weight: bold !important; border-radius: 5px !important;
            height: 50px !important; width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안: 비밀번호 체크 ---
if "login_success" not in st.session_state:
    st.session_state["login_success"] = False

if not st.session_state["login_success"]:
    st.markdown("<div class='header-box'><div class='header-text'>🔐 접속을 위해 비밀번호를 입력하세요</div></div>", unsafe_allow_html=True)
    pwd = st.text_input("PASSWORD", type="password")
    if st.button("접속하기"):
        if pwd == "0985":
            st.session_state["login_success"] = True
            st.rerun()
        else: st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# --- 3. 핵심 함수: 채널 ID 찾기 (비싼 검색 대신 저렴한 기능 사용) ---
def get_channel_id_efficient(url, youtube):
    # 핸들(@name) 추출
    handle_match = re.search(r"@([\w.-]+)", url)
    if handle_match:
        handle = "@" + handle_match.group(1)
        # forHandle 방식은 단 1점만 소모합니다 (기존 100점 대비 100배 절약!)
        res = youtube.channels().list(forHandle=handle, part='id').execute()
        if res.get('items'): return res['items'][0]['id']
    
    # 직접 ID(UC...) 추출
    id_match = re.search(r"(UC[\w-]{22})", url)
    if id_match: return id_match.group(1)
    return None

# --- 4. 메인 대시보드 화면 ---
st.markdown("<div class='header-box'><div class='header-text'>📊 유튜브 채널 분석 대시보드</div></div>", unsafe_allow_html=True)

api_key = st.secrets.get("YOUTUBE_API_KEY", "")
url_input = st.text_input("🔗 분석할 채널 주소를 입력하세요", value="https://youtube.com/@jtvnews2021")

col1, col2, col3 = st.columns(3)
with col1: start_date = st.date_input("📅 시작", datetime.now() - timedelta(days=30))
with col2: end_date = st.date_input("📅 종료", datetime.now())
with col3: min_views = st.number_input("📈 최소 조회수", value=1000, step=1000)

if st.button("🚀 데이터 분석 시작"):
    if not api_key: st.error("API 키가 Secrets에 설정되지 않았습니다.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            target_id = get_channel_id_efficient(url_input, youtube)
            
            if not target_id:
                st.error("❌ 채널 ID를 찾을 수 없습니다. 주소 형식을 확인해 주세요.")
                st.stop()
            
            with st.spinner('유튜브에서 데이터를 가져오는 중...'):
                ch_res = youtube.channels().list(part='snippet,contentDetails', id=target_id).execute()
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
                    st.success(f"✅ {channel_name} 채널에서 {len(videos)}개의 영상을 찾았습니다!")
                    st.dataframe(pd.DataFrame(videos), column_config={"썸네일": st.column_config.ImageColumn(), "링크": st.column_config.LinkColumn()}, hide_index=True, use_container_width=True)
                else:
                    st.warning("🧐 해당 조건에 맞는 영상이 없습니다. 날짜나 조회수를 조절해 보세요.")
                    
        except Exception as e:
            if "quotaExceeded" in str(e):
                st.error("🚨 유튜브 API 일일 사용량이 초과되었습니다. 오늘 오후 4시 이후에 다시 시도해 주세요.")
            else:
                st.error(f"⚠️ 에러 발생: {e}")
