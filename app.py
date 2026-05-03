import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="유튜브 채널 분석 대시보드", layout="wide")

# --- 2. 보안: 비밀번호 체크 (나만 접속 가능하게) ---
def check_password():
    """비밀번호가 맞는지 확인하는 함수"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔐 비밀 관제탑 접속")
        password = st.text_input("비밀번호를 입력하세요", type="password")
        if st.button("접속하기"):
            if password == "0985": # <--- 여기에 본인만의 비밀번호를 설정하세요!
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
        return False
    return True

# --- 3. 데이터 분석 로직 (이전과 동일) ---
def get_id_from_url(url, youtube):
    channel_id_match = re.search(r"channel/(UC[\w-]+)", url)
    if channel_id_match: return channel_id_match.group(1)
    handle_match = re.search(r"@([\w.-]+)", url)
    if handle_match:
        handle = "@" + handle_match.group(1)
        search_res = youtube.search().list(q=handle, type='channel', part='id', maxResults=1).execute()
        if search_res.get('items'): return search_res['items'][0]['id']['channelId']
    return None

# 비밀번호 통과 시 메인 대시보드 실행
if check_password():
    # --- 4. 대시보드 UI ---
    st.markdown("<h1 style='text-align: center; border: 3px solid black; padding: 20px; border-radius: 15px;'>📊 유튜브 채널 분석 대시보드</h1>", unsafe_allow_html=True)
    st.write("")

    # 사이드바 설정 (입력창들을 왼쪽으로 몰아서 결과 화면을 넓게 씀)
    with st.sidebar:
        st.header("⚙️ 설정")
        # API 키는 보안을 위해 secrets에서 불러오거나, 없으면 입력받음
        api_key = st.secrets.get("YOUTUBE_API_KEY", "") 
        if not api_key:
            api_key = st.text_input("YouTube API 키", type="password")
        
        channel_url = st.text_input("🔗 채널 주소", value="https://youtube.com/@jtvnews2021")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("📅 시작 날짜", datetime.now())
        with col2:
            end_date = st.date_input("📅 종료 날짜", datetime.now())
        
        st.write("---")
        st.write("🔥 **빠른 필터링**")
        v10 = st.button("1만뷰 이상")
        v50 = st.button("5만뷰 이상")
        v100 = st.button("10만뷰 이상")

    # 결과 처리 로직
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
                target_id = get_id_from_url(channel_url, youtube)
                
                if target_id:
                    with st.spinner('🚀 데이터를 분석 중입니다...'):
                        # 채널 정보 가져오기
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
                                            '제목': item['snippet']['title'],
                                            '시간': pub_dt.strftime("%Y-%m-%d %H:%M"),
                                            '조회수': f"{views:,}회",
                                            '링크': f"https://www.youtube.com/watch?v={v_id}"
                                        })
                                elif pub_dt < s_dt:
                                    next_page_token = None; break
                            next_page_token = res.get('nextPageToken')
                            if not next_page_token or pub_dt < s_dt: break

                    if videos:
                        st.success(f"✅ 총 {len(videos)}개의 영상을 찾았습니다.")
                        
                        # 표 대신 카드 형식이나 데이터프레임으로 출력 (Streamlit은 표 출력이 아주 깔끔함)
                        df = pd.DataFrame(videos)
                        st.data_editor(
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
