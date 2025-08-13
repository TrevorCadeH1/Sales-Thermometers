import streamlit as st
import base64
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import plotly.io as pio
import os

# Register the custom font for Plotly image exports
def register_font_for_plotly():
    """Register the wurthfont.ttf for use in Plotly image exports"""
    try:
        # Get the absolute path to the font file
        font_path = os.path.abspath("fonts/wurthfont.ttf")
        
        # Check if font file exists
        if os.path.exists(font_path):
            # Configure Plotly for better font support
            pio.kaleido.scope.default_format = "png"
            pio.kaleido.scope.default_engine = "kaleido"
            
            # Set a more compatible default template
            pio.templates.default = "plotly_white"
            
            # Try to copy font to system accessible location
            import tempfile
            import shutil
            temp_dir = tempfile.gettempdir()
            temp_font_path = os.path.join(temp_dir, "wurthfont.ttf")
            
            try:
                if not os.path.exists(temp_font_path):
                    shutil.copy2(font_path, temp_font_path)
                    print(f"Font copied to temp directory: {temp_font_path}")
            except Exception as copy_error:
                print(f"Could not copy font to temp directory: {copy_error}")
            
            return True
        else:
            print(f"Font file not found at: {font_path}")
            return False
    except Exception as e:
        print(f"Error registering font: {e}")
        return False

# Register the font
font_registered = register_font_for_plotly()

# Set page config
st.set_page_config(
    page_title="Sales & Gross Profit Thermometer Dashboard",
    page_icon="🌡️",
    layout="wide"
)

# Embed wurthfont.ttf as base64 in the CSS so it works in Streamlit
try:
    with open("fonts/wurthfont.ttf", "rb") as f:
        font_data = f.read()
    font_base64 = base64.b64encode(font_data).decode()
    
    # Also try to copy font to system temp directory for Plotly access
    import tempfile
    import shutil
    temp_font_path = os.path.join(tempfile.gettempdir(), "wurthfont.ttf")
    if not os.path.exists(temp_font_path):
        shutil.copy2("fonts/wurthfont.ttf", temp_font_path)
        
except Exception as e:
    st.error(f"Error loading font: {e}")
    font_base64 = ""

st.markdown(
    f"""
    <style>
    @font-face {{
        font-family: 'wurthfont';
        src: url(data:font/ttf;base64,{font_base64}) format('truetype');
        font-weight: normal;
        font-style: normal;
    }}
    html, body, [class^="st-"], [class*=" st-"], .stText, .stMarkdown, .stMetric, .stTitle, .stHeader, .stDataFrame, .stTable, .stSubheader, .stCaption, .stButton, .stRadio, .stSelectbox, .stSidebar, .stNumberInput, .stFileUploader, .stAlert, .stInfo, .stError, .stSuccess, .stWarning {{
        font-family: 'wurthfont';
        color: #000000 !important;
    }}
    /* Hide the sidebar tooltip */
    [data-testid="stSidebarCollapseButton"] {{
        display: none !important;
    }}
    .stSidebar [title*="keyboard_double_arrow_right"] {{
        display: none !important;
    }}
    button[title*="keyboard_double_arrow_right"] {{
        display: none !important;
    }}
    </style> 
    """,
    unsafe_allow_html=True 
)

