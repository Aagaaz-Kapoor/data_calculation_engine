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

if "saved_templates" not in st.session_state:
    st.session_state.saved_templates = {
        "Default Template": [
            {"name": "Display Name", "type": "Text"},
            {"name": "Value", "type": "Number"},
        ]
    }

if "current_template_name" not in st.session_state:
    st.session_state.current_template_name = ""

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

# Display current template name if defined
if st.session_state.template_defined and st.session_state.current_template_name:
    st.info(f"📋 Current Template: **{st.session_state.current_template_name}**")

st.divider()

# ---------------- TEMPLATE BUILDER ----------------
if not st.session_state.template_defined:
    st.header("📝 Step 1: Define Template")
    
    # Template selection section
    st.subheader("🔽 Load Existing Template")
    col_select, col_load = st.columns([3, 1])
    
    with col_select:
        selected_template = st.selectbox(
            "Choose a saved template",
            ["Create New"] + list(st.session_state.saved_templates.keys()),
            key="template_selector"
        )
    
    with col_load:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📂 Load", use_container_width=True, disabled=(selected_template == "Create New")):
            st.session_state.template_schema = st.session_state.saved_templates[selected_template].copy()
            st.success(f"Loaded template: {selected_template}")
            st.rerun()
    
    st.divider()
    
    # Template name input
    st.subheader("📋 Template Configuration")
    st.session_state.current_template_name = st.text_input(
        "Template Name",
        value=st.session_state.current_template_name,
        placeholder="Enter a name for this template (e.g., Sales Report, Financial Data)"
    )
    
    st.markdown("### Column Definitions")

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

    col_add, col_save = st.columns([1, 1])
    
    with col_add:
        if st.button("➕ Add Column", use_container_width=True):
            st.session_state.template_schema.append(
                {"name": f"Column {len(updated_schema)+1}", "type": "Text"}
            )
            st.rerun()
    
    with col_save:
        if st.button("💾 Save Template", use_container_width=True):
            if not st.session_state.current_template_name:
                st.error("Please enter a template name")
            else:
                names = [c["name"] for c in st.session_state.template_schema]
                if len(names) != len(set(names)):
                    st.error("Column names must be unique")
                else:
                    st.session_state.saved_templates[st.session_state.current_template_name] = st.session_state.template_schema.copy()
                    st.success(f"Template '{st.session_state.current_template_name}' saved successfully!")
                    st.rerun()

    st.divider()

    if st.button("✅ Confirm Template & Start", type="primary", use_container_width=True):
        names = [c["name"] for c in st.session_state.template_schema]
        if len(names) != len(set(names)):
            st.error("Column names must be unique")
        else:
            for k in st.session_state.data_store:
                st.session_state.data_store[k] = empty_df()
            st.session_state.template_defined = True
            st.success("Template confirmed! You can now start entering data.")
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

# ---------------- DATA VIEW + CLICKABLE CELLS ----------------
with left:
    st.header("📋 Data Store")
    st.markdown("**💡 Click on any cell value to add it to your formula**")
    
    for cat, df in st.session_state.data_store.items():
        if not df.empty:
            st.subheader(cat.capitalize())
            
            # Create a properly formatted table structure
            table_data = []
            table_data.append(["S-No"] + list(df.columns))  # Header row
            
            for idx, row in df.iterrows():
                table_row = [str(idx)]
                for col in df.columns:
                    table_row.append(row[col])
                table_data.append(table_row)
            
            # Custom CSS for table styling
            st.markdown("""
            <style>
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    background-color: #1e1e1e;
                }
                .data-table th {
                    background-color: #2d2d2d;
                    color: white;
                    padding: 12px;
                    text-align: center;
                    border: 1px solid #444;
                    font-weight: bold;
                }
                .data-table td {
                    padding: 10px;
                    text-align: center;
                    border: 1px solid #444;
                    color: white;
                }
                .clickable-cell {
                    background-color: #2d2d2d;
                    cursor: pointer;
                    transition: background-color 0.2s;
                }
                .clickable-cell:hover {
                    background-color: #3d3d3d;
                }
                .non-clickable-cell {
                    background-color: #252525;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Display the table with proper structure
            # Header
            header_html = "<table class='data-table'><thead><tr>"
            for col in table_data[0]:
                header_html += f"<th>{col}</th>"
            header_html += "</tr></thead><tbody>"
            st.markdown(header_html, unsafe_allow_html=True)
            
            # Rows with clickable buttons
            for row_idx in range(1, len(table_data)):
                cols = st.columns([1] + [1] * len(df.columns))
                
                # S-No column
                cols[0].markdown(f"<div style='text-align: center; padding: 10px;'><strong>{table_data[row_idx][0]}</strong></div>", unsafe_allow_html=True)
                
                # Data columns
                for col_idx in range(1, len(table_data[row_idx])):
                    cell_value = table_data[row_idx][col_idx]
                    col_name = df.columns[col_idx - 1]
                    col_type = next((c["type"] for c in schema if c["name"] == col_name), None)
                    
                    with cols[col_idx]:
                        if col_type in NUMERIC_TYPES:
                            # Clickable numeric cell as button
                            if st.button(
                                f"{cell_value}",
                                key=f"cell_{cat}_{col_name}_{row_idx}",
                                use_container_width=True,
                                help=f"Click to add {cell_value} to formula"
                            ):
                                st.session_state.formula += str(float(cell_value))
                                st.rerun()
                        else:
                            # Non-clickable cell
                            st.markdown(
                                f"<div style='text-align: center; padding: 8px; background-color: #252525; border-radius: 4px;'>{cell_value}</div>",
                                unsafe_allow_html=True
                            )
            
            st.markdown("</tbody></table>", unsafe_allow_html=True)
            st.markdown("---")
            
            # Variable buttons (using display name)
            st.markdown("**Quick Variables:**")
            cols = st.columns(min(len(df), 4))
            for i, row in df.iterrows():
                with cols[i % 4]:
                    if st.button(f"➕ {row[display_col]}", key=f"var_{cat}_{i}"):
                        st.session_state.formula += f"{{{row[display_col]}}}"
                        st.rerun()
            
            st.markdown("---")

# ---------------- FORMULA ENGINE ----------------
with right:
    st.header("🔧 Calculation Engine")

    ops = ['+', '-', '*', '/', '%', '^', '(', ')']
    op_cols = st.columns(len(ops))
    for i, op in enumerate(ops):
        with op_cols[i]:
            if st.button(op, key=f"op_{op}"):
                st.session_state.formula += op
                st.rerun()

    nums1 = ['7','8','9','4','5','6']
    nums2 = ['1','2','3','0','.']

    r1 = st.columns(6)
    r2 = st.columns(5)

    for i, n in enumerate(nums1):
        with r1[i]:
            if st.button(n, key=f"num1_{n}"):
                st.session_state.formula += n
                st.rerun()

    for i, n in enumerate(nums2):
        with r2[i]:
            if st.button(n, key=f"num2_{n}"):
                st.session_state.formula += n
                st.rerun()

    st.text_area("Formula", st.session_state.formula, height=100, key="formula_display")

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