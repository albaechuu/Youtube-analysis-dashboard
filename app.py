import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 1. 디자인 설정 (Wide 레이아웃) ---
st.set_page_config(page_title="JTV 뉴스 데이터 센터", layout="wide") 

st.markdown("""
    <style>
        /* 1. 배경 및 전체 폰트 */
        [data-testid="stAppViewContainer"] { background-color: #ffffff; }

        /* 2. [가장 중요] 표를 제외한 모든 요소를 800px로 가두고 중앙 정렬 */
        /* 이 코드가 버튼, 입력창, 제목 박스, 안내문을 억지로 화면 중앙으로 모읍니다. */
        [data-testid="stVerticalBlock"] > div:not(:has([data-testid="stDataEditor"])) {
            max-width: 800px !important;
            margin: 0 auto !important;
        }

        /* 3. 제목 박스 디자인 복구 */
        .header-box {
            border: 3px solid #000; padding: 25px; border-radius: 12px; 
            text-align: center; margin-bottom: 20px;
            width: 100%;
        }
        .header-text { color: #000; font-size: 26px; font-weight: bold; }
        
        /* 4. 버튼 정중앙 정렬 (flexbox 강제 주입) */
        div.stButton {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
        }
        div.stButton > button {
            background-color: #000 !important; 
            color: #fff !important;
            font-weight: bold !important; 
            border-radius: 5px !important;
            height: 50px !important; 
            width: 300px !important; /* 버튼 너무 크지 않게 고정 */
            font-size: 16px !important; 
            border: none !important;
            margin: 0 auto !important;
        }

        /* 5. 입력창(Columns) 간격 조절 및 중앙 유지 */
        [data-testid="stHorizontalBlock"] {
            gap: 1rem !important;
        }

        /* 6. 결과 표(Data Editor)는 이 모든 제한을 풀고 100% 가로 너비 사용 */
        div[data-testid="stDataEditor"] {
            max-width: 100% !important;
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 보안: 비밀번호 (800px 중앙 정렬 적용됨) ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<div class='header-box'><div class='header-text'>🔐 데이터 센터 접속</div></div>", unsafe_allow_html=True)
    pwd = st.text_input("PASSWORD", type="password")
    if st.button("접속하기"): 
        if pwd == "1234": st.session_state["auth"] = True; st.rerun()
        else: st.error("❌ 비밀번호 오류")
    st.stop()

# --- 3. 메인 화면 ---
st.markdown("<div class='header-box'><div class='header-text'>📊 JTV 뉴스 정밀 분석 대시보드</div></div>", unsafe_allow_html=True)

CHANNEL_ID = "UCWGk_-J9WJxgFBAgJXi4ilA"
UPLOADS_PLAYLIST_ID = "UUWGk_-J9WJxgFBAgJXi4ilA"
api_key = st.secrets.get("YOUTUBE_API_KEY", "")

st.info("📢 현재 **JTV 뉴스 (@jtvnews2021)** 채널의 데이터를 분석 중입니다.")

# 입력 영역 (3열 구성 - 중앙 800px 안에서 옹골차게 배치됨)
c1, c2, c3 = st.columns(3)
with c1: start_date = st.date_input("📅 시작일", datetime.now() - timedelta(days=7))
with c2: end_date = st.date_input("📅 종료일", datetime.now())
with c3: min_views = st.number_input("📈 최소 조회수", value=1000, step=500)

st.write("") 

# 분석 시작 버튼 (CSS에 의해 무조건 정중앙 배치)
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

            with st.spinner('유튜브 데이터 수집 중...'):
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
                    st.success(f"✅ 분석 완료! 총 {len(videos)}개의 영상을 발견했습니다.")
                    
                    # [결과 표] 상단 중앙 정렬 제한을 무시하고 화면 끝까지 광활하게 펼쳐짐
                    st.data_editor(
                        pd.DataFrame(videos), 
                        column_config={
                            "썸네일": st.column_config.ImageColumn(label="미리보기", width="large"), 
                            "링크": st.column_config.LinkColumn("영상 링크")
                        }, 
                        hide_index=True, 
                        use_container_width=True, 
                        row_height=200,            
                        height=900                 
                    )
                else:
                    st.warning("🧐 해당 조건에 맞는 영상이 없습니다.")
                    
        except Exception as e:
            st.error(f"⚠️ 오류 발생: {e}")
