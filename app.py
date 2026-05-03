import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 기본 설정 및 디자인 (코랩 디자인 이식) ---
st.set_page_config(page_title="유튜브 채널 분석 대시보드", layout="centered")

# 스트림릿 기본 UI 숨기기 및 코랩 스타일 주입
st.markdown("""
    <style>
        /* 메인 배경 및 폰트 */
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }
        .main { align-items: center; }
        
        /* 헤더 스타일 (900px 박스) */
        .header-box {
            background-color: #ffffff; padding: 40px 20px; 
            border: 3px solid #000000; border-radius: 15px; 
            margin-bottom: 35px; width: 100%; max-width: 800px;
            display: flex; justify-content: center; align-items: center;
            margin-left: auto; margin-right: auto;
        }
        .header-text {
            color: #000000; margin: 0; font-family: 'Arial'; 
            font-size: 32px; text-align: center; letter-spacing: 2px; font-weight: bold;
        }

        /* 버튼 스타일 (블랙 테마) */
        div.stButton > button {
            background-color: #000000 !important;
            color: #ffffff !important;
            font-weight: bold !important;
            border-radius: 5px !important;
            height: 50px !important;
            width: 100% !important;
            border: none !important;
        }
        div.stButton > button:hover { background-color: #333333 !important; }

        /* 입력창 라벨 정렬 */
        .stTextInput label, .stDateInput label {
            font-weight: bold !important;
            color: #000000 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안: 비밀번호 체크 (나만 접속) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<div class='header-box'><h1 class='header-text'>🔐 접속 대기 중</h1></div>", unsafe_allow_html=True)
        password = st.text_input("비밀번호를 입력하세요", type="password")
        if st.button("접속하기"):
            if password == "1234": # <--- 사용자님의 비밀번호
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    return True

# --- 3. 분석 로직 ---
def get_id_from_url(url, youtube):
    channel_id_match = re.search(r"channel/(UC[\w-]+)", url)
    if channel_id_match: return channel_id_match.group(1)
    handle_match = re.search(r"@([\w.-]+)", url)
    if handle_match:
        handle = "@" + handle_match.group(1)
        search_res = youtube.search().list(q=handle, type='channel', part='id', maxResults=1).execute()
        if search_res.get('items'): return search_res['items'][0]['id']['channelId']
    return None

# 메인 화면 실행
if check_password():
    # 헤더 출력
    st.markdown("<div class='header-box'><h1 class='header-text'>📊 유튜브 채널 분석 대시보드</h1></div>", unsafe_allow_html=True)

    # 입력 UI (사이드바 안 쓰고 중앙에 배치)
    api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    
    url_input = st.text_input("🔗 유튜브 주소", value="https://youtube.com/@jtvnews2021")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("📅 시작 날짜", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("📅 종료 날짜", datetime.now())

    st.write("")
    # 버튼 3개 가로 배치
    b1, b2, b3 = st.columns(3)
    with b1: v10 = st.button("1만뷰 이상")
    with b2: v50 = st.button("5만뷰 이상")
    with b3: v100 = st.button("10만뷰 이상")

    target_views = 0
    if v10: target_views = 10000
    elif v50: target_views = 50000
    elif v100: target_views = 100000

    if target_views > 0:
        if not api_key:
            st.error("⚠️ API 키가 설정되지 않았습니다.")
        else:
            try:
                youtube = build('youtube', 'v3', developerKey=api_key)
                target_id = get_id_from_url(url_input, youtube)
                
                if target_id:
                    with st.spinner('🚀 데이터를 분석 중입니다...'):
                        ch_res = youtube.channels().list(part='contentDetails,snippet', id=target_id).execute()
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
                                    if views >= target_views:
                                        videos.append({
                                            '썸네일': item['snippet']['thumbnails']['medium']['url'],
                                            '영상 정보': item['snippet']['title'],
                                            '날짜': pub_dt.strftime("%Y-%m-%d %H:%M"),
                                            '조회수': f"{views:,}회",
                                            '링크': f"https://www.youtube.com/watch?v={v_id}"
                                        })
                                elif pub_dt < s_dt:
                                    next_page_token = None; break
                            next_page_token = res.get('nextPageToken')
                            if not next_page_token or pub_dt < s_dt: break

                    if videos:
                        st.success(f"✅ {target_views:,}회 이상 영상 {len(videos)}개를 찾았습니다.")
                        df = pd.DataFrame(videos)
                        # 표 디자인을 최대한 깔끔하게 출력
                        st.dataframe(
                            df,
                            column_config={
                                "썸네일": st.column_config.ImageColumn("미리보기"),
                                "링크": st.column_config.LinkColumn("유튜브 연결")
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("❌ 조건에 맞는 영상이 없습니다.")
            except Exception as e:
                st.error(f"⚠️ 오류 발생: {e}")
