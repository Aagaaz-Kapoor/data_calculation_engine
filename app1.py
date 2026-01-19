import streamlit as st
import pandas as pd
import io
from datetime import datetime, date

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Data Calculation Engine",
    page_icon="🧮",
    layout="wide"
)

# ---------------- SESSION STATE ----------------
if "template_defined" not in st.session_state:
    st.session_state.template_defined = False

if "template_schema" not in st.session_state:
    st.session_state.template_schema = [
        {"name": "Display Name", "type": "Text"},
        {"name": "Value", "type": "Number"},
    ]

if "data_store" not in st.session_state:
    st.session_state.data_store = {
        "business": pd.DataFrame(),
        "financial": pd.DataFrame(),
        "cost": pd.DataFrame(),
        "other": pd.DataFrame(),
    }

if "formula" not in st.session_state:
    st.session_state.formula = ""

if "calculation_result" not in st.session_state:
    st.session_state.calculation_result = None

if "formula_value_column" not in st.session_state:
    st.session_state.formula_value_column = None

# 🔧 NEW (for safe Excel export)
if "result_export_ready" not in st.session_state:
    st.session_state.result_export_ready = False

DATA_TYPES = ["Number", "Text", "Percentage", "Currency", "Date"]
NUMERIC_TYPES = {"Number", "Percentage", "Currency"}

# ---------------- HELPERS ----------------
def empty_df():
    return pd.DataFrame(columns=[c["name"] for c in st.session_state.template_schema])

def render_input(col, key):
    if col["type"] == "Number":
        return st.number_input(col["name"], key=key, value=0.0)
    if col["type"] == "Percentage":
        return st.number_input(col["name"], key=key, min_value=0.0, max_value=100.0)
    if col["type"] == "Currency":
        return st.number_input(col["name"], key=key, value=0.0, format="%.2f")
    if col["type"] == "Date":
        return st.date_input(col["name"], key=key, value=date.today())
    return st.text_input(col["name"], key=key)

# ---------------- TITLE ----------------
st.title("🧮 Data Calculation Engine")
st.markdown("**Typed templates + button-based formula engine + exportable outputs**")
st.divider()

# ---------------- TEMPLATE BUILDER ----------------
if not st.session_state.template_defined:
    st.header("📝 Step 1: Define Template")

    updated_schema = []

    for i, col in enumerate(st.session_state.template_schema):
        c1, c2, c3 = st.columns([3, 2, 1])

        with c1:
            name = st.text_input("Column Name", col["name"], key=f"name_{i}")
        with c2:
            dtype = st.selectbox(
                "Data Type",
                DATA_TYPES,
                DATA_TYPES.index(col["type"]),
                key=f"type_{i}",
            )
        with c3:
            if len(st.session_state.template_schema) > 1:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.template_schema.pop(i)
                    st.rerun()

        updated_schema.append({"name": name, "type": dtype})

    st.session_state.template_schema = updated_schema

    if st.button("➕ Add Column"):
        st.session_state.template_schema.append(
            {"name": f"Column {len(updated_schema)+1}", "type": "Text"}
        )
        st.rerun()

    if st.button("✅ Confirm Template", type="primary"):
        names = [c["name"] for c in st.session_state.template_schema]
        if len(names) != len(set(names)):
            st.error("Column names must be unique")
        else:
            for k in st.session_state.data_store:
                st.session_state.data_store[k] = empty_df()
            st.session_state.template_defined = True
            st.success("Template saved successfully")
            st.rerun()

    st.stop()

# ---------------- FORMULA COLUMN SELECTION ----------------
schema = st.session_state.template_schema
display_col = schema[0]["name"]

numeric_columns = [c["name"] for c in schema if c["type"] in NUMERIC_TYPES]

st.subheader("🧮 Formula Configuration")

st.session_state.formula_value_column = st.selectbox(
    "Select column to use for arithmetic calculations",
    numeric_columns,
)

st.caption(f"📌 Using column: **{st.session_state.formula_value_column}**")
st.divider()

