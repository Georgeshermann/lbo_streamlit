import math
from dataclasses import dataclass

import pandas as pd
import streamlit as st


@dataclass
class LoanInputs:
    principal: float
    annual_rate: float
    years: int


def compute_monthly_schedule(loan: LoanInputs) -> pd.DataFrame:
    """Return a month-by-month amortization schedule for a standard fixed-rate loan."""
    months = loan.years * 12
    monthly_rate = loan.annual_rate / 100 / 12

    if monthly_rate == 0:
        monthly_payment = loan.principal / months
    else:
        monthly_payment = loan.principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months))

    rows = []
    balance = loan.principal
    for month in range(1, months + 1):
        interest = balance * monthly_rate
        principal_paid = monthly_payment - interest
        balance = max(0.0, balance - principal_paid)
        rows.append(
            {
                "month": month,
                "year": math.ceil(month / 12),
                "payment": monthly_payment,
                "principal": principal_paid,
                "interest": interest,
            }
        )
    return pd.DataFrame(rows)


def aggregate_schedule(df: pd.DataFrame, view: str) -> pd.DataFrame:
    """
    Aggregate monthly schedule to yearly totals or average monthly values per year.
    view: "Annuel" (totals per year) or "Mensuel" (mean monthly amounts within each year).
    """
    agg = (
        df.groupby("year")
        .agg(
            payment=("payment", "sum"),
            principal=("principal", "sum"),
            interest=("interest", "sum"),
            months=("month", "count"),
        )
        .reset_index()
    )

    if view == "Mensuel":
        for col in ["payment", "principal", "interest"]:
            agg[col] = agg[col] / agg["months"]
    agg = agg.drop(columns=["months"])
    agg = agg.rename(
        columns={
            "year": "Année",
            "payment": "Remboursement du prêt",
            "principal": "Principal",
            "interest": "Intérêt",
        }
    )
    return agg


def format_currency(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    for col in formatted.columns:
        if col != "Année" and pd.api.types.is_numeric_dtype(formatted[col]):
            formatted[col] = formatted[col].apply(lambda x: f"${x:,.2f}")
    return formatted


def main() -> None:
    st.set_page_config(page_title="Calculateur LBO", layout="centered")
    st.title("Calculateur LBO")

    st.header("Valorisation")
    col1, col2 = st.columns(2)
    with col1:
        ebitda = st.number_input("Cashflow / EBITDA", min_value=0.0, value=300_000.0, step=25_000.0, format="%.0f")
    with col2:
        sell_price = st.number_input("Prix de vente", min_value=0.0, value=1_000_000.0, step=100_000.0, format="%.0f")

    if ebitda > 0:
        multiple = sell_price / ebitda
        st.metric("Multiple du prix de vente sur le cashflow", f"{multiple:,.2f}x")
    else:
        st.info("Saisissez un cashflow/EBITDA non nul pour calculer le multiple.")

    st.header("Structure de la dette")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        annual_rate = st.number_input("Taux d'intérêt (annuel %)", min_value=0.0, value=3.5, step=0.1)
    with col_b:
        duration_years = st.number_input("Durée (années)", min_value=1, value=7, step=1)
    with col_c:
        principal = st.number_input("Montant du prêt", min_value=0.0, value=700_000.0, step=50_000.0, format="%.0f")

    st.markdown("### Périodicité d'affichage des montants")
    st.caption("Choisissez si les montants sont affichés en cumul annuel ou en moyenne mensuelle par année.")
    view = st.radio(
        "Périodicité des montants",
        options=["Annuel", "Mensuel"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

    loan = LoanInputs(principal=principal, annual_rate=annual_rate, years=int(duration_years))
    monthly_schedule = compute_monthly_schedule(loan)

    monthly_payment = monthly_schedule.loc[0, "payment"] if not monthly_schedule.empty else 0.0
    yearly_payment = monthly_payment * 12

    if view == "Mensuel":
        base_cf = ebitda / 12 if ebitda else 0
        delta = f"{(monthly_payment / base_cf):,.2f}x du cashflow mensuel" if base_cf else None
        st.metric("Mensualité moyenne du prêt", f"${monthly_payment:,.2f}", delta=delta)
    else:
        base_cf = ebitda if ebitda else 0
        delta = f"{(yearly_payment / base_cf):,.2f}x du cashflow annuel" if base_cf else None
        st.metric("Remboursement annuel du prêt", f"${yearly_payment:,.2f}", delta=delta)

    yearly_table = aggregate_schedule(monthly_schedule, view)
    cashflow_value = ebitda if view == "Annuel" else ebitda / 12
    yearly_table["Cashflow"] = cashflow_value
    yearly_table = yearly_table[["Année", "Cashflow", "Remboursement du prêt", "Principal", "Intérêt"]]
    st.subheader("Tableau d'amortissement (par année)")
    st.dataframe(format_currency(yearly_table), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
