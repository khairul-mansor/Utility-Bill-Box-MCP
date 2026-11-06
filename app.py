"""
Streamlit demo app for the utility bill extraction pipeline.

Run with: streamlit run app.py
"""

import asyncio
import os

import pandas as pd
import streamlit as st

from invoice_pipeline import ask_about_bills, run_extraction

st.set_page_config(page_title="Utility Bill Extractor", page_icon="🧾")
st.title("🧾 Utility Bill Extractor")
st.caption(
    "Extracts structured data from utility bills stored in a Box folder, "
    "using Gemini + the Box MCP Server."
)

if "bills" not in st.session_state:
    st.session_state.bills = None

folder_id = st.text_input("Box folder ID", value=os.getenv("BOX_FOLDER_ID", ""))

if st.button("Extract bills", type="primary", disabled=not folder_id):
    status = st.empty()

    def progress_cb(message: str):
        status.info(message)

    with st.spinner("Connecting to Box and extracting bills..."):
        try:
            st.session_state.bills = asyncio.run(run_extraction(folder_id, progress_cb=progress_cb))
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.session_state.bills = None
    status.empty()

if st.session_state.bills:
    df = pd.DataFrame(st.session_state.bills)

    st.subheader("Extracted bills")
    st.dataframe(df, use_container_width=True)

    st.subheader("Summary")
    col1, col2 = st.columns(2)
    col1.metric("Total bills", len(df))
    col2.metric("Total amount", f"€{df['bill_amount_euro'].sum():,.2f}")

    st.markdown("**Breakdown by provider**")
    breakdown = (
        df.groupby("provider_name")["bill_amount_euro"]
        .agg(["count", "sum"])
        .rename(columns={"count": "bills", "sum": "total_amount"})
    )
    st.dataframe(breakdown, use_container_width=True)

    st.subheader("Ask a question about these bills")
    question = st.text_input(
        "e.g. Which bill is highest? Is spend trending up or down?",
        key="question_input",
    )
    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            try:
                answer = asyncio.run(ask_about_bills(question, st.session_state.bills))
                st.write(answer)
            except Exception as e:
                st.error(f"Couldn't get an answer: {e}")
else:
    st.info("Enter a Box folder ID and click 'Extract bills' to get started.")
