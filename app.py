import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 🚨 선생님 시트의 '고유 번호(ID)'
SHEET_ID = "14mUDHaDal_-ErQIMPNYmy5MPllZ0EZaNcuSFUwso0ZI" 
# ==========================================

# 저장할 엑셀 기둥(컬럼) 이름 세팅
DB_COLUMNS = ["상담일자", "학생명", "상담내용", "주요영역", "핵심감정", "심리적원인", "개입목표", "교사행동지침", "추천첫마디"]

# 1. API 및 구글 시트 권한 설정
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

@st.cache_resource
def init_connection():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

client = init_connection()

# 페이지 설정
st.set_page_config(page_title="학생 심리 분석 시스템", layout="wide")
st.title("🧠 AI 학생 심리 상담 심층 분석 시스템")
st.markdown("단 한 번의 분석으로 엑셀 파일을 정리하고, 구글 클라우드에 데이터를 영구적으로 누적 및 조회합니다.")

# 2. 구글 시트 데이터 불러오기 (최신화)
try:
    sheet = client.open_by_key(SHEET_ID).sheet1
except Exception as e:
    st.error("❌ 구글 시트에 접근할 수 없습니다. 로봇 권한을 확인해 주세요.")
    st.stop()

existing_data = sheet.get_all_values()
if not existing_data:
    sheet.append_row(DB_COLUMNS)
    db_df = pd.DataFrame(columns=DB_COLUMNS)
else:
    db_df = pd.DataFrame(existing_data[1:], columns=existing_data[0])

# 🎨 [가독성 개선] 개별 학생 리포트를 예쁜 카드로 그려주는 함수
def display_student_card(row):
    with st.container(border=True):
        st.markdown(f"### 👤 {row['학생명']} 학생 (상담일: {row['상담일자']})")
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.info(f"**🗣️ 실제 상담 내용**\n\n{row['상담내용']}")
        with col_right:
            st.markdown(f"**📌 주요 영역:** `{row['주요영역']}`")
            st.markdown(f"**💡 핵심 감정:** `{row['핵심감정']}`")
            st.markdown(f"**🔍 심리적 원인:** {row['심리적원인']}")
            st.markdown(f"**🎯 개입 목표:** {row['개입목표']}")
        st.warning(f"**🛠️ 교사 행동 지침:** {row['교사행동지침']}")
        st.success(f"**💬 추천 첫 마디:** {row['추천첫마디']}")

# ==========================================
# 🗂️ 화면을 2개의 탭으로 깔끔하게 분리
# ==========================================
tab1, tab2 = st.tabs(["🚀 새로운 상담 분석 및 저장", "📊 누적 데이터 조회 및 모니터링"])

# ------------------------------------------
# [탭 1] 새로운 상담 분석 및 저장
# ------------------------------------------
with tab1:
    st.subheader("📤 새로운 상담 기록 분석")
    
    # 샘플 양식 다운로드
    sample_df = pd.DataFrame({"학생명": ["홍길동", "김유신"], "상담일자": ["2024-03-04", "2024-03-05"], "상담내용": ["성적이 떨어져서 너무 우울해요.", "친구들과 다퉈서 힘들어요."]})
    sample_csv = sample_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📄 엑셀(CSV) 샘플 양식 다운로드", data=sample_csv, file_name="counseling_sample.csv", mime="text/csv")

    file = st.file_uploader("작성된 상담 데이터 CSV 파일 업로드", type=["csv"])

    def analyze_all_counseling(df_records):
        records_text = ""
        for i, row in df_records.iterrows():
            records_text += f"[ID: {i}] 학생명: {row['학생명']}, 상담내용: {row['상담내용']}\n"

        prompt = f"""
        당신은 15년 차 경력의 전문 학생 심리 상담사입니다.
        아래 [학생 상담 기록 목록]을 모두 분석하여, 반드시 JSON 배열(Array) 형식으로 출력하세요.
        총 {len(df_records)}명의 데이터가 있습니다. 반드시 {len(df_records)}개의 JSON 객체를 순서대로 배열에 담아 반환하세요.
        마크다운이나 다른 설명은 일절 적지 말고 오직 JSON 배열만 출력하세요.
        
        [학생 상담 기록 목록]
        {records_text}

        [출력 JSON 양식]
        [
          {{
            "domain": "(학업/교우관계/심리정서/진로/가정/학교생활 중 1개)",
            "emotion": "(예: 불안, 무기력 등 핵심 감정 1~2개)",
            "cause": "(이 문제가 발생한 근본적 원인을 1문장으로 추정)",
            "goal": "(상담 시 달성해야 할 단기적 목표)",
            "action": "(교사가 즉시 시도해볼 수 있는 구체적인 지도 방법)",
            "first_words": "(학생의 마음을 열기 위한 교사의 따뜻한 첫 마디)"
          }}
        ]
        """
        try:
            model = genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            if raw_text.startswith("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
http://googleusercontent.com/immersive_entry_chip/2
