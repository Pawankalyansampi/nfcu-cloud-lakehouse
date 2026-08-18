import pandas as pd
import streamlit as st

from app.config import ROOT

st.set_page_config(page_title="NFCU Cloud Dashboard", layout="wide")
st.title("Navy Federal Credit Union")
st.caption("Lakehouse on Amazon S3, Glue, Athena, Kinesis, and Databricks — no RDS/Redshift")

LAKE = ROOT / "data" / "lake"


def load_parquet(layer: str, name: str) -> pd.DataFrame:
    path = LAKE / layer / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


payments = load_parquet("silver", "payments")
accounts = load_parquet("bronze", "accounts")
bank_txns = load_parquet("bronze", "bank_transactions")
alerts = payments[payments["fraud_flag"] == "Yes"] if not payments.empty else payments
gold = load_parquet("gold", "gold_daily_volume")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Payments", f"{len(payments):,}")
c2.metric("Bank accounts (Plaid)", f"{len(accounts):,}")
c3.metric("Bank transactions", f"{len(bank_txns):,}")
c4.metric("Fraud alerts", f"{len(alerts):,}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Payments", "Plaid accounts", "Fraud alerts", "Gold", "Athena", "Policy RAG"]
)

with tab1:
    if payments.empty:
        st.write("Run python run_local.py first.")
    else:
        st.bar_chart(payments.groupby("type")["amount"].sum())
        st.dataframe(payments.head(200), use_container_width=True)

with tab2:
    st.dataframe(accounts, use_container_width=True)
    st.dataframe(bank_txns.head(200), use_container_width=True)

with tab3:
    st.dataframe(alerts, use_container_width=True)

with tab4:
    st.dataframe(gold, use_container_width=True)

with tab5:
    st.caption("Amazon Athena over Glue tables on S3.")
    if st.button("Run Athena gold query"):
        from app.athena import run_query

        result = run_query()
        st.write(result.get("status"), result.get("reason", ""))
        if result.get("rows"):
            st.dataframe(pd.DataFrame(result["rows"]), use_container_width=True)

with tab6:
    from app.rag import ask

    question = st.text_input("Ask a policy question", "When should a payment be flagged as fraud?")
    if st.button("Search") and question:
        result = ask(question)
        st.write(result["answer"])
        st.caption("Sources: " + ", ".join(h["file"] for h in result["sources"]))
