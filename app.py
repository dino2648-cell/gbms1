import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 🚨 선생님 시트의 '고유 번호(ID)'
SHEET_ID = "14mUDHaDal_-ErQIMPNYmy5MPllZ0E ঐতিহ্যQIMPNYmy5MPllZ0EZaNcuSFUwso0ZI" 
# ==========================================

# 🌟 [업데이트] 새로운 기둥(컬럼) 2개 추가!
DB_COLUMNS = ["상담일자", "학생명", "상담내용", "상담요약", "주요영역", "핵심감정", "심리적원인", "전문적분석", "개입목표", "교사행동지침", "추천첫마디"]

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
st.title("🧠 AI 학생 심리 상담 심층 분석 시스템 (PRO)")
st.markdown("단 한 번의 분석으로 상담을 요약하고, 전문가 수준의 심리 분석 결과를 구글 클라우드에 영구 누적합니다.")

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

# 🎨 [가독성+전문성 개선] 개별 학생 리포트를 예쁜 카드로 그려주는 함수
def display_student_card(row):
    with st.container(border=True):
        st.markdown(f"### 👤 {row['학생명']} 학생 (상담일: {row['상담일자']})")
        
        # 🌟 새로 추가된 '상담 요약'을 눈에 띄게 배치
        st.info(f"**📝 상담 핵심 요약:** {row['상담요약']}")
        
        col_left, col_right = st.columns([1, 1])
        with col_left:
            with st.expander("🗣️ 실제 상담 내용 원본 보기 (클릭)"):
                st.write(row['상담내용'])
            st.markdown(f"**📌 주요 영역:** `{row['주요영역']}`")
            st.markdown(f"**💡 핵심 감정:** `{row['핵심감정']}`")
        with col_right:
            st.markdown(f"**🔍 심리적 원인:** {row['심리적원인']}")
            st.markdown(f"**🎯 개입 목표:** {row['개입목표']}")
            
        # 🌟 새로 추가된 '전문적 분석' 및 지침
        st.success(f"**🧠 전문가 심층 분석 (심리학적 관점):** {row['전문적분석']}")
        st.warning(f"**🛠️ 교사 행동 지침:** {row['교사행동지침']}")
        st.markdown(f"> **💬 추천 첫 마디:** {row['추천첫마디']}")

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

        # 🌟 AI 프롬프트 대폭 강화 (요약 및 전문 분석 추가)
        prompt = f"""
        당신은 15년 차 경력의 수석 학생 심리 상담사 및 교육 심리학 전문가입니다.
        아래 [학생 상담 기록 목록]을 모두 분석하여, 반드시 JSON 배열(Array) 형식으로 출력하세요.
        총 {len(df_records)}명의 데이터가 있습니다. 반드시 {len(df_records)}개의 JSON 객체를 순서대로 배열에 담아 반환하세요.
        마크다운이나 다른 설명은 일절 적지 말고 오직 JSON 배열만 출력하세요.
        
        [학생 상담 기록 목록]
        {records_text}

        [출력 JSON 양식]
        [
          {{
            "summary": "(긴 상담 내용을 1~2문장으로 핵심만 명확하게 요약)",
            "domain": "(학업/교우관계/심리정서/진로/가정/학교생활 중 1개)",
            "emotion": "(예: 불안, 무기력 등 핵심 감정 1~2개)",
            "cause": "(이 문제가 발생한 근본적 원인을 1문장으로 추정)",
            "professional_insight": "(발달 심리학, 상담 이론 등 전문적인 관점에서의 심층 분석 1~2문장)",
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
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            parsed = json.loads(raw_text)
            while len(parsed) < len(df_records):
                parsed.append({
                    "summary": "누락", "domain": "분석누락", "emotion": "-", 
                    "cause": "누락", "professional_insight": "누락", 
                    "goal": "-", "action": "-", "first_words": "-"
                })
            return parsed[:len(df_records)] 
        except Exception as e:
            return f"API 에러 발생: {str(e)}"

    if file:
        new_df = pd.read_csv(file)
        st.info(f"📄 총 {len(new_df)}건의 새로운 상담 데이터가 확인되었습니다.")

        if st.button("🚀 심층 분석 시작 및 DB(구글 시트)에 영구 저장하기"):
            with st.spinner("AI가 상담 내용을 요약하고 전문가 관점에서 심층 분석 중입니다..."):
                parsed_data = analyze_all_counseling(new_df)
                
                if isinstance(parsed_data, str):
                    st.error(parsed_data)
                elif not parsed_data:
                    st.error("오류가 발생했습니다.")
                else:
                    analysis_df = pd.DataFrame(parsed_data)
                    analysis_df.rename(columns={
                        "summary": "상담요약",
                        "domain": "주요영역", "emotion": "핵심감정", "cause": "심리적원인",
                        "professional_insight": "전문적분석",
                        "goal": "개입목표", "action": "교사행동지침", "first_words": "추천첫마디"
                    }, inplace=True)

                    final_df = pd.concat([new_df.reset_index(drop=True), analysis_df], axis=1)
                    final_df['상담일자'] = pd.to_datetime(final_df['상담일자']).dt.strftime('%Y-%m-%d')
                    
                    final_df = final_df.fillna("") # 빈칸 에러 방지
                    
                    # 구글 시트에 저장
                    data_to_append = final_df[DB_COLUMNS].values.tolist()
                    sheet.append_rows(data_to_append)
                    
                    st.success("✅ 분석 완료! 구글 스프레드시트에 영구적으로 저장되었습니다.")
                    st.divider()
                    
                    st.subheader("📋 방금 분석된 학생 상세 리포트")
                    for idx, row in final_df.iterrows():
                        display_student_card(row)

# ------------------------------------------
# [탭 2] 누적 데이터 조회 및 모니터링
# ------------------------------------------
with tab2:
    if db_df.empty:
        st.info("아직 누적된 상담 데이터가 없습니다. 첫 번째 탭에서 상담 기록을 분석하고 저장해 보세요!")
    else:
        st.subheader("📈 전체 누적 통계 대시보드")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📊 주요 영역별 상담 누적 건수**")
            st.bar_chart(db_df["주요영역"].value_counts())
        with col2:
            st.markdown("**💡 발견된 핵심 감정 빈도수**")
            st.dataframe(db_df["핵심감정"].value_counts().reset_index().rename(columns={"핵심감정":"키워드", "count":"빈도수"}), hide_index=True, use_container_width=True)

        st.divider()
        st.subheader("🔍 학생별 상세 상담 기록 조회")
        
        # 전체 학생 명단 추출 (중복 제거)
        student_list = ["전체 학생 요약 표로 보기"] + list(db_df["학생명"].unique())
        selected_student = st.selectbox("조회할 학생을 선택하세요:", student_list)
        
        if selected_student == "전체 학생 요약 표로 보기":
            st.markdown("전체 학생의 상담 기록이 요약 표 형태로 제공됩니다.")
            st.dataframe(db_df, use_container_width=True, hide_index=True)
        else:
            student_records = db_df[db_df["학생명"] == selected_student].sort_values(by="상담일자", ascending=False)
            st.success(f"총 {len(student_records)}건의 [{selected_student}] 학생 상담 기록이 발견되었습니다. (최근 상담순)")
            
            for idx, row in student_records.iterrows():
                display_student_card(row)
