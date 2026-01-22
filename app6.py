import streamlit as st
import pandas as pd
import io
from datetime import datetime, date
import plotly.graph_objects as go
import plotly.express as px

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

if "show_analytics" not in st.session_state:
    st.session_state.show_analytics = False

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

def infer_column_type(series):
    """Infer the data type of a pandas series"""
    # Try to convert to numeric
    try:
        pd.to_numeric(series.dropna())
        # Check if values are percentages
        if series.dropna().astype(str).str.contains('%').any():
            return "Percentage"
        # Check if values look like currency
        elif series.dropna().astype(str).str.contains('₹|$|€|£').any():
            return "Currency"
        else:
            return "Number"
    except:
        pass
    
    # Try to convert to datetime
    try:
        pd.to_datetime(series.dropna())
        return "Date"
    except:
        pass
    
    return "Text"

def clean_column_value(value, col_type):
    """Clean and convert column values based on type"""
    if pd.isna(value):
        if col_type in NUMERIC_TYPES:
            return 0.0
        elif col_type == "Date":
            return date.today()
        else:
            return ""
    
    if col_type == "Number":
        try:
            return float(str(value).replace(',', '').replace('₹', '').replace('$', '').replace('%', ''))
        except:
            return 0.0
    elif col_type == "Percentage":
        try:
            val = str(value).replace('%', '').replace(',', '')
            return float(val)
        except:
            return 0.0
    elif col_type == "Currency":
        try:
            return float(str(value).replace(',', '').replace('₹', '').replace('$', '').replace('€', '').replace('£', ''))
        except:
            return 0.0
    elif col_type == "Date":
        try:
            return pd.to_datetime(value).date()
        except:
            return date.today()
    else:
        return str(value)

def create_trend_graph(df, value_column, display_column, category_name):
    """Create a trend line graph for the data"""
    if df.empty:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(range(len(df))),
        y=df[value_column],
        mode='lines+markers',
        name=category_name.capitalize(),
        line=dict(width=3),
        marker=dict(size=10),
        text=df[display_column],
        hovertemplate='<b>%{text}</b><br>Value: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f"{category_name.capitalize()} Data Trend",
        xaxis_title="Entry Number",
        yaxis_title=value_column,
        hovermode='closest',
        template='plotly_dark',
        height=400
    )
    
    return fig

def create_rent_growth_graph(initial_rent, growth_rate, interval_months, total_periods):
    """Create a rent growth projection graph"""
    periods = list(range(total_periods + 1))
    rent_values = [initial_rent * ((1 + growth_rate/100) ** i) for i in periods]
    time_labels = [f"{i * interval_months} months" for i in periods]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=periods,
        y=rent_values,
        mode='lines+markers',
        name='Rent Amount',
        line=dict(width=3, color='#FF6B6B'),
        marker=dict(size=10),
        text=[f"₹{val:,.2f}" for val in rent_values],
        hovertemplate='<b>Period %{x}</b><br>Time: %{customdata}<br>Rent: %{text}<extra></extra>',
        customdata=time_labels
    ))
    
    fig.update_layout(
        title="Rent Growth Projection Over Time",
        xaxis_title="Growth Period",
        yaxis_title="Rent Amount (₹)",
        hovermode='closest',
        template='plotly_dark',
        height=500,
        showlegend=True
    )
    
    return fig, rent_values, time_labels

# ---------------- TITLE ----------------
st.title("🧮 Data Calculation Engine")
st.markdown("**Typed templates + button-based formula engine + exportable outputs + trend analytics**")

# Display current template name if defined
if st.session_state.template_defined and st.session_state.current_template_name:
    st.info(f"📋 Current Template: **{st.session_state.current_template_name}**")

st.divider()

