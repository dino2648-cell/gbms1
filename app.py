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

# 🌟 '기술스택', '추천진로' 컬럼 추가! (총 14개)
DB_COLUMNS = ["상담일자", "학생명", "상담내용", "상담요약", "기술스택", "추천진로", "주요영역", "핵심감정", "심리적원인", "전문적분석", "개입목표", "교사행동지침", "맞춤진로조언", "추천첫마디"]

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
st.set_page_config(page_title="SW 마이스터고 학생 심리/진로 분석", layout="wide")
st.title("💻 SW 마이스터고 학생 심리 및 진로 통합 분석 시스템")
st.markdown("예비 소프트웨어 개발자들의 멘탈 케어, 기술 스택 파악, 취업 진로 설계를 동시에 지원하는 대시보드입니다.")

# 2. 구글 시트 데이터 불러오기
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

# 🎨 [가독성+전문성 개선] 개별 학생 리포트 카드 (SW 특화)
def display_student_card(row):
    with st.container(border=True):
        st.markdown(f"### 👤 {row['학생명']} 학생 (상담일: {row['상담일자']})")
        
        # 🌟 기술 스택과 추천 진로를 뱃지 형태로 상단에 강조!
        st.markdown(f"**🛠️ 관심/보유 기술 스택:** `{row['기술스택']}` ｜ **🎯 추천 세부 직무:** `{row['추천진로']}`")
        
        st.info(f"**📝 상담 핵심 요약:** {row['상담요약']}")
        
        col_left, col_right = st.columns([1, 1])
        with col_left:
            with st.expander("🗣️ 실제 상담 내용 원본 보기 (클릭)"):
                st.write(row['상담내용'])
            st.markdown(f"**📌 주요 영역:** `{row['주요영역']}`")
            st.markdown(f"**💡 핵심 감정:** `{row['핵심감정']}`")
            st.markdown(f"**🔍 심리적 원인:** {row['심리적원인']}")
        with col_right:
            st.markdown(f"**🎯 단기 개입 목표:** {row['개입목표']}")
            st.success(f"**🧠 전문가 심층 분석 (심리/발달):** {row['전문적분석']}")
            
        # 🌟 SW 개발자 특화 조언 섹션
        st.error(f"**💻 SW 직무 맞춤 진로 조언:** {row['맞춤진로조언']}")
        st.warning(f"**🛠️ 교사 행동 지침:** {row['교사행동지침']}")
        st.markdown(f"> **💬 추천 첫 마디:** {row['추천첫마디']}")

# ==========================================
# 🗂️ 화면을 3개의 탭으로 분리
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚀 새로운 상담 분석 및 저장", "📊 누적 데이터 조회 및 모니터링", "🧭 SW 마이스터고 취업/진로 정보 가이드"])

