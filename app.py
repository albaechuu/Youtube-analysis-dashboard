import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 디자인 설정 (Wide 모드 사용) ---
st.set_page_config(page_title="JTV 뉴스 데이터 센터", layout="wide") 
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }
        
        /* [중앙 정렬 핵심] 상단 요소들을 무조건 가운데로 모음 */
        .header-box {
            border: 3px solid #000; padding: 30px; border-radius: 15px; 
            text-align: center; margin-bottom: 25px;
            max-width: 800px; margin: 0 auto; /* 컬럼 없이 중앙 정렬 */
        }
        .header-text { color: #000; font-size: 28px; font-weight: bold; }
        
        /* 버튼 정중앙 고정 */
        div.stButton {
            display: flex;
            justify-content: center;
            margin: 10px 0;
        }
        div.stButton > button {
            background-color: #000 !important; 
            color: #fff !important;
            font-weight: bold !important; 
            border-radius: 5px !important;
            height: 55px !important; 
            width: 320px !important;
            font-size: 18px !important; 
            border: none !important;
        }

        /* 입력창과 안내문구도 중앙으로 제한 */
        .stTextInput, .stAlert, [data-testid="stHorizontalBlock"] {
            max-width: 800px;
            margin: 0 auto;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안: 비밀번호 ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<div class='header-box'><div class='header-text'>🔐 데이터 센터 접속</div></div>", unsafe_allow_html=True)
    pwd = st.text_input("PASSWORD", type="password")
    if st.button("접속하기"): # 중앙 정렬 적용됨
        if pwd == "1234": st.session_state["auth"] = True; st.rerun()
        else: st.error("❌ 비밀번호 오류")
    st.stop()

# --- 3. 메인 화면 ---
st.markdown("<div class='header-box'><div class='header-text'>📊 JTV 뉴스 정밀 분석 대시보드</div></div>", unsafe_allow_html=True)

CHANNEL_ID = "UCWGk_-J9WJxgFBAgJXi4ilA"
UPLOADS_PLAYLIST_ID = "UUWGk_-J9WJxgFBAgJXi4ilA"
api_key = st.secrets.get("YOUTUBE_API_KEY", "")

st.info("📢 현재 **JTV 뉴스 (@jtvnews2021)** 채널의 데이터를 분석 중입니다.")

# 입력창 3개 (날짜, 조회수) - 이건 원래대로 3분할 유지 (중앙 모임 적용)
c1, c2, c3 = st.columns(3)
with c1: start_date = st.date_input("📅 분석 시작일", datetime.now() - timedelta(days=7))
with c2: end_date = st.date_input("📅 종료일", datetime.now())
with c3: min_views = st.number_input("📈 최소 조회수", value=1000, step=500)

st.write("") 

# 분석 버튼
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
                                thumb_url = item['snippet']['thumbnails'].get('high', item['snippet']['thumbnails']['medium'])['url']
                                videos.append({
                                    '썸네일': thumb_url,
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
                    st.success(f"✅ 분석 완료!")
                    
                    # --- [결과 표] 상단과 다르게 화면 가로를 꽉 채우도록 설정 ---
                    st.data_editor(
                        pd.DataFrame(videos), 
                        column_config={
                            "썸네일": st.column_config.ImageColumn(label="미리보기", width="large"), 
                            "링크": st.column_config.LinkColumn("영상 링크")
                        }, 
                        hide_index=True, 
                        use_container_width=True, # 가로 꽉 채우기
                        row_height=200,            # 썸네일 크게 유지
                        height=1000                # 세로 길이 충분히
                    )
                else:
                    st.warning("🧐 해당 조건에 맞는 영상이 없습니다.")
                    
        except Exception as e:
            st.error(f"⚠️ 시스템 오류: {e}")
