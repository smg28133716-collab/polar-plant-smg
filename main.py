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

def nfc(text):
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", text))

def find_files(directory, keyword):
    return [f for f in directory.iterdir() if nfc(keyword) in nfc(f.name)]

@st.cache_data
def load_environment_data():
    env_files = find_files(DATA_DIR, "환경데이터")
    if not env_files:
        return None
    data = {}
    for f in env_files:
        school = nfc(f.name.split("_")[0])
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
        school = nfc(sheet)
        df = pd.read_excel(xlsx_files[0], sheet_name=sheet)
        df["학교"] = school
        data[school] = df
    return data

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    grow_data = load_growth_data()

if env_data is None or grow_data is None:
    st.error("❗ data 폴더에 필요한 파일이 없습니다.")
    st.stop()

school_list = sorted(env_data.keys())

st.sidebar.title("학교 선택")
school_option = nfc(st.sidebar.selectbox("학교", ["전체"] + school_list))

st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ================= TAB1 =================
with tab1:
    info_df = pd.DataFrame([
        {"학교명": k, "EC 목표": v, "개체수": len(grow_data.get(k, []))}
        for k, v in SCHOOL_EC.items()
    ])
    st.table(info_df)

    total_cnt = sum(len(v) for v in grow_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_cnt)
    c2.metric("평균 온도", f"{avg_temp:.2f}℃")
    c3.metric("평균 습도", f"{avg_hum:.2f}%")
    c4.metric("최적 EC", "2.0")

# ================= TAB2 =================
with tab2:
    avg_env = pd.concat(env_data.values()).groupby("학교").mean(numeric_only=True).reset_index()

    fig = make_subplots(rows=2, cols=2, subplot_titles=["온도", "습도", "pH", "EC"])
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["temperature"]), 1, 1)
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["humidity"]), 1, 2)
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["ph"]), 2, 1)
    fig.add_trace(go.Bar(x=avg_env["학교"], y=avg_env["ec"]), 2, 2)
    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]
        fig2 = px.line(df, x="time", y=["temperature", "humidity", "ec"])
        fig2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig2, use_container_width=True)

# ================= TAB3 =================
with tab3:
    grow_all = pd.concat(grow_data.values())
    grow_all["EC"] = grow_all["학교"].map(SCHOOL_EC)

    ec_mean = grow_all.groupby("EC")["생중량(g)"].mean().reset_index()

    fig3 = px.bar(ec_mean, x="EC", y="생중량(g)")
    fig3.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig3, use_container_width=True)