# ---------------- TEMPLATE BUILDER ----------------
if not st.session_state.template_defined:
    st.header("📝 Step 1: Define Template")
    
    # Template selection section
    st.subheader("📂 Load Existing Template")
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
    
    # Excel Upload Section
    st.subheader("📤 Upload Excel File to Create Template")
    st.markdown("Upload an Excel file to automatically create a template based on the file's columns")
    
    uploaded_file = st.file_uploader(
        "Choose an Excel file",
        type=['xlsx', 'xls'],
        help="Upload an Excel file to automatically create template from its columns"
    )
    
    if uploaded_file is not None:
        try:
            # Read the Excel file
            df_uploaded = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File uploaded successfully! Found {len(df_uploaded.columns)} columns and {len(df_uploaded)} rows.")
            
            # Display preview
            with st.expander("📊 Preview of uploaded data", expanded=True):
                st.dataframe(df_uploaded.head(10), use_container_width=True)
            
            # Auto-generate template schema with editable types
            if 'auto_schema' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
                auto_schema = []
                for col in df_uploaded.columns:
                    col_type = infer_column_type(df_uploaded[col])
                    auto_schema.append({"name": str(col), "type": col_type})
                st.session_state.auto_schema = auto_schema
                st.session_state.uploaded_file_name = uploaded_file.name
            
            st.markdown("**🔍 Detected Column Types (Editable):**")
            st.markdown("*Modify the data types if needed before applying the template*")
            
            # Create editable table for column types
            updated_auto_schema = []
            for i, col_def in enumerate(st.session_state.auto_schema):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.text_input(
                        "Column Name",
                        value=col_def["name"],
                        key=f"auto_col_name_{i}",
                        disabled=True,
                        label_visibility="collapsed"
                    )
                
                with col2:
                    selected_type = st.selectbox(
                        "Type",
                        DATA_TYPES,
                        index=DATA_TYPES.index(col_def["type"]),
                        key=f"auto_col_type_{i}",
                        label_visibility="collapsed"
                    )
                
                updated_auto_schema.append({"name": col_def["name"], "type": selected_type})
            
            # Update the auto_schema with user selections
            st.session_state.auto_schema = updated_auto_schema
            
            # Category selection for the uploaded data
            st.markdown("**📁 Select category for this data:**")
            upload_category = st.selectbox(
                "Data Category",
                ["business", "financial", "cost", "other"],
                format_func=str.capitalize,
                key="upload_category"
            )
            
            col_apply1, col_apply2 = st.columns(2)
            
            with col_apply1:
                if st.button("✅ Apply Template & Load Data", type="primary", use_container_width=True):
                    # Set the template schema from user-edited schema
                    st.session_state.template_schema = st.session_state.auto_schema.copy()
                    st.session_state.current_template_name = uploaded_file.name.replace('.xlsx', '').replace('.xls', '')
                    
                    # Initialize data store with empty dataframes
                    for k in st.session_state.data_store:
                        st.session_state.data_store[k] = empty_df()
                    
                    # Clean and load the data into the selected category
                    cleaned_data = []
                    for _, row in df_uploaded.iterrows():
                        cleaned_row = {}
                        for col_def in st.session_state.auto_schema:
                            col_name = col_def["name"]
                            col_type = col_def["type"]
                            if col_name in df_uploaded.columns:
                                cleaned_row[col_name] = clean_column_value(row[col_name], col_type)
                        cleaned_data.append(cleaned_row)
                    
                    # Convert to DataFrame and store
                    st.session_state.data_store[upload_category] = pd.DataFrame(cleaned_data)
                    
                    # Mark template as defined
                    st.session_state.template_defined = True
                    
                    # Clear the auto_schema from session state
                    if 'auto_schema' in st.session_state:
                        del st.session_state.auto_schema
                    if 'uploaded_file_name' in st.session_state:
                        del st.session_state.uploaded_file_name
                    
                    st.success(f"✅ Template created and {len(df_uploaded)} rows loaded into '{upload_category}' category!")
                    st.rerun()
            
            with col_apply2:
                if st.button("📋 Apply Template Only", use_container_width=True):
                    st.session_state.template_schema = st.session_state.auto_schema.copy()
                    st.session_state.current_template_name = uploaded_file.name.replace('.xlsx', '').replace('.xls', '')
                    
                    # Initialize data store with empty dataframes
                    for k in st.session_state.data_store:
                        st.session_state.data_store[k] = empty_df()
                    
                    # Mark template as defined
                    st.session_state.template_defined = True
                    
                    # Clear the auto_schema from session state
                    if 'auto_schema' in st.session_state:
                        del st.session_state.auto_schema
                    if 'uploaded_file_name' in st.session_state:
                        del st.session_state.uploaded_file_name
                    
                    st.success("✅ Template created! You can now add data manually.")
                    st.rerun()
            
            st.divider()
        
        except Exception as e:
            st.error(f"Error reading Excel file: {str(e)}")
            st.info("Please make sure the file is a valid Excel file (.xlsx or .xls)")
    
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

