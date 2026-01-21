import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Data Calculation Engine", page_icon="🧮", layout="wide")

# Initialize session state
if 'template_defined' not in st.session_state:
    st.session_state.template_defined = False

if 'template_columns' not in st.session_state:
    st.session_state.template_columns = ['Display Name', 'Data Type', 'Value']

if 'data_store' not in st.session_state:
    st.session_state.data_store = {
        'business': pd.DataFrame(columns=st.session_state.template_columns),
        'financial': pd.DataFrame(columns=st.session_state.template_columns),
        'cost': pd.DataFrame(columns=st.session_state.template_columns),
        'other': pd.DataFrame(columns=st.session_state.template_columns)
    }

if 'formula' not in st.session_state:
    st.session_state.formula = ""

if 'calculation_result' not in st.session_state:
    st.session_state.calculation_result = None

# Title
st.title("🧮 Data Calculation Engine")
st.markdown("**Centralized data management with powerful calculation tools**")
st.divider()

# Template Definition Section
if not st.session_state.template_defined:
    st.header("📝 Step 1: Define Your Data Template")
    st.markdown("**Before adding data, let's define what columns your Excel file and manual entries will have.**")
    
    col_temp1, col_temp2 = st.columns([2, 1])
    
    with col_temp1:
        st.info("💡 **Default columns:** Display Name, Data Type, Value. You can add more columns using the '+' button below.")
        
        # Initialize editing columns in session state
        if 'editing_columns' not in st.session_state:
            st.session_state.editing_columns = ['Display Name', 'Data Type', 'Value']
        
        st.subheader("Column Configuration")
        st.markdown("### Current Columns:")
        
        # Create a container for the columns
        columns_container = st.container()
        
        # Display current columns with delete buttons
        cols_to_remove = []
        
        with columns_container:
            for i, col_name in enumerate(st.session_state.editing_columns):
                col_col1, col_col2 = st.columns([5, 1])
                with col_col1:
                    new_name = st.text_input(
                        f"Column {i+1}",
                        value=col_name,
                        key=f"edit_col_{i}",
                        placeholder=f"Column {i+1}"
                    )
                    if new_name != col_name:
                        st.session_state.editing_columns[i] = new_name
                
                with col_col2:
                    # Only allow delete if we have more than 3 columns (keep minimum)
                    if len(st.session_state.editing_columns) > 3:
                        if st.button("🗑️", key=f"del_col_{i}", help="Delete this column"):
                            cols_to_remove.append(i)
        
        # Remove columns marked for deletion
        for idx in sorted(cols_to_remove, reverse=True):
            if idx < len(st.session_state.editing_columns):
                st.session_state.editing_columns.pop(idx)
            st.rerun()
        
        # Add new column section
        st.markdown("---")
        st.markdown("### Add New Column")
        
        # Use a form for adding columns to reset the input
        with st.form(key="add_column_form", clear_on_submit=True):
            col_add1, col_add2 = st.columns([3, 1])
            with col_add1:
                new_col_name = st.text_input("New Column Name", placeholder="e.g., Unit, Description, Category", key="new_col_input")
            with col_add2:
                submit_new_col = st.form_submit_button("➕ Add Column", use_container_width=True)
            
            if submit_new_col:
                if new_col_name and new_col_name.strip():
                    if new_col_name not in st.session_state.editing_columns:
                        st.session_state.editing_columns.append(new_col_name.strip())
                        st.rerun()
                    else:
                        st.warning("Column name already exists!")
                else:
                    st.warning("Please enter a column name")
        
        st.markdown("---")
        st.markdown("**Note:** The first column will be used as 'Display Name' for formulas, and the last column will be used as 'Value' for calculations.")
        
        # Confirm template button
        if st.button("✅ Confirm Template", type="primary", use_container_width=True, key="confirm_template_btn"):
            # Validate columns
            if len(st.session_state.editing_columns) < 2:
                st.error("⚠️ At least 2 columns are required!")
            elif len(st.session_state.editing_columns) != len(set(st.session_state.editing_columns)):
                st.error("⚠️ Column names must be unique!")
            else:
                st.session_state.template_columns = st.session_state.editing_columns.copy()
                st.session_state.template_defined = True
                
                # Reinitialize data store with new columns
                st.session_state.data_store = {
                    'business': pd.DataFrame(columns=st.session_state.template_columns),
                    'financial': pd.DataFrame(columns=st.session_state.template_columns),
                    'cost': pd.DataFrame(columns=st.session_state.template_columns),
                    'other': pd.DataFrame(columns=st.session_state.template_columns)
                }
                
                st.success("✅ Template defined successfully! You can now add data.")
                st.rerun()
    
    with col_temp2:
        st.subheader("📋 Template Preview")
        preview_df = pd.DataFrame(columns=st.session_state.editing_columns)
        st.dataframe(preview_df, use_container_width=True)
        
        st.markdown("**Example Row:**")
        example_data = {}
        for i, col in enumerate(st.session_state.editing_columns):
            if i == 0:  # First column
                example_data[col] = "Revenue"
            elif i == 1:  # Second column (usually Data Type)
                example_data[col] = "number"
            elif i == len(st.session_state.editing_columns) - 1:  # Last column
                example_data[col] = 1000.50
            else:
                example_data[col] = "Sample"
        
        example_df = pd.DataFrame([example_data])
        st.dataframe(example_df, use_container_width=True, hide_index=True)
    
    st.stop()  # Stop here until template is defined