@st.cache_data
def load_data(file_path):
    """Load and process the Excel data from two tabs"""
    try:
        # Read the Excel file with specific structure
        # Row 1: Title, Row 2: Company names, Row 3: Sales/GP headers, Row 4+: Data
        
        # Read raw data
        daily_df_raw = pd.read_excel(file_path, sheet_name=0, header=None)
        
        # Extract company names from row 2 (index 1)
        company_row = daily_df_raw.iloc[1]
        # Extract sales/GP headers from row 3 (index 2)
        header_row = daily_df_raw.iloc[2]
        # Build proper column names by combining company + sales/GP
        columns = ['Day']  # First column is Day
        companies = []
        current_company = None
        # Start from column AA (index 26)
        for i in range(26, len(company_row)):
            company = company_row.iloc[i]
            header = header_row.iloc[i]
            if pd.notna(company) and str(company).strip():
                current_company = str(company).strip()
                if current_company not in companies:
                    companies.append(current_company)
            if current_company and pd.notna(header):
                column_name = f"{current_company} {header}".strip()
                columns.append(column_name)
            elif current_company:
                if len(columns) > 1 and 'Sales' in columns[-1]:
                    column_name = f"{current_company} GP"
                else:
                    column_name = f"{current_company} Sales"
                columns.append(column_name)
            else:
                columns.append(f"Col_{i}")
        # Read the actual data starting from row 4 (index 3), and only use columns from AA onwards
        data_df = pd.read_excel(file_path, sheet_name=0, header=None, skiprows=3)
        # Only keep columns from AA onwards (index 26+)
        data_df = data_df.iloc[:, [0] + list(range(26, data_df.shape[1]))]
        data_df.columns = columns[:len(data_df.columns)]
        
        # Read goal data from second tab
        goals_df = pd.read_excel(file_path, sheet_name=1)
        # Extract month from cell F2 (row 1, col 5) of second tab
        try:
            month_cell = pd.read_excel(file_path, sheet_name=1, header=None).iloc[1, 5]
            month_name_from_excel = str(month_cell) if pd.notna(month_cell) else None
        except Exception:
            month_name_from_excel = None
        
        # Process the data into our required format
        processed_data = []
        
        for _, row in data_df.iterrows():
            # Get the day number - clean and convert to numeric
            if 'Day' in data_df.columns and pd.notna(row['Day']):
                day_value = row['Day']
                # Try to convert to integer, skip if it's text like "Total"
                try:
                    day = int(day_value) if pd.notna(day_value) else row.name + 1
                except (ValueError, TypeError):
                    # Skip rows with non-numeric day values (like "Total" row)
                    continue
            else:
                day = row.name + 1
            
            # Process each company
            for company in companies:
                sales_col = f"{company} Sales"
                gp_col = f"{company} GP"
                
                if sales_col in data_df.columns and gp_col in data_df.columns:
                    sales_value = row[sales_col] if pd.notna(row[sales_col]) else 0
                    gp_value = row[gp_col] if pd.notna(row[gp_col]) else 0
                    
                    # Only add if at least one value is non-zero
                    if sales_value != 0 or gp_value != 0:
                        processed_data.append({
                            'Day': day,
                            'Company': company,
                            'Sales': sales_value,
                            'Gross_Profit': gp_value
                        })
        
        # Convert to DataFrame
        df = pd.DataFrame(processed_data)
        
        # Ensure Day column is numeric
        if not df.empty and 'Day' in df.columns:
            df['Day'] = pd.to_numeric(df['Day'], errors='coerce')
            # Remove any rows where Day couldn't be converted to numeric
            df = df.dropna(subset=['Day'])
        
        if df.empty:
            st.error("No data found. Please check that your Excel file has the correct format.")
            return None, None
        
        # Merge with goals data
        # Always use the 105% columns for goals
        goals_dict = {}
        for _, row in goals_df.iterrows():
            company = row['Company']
            sales_goal = row.get('105% Sales', 0)
            gp_goal = row.get('105% GP', 0)
            goals_dict[company] = {
                'Sales_Goal': sales_goal,
                'GP_Goal': gp_goal
            }
        # Add goals to the main dataframe
        df['Sales_Goal'] = df['Company'].map(lambda x: goals_dict.get(x, {}).get('Sales_Goal', 0))
        df['GP_Goal'] = df['Company'].map(lambda x: goals_dict.get(x, {}).get('GP_Goal', 0))
        
        return df, goals_df, month_name_from_excel
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

def calculate_monthly_targets(monthly_goal, target_percentage=100):
    """Calculate the target based on percentage of monthly goal (now goals are already 105%)"""
    return monthly_goal * (target_percentage / 100)

def calculate_daily_target(monthly_target, total_days, current_day):
    """Calculate where company should be on current day"""
    daily_average = monthly_target / total_days
    return daily_average * current_day

