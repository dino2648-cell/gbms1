import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 🚨 [필수 확인] 여기에 구글 시트 인터넷 주소창의 URL을 통째로 붙여넣어 주세요!
SHEET_URL = "https://docs.google.com/spreadsheets/d/14mUDHaDal_-ErQIMPNYmy5MPllZ0EZaNcuSFUwso0ZI/edit?gid=0#gid=0" 
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
st.title("🧠 AI 학생 심리 상담 심층 분석 시스템 (DB 연동형)")
st.markdown("단 한 번의 분석으로 엑셀 파일을 정리하고, 구글 클라우드에 데이터를 영구적으로 누적합니다.")

# 2. 구글 시트 URL로 확실하게 데이터 불러오기
try:
    sheet = client.open_by_url(SHEET_URL).sheet1
except Exception as e:
    st.error("❌ 구글 시트에 접근할 수 없습니다. URL이 정확한지, 공유 권한이 잘 들어가 있는지 확인해 주세요!")
    st.stop()

# 기존 데이터 읽기
existing_data = sheet.get_all_values()
if not existing_data:
    # 시트가 비어있으면 뼈대(헤더) 세팅
    sheet.append_row(DB_COLUMNS)
    db_df = pd.DataFrame(columns=DB_COLUMNS)
else:
    db_df = pd.DataFrame(existing_data[1:], columns=existing_data[0])

# --- [대시보드] 누적된 데이터 모니터링 ---
if not db_df.empty:
    with st.expander("📊 현재까지 누적된 전체 학생 상담 현황 보기 (클릭하여 펼치기)", expanded=False):
        st.dataframe(db_df, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**영역별 누적 상담 건수**")
            st.bar_chart(db_df["주요영역"].value_counts())
        with col2:
            st.markdown("**발견된 주요 감정 키워드**")
            st.dataframe(db_df["핵심감정"].value_counts().reset_index().rename(columns={"핵심감정":"키워드", "count":"빈도수"}), hide_index=True)
st.divider()

# --- [신규 분석] 새로운 데이터 업로드 및 DB 추가 ---
st.subheader("📤 새로운 상담 기록 분석 및 DB 저장")

# 샘플 양식 다운로드 버튼
sample_df = pd.DataFrame({
    "학생명": ["홍길동", "김유신"], 
    "상담일자": ["2024-03-04", "2024-03-05"], 
    "상담내용": ["성적이 떨어져서 너무 우울해요.", "친구들과 다퉈서 힘들어요."]
})
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
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        parsed = json.loads(raw_text.strip())
        
        while len(parsed) < len(df_records):
            parsed.append({
                "domain": "분석누락", "emotion": "-", "cause": "누락", 
                "goal": "-", "action": "-", "first_words": "-"
            })
            
        return parsed[:len(df_records)] 
    except Exception as e:
        return f"API 에러 발생: {str(e)}"

if file:
    new_df = pd.read_csv(file)
    st.info(f"📄 총 {len(new_df)}건의 새로운 상담 데이터가 확인되었습니다.")

    if st.button("🚀 분석 시작 및 DB(구글 시트)에 영구 저장하기"):
        with st.spinner("AI가 분석하고 구글 서버에 저장 중입니다. 잠시만 기다려주세요..."):
            
            parsed_data = analyze_all_counseling(new_df)
            
            if isinstance(parsed_data, str):
                st.error(parsed_data)
            elif not parsed_data:
                st.error("오류가 발생했습니다.")
            else:
                analysis_df = pd.DataFrame(parsed_data)
                analysis_df.rename(columns={
                    "domain": "주요영역", "emotion": "핵심감정", "cause": "심리적원인",
                    "goal": "개입목표", "action": "교사행동지침", "first_words": "추천첫마디"
                }, inplace=True)

                final_df = pd.concat([new_df.reset_index(drop=True), analysis_df], axis=1)
                final_df['상담일자'] = pd.to_datetime(final_df['상담일자']).dt.strftime('%Y-%m-%d')
                
                # 구글 시트에 데이터 밀어넣기 (Append)
                data_to_append = final_df[DB_COLUMNS].values.tolist()
                sheet.append_rows(data_to_append)
                
                st.success("✅ 분석 완료! 구글 스프레드시트에 영구적으로 저장되었습니다. (새로고침 하시면 누적 데이터를 볼 수 있습니다)")
                
                st.subheader("이번에 추가된 분석 결과")
                st.dataframe(final_df, use_container_width=True)