# Display current template info
st.success(f"📋 **Current Template:** {' | '.join(st.session_state.template_columns)}")
if st.button("🔄 Change Template"):
    st.session_state.template_defined = False
    st.session_state.editing_columns = st.session_state.template_columns.copy()
    st.rerun()
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
        f"Upload data (Excel columns: {' | '.join(st.session_state.template_columns)})",
        type=['xlsx', 'xls'],
        key=f"uploader_{category}"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            if len(df.columns) == len(st.session_state.template_columns):
                df.columns = st.session_state.template_columns
                df = df.dropna(subset=[st.session_state.template_columns[0]])  # Drop rows where first column is empty
                st.session_state.data_store[category] = pd.concat(
                    [st.session_state.data_store[category], df], 
                    ignore_index=True
                )
                st.success(f"✅ Uploaded {len(df)} rows to {category.capitalize()} Data")
            else:
                st.error(f"⚠️ Excel must have {len(st.session_state.template_columns)} columns: {', '.join(st.session_state.template_columns)}")
        except Exception as e:
            st.error(f"⚠️ Error reading file: {str(e)}")
    
    st.divider()
    st.subheader("Manual Entry")
    
    with st.form(key="manual_entry_form"):
        # Create input fields dynamically based on template
        entry_data = {}
        
        for idx, col_name in enumerate(st.session_state.template_columns):
            if idx == 0:  # First column (Display Name)
                entry_data[col_name] = st.text_input(col_name, placeholder=f"e.g., Revenue")
            elif "type" in col_name.lower():  # Data type column
                entry_data[col_name] = st.selectbox(col_name, ["number", "text", "percentage", "currency"])
            elif idx == len(st.session_state.template_columns) - 1:  # Last column (Value)
                # Check if previous column indicates text type
                is_text = False
                for prev_col in entry_data.values():
                    if prev_col == "text":
                        is_text = True
                        break
                
                if is_text:
                    entry_data[col_name] = st.text_input(col_name, placeholder="Enter text value")
                else:
                    entry_data[col_name] = st.number_input(col_name, value=0.0, format="%.2f")
            else:  # Other columns
                entry_data[col_name] = st.text_input(col_name, placeholder=f"Enter {col_name}")
        
        submit_button = st.form_submit_button("➕ Add Entry")
        
        if submit_button:
            # Check if first column (display name) is filled
            if entry_data[st.session_state.template_columns[0]]:
                new_row = pd.DataFrame([entry_data])
                st.session_state.data_store[category] = pd.concat(
                    [st.session_state.data_store[category], new_row],
                    ignore_index=True
                )
                st.success(f"✅ Added '{entry_data[st.session_state.template_columns[0]]}' to {category.capitalize()} Data")
                st.rerun()
            else:
                st.error(f"⚠️ Please fill in at least the '{st.session_state.template_columns[0]}' field")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📋 Data Store - All Categories")
    
    # Display all data in a single view organized by category
    all_empty = all(st.session_state.data_store[cat].empty for cat in ['business', 'financial', 'cost', 'other'])
    
    if not all_empty:
        category_colors = {
            'business': '🟦',
            'financial': '🟩',
            'cost': '🟨',
            'other': '🟪'
        }
        
        for cat_key in ['business', 'financial', 'cost', 'other']:
            df = st.session_state.data_store[cat_key]
            
            if not df.empty:
                st.subheader(f"{category_colors[cat_key]} {cat_key.capitalize()} Data ({len(df)} items)")
                
                # Create a container for each category
                with st.container():
                    # Display the dataframe
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Add to formula buttons for each entry
                    display_col = st.session_state.template_columns[0]
                    cols_buttons = st.columns(min(len(df), 4))
                    for idx, (_, row) in enumerate(df.iterrows()):
                        with cols_buttons[idx % 4]:
                            if st.button(
                                f"➕ {row[display_col]}", 
                                key=f"add_formula_{cat_key}_{idx}",
                                use_container_width=True
                            ):
                                st.session_state.formula += f"{{{row[display_col]}}}"
                                st.rerun()
                    
                    # Delete functionality
                    col_del1, col_del2 = st.columns([3, 1])
                    with col_del1:
                        entry_to_delete = st.selectbox(
                            "Delete entry",
                            df[display_col].tolist(),
                            key=f"delete_{cat_key}",
                            label_visibility="collapsed"
                        )
                    with col_del2:
                        if st.button(f"🗑️ Delete", key=f"del_btn_{cat_key}"):
                            st.session_state.data_store[cat_key] = df[df[display_col] != entry_to_delete]
                            st.success(f"✅ Deleted '{entry_to_delete}'")
                            st.rerun()
                
                st.divider()
    else:
        st.info("No data yet. Add some data using the sidebar to get started!")

