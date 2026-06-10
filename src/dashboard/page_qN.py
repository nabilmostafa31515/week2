# src/dashboard/page_qN.py
import streamlit as st

def render(DATA, page_header, kpi_card, insight_card):
    page_header("QN — Title", "Description")

    # 1. KPI row       → kpi_card()
    # 2. st.markdown("---")
    # 3. Charts        → st.plotly_chart()
    # 4. Insight cards → insight_card(..., "finding")
    #                    insight_card(..., "insight")
    #                    insight_card(..., "action")
    #                    insight_card(..., "solution")