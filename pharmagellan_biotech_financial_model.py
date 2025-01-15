import numpy as np
import yfinance as yf
import streamlit as st
import pandas as pd

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

# Rare disease probabilities
RARE_DISEASE_PHASE_PROBABILITIES = {
    "Phase 1": 0.7,
    "Phase 2": 0.45,
    "Phase 3": 0.8
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
        cash_on_hand = info.get("totalCash", info.get("freeCashflow", 0))  # Default to freeCashflow if totalCash is unavailable
        current_revenue = info.get("totalRevenue", 0)  # Default to 0 if unavailable
        analyst_price_target = info.get("targetMeanPrice", "N/A")
        summary = info.get("longBusinessSummary", "No summary available.")

        return {
            "market_cap": market_cap,
            "shares_outstanding": shares_outstanding,
            "cash_on_hand": cash_on_hand,
            "current_revenue": current_revenue,
            "analyst_price_target": analyst_price_target,
            "summary": summary
        }
    except Exception as e:
        return {"error": f"Failed to fetch data for {ticker_symbol}: {e}"}


def calculate_npv(cash_flows: list, discount_rate: float) -> float:
    """
    Calculates the Net Present Value (NPV) of a series of cash flows.
    """
    return sum(cf / ((1 + discount_rate) ** t) for t, cf in enumerate(cash_flows, start=1))


def calculate_revenue_curve(eligible_population, price_per_patient, market_penetration, ramp_years, peak_years, decline_years, decline_rate):
    """
    Generates revenue over time with ramp-up, peak, and decline phases.
    """
    peak_revenue = eligible_population * price_per_patient * (market_penetration / 100)

    # Ramp-up phase (S-curve)
    ramp_curve = [peak_revenue * p for p in np.linspace(0.1, 1.0, ramp_years)]

    # Peak phase (constant revenue for a defined period)
    peak_curve = [peak_revenue] * peak_years

    # Decline phase (exponential decay)
    decline_curve = [peak_revenue * ((1 - decline_rate) ** year) for year in range(1, decline_years + 1)]

    # Combine all phases
    return ramp_curve + peak_curve + decline_curve


def simulate_pipeline_cash_flows(
    eligible_population, price_per_patient, market_penetration, delay_years, ramp_years, peak_years, decline_years, decline_rate
):
    """
    Simulates cash flows for a pipeline product using revenue ramp-up, peak, and decline phases.
    """
    cash_flows = [-500e6 for _ in range(delay_years)]  # Negative cash flows for delay period
    revenue_curve = calculate_revenue_curve(
        eligible_population, price_per_patient, market_penetration, ramp_years, peak_years, decline_years, decline_rate
    )
    cash_flows.extend(revenue_curve)
    return cash_flows


def calculate_fair_market_values(stock_data, pipeline_cash_flows, discount_rate):
    """
    Calculates the valuation from:
      - NPV of pipeline product
    """
    market_cap = stock_data.get("market_cap", 0) or 0
    shares_outstanding = stock_data.get("shares_outstanding", 1)

    current_price_per_share = market_cap / shares_outstanding if shares_outstanding > 0 else 0

    # Calculate NPV of the pipeline
    npv_pipeline = calculate_npv(pipeline_cash_flows, discount_rate)

    # Adjust projected market cap
    projected_market_cap = max(0, market_cap + npv_pipeline)

    # Ensure shares outstanding are reasonable
    if shares_outstanding <= 0:
        shares_outstanding = 1e6  # Default to avoid division errors

    projected_price_per_share = projected_market_cap / shares_outstanding

    # Return detailed results
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

        st.markdown("## **Company Overview**")
        st.write(stock_data.get("summary", "No company summary available."))

        st.markdown("## **Balance Sheet Highlights**")
        st.write(f"Market Cap: ${stock_data['market_cap']:,}" if stock_data['market_cap'] else "Market Cap: N/A")
        st.write(f"Shares Outstanding: {stock_data['shares_outstanding']:,}" if stock_data['shares_outstanding'] else "Shares Outstanding: N/A")
        st.write(f"Cash on Hand: ${stock_data['cash_on_hand']:,}" if stock_data['cash_on_hand'] else "Cash on Hand: N/A")
        st.write(f"Current Revenue: ${stock_data['current_revenue']:,}" if stock_data['current_revenue'] else "Current Revenue: N/A")
        st.write(f"Analyst Price Target: ${stock_data['analyst_price_target']}" if stock_data['analyst_price_target'] != "N/A" else "Analyst Price Target: N/A")

        st.subheader("Pipeline Inputs")
        num_assets = st.number_input("Number of Pipeline Assets:", min_value=1, max_value=10, value=1, step=1)

        pipeline_cash_flows = []
        for i in range(num_assets):
            # Existing pipeline input code...
            pass

        valuation_results = calculate_fair_market_values(
            stock_data=stock_data,
            pipeline_cash_flows=pipeline_cash_flows,
            discount_rate=DEFAULT_DISCOUNT_RATE
        )

        st.subheader("Valuation Results")
        st.write(f"Current Price per Share: ${valuation_results['current_price_per_share']:,.2f}")
        st.write(f"Projected Price per Share: ${valuation_results['projected_price_per_share']:,.2f}")
        st.write(f"NPV of Pipeline: ${valuation_results['npv_pipeline']:,.2f}")

        # Revenue graph
        years = list(range(1, len(pipeline_cash_flows) + 1))
        revenue_data = pd.DataFrame({"Year": years, "Revenue": pipeline_cash_flows})
        st.subheader("Revenue Projection Over Time")
        st.line_chart(revenue_data.set_index("Year"))
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