with col2:
    st.header("🔧 Calculation Engine")
    
    # Formula builder
    st.subheader("Build Formula")
    
    # Operations
    st.markdown("**Quick Operations:**")
    
    # First row of operations
    ops_row1 = st.columns(8)
    operations_row1 = ['+', '-', '*', '/', '%', '^', '(', ')']
    
    for idx, op in enumerate(operations_row1):
        with ops_row1[idx]:
            if st.button(op, key=f"op_{op}", use_container_width=True):
                st.session_state.formula += op
                st.rerun()
    
    # Second row of numbers
    st.markdown("**Numbers:**")
    num_cols1 = st.columns(6)
    num_cols2 = st.columns(6)
    
    numbers1 = ['7', '8', '9', '4', '5', '6']
    numbers2 = ['1', '2', '3', '0', '.', '=']
    
    for idx, num in enumerate(numbers1):
        with num_cols1[idx]:
            if st.button(num, key=f"num_{num}", use_container_width=True):
                st.session_state.formula += num
                st.rerun()
    
    for idx, num in enumerate(numbers2):
        with num_cols2[idx]:
            if num == '=':
                if st.button("Calculate", key="btn_calculate", type="primary", use_container_width=True):
                    calculate_btn = True
            else:
                if st.button(num, key=f"num_{num}", use_container_width=True):
                    st.session_state.formula += num
                    st.rerun()
    
    st.markdown("---")
    
    # Formula input area
    formula_display = st.text_area(
        "Formula Input", 
        value=st.session_state.formula, 
        height=100, 
        key="formula_input",
        placeholder="Type formula here or use buttons above. Use {VariableName} for data variables."
    )
    
    # Update formula if manually typed
    if formula_display != st.session_state.formula:
        st.session_state.formula = formula_display
        st.rerun()
    
    st.caption("💡 **Tip:** Click on any data item from the left panel to add it to your formula, then use operations above to build your calculation.")
    
    # Control buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("🧹 Clear Formula", use_container_width=True):
            st.session_state.formula = ""
            st.session_state.calculation_result = None
            st.rerun()
    
    with col_btn2:
        if st.button("⬅️ Backspace", use_container_width=True):
            st.session_state.formula = st.session_state.formula[:-1]
            st.rerun()
    
    with col_btn3:
        calculate_btn = st.button("✅ Calculate", type="primary", use_container_width=True)
    
    # Calculate result
    if calculate_btn:
        if st.session_state.formula:
            try:
                # Replace variables with values
                eval_formula = st.session_state.formula
                
                # Use first column as display name and last column as value
                display_col = st.session_state.template_columns[0]
                value_col = st.session_state.template_columns[-1]
                
                for cat_key in ['business', 'financial', 'cost', 'other']:
                    df = st.session_state.data_store[cat_key]
                    for _, row in df.iterrows():
                        var_name = f"{{{row[display_col]}}}"
                        if var_name in eval_formula:
                            try:
                                value = float(row[value_col])
                                eval_formula = eval_formula.replace(var_name, str(value))
                            except:
                                st.error(f"⚠️ Cannot use '{row[display_col]}' in calculation (not a number)")
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
            result_name = st.text_input(f"{st.session_state.template_columns[0]}", placeholder="e.g., Total Profit")
            
            # Create input fields for other columns (except the value column which is the result)
            result_data = {st.session_state.template_columns[0]: result_name}
            
            for col_name in st.session_state.template_columns[1:-1]:
                result_data[col_name] = st.text_input(col_name, value="calculated" if "type" in col_name.lower() else "")
            
            result_data[st.session_state.template_columns[-1]] = st.session_state.calculation_result
            
            save_category = st.selectbox(
                "Save to Category",
                ["business", "financial", "cost", "other"],
                format_func=lambda x: x.capitalize() + " Data"
            )
            
            if st.form_submit_button("💾 Save Result"):
                if result_name:
                    new_result = pd.DataFrame([result_data])
                    st.session_state.data_store[save_category] = pd.concat(
                        [st.session_state.data_store[save_category], new_result],
                        ignore_index=True
                    )
                    st.success(f"✅ Saved '{result_name}' to {save_category.capitalize()} Data")
                    st.session_state.calculation_result = None
                    st.rerun()
                else:
                    st.error(f"⚠️ Please provide a name for the result")

# Download section
st.divider()
st.header("📥 Download Data")

# Combine all data
all_data = []
for cat_key in ['business', 'financial', 'cost', 'other']:
    df = st.session_state.data_store[cat_key].copy()
    if not df.empty:
        df.insert(0, 'Category', cat_key.capitalize())
        all_data.append(df)

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