import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Sales & Gross Profit Thermometer Dashboard",
    page_icon="🌡️",
    layout="wide"
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
        company_row = daily_df_raw.iloc[1]  # Row 2 (0-indexed as 1)
        
        # Extract sales/GP headers from row 3 (index 2)  
        header_row = daily_df_raw.iloc[2]  # Row 3 (0-indexed as 2)
        
        # Build proper column names by combining company + sales/GP
        columns = ['Day']  # First column is Day
        companies = []
        
        # Track the current company being processed
        current_company = None
        
        for i in range(1, len(company_row)):  # Start from column B (index 1)
            company = company_row.iloc[i]
            header = header_row.iloc[i]
            
            # If we find a company name, store it as current company
            if pd.notna(company) and str(company).strip():
                current_company = str(company).strip()
                if current_company not in companies:
                    companies.append(current_company)
            
            # Use the current company with the header (Sales or GP)
            if current_company and pd.notna(header):
                column_name = f"{current_company} {header}".strip()
                columns.append(column_name)
            elif current_company:
                # If no header but we have a company, assume it alternates Sales/GP
                # Check if previous column was Sales, then this should be GP
                if len(columns) > 1 and 'Sales' in columns[-1]:
                    column_name = f"{current_company} GP"
                else:
                    column_name = f"{current_company} Sales"
                columns.append(column_name)
            else:
                columns.append(f"Col_{i}")
        
        # Read the actual data starting from row 4 (index 3)
        data_df = pd.read_excel(file_path, sheet_name=0, header=None, skiprows=3)
        data_df.columns = columns[:len(data_df.columns)]  # Assign our custom column names
        
        # Read goal data from second tab
        goals_df = pd.read_excel(file_path, sheet_name=1)
        
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
        
        return df, goals_df
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

