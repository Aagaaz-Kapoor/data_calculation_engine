import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Data Calculation Engine", page_icon="🧮", layout="wide")

# Initialize session state
if 'data_store' not in st.session_state:
    st.session_state.data_store = {
        'business': pd.DataFrame(columns=['Display Name', 'Data Type', 'Value']),
        'financial': pd.DataFrame(columns=['Display Name', 'Data Type', 'Value']),
        'cost': pd.DataFrame(columns=['Display Name', 'Data Type', 'Value']),
        'other': pd.DataFrame(columns=['Display Name', 'Data Type', 'Value'])
    }

if 'formula' not in st.session_state:
    st.session_state.formula = ""

if 'calculation_result' not in st.session_state:
    st.session_state.calculation_result = None

# Title
st.title("🧮 Data Calculation Engine")
st.markdown("**Centralized data management with powerful calculation tools**")
st.divider()

# Sidebar for data input
with st.sidebar:
    st.header("📊 Data Input")
    
    # Category selection
    category = st.selectbox(
        "Select Category",
        ["business", "financial", "cost", "other"],
        format_func=lambda x: x.capitalize() + " Data"
    )
    
    st.subheader("Upload Excel File")
    uploaded_file = st.file_uploader(
        "Upload data (Excel format: Display Name | Data Type | Value)",
        type=['xlsx', 'xls'],
        key=f"uploader_{category}"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            if len(df.columns) >= 3:
                df.columns = ['Display Name', 'Data Type', 'Value']
                df = df[['Display Name', 'Data Type', 'Value']].dropna(subset=['Display Name'])
                st.session_state.data_store[category] = pd.concat(
                    [st.session_state.data_store[category], df], 
                    ignore_index=True
                )
                st.success(f"✅ Uploaded {len(df)} rows to {category.capitalize()} Data")
            else:
                st.error("⚠️ Excel must have 3 columns: Display Name, Data Type, Value")
        except Exception as e:
            st.error(f"⚠️ Error reading file: {str(e)}")
    
    st.divider()
    st.subheader("Manual Entry")
    
    with st.form(key="manual_entry_form"):
        display_name = st.text_input("Display Name", placeholder="e.g., Revenue")
        data_type = st.selectbox("Data Type", ["number", "text", "percentage", "currency"])
        
        if data_type == "text":
            value = st.text_input("Value", placeholder="Enter text value")
        else:
            value = st.number_input("Value", value=0.0, format="%.2f")
        
        submit_button = st.form_submit_button("➕ Add Entry")
        
        if submit_button:
            if display_name and value != "":
                new_row = pd.DataFrame({
                    'Display Name': [display_name],
                    'Data Type': [data_type],
                    'Value': [value]
                })
                st.session_state.data_store[category] = pd.concat(
                    [st.session_state.data_store[category], new_row],
                    ignore_index=True
                )
                st.success(f"✅ Added '{display_name}' to {category.capitalize()} Data")
                st.rerun()
            else:
                st.error("⚠️ Please fill in all fields")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📋 Data Store")
    
    # Display data in tabs
    tabs = st.tabs(["Business", "Financial", "Cost", "Other"])
    
    for idx, (cat_key, tab) in enumerate(zip(['business', 'financial', 'cost', 'other'], tabs)):
        with tab:
            df = st.session_state.data_store[cat_key]
            
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Delete functionality
                st.subheader("Delete Entry")
                if len(df) > 0:
                    entry_to_delete = st.selectbox(
                        "Select entry to delete",
                        df['Display Name'].tolist(),
                        key=f"delete_{cat_key}"
                    )
                    if st.button(f"🗑️ Delete", key=f"del_btn_{cat_key}"):
                        st.session_state.data_store[cat_key] = df[df['Display Name'] != entry_to_delete]
                        st.success(f"✅ Deleted '{entry_to_delete}'")
                        st.rerun()
            else:
                st.info(f"No {cat_key} data yet. Add some data to get started!")

with col2:
    st.header("🔧 Calculation Engine")
    
    # Formula builder
    st.subheader("Build Formula")
    
    # Display available variables
    st.markdown("**Available Variables (click to add to formula):**")
    
    cols_vars = st.columns(4)
    for idx, (cat_key, cat_name) in enumerate(zip(['business', 'financial', 'cost', 'other'], 
                                                    ['Business', 'Financial', 'Cost', 'Other'])):
        with cols_vars[idx]:
            st.markdown(f"**{cat_name}**")
            df = st.session_state.data_store[cat_key]
            if not df.empty:
                for _, row in df.iterrows():
                    if st.button(f"{row['Display Name']}", key=f"var_{cat_key}_{row['Display Name']}"):
                        st.session_state.formula += f"{{{row['Display Name']}}}"
                        st.rerun()
            else:
                st.caption("No data")
    
    st.divider()
    
    # Operations
    st.markdown("**Operations:**")
    ops_col = st.columns(8)
    operations = ['+', '-', '*', '/', '%', '^', '(', ')']
    
    for idx, op in enumerate(operations):
        with ops_col[idx]:
            if st.button(op, key=f"op_{op}"):
                st.session_state.formula += op
                st.rerun()
    
    # Formula input
    st.text_area("Formula", value=st.session_state.formula, height=100, key="formula_display", disabled=True)
    
    # Control buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🧹 Clear Formula"):
            st.session_state.formula = ""
            st.session_state.calculation_result = None
            st.rerun()
    
    with col_btn2:
        if st.button("⬅️ Backspace"):
            st.session_state.formula = st.session_state.formula[:-1]
            st.rerun()
    
    with col_btn3:
        calculate_btn = st.button("✅ Calculate", type="primary")
    
    # Calculate result
    if calculate_btn:
        if st.session_state.formula:
            try:
                # Replace variables with values
                eval_formula = st.session_state.formula
                
                for cat_key in ['business', 'financial', 'cost', 'other']:
                    df = st.session_state.data_store[cat_key]
                    for _, row in df.iterrows():
                        var_name = f"{{{row['Display Name']}}}"
                        if var_name in eval_formula:
                            try:
                                value = float(row['Value'])
                                eval_formula = eval_formula.replace(var_name, str(value))
                            except:
                                st.error(f"⚠️ Cannot use '{row['Display Name']}' in calculation (not a number)")
                                break
                
                # Replace ^ with **
                eval_formula = eval_formula.replace('^', '**')
                
                # Evaluate
                result = eval(eval_formula)
                st.session_state.calculation_result = result
                
            except Exception as e:
                st.error(f"⚠️ Error in formula: {str(e)}")
                st.session_state.calculation_result = None
        else:
            st.warning("⚠️ Please enter a formula")
    
    # Display result
    if st.session_state.calculation_result is not None:
        st.success(f"**Result:** {st.session_state.calculation_result}")
        
        st.divider()
        st.subheader("💾 Save Result")
        
        with st.form("save_result_form"):
            result_name = st.text_input("Result Name", placeholder="e.g., Total Profit")
            save_category = st.selectbox(
                "Save to Category",
                ["business", "financial", "cost", "other"],
                format_func=lambda x: x.capitalize() + " Data"
            )
            
            if st.form_submit_button("💾 Save Result"):
                if result_name:
                    new_result = pd.DataFrame({
                        'Display Name': [result_name],
                        'Data Type': ['number'],
                        'Value': [st.session_state.calculation_result]
                    })
                    st.session_state.data_store[save_category] = pd.concat(
                        [st.session_state.data_store[save_category], new_result],
                        ignore_index=True
                    )
                    st.success(f"✅ Saved '{result_name}' to {save_category.capitalize()} Data")
                    st.session_state.calculation_result = None
                    st.rerun()
                else:
                    st.error("⚠️ Please provide a name for the result")

# Download section
st.divider()
st.header("📥 Download Data")

# Combine all data
all_data = []
for cat_key in ['business', 'financial', 'cost', 'other']:
    df = st.session_state.data_store[cat_key].copy()
    if not df.empty:
        df['Category'] = cat_key.capitalize()
        all_data.append(df[['Category', 'Display Name', 'Data Type', 'Value']])

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Create Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        combined_df.to_excel(writer, sheet_name='All Data', index=False)
        
        # Also create separate sheets for each category
        for cat_key in ['business', 'financial', 'cost', 'other']:
            df = st.session_state.data_store[cat_key]
            if not df.empty:
                df.to_excel(writer, sheet_name=cat_key.capitalize(), index=False)
    
    excel_data = output.getvalue()
    
    st.download_button(
        label="📥 Download All Data as Excel",
        data=excel_data,
        file_name=f"calculation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data available to download. Add some data first!")

# Footer
st.divider()
st.caption("Data Calculation Engine v1.0 | Built with Streamlit")