import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- 디자인 ---
st.set_page_config(page_title="유튜브 정밀 분석", layout="wide")
st.markdown("""<style>
    [data-testid="stAppViewContainer"] { background-color: #ffffff; }
    .header-box { border: 3px solid #000; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    div.stButton > button { background-color: #000 !important; color: #fff !important; font-weight: bold; height: 50px; width: 100%; }
</style>""", unsafe_allow_html=True)

# --- 보안 ---
if "pwd" not in st.session_state: st.session_state["pwd"] = False
if not st.session_state["pwd"]:
    st.markdown("<div class='header-box'>🔐 비밀번호를 입력하세요</div>", unsafe_allow_html=True)
    if st.text_input("PASSWORD", type="password") == "0985":
        if st.button("접속"): st.session_state["pwd"] = True; st.rerun()
    st.stop()

# --- 주소 해석 ---
def get_channel_id(url, youtube):
    url = url.split('?')[0].split('/videos')[0].split('/shorts')[0]
    id_match = re.search(r"(UC[\w-]{22})", url)
    if id_match: return id_match.group(1)
    handle_match = re.search(r"@([\w.-]+)", url)
    if handle_match:
        res = youtube.search().list(q="@"+handle_match.group(1), type='channel', part='id', maxResults=1).execute()
        if res.get('items'): return res['items'][0]['id']['channelId']
    return None

# --- 메인 UI ---
st.markdown("<div class='header-box'><h1>📊 유튜브 정밀 진단 대시보드</h1></div>", unsafe_allow_html=True)

api_key = st.secrets.get("YOUTUBE_API_KEY", "")
url_input = st.text_input("🔗 채널 주소", value="https://youtube.com/@jtvnews2021")

c1, c2, c3 = st.columns(3)
with c1: start_date = st.date_input("📅 시작", datetime.now() - timedelta(days=60))
with c2: end_date = st.date_input("📅 종료", datetime.now())
with c3: min_views = st.number_input("📈 최소 조회수", value=1000)

if st.button("🚀 정밀 분석 시작"):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        target_id = get_channel_id(url_input, youtube)
        
        if not target_id:
            st.error("❌ 채널을 찾을 수 없습니다.")
            st.stop()
            
        # 1. 채널 정보 확인
        ch_res = youtube.channels().list(part='snippet,contentDetails', id=target_id).execute()
        channel_name = ch_res['items'][0]['snippet']['title']
        uploads_id = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        st.info(f"📍 분석 중인 채널: **{channel_name}** (ID: {target_id})")
        
        videos = []
        next_page_token = None
        s_dt = datetime.combine(start_date, datetime.min.time())
        e_dt = datetime.combine(end_date, datetime.max.time())
        
        # [진단용] 로그 상자
        with st.expander("🔍 내부 데이터 분석 로그 (영상이 안 나오면 여기를 펼쳐보세요)", expanded=True):
            st.write("--- 데이터를 읽어오는 중입니다... ---")
            
            while True:
                res = youtube.playlistItems().list(part='snippet,contentDetails', playlistId=uploads_id, maxResults=50, pageToken=next_page_token).execute()
                
                for item in res['items']:
                    title = item['snippet']['title']
                    pub_raw = item['snippet']['publishedAt']
                    pub_dt = datetime.strptime(pub_raw, '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=9)
                    v_id = item['contentDetails']['videoId']
                    
                    # 날짜 체크
                    is_date_ok = s_dt <= pub_dt <= e_dt
                    
                    # 조회수 체크
                    v_stats = youtube.videos().list(part='statistics', id=v_id).execute()
                    views = int(v_stats['items'][0]['statistics'].get('viewCount', 0))
                    is_view_ok = views >= min_views
                    
                    # 로그 기록 (상위 10개만 일단 표시)
                    if len(videos) < 10:
                        status_msg = "✅ 통과" if (is_date_ok and is_view_ok) else f"❌ 탈락 (날짜:{'OK' if is_date_ok else 'Fail'}, 조회수:{views})"
                        st.write(f"🎥 {title[:30]}... | {pub_dt.strftime('%m/%d')} | {status_msg}")

                    if is_date_ok and is_view_ok:
                        videos.append({
                            '썸네일': item['snippet']['thumbnails']['medium']['url'],
                            '제목': title, '날짜': pub_dt.strftime("%Y-%m-%d %H:%M"),
                            '조회수': f"{views:,}회", '링크': f"https://www.youtube.com/watch?v={v_id}"
                        })
                
                next_page_token = res.get('nextPageToken')
                # 날짜가 시작날짜보다 과거로 가면 중단
                if not next_page_token or pub_dt < s_dt: break

        if videos:
            st.success(f"결과: {len(videos)}개의 영상을 찾았습니다!")
            st.dataframe(pd.DataFrame(videos), column_config={"썸네일": st.column_config.ImageColumn(), "링크": st.column_config.LinkColumn()}, hide_index=True, use_container_width=True)
        else:
            st.warning("결과가 없습니다. 위의 로그 상자를 확인해 보세요.")

    except Exception as e:
        st.error(f"⚠️ 에러 발생: {e}")
