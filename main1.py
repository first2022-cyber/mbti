
import streamlit as st
import requests
import re
from urllib.parse import quote

# ---------------------------------
# 기본 설정
# ---------------------------------
st.set_page_config(
    page_title="PubChem 물질 탐험",
    page_icon="🧪",
    layout="wide"
)

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# 교육용 인기 물질
POPULAR = {
    "물 (Water)": "water",
    "산소 (Oxygen)": "oxygen",
    "이산화탄소 (Carbon dioxide)": "carbon dioxide",
    "염화나트륨 (Sodium chloride)": "sodium chloride",
    "포도당 (Glucose)": "glucose",
    "구연산 (Citric acid)": "citric acid",
    "탄산수소나트륨 (Sodium bicarbonate)": "sodium bicarbonate",
    "질소 (Nitrogen)": "nitrogen",
    "탄산칼슘 (Calcium carbonate)": "calcium carbonate",
    "셀룰로스 (Cellulose)": "cellulose",
}

# ---------------------------------
# PubChem API 함수
# ---------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_compound(name):
    """물질명으로 PubChem 기본 정보를 조회한다."""
    encoded_name = quote(name, safe="")
    url = (
        f"{BASE_URL}/compound/name/{encoded_name}"
        "/property/MolecularFormula,MolecularWeight,"
        "IUPACName,InChIKey,CanonicalSMILES/JSON"
    )

    response = requests.get(url, timeout=20)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    data = response.json()

    properties = data.get("PropertyTable", {}).get("Properties", [])

    if not properties:
        return None

    return properties[0]


@st.cache_data(ttl=3600, show_spinner=False)
def get_synonyms(cid):
    """물질의 동의어 목록에서 CAS 등록번호를 찾아본다."""
    url = f"{BASE_URL}/compound/cid/{cid}/synonyms/JSON"
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        return []

    data = response.json()
    records = data.get("InformationList", {}).get("Information", [])

    if records:
        return records[0].get("Synonym", [])

    return []


@st.cache_data(ttl=3600, show_spinner=False)
def get_description(cid):
    """PubChem 물질 설명을 가져온다."""
    url = f"{BASE_URL}/compound/cid/{cid}/description/JSON"
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        return ""

    data = response.json()
    records = data.get("InformationList", {}).get("Information", [])

    for record in records:
        if record.get("Description"):
            return record["Description"]

    return ""


def find_cas(synonyms):
    """동의어에서 CAS 번호 형식의 문자열을 찾는다."""
    pattern = re.compile(r"^\d{2,7}-\d{2}-\d$")

    for synonym in synonyms:
        if pattern.match(synonym):
            return synonym

    return "제공 정보 없음"


# ---------------------------------
# 화면 디자인
# ---------------------------------
st.title("🧪 PubChem 물질 탐험")
st.write(
    "관심 있는 물질을 선택하거나 직접 검색해 "
    "분자식과 분자량 등 화학 정보를 알아보세요."
)

st.caption(
    "데이터 출처: NIH PubChem 공개 데이터베이스 · "
    "검색 결과는 데이터베이스의 등록 정보에 따라 달라질 수 있습니다."
)

st.divider()

# 인기 물질 선택
st.subheader("🔎 물질 검색")

tab1, tab2 = st.tabs(["⭐ 인기 물질", "⌨️ 직접 검색"])

with tab1:
    selected = st.selectbox(
        "알아보고 싶은 물질을 선택하세요.",
        list(POPULAR.keys())
    )
    if st.button("물질 정보 조회", key="popular_search",
                 type="primary", use_container_width=True):
        st.session_state["chemical_query"] = POPULAR[selected]

with tab2:
    with st.form("search_form"):
        search_name = st.text_input(
            "물질 이름 또는 화학식",
            placeholder="예: water, glucose, NaCl"
        )
        submitted = st.form_submit_button(
            "🔍 검색",
            use_container_width=True
        )

    if submitted:
        if search_name.strip():
            st.session_state["chemical_query"] = search_name.strip()
        else:
            st.warning("검색할 물질 이름이나 화학식을 입력하세요.")

# ---------------------------------
# 검색 결과 표시
# ---------------------------------
if "chemical_query" in st.session_state:
    query = st.session_state["chemical_query"]

    st.divider()
    st.subheader(f"📋 검색 결과: {query}")

    try:
        with st.spinner("PubChem에서 정보를 가져오는 중입니다..."):
            compound = get_compound(query)

        if compound is None:
            st.warning(
                "해당 물질을 찾지 못했습니다. "
                "영문 물질명이나 화학식을 사용해 다시 검색해 보세요."
            )
        else:
            cid = compound.get("CID")
            formula = compound.get("MolecularFormula", "정보 없음")
            weight = compound.get("MolecularWeight")
            iupac = compound.get("IUPACName", "정보 없음")
            inchikey = compound.get("InChIKey", "정보 없음")
            smiles = compound.get("ConnectivitySMILES", "정보 없음")

            synonyms = get_synonyms(cid)
            cas = find_cas(synonyms)
            description = get_description(cid)

            # 물질 정보 카드
            st.success("물질 정보를 찾았습니다!")

            c1, c2, c3 = st.columns(3)

            c1.metric("PubChem CID", str(cid))
            c2.metric("분자식", formula)
            c3.metric(
                "분자량 (g/mol)",
                f"{float(weight):,.3f}" if weight is not None
                else "정보 없음"
            )

            st.markdown("### 🧬 물질 상세 정보")

            left, right = st.columns([1, 2])

            with left:
                image_url = (
                    f"{BASE_URL}/compound/cid/{cid}/PNG"
                    "?image_size=large"
                )
                st.image(
                    image_url,
                    caption="PubChem 분자 구조 이미지",
                    use_container_width=True
                )

            with right:
                st.markdown(f"**물질명:** {query}")
                st.markdown(f"**CAS 등록번호:** {cas}")
                st.markdown(f"**IUPAC 이름:** {iupac}")
                st.markdown(f"**InChIKey:** `{inchikey}`")
                st.markdown(f"**SMILES:** `{smiles}`")

                st.link_button(
                    "PubChem 공식 페이지 열기 ↗",
                    f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
                )

            if description:
                st.markdown("### 📖 물질 설명")
                st.write(description)

            with st.expander("🔬 추가 정보 및 동의어"):
                st.write("**PubChem CID:**", cid)
                st.write("**분자식:**", formula)
                st.write("**분자량:**", weight)
                st.write("**동의어:**")
                if synonyms:
                    st.write(", ".join(synonyms[:20]))
                else:
                    st.write("동의어 정보가 없습니다.")

            st.info(
                "참고: 분자 구조 그림이나 일부 속성은 "
                "PubChem의 응답 상태에 따라 표시되지 않을 수 있습니다. "
                "CAS 번호도 모든 물질에서 제공되는 것은 아닙니다."
            )

    except requests.exceptions.Timeout:
        st.error("PubChem 응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")

    except requests.exceptions.RequestException:
        st.error(
            "PubChem 서버에 연결하지 못했습니다. "
            "인터넷 연결이나 PubChem 서비스 상태를 확인하세요."
        )

    except (ValueError, KeyError, TypeError):
        st.error("응답 데이터를 처리하지 못했습니다. 다른 검색어를 사용해 보세요.")

st.divider()
st.caption(
    "교육용 화학 정보 탐색 도구입니다. "
    "데이터 조회 결과만으로 물질의 안전성을 판단하지 마세요."
)
