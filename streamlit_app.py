import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="FruitBlend24 Business Intelligence",
    page_icon="    ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants & Paths ---
DATA_DIR = Path(__file__).resolve().parent / "cleaned_data"
ORDERS_PATH = DATA_DIR / "orders_hourly_clean.csv"
BUDGET_PATH = DATA_DIR / "monthly_budget_clean.csv"

@st.cache_data
def load_and_validate_data():
    missing_files = [path for path in (ORDERS_PATH, BUDGET_PATH) if not path.is_file()]
    if missing_files:
        errors = [
            f"Missing required data file: {path.name}. Looked for it at: {path}"
            for path in missing_files
        ]
        return None, None, errors
    
    df_orders = pd.read_csv(ORDERS_PATH)
    df_orders['date'] = pd.to_datetime(df_orders['date'])
    
    df_budget = pd.read_csv(BUDGET_PATH)
    df_budget['month'] = pd.to_datetime(df_budget['month'])
    
    # Validation Checks
    warnings = []
    row_count = len(df_orders)
    total_units = df_orders['units_sold'].sum()
    total_rev = df_orders['gross_revenue_thb'].sum()
    unmapped_count = df_orders['sku_standard'].isna().sum()
    
    if row_count != 124025:
        warnings.append(f"Validation Warning: Expected 124,025 rows, found {row_count:,}")
    if total_units != 618883:
        warnings.append(f"Validation Warning: Expected 618,883 units sold, found {total_units:,}")
    if not np.isclose(total_rev, 31185410.57):
        warnings.append(f"Validation Warning: Expected gross revenue of 31,185,410.57 THB, found {total_rev:,.2f} THB")
    if unmapped_count != 0:
        warnings.append(f"Validation Warning: Found {unmapped_count} unmapped SKU items!")
        
    return df_orders, df_budget, warnings

# --- Load Data ---
df_orders, df_budget, validation_warnings = load_and_validate_data()

if df_orders is None:
    for error in validation_warnings:
        st.error(f"Critical Error: {error}")
    st.stop()

# --- Sidebar Navigation & Filtering ---
st.sidebar.title("   FruitBlend24 BI App")
st.sidebar.markdown("**Analytical Dashboard** (Sept 2025 - Aug 2026)")
st.sidebar.markdown("--- ")

# Warnings Display
if validation_warnings:
    with st.sidebar.expander("★ System Validation Warnings", expanded=True):
        for warn in validation_warnings:
            st.warning(warn)
else:
    st.sidebar.success("✔ Baseline Mathematical Validation Passed!")

app_mode = st.sidebar.radio("Select Section", ["Business Overview", "Sales & Demand Analysis", "Budget Performance"])

# Global Sidebar Filters
st.sidebar.markdown("--- ")
st.sidebar.subheader("Global Segment Filters")

min_date, max_date = df_orders['date'].min(), df_orders['date'].max()
selected_date_range = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

selected_kitchens = st.sidebar.multiselect("Kitchen Branches", options=sorted(df_orders['kitchen'].unique()), default=sorted(df_orders['kitchen'].unique()))
selected_platforms = st.sidebar.multiselect("Platforms", options=sorted(df_orders['platform_code'].unique()), default=sorted(df_orders['platform_code'].unique()))
selected_skus = st.sidebar.multiselect("Standardized SKUs", options=sorted(df_orders['sku_standard'].unique()), default=sorted(df_orders['sku_standard'].unique()))

# Filter dataset safely
if len(selected_date_range) == 2:
    start_date, end_date = pd.to_datetime(selected_date_range[0]), pd.to_datetime(selected_date_range[1])
else:
    start_date, end_date = pd.to_datetime(min_date), pd.to_datetime(max_date)

filtered_df = df_orders[
    (df_orders['date'] >= start_date) &
    (df_orders['date'] <= end_date) &
    (df_orders['kitchen'].isin(selected_kitchens)) &
    (df_orders['platform_code'].isin(selected_platforms)) &
    (df_orders['sku_standard'].isin(selected_skus))
]