def create_thermometer(company_data, company_name, metric_type="Sales", total_days=22, month_name=None):
    # Define font family with fallbacks for better compatibility
    font_family = "wurthfont, Arial Black, Arial, sans-serif"
    
    # Get the goal from the data (goals are already 105% targets)
    if metric_type == "Sales":
        monthly_target = company_data['Sales_Goal'].iloc[0] if len(company_data) > 0 else 0
        current_total = company_data['Sales'].sum()
        yesterday_value = company_data['Sales'].iloc[-1] if len(company_data) > 0 else 0
    else:  # Gross Profit
        monthly_target = company_data['GP_Goal'].iloc[0] if len(company_data) > 0 else 0
        current_total = company_data['Gross_Profit'].sum()
        yesterday_value = company_data['Gross_Profit'].iloc[-1] if len(company_data) > 0 else 0

    # Calculate values for the bars
    previous_days_value = current_total - yesterday_value
    current_day = len(company_data)
    expected_position = calculate_daily_target(monthly_target, total_days, current_day)

    # Calculate bulb position and tube start
    bulb_center_y = 10
    tube_start_y = 23.5  # Top of the bulb
    tube_height = 100 - tube_start_y  # Available tube height for 100%

    # Percentages adjusted for tube position, capped at 100%
    percent_filled = min(current_total / monthly_target, 1.0) if monthly_target > 0 else 0
    previous_days_percent = min((previous_days_value / monthly_target) * tube_height, tube_height) if monthly_target > 0 else 0
    yesterday_percent = min((yesterday_value / monthly_target) * tube_height, tube_height - previous_days_percent) if monthly_target > 0 else 0
    total_percent = percent_filled * tube_height
    expected_percent = (expected_position / monthly_target) * tube_height + tube_start_y if monthly_target > 0 else tube_start_y

    fig = go.Figure()

    # Red fill (previous days) - bottom portion
    fig.add_trace(go.Bar(
        x=["Thermometer"],
        y=[previous_days_percent],
        base=[tube_start_y],
        marker=dict(color='#CC0000'),
        name='Previous Days',
        width=0.25,
    ))

    # Green fill (yesterday's sales) - top portion (larger text)
    fig.add_trace(go.Bar(
        x=["Thermometer"],
        y=[yesterday_percent],
        base=[previous_days_percent + tube_start_y],
        marker=dict(color='#008448'),
        name="Yesterday's Sales",
        width=0.25,
    ))

    # Add arrow annotation pointing to the top of the green section (yesterday's sales)
    green_top_y = previous_days_percent + yesterday_percent + tube_start_y
    fig.add_annotation(
        x=0.35,
        y=green_top_y + 2,  # Position "YESTERDAY" label above the number
        text="<b>YESTERDAY</b>",
        showarrow=False,
        font=dict(size=12, color='#008448', family=font_family),
        xanchor='left',
        yanchor='bottom'
    )
    fig.add_annotation(
        x=0.26,
        y=green_top_y,
        text=f"<b>${yesterday_value:,.0f}</b> <br>",
        showarrow=True,
        arrowhead=2,
        arrowcolor='#008448',
        arrowwidth=2,
        ax=55,
        ay=0,
        font=dict(size=14, color='#008448', family=font_family)
    )
    # Annotation for per day needed for Goal
    per_day_needed = (monthly_target - current_total) / max(1, total_days - current_day)
    fig.add_annotation(
        x=0.25,
        y=green_top_y - 2,
        text=(
            f"<span style='color:#0093DD;'>"
            f"<b>NEEDED <br> "
            f"<span style='font-size:14px;'>${per_day_needed:,.0f} / DAY</span>"
            f"</b></span>"
        ),
        showarrow=False,
        font=dict(size=12, color='#0093DD', family=font_family),
        xanchor='left',
        yanchor='top'
    )

    # Large red bulb at bottom
    fig.add_trace(go.Scatter(
        x=["Thermometer"],
        y=[bulb_center_y],
        mode='markers',
        marker=dict(
            size=100,
            color='#CC0000',
            line=dict(color='#000000', width=2),
            symbol='circle'
        ),
        showlegend=False
    ))

    # Add current metric and total inside the bulb (red circle)
    if metric_type == 'Sales':
        bulb_label = f"Current<br><span style='font-size:16px;'>${current_total:,.0f}</span>"
    else:
        bulb_label = f"Current<br><span style='font-size:16px;'>${current_total:,.0f}</span>"
    fig.add_annotation(
        x=0,
        y=bulb_center_y,
        text=bulb_label,
        showarrow=False,
        font=dict(size=14, color='white', family=font_family),
        xanchor='center',
        yanchor='middle',
        align='center',
    )

    # Add "X out of Y Days" text (bold)
    fig.add_annotation(
        x=-0.25,
        y=bulb_center_y,
        text=f"<b>{current_day} out of<br>{total_days} Days</b>",
        showarrow=False,
        font=dict(size=16, color='#000000', family=font_family),
        xanchor='right',
        yanchor='middle',
        align='right',
    )

    # Draw left side of tube
    fig.add_shape(
        type='line',
        x0=-0.125,
        x1=-0.125,
        y0=tube_start_y,
        y1=tube_start_y + tube_height,
        line=dict(color='#000000', width=1)
    )

    # Draw right side of tube
    fig.add_shape(
        type='line',
        x0=0.125,
        x1=0.125,
        y0=tube_start_y,
        y1=tube_start_y + tube_height,
        line=dict(color='#000000', width=1)
    )

    if current_total < monthly_target:
        # Target pace line (blue horizontal line) - positioned correctly within tube
        fig.add_shape(
            type="line",
            x0=-0.15, x1=0.15,
            y0=expected_percent,
            y1=expected_percent,
            line=dict(color='#0093DD', width=3)
        )

        # Target pace annotation - bring arrow and text closer together
        fig.add_annotation(
            x=-0.15,  # Keep text to the left
            y=expected_percent,
            text=f"<b>100% Pace",
            showarrow=True,
            arrowhead=2,
            arrowcolor='#0093DD',
            arrowwidth=2,
            ax=-20,   # Less negative: shorter arrow, brings text closer
            ay=0,
            font=dict(size=12, color='#0093DD', family=font_family),
            xanchor='right',
            yanchor='middle'
        )
    else:
        # Show blue percent annotation to the left of the top of the tube
        percent = (current_total / monthly_target) * 100 if monthly_target > 0 else 0
        fig.add_annotation(
            x=-0.16,  # Shifted right from -0.22 to -0.12
            y=tube_start_y + tube_height - 4,
            text=f"<b><span style='color:#0093DD;font-size:14px'>Percent of Goal: <br></span><span style='color:#0093DD;font-size:18px'>{percent:.0f}%      </span></b>",
            showarrow=False,
            font=dict(size=22, color='#0093DD', family=font_family),
            xanchor='right',
            yanchor='middle',
            align='right',
        )

    # Percentage tick marks and labels - only within tube area
    for pct in range(10, 110, 10):  # start at 10 instead of 0
        tube_position = tube_start_y + (pct / 100.0) * tube_height
            
        if tube_position <= 100:
            # Tick line
            fig.add_shape(
                type='line',
                x0=-0.125,
                x1=0.125,
                y0=tube_position,
                y1=tube_position,
                line=dict(color='#000000', width=2)
            )
            # Label
            fig.add_annotation(
                x=0.15,
                y=tube_position,
                text=f"{pct}%",
                showarrow=False,
                font=dict(size=10, color='#000000', family=font_family),
                xanchor='left',
                yanchor='middle'
            )


    # Layout
    # Use the provided month_name if available, else fallback
    title_month = month_name if month_name else 'Current Month'
    # Determine metric label for the title
    metric_label = "Sales" if metric_type == "Sales" else "GP"
    fig.update_layout(
        title=dict(
            text=f"<b>{company_name} {title_month} {metric_label} Goal:<br> <span style='color:#0093DD;'>${monthly_target:,.0f}</span></b>",
            x=0.42,
            xanchor='center',
            yanchor='top',
            font=dict(size=20, family=font_family, color='#000000', weight="bold")
        ),
        yaxis=dict(range=[-10, tube_start_y + tube_height + 4], showgrid=False, showticklabels=False, zeroline=False),
        xaxis=dict(showticklabels=False, range=[-0.4, 0.6]),
        height=500,
        width=300,
        margin=dict(l=60, r=80, t=80, b=60),
        showlegend=False,
        barmode='stack',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    # Enable HTML in the title
    fig.update_layout(title_font_color='#000000', title_font_family=font_family)
    fig.update_layout(title={'text': fig.layout.title.text, 'font': fig.layout.title.font, 'x': fig.layout.title.x, 'xanchor': fig.layout.title.xanchor, 'yanchor': fig.layout.title.yanchor})
    fig.layout.title.text = fig.layout.title.text  # Ensures HTML is rendered

    return fig



def main():
    st.markdown(
        "<h1>Sales & Gross Profit Thermometer Dashboard</h1>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    
    # File uploader
    st.markdown(
        "<div style='font-size:16px;'>Upload your Excel file with daily data (tab 1) and goals (tab 2)</div>",
        unsafe_allow_html=True
    )
    uploaded_file = st.file_uploader(
        "", 
        type=['xlsx', 'xls']
    )
    
    if uploaded_file is not None:
        # Load data
        df, goals_df, month_name_A13 = load_data(uploaded_file)
        
        if df is not None and goals_df is not None:
            # Get unique companies
            companies = df['Company'].unique()
            # Sidebar for controls
            st.sidebar.markdown(
                "<h2>Dashboard Controls</h2>",
                unsafe_allow_html=True
            )
            
            # Total days in month for each company
            st.sidebar.markdown(
                "<div style='font-size:16px;'>Total Days in Month</div>",
                unsafe_allow_html=True
            )
            
            # Create a dictionary to store total days for each company
            company_total_days = {}
            for company in companies:
                company_total_days[company] = st.sidebar.number_input(
                    f"{company}:", 
                    value=22, 
                    min_value=1, 
                    max_value=31, 
                    key=f"total_days_input_{company}"
                )
            
            # Display summary stats
            st.markdown(
                "<h3 style='font-weight:bold;'>Summary Statistics</h3>",
                unsafe_allow_html=True
            )
            col1, col2, col3, col4 = st.columns(4)
            
            total_sales = df['Sales'].sum()
            total_gross_profit = df['Gross_Profit'].sum()
            days_elapsed = len(df['Day'].unique())
            
            with col1:
                st.markdown(
                    f"<div style='font-size:18px;'>Total Sales</div>",
                    unsafe_allow_html=True
                )
                st.metric("", f"${total_sales:,.0f}")
            with col2:
                st.markdown(
                    f"<div style='font-size:18px;'>Total Gross Profit</div>",
                    unsafe_allow_html=True
                )
                st.metric("", f"${total_gross_profit:,.0f}")
            with col3:
                st.markdown(
                    f"<div style='font-size:18px;'>Total Sales Goal (105%)</div>",
                    unsafe_allow_html=True
                )
                # Get total sales goal from cell D10 (row 9, col 3) of second tab
                try:
                    total_sales_goal_cell = pd.read_excel(uploaded_file, sheet_name=1, header=None).iloc[9, 3]
                    total_sales_goal_value = total_sales_goal_cell if pd.notna(total_sales_goal_cell) else 0
                except Exception:
                    total_sales_goal_value = 0
                st.metric("", f"${total_sales_goal_value:,.0f}")
            with col4:
                st.markdown(
                    f"<div style='font-size:18px;'>Days Elapsed</div>",
                    unsafe_allow_html=True
                )
                st.metric("", days_elapsed)
            
            st.markdown("---")
            
            # Create thermometers
            st.markdown(
                "<h4>Sales Thermometers</h4>",
                unsafe_allow_html=True
            )
            cols = st.columns(4)  # 4 thermometers per row

            for i, company in enumerate(companies):
                company_data = df[df['Company'] == company].sort_values('Day')
                
                with cols[i % 4]:
                    fig = create_thermometer(
                        company_data,
                        company,
                        "Sales",
                        company_total_days[company],
                        month_name_A13
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Start new row every 4
                if (i + 1) % 4 == 0 and i + 1 < len(companies):
                    cols = st.columns(4)

            
            st.markdown("---")
            st.markdown(
                "<h4>Gross Profit Thermometers</h4>",
                unsafe_allow_html=True
            )
            cols = st.columns(4)  # 4 thermometers per row

            for i, company in enumerate(companies):
                company_data = df[df['Company'] == company].sort_values('Day')
                
                with cols[i % 4]:
                    fig = create_thermometer(
                        company_data,
                        company,
                        "Gross Profit",
                        company_total_days[company],
                        month_name_A13
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Start new row every 4
                if (i + 1) % 4 == 0 and i + 1 < len(companies):
                    cols = st.columns(4)

        else:
            st.error("Failed to load data. Please check your Excel file format.")
    
    else:
        st.info("Please upload your Excel file to get started!")

if __name__ == "__main__":
    main()