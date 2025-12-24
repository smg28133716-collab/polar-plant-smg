import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

st.set_page_config(page_title="극지식물 최적 EC 농도 연구", layout="wide")

# ================= 한글 폰트 =================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# ================= 파일 탐색 =================
def normalize_text(t):
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", t))

def find_files(directory, keyword):
    result = []
    for f in directory.iterdir():
        if normalize_text(keyword) in normalize_text(f.name):
            result.append(f)
    return result

# ================= 데이터 로딩 =================
@st.cache_data
def load_environment_data():
    env_files = find_files(DATA_DIR, "환경데이터")
    if not env_files:
        return None
    data = {}
    for f in env_files:
        school = f.name.split("_")[0]
        df = pd.read_csv(f)
        df["time"] = pd.to_datetime(df["time"])
        df["학교"] = school
        data[school] = df
    return data

@st.cache_data
def load_growth_data():
    xlsx_files = find_files(DATA_DIR, "생육결과데이터")
    if not xlsx_files:
        return None
    xls = pd.ExcelFile(xlsx_files[0])
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xlsx_files[0], sheet_name=sheet)
        df["학교"] = sheet
        data[sheet] = df
    return data

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    grow_data = load_growth_data()

if env_data is None or grow_data is None:
    st.error("❗ data 폴더 안의 파일을 찾을 수 없습니다.")
    st.stop()

# ================= 사이드바 =================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox("학교", ["전체"] + list(SCHOOL_EC.keys()))

# ================= 타이틀 =================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ================= TAB 1 =================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("EC 농도 변화에 따른 극지식물 생육 최적 조건을 분석한다.")

    info_df = pd.DataFrame([
        {"학교명": k, "EC 목표": v, "개체수": len(grow_data.get(k, [])), "색상": ""}
        for k, v in SCHOOL_EC.items()
    ])
    st.table(info_df)

    total_cnt = sum(len(v) for v in grow_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()
    best_ec = 2.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_cnt)
    c2.metric("평균 온도", f"{avg_temp:.2f}℃")
    c3.metric("평균 습도", f"{avg_hum:.2f}%")
    c4.metric("최적 EC", best_ec)

# ================= TAB 2 =================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_env = pd.concat(env_data.values()).groupby("학교").mean(numeric_only=True).reset_index()

    fig = make_subplots(rows=2, cols=2, subplot_titles=["온도", "습도", "pH", "EC 비교"])
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["temperature"]), 1, 1)
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["humidity"]), 1, 2)
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["ph"]), 2, 1)
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["ec"]), 2, 2)
    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]
        target_ec = SCHOOL_EC[school_option]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df["time"], y=df["temperature"], name="온도"))
        fig2.add_trace(go.Scatter(x=df["time"], y=df["humidity"], name="습도"))
        fig2.add_trace(go.Scatter(x=df["time"], y=df["ec"], name="EC"))
        fig2.add_hline(y=target_ec, line_dash="dash")
        fig2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("환경 데이터 원본"):
        raw = pd.concat(env_data.values())
        st.dataframe(raw)
        buf = io.BytesIO()
        raw.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button("CSV 다운로드", buf, "환경데이터.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ================= TAB 3 =================
with tab3:
    st.subheader("EC별 생육 비교")

    grow_all = pd.concat(grow_data.values())
    grow_all["EC"] = grow_all["학교"].map(SCHOOL_EC)

    ec_mean = grow_all.groupby("EC")["생중량(g)"].mean().reset_index()
    best_val = ec_mean["생중량(g)"].max()

    c1, = st.columns(1)
    c1.metric("최대 평균 생중량", f"{best_val:.2f} g")

    fig3 = px.bar(ec_mean, x="EC", y="생중량(g)")
    fig3.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.box(grow_all, x="학교", y="생중량(g)")
    fig4.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig4, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(grow_all)
        buf = io.BytesIO()
        grow_all.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button("XLSX 다운로드", buf, "생육결과.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