# --- Section 1: Business Overview ---
if app_mode == "Business Overview":
    st.title("   Business Performance Overview")
    st.markdown("View overall sales, product revenue shares, and daily timelines across segmented filter selections.")
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_revenue = filtered_df['gross_revenue_thb'].sum()
    total_units_sold = filtered_df['units_sold'].sum()
    avg_price = total_revenue / total_units_sold if total_units_sold > 0 else 0.0
    total_transactions = len(filtered_df)
    
    col1.metric("Gross Revenue", f"{total_revenue:,.2f} THB")
    col2.metric("Total Units Sold", f"{total_units_sold:,} Units")
    col3.metric("Avg Unit Revenue (AUR)", f"{avg_price:,.2f} THB")
    col4.metric("Line Transaction Logs", f"{total_transactions:,} lines")
    
    # Historical timeline chart
    st.markdown("### Daily Sales Revenue Timeline")
    daily_sales = filtered_df.groupby('date').agg(
        revenue=('gross_revenue_thb', 'sum'),
        units=('units_sold', 'sum')
    ).reset_index()
    
    fig_timeline = px.line(
        daily_sales, 
        x='date', 
        y='revenue', 
        labels={'revenue': 'Gross Revenue (THB)', 'date': 'Date'},
        title="Gross Revenue Over Time (Daily Grain)",
        color_discrete_sequence=["royalblue"]
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Product breakdown matrix
    st.markdown("### Product Performance Metrics & Share")
    product_breakdown = filtered_df.groupby('sku_standard').agg(
        revenue=('gross_revenue_thb', 'sum'),
        units=('units_sold', 'sum')
    ).reset_index().sort_values(by='revenue', ascending=False)
    
    product_breakdown['rev_share_pct'] = (product_breakdown['revenue'] / total_revenue * 100) if total_revenue > 0 else 0.0
    product_breakdown['unit_share_pct'] = (product_breakdown['units'] / total_units_sold * 100) if total_units_sold > 0 else 0.0
    
    col_table, col_pie = st.columns([3, 2])
    
    with col_table:
        st.dataframe(
            product_breakdown.style.format({
                'revenue': '{:,.2f} THB',
                'units': '{:,}',
                'rev_share_pct': '{:.2f}%',
                'unit_share_pct': '{:.2f}%'
            }),
            use_container_width=True
        )
        
    with col_pie:
        fig_pie = px.pie(
            product_breakdown, 
            values='revenue', 
            names='sku_standard', 
            title="Revenue Breakdown by SKU",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# --- Section 2: Sales & Demand Analysis ---
elif app_mode == "Sales & Demand Analysis":
    st.title("   Sales & Operational Demand Patterns")
    st.markdown("Analyze hourly demand distributions, platform shares, kitchen performance, and day-of-week trends.")
    
    # Temporal Plots
    st.markdown("### Temporal Sales Distribution")
    col_hour, col_dow = st.columns(2)
    
    with col_hour:
        hourly_sales = filtered_df.groupby('hour')['gross_revenue_thb'].sum().reset_index()
        fig_hour = px.line(
            hourly_sales, 
            x='hour', 
            y='gross_revenue_thb', 
            labels={'gross_revenue_thb': 'Revenue (THB)', 'hour': 'Hour of Day (0-23)'},
            title="Hourly Peak-Load Curve",
            markers=True,
            color_discrete_sequence=["darkgreen"]
        )
        fig_hour.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
        st.plotly_chart(fig_hour, use_container_width=True)
        
    with col_dow:
        dow_mapping = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
        dow_sales = filtered_df.groupby('day_of_week')['gross_revenue_thb'].sum().reset_index()
        dow_sales['day_name'] = dow_sales['day_of_week'].map(dow_mapping)
        
        fig_dow = px.bar(
            dow_sales, 
            x='day_name', 
            y='gross_revenue_thb', 
            labels={'gross_revenue_thb': 'Revenue (THB)', 'day_name': 'Day of Week'},
            title="Sales Distribution by Day of Week",
            category_orders={'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']},
            color_discrete_sequence=["teal"]
        )
        st.plotly_chart(fig_dow, use_container_width=True)
        
    # Platform & Kitchen Splits
    st.markdown("### Channels and Branches")
    col_plat, col_kit = st.columns(2)
    
    with col_plat:
        plat_sales = filtered_df.groupby('platform_code').agg(
            revenue=('gross_revenue_thb', 'sum'),
            units=('units_sold', 'sum')
        ).reset_index()
        fig_plat = px.bar(
            plat_sales, 
            x='platform_code', 
            y='revenue', 
            text='revenue', 
            labels={'revenue': 'Revenue (THB)', 'platform_code': 'Platform'},
            title="Platform Sales Split",
            color_discrete_sequence=["coral"]
        )
        fig_plat.update_traces(texttemplate='%{text:,.2f} THB', textposition='outside')
        st.plotly_chart(fig_plat, use_container_width=True)
        
    with col_kit:
        kit_sales = filtered_df.groupby('kitchen').agg(
            revenue=('gross_revenue_thb', 'sum'),
            units=('units_sold', 'sum')
        ).reset_index().sort_values(by='revenue', ascending=False)
        fig_kit = px.bar(
            kit_sales, 
            y='kitchen', 
            x='revenue', 
            orientation='h', 
            labels={'revenue': 'Revenue (THB)', 'kitchen': 'Kitchen Branch'},
            title="Kitchen Revenue Leaderboard",
            color_discrete_sequence=["royalblue"]
        )
        st.plotly_chart(fig_kit, use_container_width=True)

# --- Section 3: Budget Performance ---
elif app_mode == "Budget Performance":
    st.title("   Monthly Target & Budget Variance")
    st.markdown("Compare actual operating revenues against monthly budget targets specified by corporate finance.")
    
    # Calculate Monthly actual performance
    df_orders['month_start'] = df_orders['date'].dt.to_period('M').dt.to_timestamp()
    monthly_actuals = df_orders.groupby('month_start')['gross_revenue_thb'].sum().reset_index()
    
    # Align budget and actuals
    budget_df = pd.merge(df_budget, monthly_actuals, left_on='month', right_on='month_start', how='inner')
    budget_df['variance_thb'] = budget_df['gross_revenue_thb'] - budget_df['budget_revenue_thb']
    budget_df['variance_pct'] = (budget_df['variance_thb'] / budget_df['budget_revenue_thb']) * 100
    
    # Visualising Actuals vs Budget Targets
    st.markdown("### Monthly Budget Target Comparison")
    
    fig_budget = go.Figure()
    fig_budget.add_trace(go.Bar(
        x=budget_df['month'].dt.strftime('%b %Y'),
        y=budget_df['budget_revenue_thb'],
        name='Budget Target',
        marker_color='silver'
    ))
    fig_budget.add_trace(go.Bar(
        x=budget_df['month'].dt.strftime('%b %Y'),
        y=budget_df['gross_revenue_thb'],
        name='Actual Revenue',
        marker_color='royalblue'
    ))
    fig_budget.update_layout(
        bmode='group',
        title="Monthly Actual Revenue vs Budget Targets",
        xaxis_title="Month",
        yaxis_title="Gross Revenue (THB)",
        legend_title="Legend",
        hovermode="x"
    )
    st.plotly_chart(fig_budget, use_container_width=True)
    
    # Table of Variances
    st.markdown("### Monthly Variance Ledger")
    
    display_budget = budget_df[[
        'month', 'budget_revenue_thb', 'gross_revenue_thb', 'variance_thb', 'variance_pct'
    ]].rename(columns={
        'month': 'Month',
        'budget_revenue_thb': 'Budget (THB)',
        'gross_revenue_thb': 'Actual Gross (THB)',
        'variance_thb': 'Variance (THB)',
        'variance_pct': 'Variance %'
    })
    
    # Format columns nicely
    display_budget['Month'] = display_budget['Month'].dt.strftime('%Y-%m')
    
    def color_variance(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    st.dataframe(
        display_budget.style.format({
            'Budget (THB)': '{:,.2f}',
            'Actual Gross (THB)': '{:,.2f}',
            'Variance (THB)': '{:+,.2f}',
            'Variance %': '{:+.2f}%'
        }).applymap(color_variance, subset=['Variance (THB)', 'Variance %']),
        use_container_width=True
    )
    
    # Notes Studied
    st.info("**Analytical Insight Note:** There is a standard budget revenue hurdle rate of 2,700,000 THB applied monthly by corporate management. Significant positive variances occurred in high-temperature seasonal months (such as March and April 2026), whereas rainy-season low periods (September-October 2025 and June-August 2026) fell short of flat target expectations.")
