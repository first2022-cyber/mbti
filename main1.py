
import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import json
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
# PubChem API
# ---------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_compound(name):
    url = (
        f"{BASE_URL}/compound/name/{quote(name, safe='')}"
        "/property/MolecularFormula,MolecularWeight,"
        "IUPACName,InChIKey,ConnectivitySMILES/JSON"
    )

    response = requests.get(url, timeout=20)

    if response.status_code == 404:
        return None

    response.raise_for_status()

    properties = (
        response.json()
        .get("PropertyTable", {})
        .get("Properties", [])
    )

    return properties[0] if properties else None


@st.cache_data(ttl=3600, show_spinner=False)
def get_synonyms(cid):
    url = f"{BASE_URL}/compound/cid/{cid}/synonyms/JSON"
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        return []

    records = response.json().get(
        "InformationList", {}
    ).get("Information", [])

    return records[0].get("Synonym", []) if records else []


@st.cache_data(ttl=3600, show_spinner=False)
def get_description(cid):
    url = f"{BASE_URL}/compound/cid/{cid}/description/JSON"
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        return ""

    records = response.json().get(
        "InformationList", {}
    ).get("Information", [])

    for record in records:
        if record.get("Description"):
            return record["Description"]

    return ""


@st.cache_data(ttl=3600, show_spinner=False)
def get_3d_sdf(cid):
    """PubChem에서 3차원 좌표가 포함된 SDF를 가져온다."""
    url = f"{BASE_URL}/compound/cid/{cid}/SDF"

    response = requests.get(
        url,
        params={"record_type": "3d"},
        timeout=30
    )

    if response.status_code != 200:
        return None

    sdf = response.text.strip()

    if not sdf or "V2000" not in sdf and "V3000" not in sdf:
        return None

    return sdf


def find_cas(synonyms):
    pattern = re.compile(r"^\d{2,7}-\d{2}-\d$")
    for synonym in synonyms:
        if pattern.match(synonym):
            return synonym
    return "제공 정보 없음"


