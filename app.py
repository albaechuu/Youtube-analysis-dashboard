import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 기본 설정 및 디자인 ---
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
            height: 45px !important; width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.markdown("<div class='header-box'><div class='header-text'>🔐 비밀번호 입력</div></div>", unsafe_allow_html=True)
        pwd = st.text_input("PASSWORD", type="password")
        if st.button("LOGIN"):
            if pwd == "0985": # 비밀번호 수정 가능
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("❌ 틀렸습니다.")
        return False
    return True

# --- 3. 핵심 로직 ---
def get_id_from_url(url, youtube):
    # 주소에서 채널 ID나 핸들을 뽑아내는 정규식
    if "channel/" in url:
        return url.split("channel/")[1].split("/")[0].split("?")[0]
    handle_match = re.search(r"@([\w.-]+)", url)
    if handle_match:
        handle = "@" + handle_match.group(1)
        res = youtube.search().list(q=handle, type='channel', part='id', maxResults=1).execute()
        if res.get('items'): return res['items'][0]['id']['channelId']
    return None

if check_password():
    st.markdown("<div class='header-box'><div class='header-text'>📊 유튜브 채널 분석 대시보드</div></div>", unsafe_allow_html=True)

    api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    
    # UI 배치
    url_input = st.text_input("🔗 채널 주소", value="https://youtube.com/@jtvnews2021")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        start_date = st.date_input("📅 시작", datetime.now() - timedelta(days=30)) # 기본 30일 전으로 변경
    with col2:
        end_date = st.date_input("📅 종료", datetime.now())
    with col3:
        # 이제 조회수를 직접 입력할 수 있습니다! (0을 넣으면 모든 영상 나옴)
        min_views = st.number_input("📈 최소 조회수", value=10000, step=1000)

    if st.button("🚀 분석 시작 (클릭하세요)"):
        if not api_key: st.error("API 키가 없습니다.")
        else:
            try:
                youtube = build('youtube', 'v3', developerKey=api_key)
                target_id = get_id_from_url(url_input, youtube)
                
                if target_id:
                    with st.spinner('데이터 수집 중...'):
                        ch_res = youtube.channels().list(part='contentDetails,snippet', id=target_id).execute()
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
                            st.success(f"✅ '{channel_name}' 채널에서 {len(videos)}개의 영상을 찾았습니다!")
                            st.dataframe(pd.DataFrame(videos), column_config={"썸네일": st.column_config.ImageColumn(), "링크": st.column_config.LinkColumn()}, hide_index=True, use_container_width=True)
                        else:
                            st.warning(f"🧐 해당 기간 내에 {min_views:,}뷰 이상인 영상이 없습니다. 날짜나 조회수를 조절해 보세요.")
                else: st.error("❌ 주소가 올바르지 않습니다. 채널 메인 주소를 넣어주세요.")
            except Exception as e: st.error(f"⚠️ 에러: {e}")