def create_thermometer(company_data, company_name, metric_type="Sales", total_days=22):
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
    bulb_radius = 0  # Approximate radius based on size=150
    tube_start_y = 24  # Top of the bulb
    tube_height = 100 - tube_start_y  # Available tube height for 100%

    # Percentages adjusted for tube position
    previous_days_percent = (previous_days_value / monthly_target) * tube_height
    yesterday_percent = (yesterday_value / monthly_target) * tube_height
    total_percent = (current_total / monthly_target) * tube_height
    expected_percent = (expected_position / monthly_target) * tube_height + tube_start_y

    fig = go.Figure()

    # Red fill (previous days) - bottom portion
    fig.add_trace(go.Bar(
        x=["Thermometer"],
        y=[previous_days_percent],
        base=[tube_start_y],
        marker=dict(color='red'),
        name='Previous Days',
        width=0.25,
    ))

    # Green fill (yesterday's sales) - top portion (larger text)
    fig.add_trace(go.Bar(
        x=["Thermometer"],
        y=[yesterday_percent],
        base=[previous_days_percent + tube_start_y],
        marker=dict(color='#28a745'),
        name="Yesterday's Sales",
        width=0.25,
    ))

    # Add arrow annotation pointing to the top of the green section (yesterday's sales)
    green_top_y = previous_days_percent + yesterday_percent + tube_start_y
    fig.add_annotation(
        x=0.35,
        y=green_top_y + 2,  # Position "YESTERDAY" label above the number
        text="YESTERDAY",
        showarrow=False,
        font=dict(size=10, color='#28a745', family="Arial Black"),
        xanchor='left',
        yanchor='bottom'
    )
    fig.add_annotation(
        x=0.25,
        y=green_top_y,
        text=f"<b>${yesterday_value:,.0f}</b>",
        showarrow=True,
        arrowhead=2,
        arrowcolor='#28a745',
        arrowwidth=2,
        ax=60,
        ay=0,
        font=dict(size=14, color='#28a745')
    )

    # Large red bulb at bottom
    fig.add_trace(go.Scatter(
        x=["Thermometer"],
        y=[bulb_center_y],
        mode='markers',
        marker=dict(
            size=100,
            color='red',
            line=dict(color='black', width=2),
            symbol='circle'
        ),
        showlegend=False
    ))

    # Add company name and total inside the bulb (larger font)
    fig.add_annotation(
        x=0,
        y=bulb_center_y,
        text=f"<br>TOTAL: <br> ${current_total:,.0f}",
        showarrow=False,
        font=dict(size=12, color='white', family="Arial Black"),
        xanchor='center',
        yanchor='middle'
    )

    # Add "X out of Y Days" text (bold)
    fig.add_annotation(
        x=0.35,
        y=bulb_center_y,
        text=f"<b>{current_day} out of<br>{total_days} Days</b>",
        showarrow=False,
        font=dict(size=14, color='black'),
        xanchor='left',
        yanchor='middle',
        align='left',
        # Plotly will render <b> as bold in annotation text
    )

    # Draw left side of tube
    fig.add_shape(
        type='line',
        x0=-0.125,
        x1=-0.125,
        y0=tube_start_y,
        y1=tube_start_y + tube_height,
        line=dict(color='black', width=1)
    )

    # Draw right side of tube
    fig.add_shape(
        type='line',
        x0=0.125,
        x1=0.125,
        y0=tube_start_y,
        y1=tube_start_y + tube_height,
        line=dict(color='black', width=1)
    )

    # Target pace line (blue horizontal line) - positioned correctly within tube
    fig.add_shape(
        type="line",
        x0=-0.15, x1=0.15,
        y0=expected_percent,
        y1=expected_percent,
        line=dict(color='#007bff', width=3)
    )

    # Recalculate total_percent to account for tube starting position
    total_percent_adjusted = total_percent + tube_start_y

    # Target pace annotation - back to original position pointing at pace line
    fig.add_annotation(
        x=-0.2,
        y=expected_percent,
        text=f"<b>100% Pace<br>{current_day} days in</b>",
        showarrow=True,
        arrowhead=2,
        arrowcolor='#007bff',
        arrowwidth=2,
        ax=-30,
        ay=0,
        font=dict(size=13, color='#007bff'),
        xanchor='right',
        yanchor='middle'
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
                line=dict(color='black', width=2)
            )
            # Label
            fig.add_annotation(
                x=0.15,
                y=tube_position,
                text=f"{pct}%",
                showarrow=False,
                font=dict(size=10, color='black'),
                xanchor='left',
                yanchor='middle'
            )


    # Layout
    # Get month name for title - removed date dependency
    month_name = 'Current Month'
    fig.update_layout(
        title=dict(
            text=f"{company_name.upper()} {metric_type.upper()}<br>Month Goal: ${monthly_target:,.0f}",
            x=0.42,
            xanchor='center',
            yanchor='top',
            font=dict(size=16, family="Arial Black", color='black')
        ),
        yaxis=dict(range=[-10, tube_start_y + tube_height + 10], showgrid=False, showticklabels=False, zeroline=False),
        xaxis=dict(showticklabels=False, range=[-0.4, 0.6]),
        height=500,
        width=300,
        margin=dict(l=60, r=80, t=80, b=60),
        showlegend=False,
        barmode='stack',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    return fig



def main():
    st.title("Sales & Gross Profit Thermometer Dashboard")
    st.markdown("---")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload your Excel file with daily data (tab 1) and goals (tab 2)", 
        type=['xlsx', 'xls']
    )
    
    if uploaded_file is not None:
        # Load data
        df, goals_df = load_data(uploaded_file)
        
        if df is not None and goals_df is not None:
            # Get unique companies
            companies = df['Company'].unique()
            
            # Sidebar for controls
            st.sidebar.header("Dashboard Controls")
            
            # Total days in month
            total_days = st.sidebar.number_input("Total Days in Month", value=31, min_value=1, max_value=31)
            
            # Display summary stats
            st.subheader(f"📊 Summary Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            total_sales = df['Sales'].sum()
            total_gross_profit = df['Gross_Profit'].sum()
            total_sales_goal = df['Sales_Goal'].sum()
            days_elapsed = len(df['Day'].unique())
            
            with col1:
                st.metric("Total Sales", f"${total_sales:,.0f}")
            with col2:
                st.metric("Total Gross Profit", f"${total_gross_profit:,.0f}")
            with col3:
                st.metric("Total Sales Goal (105%)", f"${total_sales_goal:,.0f}")
            with col4:
                st.metric("Days Elapsed", days_elapsed)
            
            st.markdown("---")
            
            # Create thermometers
            st.subheader("💰 Sales Thermometers")
            cols = st.columns(4)  # 4 thermometers per row

            for i, company in enumerate(companies):
                company_data = df[df['Company'] == company].sort_values('Day')
                
                with cols[i % 4]:
                    fig = create_thermometer(
                        company_data, 
                        company, 
                        "Sales", 
                        total_days
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Start new row every 4
                if (i + 1) % 4 == 0 and i + 1 < len(companies):
                    cols = st.columns(4)

            
            st.markdown("---")
            st.subheader("📈 Gross Profit Thermometers")
            cols = st.columns(4)  # 4 thermometers per row

            for i, company in enumerate(companies):
                company_data = df[df['Company'] == company].sort_values('Day')
                
                with cols[i % 4]:
                    fig = create_thermometer(
                        company_data, 
                        company, 
                        "Gross Profit", 
                        total_days
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Start new row every 4
                if (i + 1) % 4 == 0 and i + 1 < len(companies):
                    cols = st.columns(4)

        else:
            st.error("Failed to load data. Please check your Excel file format.")
    
    else:
        st.info("👆 Please upload your Excel file to get started!")

if __name__ == "__main__":
    main()