# ---------------------------------
# 3D 분자 뷰어
# ---------------------------------
def show_3d_molecule(sdf):
    # SDF 데이터를 JavaScript 문자열로 안전하게 전달
    sdf_json = json.dumps(sdf).replace("</", "<\\/")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script src="https://3dmol.org/build/3Dmol-min.js"></script>
      <style>
        body {{
          margin: 0;
          font-family: sans-serif;
          background: #ffffff;
        }}
        #viewer {{
          width: 100%;
          height: 460px;
          position: relative;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          overflow: hidden;
        }}
        .controls {{
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 10px;
        }}
        button {{
          padding: 9px 15px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          background: white;
          cursor: pointer;
          font-size: 14px;
        }}
        button:hover {{
          background: #f3f4f6;
        }}
        .hint {{
          color: #555;
          font-size: 13px;
          margin-top: 8px;
        }}
      </style>
    </head>
    <body>
      <div id="viewer"></div>

      <div class="controls">
        <button onclick="setStyle('stick')">막대 모형</button>
        <button onclick="setStyle('sphere')">공 모형</button>
        <button onclick="setStyle('ballstick')">공-막대 모형</button>
        <button onclick="resetView()">처음 화면</button>
      </div>

      <div class="hint">
        마우스로 끌기: 회전 · 휠: 확대/축소
      </div>

      <script>
        const sdfData = {sdf_json};
        const elementColors = {{
          H: 0xeeeeee,
          C: 0x555555,
          N: 0x3050f8,
          O: 0xff2020,
          F: 0x90e050,
          Cl: 0x1ff01f,
          Br: 0xa62929,
          I: 0x940094,
          S: 0xffff30,
          P: 0xff8000
        }};

        const elementRadii = {{
          H: 0.28, C: 0.38, N: 0.36, O: 0.34,
          F: 0.32, Cl: 0.38, Br: 0.42, I: 0.45,
          S: 0.40, P: 0.40
        }};

        const viewer = $3Dmol.createViewer(
          document.getElementById("viewer"),
          {{ backgroundColor: "white" }}
        );

        viewer.addModel(sdfData, "sdf");

        function setStyle(mode) {{
          viewer.setStyle({{}}, {{}});
          if (mode === "stick") {{
            viewer.setStyle({{}}, {{
              stick: {{ radius: 0.16, colorscheme: "Jmol" }}
            }});
          }} else if (mode === "sphere") {{
            viewer.setStyle({{}}, {{
              sphere: {{
                scale: 0.32,
                colorscheme: "Jmol"
              }}
            }});
          }} else {{
            viewer.setStyle({{}}, {{
              stick: {{ radius: 0.14, colorscheme: "Jmol" }},
              sphere: {{ scale: 0.25, colorscheme: "Jmol" }}
            }});
          }}
          viewer.zoomTo();
          viewer.render();
        }}

        function resetView() {{
          viewer.zoomTo();
          viewer.render();
        }}

        setStyle("ballstick");
      </script>
    </body>
    </html>
    """

    components.html(html_code, height=555, scrolling=False)


# ---------------------------------
# 화면
# ---------------------------------
st.title("🧪 PubChem 물질 탐험")
st.write(
    "물질을 검색하고 분자식, 분자량, "
    "2D 이미지와 3D 입체 구조를 탐색해 보세요."
)

st.caption(
    "데이터 출처: NIH PubChem · "
    "3D 시각화: 3Dmol.js"
)

st.divider()
st.subheader("🔎 물질 검색")

tab1, tab2 = st.tabs(["⭐ 인기 물질", "⌨️ 직접 검색"])

with tab1:
    selected = st.selectbox(
        "물질 선택",
        list(POPULAR.keys())
    )

    if st.button(
        "물질 정보 조회",
        key="popular_search",
        type="primary",
        use_container_width=True
    ):
        st.session_state["chemical_query"] = POPULAR[selected]

with tab2:
    with st.form("search_form"):
        search_name = st.text_input(
            "물질 이름 또는 화학식",
            placeholder="예: water, glucose, aspirin, NaCl"
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
# 검색 결과
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
                "물질을 찾지 못했습니다. "
                "영문 물질명으로 다시 검색해 보세요."
            )
        else:
            cid = compound["CID"]
            formula = compound.get("MolecularFormula", "정보 없음")
            weight = compound.get("MolecularWeight")
            iupac = compound.get("IUPACName", "정보 없음")
            inchikey = compound.get("InChIKey", "정보 없음")
            smiles = compound.get("ConnectivitySMILES", "정보 없음")

            c1, c2, c3 = st.columns(3)
            c1.metric("PubChem CID", str(cid))
            c2.metric("분자식", formula)
            c3.metric(
                "분자량 (g/mol)",
                f"{float(weight):,.3f}" if weight is not None else "정보 없음"
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
                    caption="PubChem 2D 구조",
                    use_container_width=True
                )

            with right:
                st.markdown(f"**검색어:** {query}")
                st.markdown(f"**IUPAC 이름:** {iupac}")
                st.markdown(f"**InChIKey:** `{inchikey}`")
                st.markdown(f"**SMILES:** `{smiles}`")

                synonyms = get_synonyms(cid)
                st.markdown(f"**CAS 등록번호:** {find_cas(synonyms)}")

                st.link_button(
                    "PubChem 공식 페이지 열기 ↗",
                    f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
                )

            # 3D 입체 구조
            st.divider()
            st.markdown("### 🧊 3D 입체 분자 구조")
            st.write(
                "마우스로 분자를 회전하고 확대·축소할 수 있습니다. "
                "버튼으로 분자 표현 방식도 바꿔 보세요."
            )

            try:
                with st.spinner("3D 구조를 불러오는 중입니다..."):
                    sdf = get_3d_sdf(cid)

                if sdf:
                    show_3d_molecule(sdf)
                else:
                    st.info(
                        "이 물질은 PubChem에서 3D 좌표를 가져오지 못했습니다. "
                        "2D 구조와 기본 정보는 위에서 확인할 수 있습니다."
                    )

            except requests.exceptions.RequestException:
                st.warning(
                    "3D 구조를 가져오지 못했습니다. "
                    "잠시 후 다시 시도해 주세요."
                )

            description = get_description(cid)
            if description:
                st.markdown("### 📖 물질 설명")
                st.write(description)

            with st.expander("🔬 추가 정보 및 동의어"):
                st.write("**PubChem CID:**", cid)
                st.write("**분자식:**", formula)
                st.write("**분자량:**", weight)
                st.write("**동의어:**")
                st.write(", ".join(synonyms[:20]) if synonyms else "정보 없음")

            st.caption(
                "3D 구조는 PubChem에서 제공하는 좌표를 표시합니다. "
                "시각화된 구조가 모든 환경에서 실제 분자의 움직임이나 "
                "안정한 형태를 그대로 나타내는 것은 아닙니다."
            )

    except requests.exceptions.Timeout:
        st.error("응답 시간이 초과되었습니다. 잠시 후 다시 시도하세요.")

    except requests.exceptions.RequestException:
        st.error(
            "PubChem에 연결하지 못했습니다. "
            "인터넷 연결이나 서버 상태를 확인하세요."
        )

    except (ValueError, KeyError, TypeError):
        st.error("데이터 처리 중 문제가 발생했습니다. 다시 검색해 주세요.")

st.divider()
st.caption(
    "교육용 화학 정보 탐색 도구 · "
    "PubChem 공개 API와 3Dmol.js를 이용합니다."
)
