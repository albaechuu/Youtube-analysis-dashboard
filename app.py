import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 디자인 (코랩 스타일 유지) ---
st.set_page_config(page_title="유튜브 분석기", layout="centered")
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }
        .header-box {
            background-color: #ffffff; padding: 30px; 
            border: 3px solid #000000; border-radius: 15px; 
            margin-bottom: 25px; text-align: center;
        }
        .header-text { color: #000000; font-size: 28px; font-weight: bold; }
        div.stButton > button {
            background-color: #000000 !important; color: #ffffff !important;
            font-weight: bold !important; border-radius: 5px !important;
            height: 50px !important; width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안 ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.markdown("<div class='header-box'><div class='header-text'>🔐 접속을 위해 비밀번호를 입력하세요</div></div>", unsafe_allow_html=True)
    pwd = st.text_input("PASSWORD", type="password")
    if st.button("접속하기"):
        if pwd == "0985":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# --- 3. 주소 분석 함수 (대폭 강화) ---
def get_channel_id(url, youtube):
    # 1. URL에서 불필요한 부분 제거 (/videos, /shorts 등)
    url = url.split('?')[0].split('/videos')[0].split('/shorts')[0].split('/featured')[0]
    
    # 2. 직접 ID 형식 (UC...)인 경우
    id_match = re.search(r"(UC[\w-]{22})", url)
    if id_match: return id_match.group(1)
    
    # 3. 핸들 형식 (@name)인 경우
    handle_match = re.search(r"@([\w.-]+)", url)
    if handle_match:
        handle = "@" + handle_match.group(1)
        res = youtube.search().list(q=handle, type='channel', part='id', maxResults=1).execute()
        if res.get('items'): return res['items'][0]['id']['channelId']
    
    return None

# --- 4. 메인 화면 ---
st.markdown("<div class='header-box'><div class='header-text'>📊 유튜브 채널 분석 대시보드</div></div>", unsafe_allow_html=True)

api_key = st.secrets.get("YOUTUBE_API_KEY", "")
url_input = st.text_input("🔗 채널 주소 입력 (예: https://youtube.com/@채널명)", value="https://youtube.com/@jtvnews2021")

col1, col2, col3 = st.columns(3)
with col1: start_date = st.date_input("📅 시작 날짜", datetime.now() - timedelta(days=30))
with col2: end_date = st.date_input("📅 종료 날짜", datetime.now())
with col3: min_views = st.number_input("📈 최소 조회수", value=1000)

if st.button("🚀 데이터 분석 시작"):
    if not api_key: st.error("API 키를 확인해주세요.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            
            # [진단] 주소에서 ID를 찾는 과정을 표시
            with st.status("🔍 채널 정보를 분석 중...", expanded=True) as status:
                target_id = get_channel_id(url_input, youtube)
                if not target_id:
                    st.error("❌ 채널 ID를 찾을 수 없습니다. 주소를 다시 확인해주세요.")
                    st.stop()
                
                st.write(f"✅ 채널 ID 발견: `{target_id}`")
                
                # 채널명 및 업로드 목록 ID 가져오기
                ch_res = youtube.channels().list(part='snippet,contentDetails', id=target_id).execute()
                if not ch_res.get('items'):
                    st.error("❌ 유효하지 않은 채널 ID입니다.")
                    st.stop()
                
                channel_name = ch_res['items'][0]['snippet']['title']
                uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                st.write(f"📺 채널명: **{channel_name}**")
                
                # 데이터 수집
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
                
                status.update(label="✅ 분석 완료!", state="complete", expanded=False)

            if videos:
                st.success(f"🎬 {channel_name} 채널에서 {len(videos)}개의 영상을 찾았습니다!")
                df = pd.DataFrame(videos)
                st.dataframe(df, column_config={"썸네일": st.column_config.ImageColumn(), "링크": st.column_config.LinkColumn()}, hide_index=True, use_container_width=True)
            else:
                st.warning(f"🧐 해당 기간({start_date} ~ {end_date}) 내에 {min_views:,}뷰 이상인 영상이 없습니다.")
                
        except Exception as e:
            st.error(f"⚠️ 시스템 오류: {e}")
