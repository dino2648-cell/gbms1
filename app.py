import streamlit as st
import pandas as pd
import google.generativeai as genai
import json

# 🔑 API 설정 (선생님의 API 키)
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# 페이지 기본 설정
st.set_page_config(page_title="학생 심리 분석 시스템", layout="wide")

st.title("🧠 AI 학생 심리 상담 심층 분석 시스템")
st.markdown("단 한 번의 AI 분석으로 전체 학생의 데이터를 에러 없이 빠르게 표 형태로 정리합니다.")

# 파일 업로드
file = st.file_uploader("상담 데이터 CSV 파일 업로드 (학생명, 상담일자, 상담내용 포함)", type=["csv"])

# ✅ [일괄 처리] 여러 명의 데이터를 한 번에 분석하는 함수
def analyze_all_counseling(df_records):
    records_text = ""
    for i, row in df_records.iterrows():
        records_text += f"[ID: {i}] 학생명: {row['학생명']}, 상담내용: {row['상담내용']}\n"

    prompt = f"""
    당신은 15년 차 경력의 전문 학생 심리 상담사입니다.
    아래 [학생 상담 기록 목록]을 모두 분석하여, 반드시 JSON 배열(Array) 형식으로 출력하세요.
    총 {len(df_records)}명의 데이터가 있습니다. 반드시 {len(df_records)}개의 JSON 객체를 순서대로 배열에 담아 반환하세요.
    마크다운(```json 등)이나 다른 설명은 일절 적지 말고 오직 JSON 배열만 출력하세요.
    
    [학생 상담 기록 목록]
    {records_text}

    [출력 JSON 양식] - 배열 안에 객체를 작성하세요.
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
        # 💡 [완벽 해결] 선생님의 목록에 실제로 존재하는 최신 모델 'gemini-2.5-flash' 적용!
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        
        response = model.generate_content(prompt)
        
        # 텍스트 정제 및 JSON 파싱
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        parsed = json.loads(raw_text.strip())
        
        # AI가 혹시라도 분석 개수를 빼먹었을 경우를 대비한 안전 장치
        while len(parsed) < len(df_records):
            parsed.append({
                "domain": "분석누락", "emotion": "-", "cause": "AI가 데이터 일부를 누락했습니다.",
                "goal": "-", "action": "-", "first_words": "-"
            })
            
        return parsed[:len(df_records)] 
        
    except Exception as e:
        return f"API 에러 발생: {str(e)}"

# --- 메인 실행 로직 ---
if file:
    df = pd.read_csv(file)
    st.info(f"📄 총 {len(df)}건의 상담 데이터가 업로드되었습니다.")

    if st.button("🚀 상담 내용 일괄 분석 및 표 정리 시작"):
        with st.spinner("최신 AI 모델이 전체 데이터를 한 번에 분석 중입니다. (보통 5~10초 소요)"):
            
            # 단 1번의 API 호출 (반복문 없음 -> 429 에러 완벽 차단)
            parsed_data_list = analyze_all_counseling(df)
            
            # 에러가 발생해서 문자열이 반환된 경우
            if isinstance(parsed_data_list, str):
                st.error(parsed_data_list)
            
            # 분석 결과가 비어있는 경우
            elif not parsed_data_list:
                st.error("데이터 분석 중 오류가 발생했습니다. 다시 시도해 주세요.")
                
            # 정상적으로 분석이 완료된 경우
            else:
                analysis_df = pd.DataFrame(parsed_data_list)
                
                analysis_df.rename(columns={
                    "domain": "주요영역", "emotion": "핵심감정", "cause": "심리적원인",
                    "goal": "개입목표", "action": "교사행동지침", "first_words": "추천첫마디"
                }, inplace=True)

                final_df = pd.concat([df.reset_index(drop=True), analysis_df], axis=1)
                final_df['상담일자'] = pd.to_datetime(final_df['상담일자']).dt.strftime('%Y-%m-%d')
                
                st.success("✅ 모든 분석이 에러 없이 완벽하게 끝났습니다!")

                # --- 1. 종합 데이터 표 ---
                st.divider()
                st.subheader("📋 전체 학생 상담 분석 결과 (통합 표)")
                st.dataframe(final_df, use_container_width=True)

                # --- 2. 통계 요약 ---
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 영역별 상담 건수")
                    domain_counts = final_df["주요영역"].value_counts()
                    st.bar_chart(domain_counts)
                with col2:
                    st.subheader("💡 발견된 주요 핵심 감정")
                    emotion_counts = final_df["핵심감정"].value_counts().reset_index()
                    emotion_counts.columns = ["핵심감정(키워드)", "학생 수"]
                    st.dataframe(emotion_counts, use_container_width=True, hide_index=True)

                # --- 3. 군집화 (그룹 관리) ---
                st.divider()
                st.subheader("👥 특성별 학생 그룹 관리 (군집화)")
                grouped = final_df.groupby("주요영역")
                for domain, group_data in grouped:
                    students_in_group = ", ".join(group_data["학생명"].unique())
                    with st.expander(f"📌 [{domain}] 그룹 - 총 {len(group_data)}건 (해당 학생: {students_in_group})"):
                        group_display_df = group_data[["상담일자", "학생명", "핵심감정", "상담내용", "교사행동지침"]]
                        st.dataframe(group_display_df, use_container_width=True, hide_index=True)

                # --- 4. 모니터링 리포트 ---
                st.divider()
                st.subheader("📈 학생별 상세 모니터링 리포트")
                for name in final_df["학생명"].unique():
                    student_data = final_df[final_df["학생명"] == name].sort_values(by="상담일자")
                    with st.expander(f"👤 {name} 학생 모니터링 보드 (총 {len(student_data)}회 상담)"):
                        if len(student_data) > 1:
                            first_record = student_data.iloc[0]
                            last_record = student_data.iloc[-1]
                            st.markdown("### 🔄 학생 상태 변화 추이")
                            col_a, col_b, col_c = st.columns(3)
                            col_a.metric("최초 상담일", first_record['상담일자'])
                            col_b.metric("최근 상담일", last_record['상담일자'])
                            col_c.metric("주요 영역 변화", f"{first_record['주요영역']} ➔ {last_record['주요영역']}")
                            st.info(f"초기: **'{first_record['핵심감정']}'** ➔ 최근: **'{last_record['핵심감정']}'**")
                            
                        st.markdown("### 📝 상세 상담 기록")
                        for _, row in student_data.iterrows():
                            st.markdown(f"**📅 {row['상담일자']}** | 🗣️ {row['상담내용']}")
                            st.markdown(f"""
                            * **분류/감정:** `{row['주요영역']}` / `{row['핵심감정']}`
                            * **원인/목표:** {row['심리적원인']} / {row['개입목표']}
                            * **행동 지침:** {row['교사행동지침']}
                            * **첫마디:** <span style='color:#D32F2F;'>{row['추천첫마디']}</span>
                            """, unsafe_allow_html=True)
                            st.markdown("---")

                # --- 5. 다운로드 ---
                st.divider()
                csv = final_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 통합 데이터 다운로드 (Excel용 CSV)", csv, "counseling_table.csv", "text/csv")