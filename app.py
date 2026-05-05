import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 디자인 설정 (가장 강력한 중앙 정렬 CSS) ---
st.set_page_config(page_title="JTV 뉴스 데이터 센터", layout="centered")
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }
        .header-box {
            border: 3px solid #000; padding: 30px; border-radius: 15px; 
            text-align: center; margin-bottom: 25px;
        }
        .header-text { color: #000; font-size: 28px; font-weight: bold; }
        
        /* 버튼을 감싸는 박스 자체를 중앙으로 정렬 */
        .stButton {
            display: flex;
            justify-content: center;
        }
        
        /* 버튼 본체 디자인 및 정렬 강제 적용 */
        div.stButton > button {
            background-color: #000 !important; 
            color: #fff !important;
            font-weight: bold !important; 
            border-radius: 5px !important;
            height: 55px !important; 
            width: 320px !important; /* 버튼 너비 고정 */
            font-size: 18px !important; 
            border: none !important;
            display: block !important;
            margin: 0 auto !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안: 비밀번호 ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<div class='header-box'><div class='header-text'>🔐 데이터 센터 접속</div></div>", unsafe_allow_html=True)
    pwd = st.text_input("PASSWORD", type="password")
    
    # 3분할 칸을 만들어 가운데 칸에 버튼 배치 (구조적 중앙 정렬)
    _, login_btn_col, _ = st.columns([1, 2, 1])
    with login_btn_col:
        if st.button("접속하기"):
            if pwd == "0985": st.session_state["auth"] = True; st.rerun()
            else: st.error("❌ 비밀번호 오류")
    st.stop()

# --- 3. 메인 화면 ---
st.markdown("<div class='header-box'><div class='header-text'>📊 JTV 뉴스 정밀 분석 대시보드</div></div>", unsafe_allow_html=True)

# [성공했던 마스터 ID]
CHANNEL_ID = "UCWGk_-J9WJxgFBAgJXi4ilA"
UPLOADS_PLAYLIST_ID = "UUWGk_-J9WJxgFBAgJXi4ilA"

api_key = st.secrets.get("YOUTUBE_API_KEY", "")

st.info("📢 현재 **JTV 뉴스 (@jtvnews2021)** 채널의 데이터를 분석 중입니다.")

c1, c2, c3 = st.columns(3)
with c1: start_date = st.date_input("📅 분석 시작일", datetime.now() - timedelta(days=7))
with c2: end_date = st.date_input("📅 분석 종료일", datetime.now())
with c3: min_views = st.number_input("📈 최소 조회수 설정", value=1000, step=500)

st.write("") 

# --- [핵심] 데이터 분석 시작 버튼 중앙 배치 ---
# 화면을 1:2:1 비율로 나누어 가운데 칸(2)에 버튼을 넣습니다.
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    submit = st.button("🚀 데이터 분석 시작")

if submit:
    if not api_key: st.error("API 키를 확인해 주세요.")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            videos = []
            next_page_token = None
            s_dt = datetime.combine(start_date, datetime.min.time())
            e_dt = datetime.combine(end_date, datetime.max.time())

            with st.spinner('유튜브 서버에서 데이터를 수집 중...'):
                while True:
                    res = youtube.playlistItems().list(
                        part='snippet,contentDetails', 
                        playlistId=UPLOADS_PLAYLIST_ID, 
                        maxResults=50, 
                        pageToken=next_page_token
                    ).execute()
                    
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
                    st.success(f"✅ 분석 완료! 총 {len(videos)}개의 영상을 발견했습니다.")
                    st.dataframe(pd.DataFrame(videos), 
                                 column_config={"썸네일": st.column_config.ImageColumn(), "링크": st.column_config.LinkColumn()}, 
                                 hide_index=True, use_container_width=True)
                else:
                    st.warning("🧐 해당 조건에 맞는 영상이 없습니다.")
                    
        except Exception as e:
            st.error(f"⚠️ 시스템 오류: {e}")