# ---------------- SIDEBAR DATA ENTRY ----------------
with st.sidebar:
    st.header("📊 Data Input")

    category = st.selectbox(
        "Category",
        ["business", "financial", "cost", "other"],
        format_func=str.capitalize,
    )

    with st.form("entry_form"):
        row = {}
        for i, col in enumerate(schema):
            row[col["name"]] = render_input(col, f"{category}_{i}")

        if st.form_submit_button("➕ Add Entry"):
            df = st.session_state.data_store[category]
            new_df = pd.DataFrame([row])
            st.session_state.data_store[category] = (
                new_df if df.empty else pd.concat([df, new_df], ignore_index=True)
            )
            st.success("Entry added")
            st.rerun()

# ---------------- MAIN LAYOUT ----------------
left, right = st.columns([1, 1])

# ---------------- DATA VIEW + VARIABLES ----------------
with left:
    st.header("📋 Data Store")

    for cat, df in st.session_state.data_store.items():
        if not df.empty:
            st.subheader(cat.capitalize())
            st.dataframe(df, use_container_width=True)

            cols = st.columns(min(len(df), 4))
            for i, row in df.iterrows():
                with cols[i % 4]:
                    if st.button(f"➕ {row[display_col]}", key=f"var_{cat}_{i}"):
                        st.session_state.formula += f"{{{row[display_col]}}}"
                        st.rerun()

# ---------------- FORMULA ENGINE ----------------
with right:
    st.header("🔧 Calculation Engine")

    ops = ['+', '-', '*', '/', '%', '^', '(', ')']
    op_cols = st.columns(len(ops))
    for i, op in enumerate(ops):
        with op_cols[i]:
            if st.button(op):
                st.session_state.formula += op
                st.rerun()

    nums1 = ['7','8','9','4','5','6']
    nums2 = ['1','2','3','0','.']

    r1 = st.columns(6)
    r2 = st.columns(5)

    for i, n in enumerate(nums1):
        with r1[i]:
            if st.button(n):
                st.session_state.formula += n
                st.rerun()

    for i, n in enumerate(nums2):
        with r2[i]:
            if st.button(n):
                st.session_state.formula += n
                st.rerun()

    st.text_area("Formula", st.session_state.formula, height=100)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🧹 Clear"):
            st.session_state.formula = ""
            st.session_state.calculation_result = None
            st.rerun()
    with c2:
        if st.button("⬅️ Backspace"):
            st.session_state.formula = st.session_state.formula[:-1]
            st.rerun()
    with c3:
        calculate = st.button("✅ Calculate")

    if calculate:
        try:
            expr = st.session_state.formula
            val_col = st.session_state.formula_value_column

            for df in st.session_state.data_store.values():
                for _, r in df.iterrows():
                    var = f"{{{r[display_col]}}}"
                    if var in expr:
                        expr = expr.replace(var, str(float(r[val_col])))

            expr = expr.replace("^", "**")
            st.session_state.calculation_result = eval(expr)

        except Exception as e:
            st.error(f"Calculation error: {e}")

    # ---------------- SAVE RESULT CONFIG ----------------
    if st.session_state.calculation_result is not None:
        st.success(f"Result: {st.session_state.calculation_result}")
        st.divider()
        st.subheader("💾 Save Result as Excel")

        with st.form("save_result_form"):
            output_name = st.text_input("Output Name")
            column_name = st.text_input("Column Name")
            file_name = st.text_input("Excel File Name", value="calculation_result.xlsx")

            prepare = st.form_submit_button("Prepare Excel")

            if prepare:
                if not output_name or not column_name or not file_name:
                    st.error("All fields are required")
                else:
                    st.session_state.result_export_ready = True
                    st.session_state.result_meta = {
                        "output_name": output_name,
                        "column_name": column_name,
                        "file_name": file_name,
                    }
                    st.success("Excel ready for download below ⬇️")

# ---------------- DOWNLOAD RESULT (OUTSIDE FORM) ----------------
if st.session_state.get("result_export_ready"):
    meta = st.session_state.result_meta

    result_df = pd.DataFrame(
        {meta["column_name"]: [st.session_state.calculation_result]},
        index=[meta["output_name"]],
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        result_df.to_excel(writer)

    st.download_button(
        "📥 Download Result Excel",
        buffer.getvalue(),
        file_name=meta["file_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ---------------- FOOTER ----------------
st.divider()
st.caption("Data Calculation Engine | Stable & Production Safe")