# ------------------------------------------
# [탭 1] 새로운 상담 분석 및 저장
# ------------------------------------------
with tab1:
    st.subheader("📤 새로운 상담 기록 분석 (SW 진로/멘탈 통합 엔진)")
    
    sample_df = pd.DataFrame({
        "학생명": ["홍길동", "김유신"], 
        "상담일자": ["2024-03-04", "2024-03-05"], 
        "상담내용": [
            "게임 개발이 재미있어서 유니티와 C#을 공부하고 있습니다. 그런데 이번에 로그라이크 게임 프로젝트를 하면서 취업을 잘할 수 있을지 계속 고민이 되고 불안합니다. 부모님 기대도 좀 부담스럽고요.", 
            "친구들은 다들 React나 Spring으로 웹 프로젝트를 척척 해내는데, 저는 아직 자바 문법도 헷갈려서 자괴감이 듭니다. 개발자가 제 길이 맞는지 모르겠어요."
        ]
    })
    sample_csv = sample_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📄 엑셀(CSV) 샘플 양식 다운로드", data=sample_csv, file_name="counseling_sample.csv", mime="text/csv")

    file = st.file_uploader("작성된 상담 데이터 CSV 파일 업로드", type=["csv"])

    def analyze_all_counseling(df_records):
        records_text = ""
        for i, row in df_records.iterrows():
            records_text += f"[ID: {i}] 학생명: {row['학생명']}, 상담내용: {row['상담내용']}\n"

        # 🌟 AI 프롬프트에 '기술스택', '추천진로' 추출 명령 추가
        prompt = f"""
        당신은 15년 차 경력의 수석 학생 심리 상담사, 교육 심리학 전문가이자 'IT/소프트웨어 진로 전문 컨설턴트'입니다.
        현재 상담하는 학생들은 모두 '소프트웨어 마이스터 고등학교' 재학생으로, 졸업 후 곧바로 '소프트웨어 개발자'로 취업하는 것을 목표로 하고 있습니다.
        
        아래 [학생 상담 기록 목록]을 분석하여, 심리적 분석뿐만 아니라 학생이 언급한 '기술 스택'을 파악하고 그에 맞는 '세부 진로(직무)'를 추천해 주세요.
        반드시 JSON 배열(Array) 형식으로만 출력하세요. 마크다운이나 다른 설명은 일절 적지 마세요.
        
        [학생 상담 기록 목록]
        {records_text}

        [출력 JSON 양식]
        [
          {{
            "summary": "(상담 내용을 1~2문장으로 핵심만 명확하게 요약)",
            "tech_stack": "(상담 중 언급된 프로그래밍 언어, 툴, 프레임워크 등. 없으면 '파악불가')",
            "career_path": "(관심 기술과 성향을 고려한 구체적 직무 추천. 예: 게임 클라이언트 개발자, 프론트엔드 개발자 등)",
            "domain": "(전공학습/프로젝트갈등/진로불안/심리정서/학교생활/기타 중 1개)",
            "emotion": "(예: 가면증후군, 번아웃, 불안, 기대감 등 핵심 감정 1~2개)",
            "cause": "(문제가 발생한 근본적 원인을 1문장으로 추정)",
            "professional_insight": "(교육 심리학 관점에서의 심층 분석 1~2문장)",
            "goal": "(상담 시 달성해야 할 단기적 목표)",
            "action": "(교사가 즉시 시도해볼 수 있는 구체적인 지도 방법)",
            "tech_career_advice": "(보유 기술과 고민을 바탕으로 한 포트폴리오 방향성 및 진로 설계 조언 1~2문장)",
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
                    "summary": "누락", "tech_stack": "-", "career_path": "-", "domain": "분석누락", "emotion": "-", 
                    "cause": "누락", "professional_insight": "누락", 
                    "goal": "-", "action": "-", "tech_career_advice": "누락", "first_words": "-"
                })
            return parsed[:len(df_records)] 
        except Exception as e:
            return f"API 에러 발생: {str(e)}"

    if file:
        new_df = pd.read_csv(file)
        st.info(f"📄 총 {len(new_df)}건의 새로운 상담 데이터가 확인되었습니다.")

        if st.button("🚀 심층 분석 시작 및 DB(구글 시트)에 영구 저장하기"):
            with st.spinner("AI가 SW 마이스터고 학생의 기술 스택을 파악하고 진로/심리 분석을 진행 중입니다..."):
                parsed_data = analyze_all_counseling(new_df)
                
                if isinstance(parsed_data, str):
                    st.error(parsed_data)
                elif not parsed_data:
                    st.error("오류가 발생했습니다.")
                else:
                    analysis_df = pd.DataFrame(parsed_data)
                    analysis_df.rename(columns={
                        "summary": "상담요약",
                        "tech_stack": "기술스택",
                        "career_path": "추천진로",
                        "domain": "주요영역", "emotion": "핵심감정", "cause": "심리적원인",
                        "professional_insight": "전문적분석",
                        "goal": "개입목표", "action": "교사행동지침", 
                        "tech_career_advice": "맞춤진로조언", "first_words": "추천첫마디"
                    }, inplace=True)

                    final_df = pd.concat([new_df.reset_index(drop=True), analysis_df], axis=1)
                    final_df['상담일자'] = pd.to_datetime(final_df['상담일자']).dt.strftime('%Y-%m-%d')
                    final_df = final_df.fillna("")
                    
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
        st.info("아직 누적된 상담 데이터가 없습니다.")
    else:
        st.subheader("📈 전체 누적 통계 대시보드")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📊 영역별 상담 건수**")
            st.bar_chart(db_df["주요영역"].value_counts())
        with col2:
            st.markdown("**💡 발견된 핵심 감정**")
            st.dataframe(db_df["핵심감정"].value_counts().reset_index().rename(columns={"핵심감정":"키워드", "count":"빈도수"}), hide_index=True, use_container_width=True)
        with col3:
            st.markdown("**🎯 많이 추천된 진로(직무)**")
            st.dataframe(db_df["추천진로"].value_counts().reset_index().rename(columns={"추천진로":"직무명", "count":"학생수"}), hide_index=True, use_container_width=True)

        st.divider()
        st.subheader("🔍 학생별 상세 상담 기록 조회")
        
        student_list = ["전체 학생 요약 표로 보기"] + list(db_df["학생명"].unique())
        selected_student = st.selectbox("조회할 학생을 선택하세요:", student_list)
        
        if selected_student == "전체 학생 요약 표로 보기":
            st.dataframe(db_df, use_container_width=True, hide_index=True)
        else:
            student_records = db_df[db_df["학생명"] == selected_student].sort_values(by="상담일자", ascending=False)
            st.success(f"총 {len(student_records)}건의 [{selected_student}] 학생 상담 기록이 발견되었습니다.")
            
            for idx, row in student_records.iterrows():
                display_student_card(row)

# ------------------------------------------
# [탭 3] SW 마이스터고 취업/진로 정보 가이드
# ------------------------------------------
with tab3:
    st.header("🧭 예비 개발자를 위한 진로 및 멘탈케어 가이드")
    st.markdown("상담 중 학생들에게 보여주거나, 방향성을 제시할 때 참고할 수 있는 요약 정보입니다.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("📌 포트폴리오 및 깃허브(GitHub) 관리 조언", expanded=True):
            st.markdown("""
            * **잔디(커밋)에 집착하지 않기:** 의미 없는 1일 1커밋보다, 하나의 커밋이라도 '어떤 문제를 어떻게 해결했는지' 적는 것이 중요합니다.
            * **트러블슈팅(Troubleshooting) 기록:** 에러가 났을 때 해결한 과정을 블로그(Velog, Tistory)나 README에 남기는 학생이 면접에서 승리합니다.
            * **협업 경험 강조:** 마이스터고의 가장 큰 장점은 팀 프로젝트입니다. 갈등을 해결한 경험, 코드 리뷰 경험을 반드시 이력서에 녹여내도록 지도해 주세요.
            """)
        
        with st.expander("📌 가면 증후군(Imposter Syndrome) 극복하기"):
            st.markdown("""
            * **개발자들의 고질병:** '나 빼고 다 천재 같아'라는 생각은 구글, 네이버 개발자들도 겪는 흔한 현상임을 알려주어 안심시켜 주세요.
            * **어제의 나와 비교하기:** 동기들과 코딩 속도를 비교하지 말고, 1달 전의 내가 몰랐던 것을 지금은 할 수 있는지 점검하게 하세요.
            """)

    with col_b:
        with st.expander("📌 신입 개발자 취업 준비 로드맵", expanded=True):
            st.markdown("""
            1. **주력 언어 깊게 파기:** 이것저것 다 하는 것보다 Java(Spring) 또는 JS(React) 등 하나를 깊게 이해하는 것이 훨씬 유리합니다.
            2. **CS(컴퓨터 공학) 기초:** 고등학생이지만 네트워크, 운영체제, 자료구조 기초가 탄탄하면 기술 면접에서 엄청난 가산점을 받습니다.
            3. **코딩 테스트 준비:** 백준, 프로그래머스 등에서 꾸준히 알고리즘 문제를 풀도록 격려해 주세요. (레벨 2~3 목표)
            """)
            
        with st.expander("📌 번아웃(Burnout) 예방 및 멘탈 관리"):
            st.markdown("""
            * **컴퓨터와 떨어지는 시간 확보:** 코딩이 안 풀릴 때는 계속 모니터만 보지 말고, 산책이나 운동을 하도록 강하게 권유하세요.
            * **작은 성공 경험(Small Wins) 쌓기:** 너무 거창한 프로젝트보다, 주말 안에 끝낼 수 있는 미니 프로젝트로 성취감을 맛보게 하는 것이 좋습니다.
            """)
            
    st.divider()
    st.info("💡 **교사 팁:** 개발 직군은 기술 트렌드가 매우 빠릅니다. 학생이 특정 기술스택(React, Spring, Unity 등)에 대해 고민할 때, 기술적인 정답을 주시기보다 **'스스로 공식 문서를 읽고 해결하는 방법(학습력)'**을 칭찬하고 지지해 주시는 것이 최고의 상담입니다.")
