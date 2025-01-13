import numpy as np
import yfinance as yf
import streamlit as st

# --------------------------------------
#          CONFIGURATIONS
# --------------------------------------
DEFAULT_DISCOUNT_RATE = 0.10  # 10% discount rate

# Phase success probabilities
PHASE_PROBABILITIES = {
    "Phase 1": 0.6,
    "Phase 2": 0.36,
    "Phase 3": 0.63
}

# --------------------------------------
#          HELPER FUNCTIONS
# --------------------------------------
def fetch_stock_data(ticker_symbol: str) -> dict:
    """
    Fetches key financial information about a company from Yahoo Finance.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info

        market_cap = info.get("marketCap", None)
        shares_outstanding = info.get("sharesOutstanding", None)
        summary = info.get("longBusinessSummary", "No summary available.")

        # Balance sheet details
        balance_sheet = stock.balance_sheet
        total_assets = 0
        total_liabilities = 0
        common_equity = 0
        
        if not balance_sheet.empty:
            if "Total Assets" in balance_sheet.index:
                total_assets = balance_sheet.loc["Total Assets"].max()
            if "Total Liabilities Net Minority Interest" in balance_sheet.index:
                total_liabilities = balance_sheet.loc["Total Liabilities Net Minority Interest"].max()
            if "Common Stock Equity" in balance_sheet.index:
                common_equity = balance_sheet.loc["Common Stock Equity"].max()

        return {
            "market_cap": market_cap,
            "shares_outstanding": shares_outstanding,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "common_equity": common_equity,
            "summary": summary
        }
    except Exception as e:
        return {"error": f"Failed to fetch data for {ticker_symbol}: {e}"}

def calculate_npv(cash_flows: list, discount_rate: float) -> float:
    """
    Calculates the Net Present Value (NPV) of a series of cash flows.
    """
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows, start=1))

def simulate_pipeline_cash_flows(
    eligible_population: int,
    price_per_patient: float,
    market_penetration_rate: float,
    delay_years: int,
    initial_revenue: float,
    growth_rate: float,
    years_to_simulate: int
) -> list:
    """
    Simulates cash flows for a pipeline product that is not yet approved.
    """
    cash_flows = [-500e6 for _ in range(delay_years)]  # Negative cash flows for delay period
    penetration_decimal = market_penetration_rate / 100.0
    treated_population = eligible_population * penetration_decimal
    revenue = initial_revenue + (treated_population * price_per_patient)

    for _ in range(years_to_simulate):
        cash_flows.append(revenue)
        revenue *= (1 + growth_rate / 100.0)

    return cash_flows

def calculate_fair_market_values(
    stock_data: dict,
    pipeline_cash_flows: list,
    discount_rate: float
) -> dict:
    """
    Calculates the valuation from:
      - NPV of pipeline product
    """
    market_cap = stock_data.get("market_cap", 0) or 0
    shares_outstanding = stock_data.get("shares_outstanding", 1)

    current_price_per_share = market_cap / shares_outstanding if shares_outstanding > 0 else 0
    npv_pipeline = calculate_npv(pipeline_cash_flows, discount_rate)
    projected_market_cap = max(0, market_cap + npv_pipeline)
    projected_price_per_share = projected_market_cap / shares_outstanding if shares_outstanding > 0 else 0

    return {
        "current_price_per_share": current_price_per_share,
        "projected_price_per_share": projected_price_per_share,
        "npv_pipeline": npv_pipeline
    }

# --------------------------------------
#          STREAMLIT APP
# --------------------------------------
def main():
    st.title("📈 Pharmagellan Based Biotech Valuation Model 🧬")

    with st.expander("Disclaimer"):
        st.write(
            """
            This application provides a simplified biotech valuation model based on 
            public data and user assumptions. It should not be interpreted as 
            financial or investment advice. Always do your own research.
            """
        )

    ticker_symbol = st.text_input("Enter the biotech ticker symbol:")

    if ticker_symbol:
        stock_data = fetch_stock_data(ticker_symbol)
        if "error" in stock_data:
            st.error(stock_data["error"])
            return

        st.subheader("Company Overview")
        st.write(stock_data.get("summary", "No company summary available."))

        st.subheader("Balance Sheet Highlights")
        st.write(f"Market Cap: ${stock_data['market_cap']:,}" if stock_data['market_cap'] else "Market Cap: N/A")
        st.write(f"Total Assets: ${stock_data['total_assets']:,}" if stock_data['total_assets'] else "Total Assets: N/A")
        st.write(f"Total Liabilities: ${stock_data['total_liabilities']:,}" if stock_data['total_liabilities'] else "Total Liabilities: N/A")
        st.write(f"Common Equity: ${stock_data['common_equity']:,}" if stock_data['common_equity'] else "Common Equity: N/A")
        st.write(f"Shares Outstanding: {stock_data['shares_outstanding']:,}" if stock_data['shares_outstanding'] else "Shares Outstanding: N/A")

        st.subheader("Pipeline Inputs")
        num_assets = st.number_input("Number of Pipeline Assets:", min_value=1, max_value=10, value=1)

        pipeline_cash_flows = []
        for i in range(num_assets):
            st.write(f"**Pipeline Asset {i+1}**")
            phase = st.selectbox(f"Select Phase for Asset {i+1}:", options=list(PHASE_PROBABILITIES.keys()), key=f"phase_{i}")
            phase_probability = PHASE_PROBABILITIES[phase]

            eligible_population = st.number_input(f"Eligible Patient Population for Asset {i+1}:", min_value=0, value=100_000, key=f"pop_{i}")
            market_penetration_rate = st.slider(f"Market Penetration Rate for Asset {i+1} (%):", 1, 100, 70, key=f"penetration_{i}")
            price_per_patient = st.number_input(f"Price per Patient for Asset {i+1} (in thousands USD):", min_value=0.0, value=50.0, key=f"price_{i}") * 1e3
            delay_years = st.slider(f"Years with No Cash Flow for Asset {i+1}:", 1, 20, 5, key=f"delay_{i}")
            initial_revenue = st.number_input(f"Initial Revenue for Asset {i+1} (in billions USD):", min_value=0.0, value=2.0, key=f"revenue_{i}") * 1e9
            growth_rate = st.slider(f"Annual Revenue Growth for Asset {i+1} (%):", 1, 50, 10, key=f"growth_{i}")
            years_to_simulate = st.slider(f"Years to Simulate for Asset {i+1}:", 1, 50, 15, key=f"simulate_{i}")

            cash_flows = simulate_pipeline_cash_flows(
                eligible_population=eligible_population,
                price_per_patient=price_per_patient,
                market_penetration_rate=market_penetration_rate,
                delay_years=delay_years,
                initial_revenue=initial_revenue,
                growth_rate=growth_rate,
                years_to_simulate=years_to_simulate
            )

            risk_adjusted_cash_flows = [cf * phase_probability for cf in cash_flows]
            pipeline_cash_flows.extend(risk_adjusted_cash_flows)

        valuation_results = calculate_fair_market_values(
            stock_data=stock_data,
            pipeline_cash_flows=pipeline_cash_flows,
            discount_rate=DEFAULT_DISCOUNT_RATE
        )

        st.subheader("Valuation Results")
        st.write(f"Current Price per Share: ${valuation_results['current_price_per_share']:,.2f}")
        st.write(f"Projected Price per Share: ${valuation_results['projected_price_per_share']:,.2f}")
        st.write(f"NPV of Pipeline: ${valuation_results['npv_pipeline']:,.2f}")

# Add a "Buy Me a Coffee" button
    st.markdown(
        """
        <div style="text-align: center; margin-top: 50px;">
            <a href="https://www.buymeacoffee.com/cdmccann239" target="_blank">
                <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" 
                alt="Buy Me a Coffee" 
                style="height: 60px; width: 217px;">
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
