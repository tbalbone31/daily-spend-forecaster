import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.graph_objects as go

# Set page configuration for professional horizontal dashboard layout
st.set_page_config(
    page_title="Current Account Daily Spend Forecaster",
    page_icon="£",
    layout="wide"
)

# --- CORE ENGINE FUNCTIONS ---

def get_remaining_working_days(start_date: date, end_date: date) -> int:
    """
    Calculates the number of working days (Mon-Fri) between start_date (inclusive)
    and end_date (exclusive).
    """
    np_start = np.datetime64(start_date)
    np_end = np.datetime64(end_date)
    if np_start >= np_end:
        return 0
    return int(np.busday_count(np_start, np_end))

def calculate_projections(
    current_balance: float,
    payday_date: date,
    what_if_spend: float = 0.0,
    start_date: date = None
) -> tuple:
    """
    Generates a daily timeline DataFrame tracking the Baseline vs. What-If trajectories.
    """
    if start_date is None:
        start_date = date.today()

    remaining_work_days = get_remaining_working_days(start_date, payday_date)
    if remaining_work_days <= 0:
        remaining_work_days = 1

    baseline_allowance = current_balance / remaining_work_days
    what_if_remaining_balance = current_balance - what_if_spend
    what_if_allowance = max(0.0, what_if_remaining_balance / remaining_work_days)

    date_range = pd.date_range(start=start_date, end=payday_date, freq='D')

    baseline_history = []
    what_if_history = []
    current_baseline_bal = current_balance
    current_what_if_bal = what_if_remaining_balance

    for dt in date_range:
        baseline_history.append(current_baseline_bal)
        what_if_history.append(current_what_if_bal)

        is_weekday = np.is_busday(np.datetime64(dt.date()))
        if is_weekday and dt.date() < payday_date:
            current_baseline_bal -= baseline_allowance
            current_what_if_bal -= what_if_allowance

    df = pd.DataFrame({
        'Date': date_range,
        'Baseline_Balance': baseline_history,
        'What_If_Balance': what_if_history
    })

    return df, baseline_allowance, what_if_allowance

def generate_spend_forecast_chart(df: pd.DataFrame) -> go.Figure:
    """
    Creates an interactive Plotly line chart comparing the Baseline and What-If trajectories.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Baseline_Balance'],
        mode='lines+markers',
        name='Baseline Trajectory',
        line=dict(color='#1f77b4', width=3),
        hovertemplate='<b>Date</b>: %{x|%b %d, %Y}<br><b>Balance</b>: £%{y:.2f}<extra></extra>'
    ))
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['What_If_Balance'],
        mode='lines+markers',
        name='What-If Trajectory',
        line=dict(color='#ff7f0e', width=3, dash='dash'),
        hovertemplate='<b>Date</b>: %{x|%b %d, %Y}<br><b>Balance</b>: £%{y:.2f}<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text='Account Balance Projection to Payday', font=dict(size=18, color='#333333'), x=0.5),
        xaxis=dict(title='Date', gridcolor='#f0f0f0', showgrid=True),
        yaxis=dict(title='Projected Balance (£)', gridcolor='#f0f0f0', showgrid=True, zeroline=True, zerolinecolor='#cccccc'),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    return fig

# --- STREAMLIT UI LAYER ---

st.title("🇬🇧 Current Account Daily Spend Forecaster")
st.markdown("Manage your discretionary budget logically by calculating your exact daily working-day allowance.")

# Sidebar Control Panel
st.sidebar.header("Financial Configuration")
today_val = date.today()
default_payday = today_val + timedelta(days=15)

balance_input = st.sidebar.number_input("Current Account Balance (£)", min_value=0.0, value=1000.0, step=50.0)
payday_input = st.sidebar.date_input("Next Payday Date", value=default_payday)
spend_input = st.sidebar.slider("Proposed Immediate 'What-If' Spend (£)", min_value=0.0, max_value=float(balance_input), value=150.0, step=10.0)

# Execution Flow
if payday_input <= today_val:
    st.error("Error: Next Payday Date must be set to a future date.")
else:
    total_days = (payday_input - today_val).days
    working_days = get_remaining_working_days(today_val, payday_input)
    
    df_proj, base_allow, wi_allow = calculate_projections(
        balance_input, payday_input, spend_input, today_val
    )
    
    # Presenting Row 1: Key Performance Indicators
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Baseline Daily Spend Limit", f"£{base_allow:.2f}")
    with col2:
        st.metric("What-If Daily Spend Limit", f"£{wi_allow:.2f}", delta=f"-£{(base_allow - wi_allow):.2f}", delta_color="inverse")
    with col3:
        st.metric("Remaining Working Days", f"{working_days} Days", f"{total_days} Calendar Days", delta_color="off")
    with col4:
        st.metric("Immediate Cash Reduction", f"£{spend_input:.2f}")

    # Presenting Row 2: Projected Balance Curve
    fig = generate_spend_forecast_chart(df_proj)
    st.plotly_chart(fig, use_container_width=True)
    
    # Presenting Row 3: Detail Data Table
    with st.expander("View Day-by-Day Forecast Dataframe"):
        st.dataframe(df_proj.style.format({'Baseline_Balance': '£{:.2f}', 'What_If_Balance': '£{:.2f}'}), use_container_width=True)