# Add Analytics Toggle and Export
col_toggle1, col_toggle2, col_toggle3 = st.columns(3)
with col_toggle1:
    if st.button("📊 Show Data Trends", use_container_width=True):
        st.session_state.show_analytics = True
        st.rerun()

with col_toggle2:
    if st.button("🔧 Show Calculator", use_container_width=True):
        st.session_state.show_analytics = False
        st.rerun()

with col_toggle3:
    # Check if there's any data to export
    has_data = any(not df.empty for df in st.session_state.data_store.values())
    
    if has_data:
        # Create Excel file with all categories
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            for cat, df in st.session_state.data_store.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=cat.capitalize(), index=False)
        
        st.download_button(
            "📥 Export All Data",
            buffer.getvalue(),
            file_name=f"{st.session_state.current_template_name}_data_export.xlsx" if st.session_state.current_template_name else "data_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Download all entered data as Excel file"
        )
    else:
        st.button("📥 Export All Data", disabled=True, use_container_width=True, help="No data to export")

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
    
    st.divider()
    
    # Export individual category
    st.subheader("📤 Export Category Data")
    
    current_cat_df = st.session_state.data_store[category]
    
    if not current_cat_df.empty:
        cat_buffer = io.BytesIO()
        with pd.ExcelWriter(cat_buffer, engine="xlsxwriter") as writer:
            current_cat_df.to_excel(writer, sheet_name=category.capitalize(), index=False)
        
        st.download_button(
            f"📥 Download {category.capitalize()} Data",
            cat_buffer.getvalue(),
            file_name=f"{category}_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help=f"Download {category} category data as Excel"
        )
    else:
        st.info(f"No data in {category} category to export")
    
    st.divider()
    
    # Add Excel upload for existing template
    st.subheader("📤 Upload Data to Current Template")
    data_upload_file = st.file_uploader(
        "Upload Excel to add data",
        type=['xlsx', 'xls'],
        key="data_upload",
        help="Upload data that matches the current template structure"
    )
    
    if data_upload_file is not None:
        try:
            df_data = pd.read_excel(data_upload_file)
            
            # Check if columns match
            expected_cols = [c["name"] for c in schema]
            if list(df_data.columns) == expected_cols:
                upload_cat = st.selectbox(
                    "Select category to load data into:",
                    ["business", "financial", "cost", "other"],
                    format_func=str.capitalize,
                    key="data_upload_category"
                )
                
                if st.button("✅ Load Data", key="load_data_btn"):
                    # Clean and load the data
                    cleaned_data = []
                    for _, row in df_data.iterrows():
                        cleaned_row = {}
                        for col_def in schema:
                            col_name = col_def["name"]
                            col_type = col_def["type"]
                            cleaned_row[col_name] = clean_column_value(row[col_name], col_type)
                        cleaned_data.append(cleaned_row)
                    
                    new_df = pd.DataFrame(cleaned_data)
                    existing_df = st.session_state.data_store[upload_cat]
                    
                    st.session_state.data_store[upload_cat] = (
                        new_df if existing_df.empty else pd.concat([existing_df, new_df], ignore_index=True)
                    )
                    
                    st.success(f"✅ Loaded {len(df_data)} rows into {upload_cat}!")
                    st.rerun()
            else:
                st.error("⚠️ Column mismatch!")
                st.write("**Expected columns:**", expected_cols)
                st.write("**File columns:**", list(df_data.columns))
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ---------------- CONDITIONAL DISPLAY: ANALYTICS OR CALCULATOR ----------------
if st.session_state.show_analytics:
    # ---------------- ANALYTICS VIEW ----------------
    st.header("📊 Data Trends & Analytics")
    
    # Tab for different analytics
    tab1, tab2 = st.tabs(["📈 Category Trends", "🏠 Rent Growth Calculator"])
    
    with tab1:
        st.subheader("Data Trend Analysis")
        
        # Display trend graphs for each category
        for cat, df in st.session_state.data_store.items():
            if not df.empty and st.session_state.formula_value_column in df.columns:
                st.markdown(f"### {cat.capitalize()} Category")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig = create_trend_graph(df, st.session_state.formula_value_column, display_col, cat)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Statistics:**")
                    values = df[st.session_state.formula_value_column]
                    st.metric("Total Entries", len(df))
                    st.metric("Average", f"{values.mean():.2f}")
                    st.metric("Maximum", f"{values.max():.2f}")
                    st.metric("Minimum", f"{values.min():.2f}")
                    st.metric("Total Sum", f"{values.sum():.2f}")
                
                st.divider()
        
        # Combined view
        st.subheader("📊 Combined Category Comparison")
        combined_fig = go.Figure()
        
        for cat, df in st.session_state.data_store.items():
            if not df.empty and st.session_state.formula_value_column in df.columns:
                combined_fig.add_trace(go.Scatter(
                    x=list(range(len(df))),
                    y=df[st.session_state.formula_value_column],
                    mode='lines+markers',
                    name=cat.capitalize(),
                    line=dict(width=2),
                    marker=dict(size=8)
                ))
        
        if combined_fig.data:
            combined_fig.update_layout(
                title="All Categories Comparison",
                xaxis_title="Entry Number",
                yaxis_title=st.session_state.formula_value_column,
                hovermode='closest',
                template='plotly_dark',
                height=500
            )
            st.plotly_chart(combined_fig, use_container_width=True)
        else:
            st.info("Add data to categories to see comparison trends")
    
    with tab2:
        st.subheader("🏠 Rent Growth Projection Calculator")
        st.markdown("Calculate and visualize how rent increases over time with compound growth")
        
        col1, col2 = st.columns(2)
        
        with col1:
            initial_rent = st.number_input(
                "Initial Rent Amount (₹)",
                min_value=0.0,
                value=10000.0,
                step=1000.0,
                format="%.2f"
            )
            
            growth_rate = st.number_input(
                "Growth Rate per Period (%)",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                step=0.5,
                format="%.2f"
            )
        
        with col2:
            interval_months = st.number_input(
                "Interval (months)",
                min_value=1,
                max_value=120,
                value=12,
                step=1
            )
            
            total_periods = st.number_input(
                "Number of Growth Periods",
                min_value=1,
                max_value=50,
                value=10,
                step=1
            )
        
        if st.button("📈 Generate Rent Projection", type="primary", use_container_width=True):
            fig, rent_values, time_labels = create_rent_growth_graph(
                initial_rent, growth_rate, interval_months, total_periods
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display projection table
            st.subheader("📋 Detailed Projection Table")
            
            projection_df = pd.DataFrame({
                "Period": list(range(total_periods + 1)),
                "Time Elapsed": time_labels,
                "Rent Amount (₹)": [f"₹{val:,.2f}" for val in rent_values],
                "Increase from Initial": [f"₹{val - initial_rent:,.2f}" for val in rent_values],
                "% Increase": [f"{((val/initial_rent - 1) * 100):.2f}%" for val in rent_values]
            })
            
            st.dataframe(projection_df, use_container_width=True, hide_index=True)
            
            # Export projection
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                projection_df.to_excel(writer, index=False, sheet_name="Rent Projection")
            
            st.download_button(
                "📥 Download Projection as Excel",
                buffer.getvalue(),
                file_name="rent_growth_projection.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

else:
    # ---------------- ORIGINAL CALCULATOR VIEW ----------------
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
st.caption("Data Calculation Engine | Stable & Production Safe | Enhanced with Trend Analytics & Excel Upload")