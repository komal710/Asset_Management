import yfinance as yf
import pandas as pd
import numpy as np

# -----------------------------------
# 1. FETCH DATA (ETF + BENCHMARK)
# -----------------------------------
def fetch_data(tickers, benchmark, period="5y"):
    price_data = pd.DataFrame()
    volume_data = pd.DataFrame()

    for ticker in tickers:
        temp = yf.download(ticker, period=period)
        price_data[ticker] = temp["Close"]
        volume_data[ticker] = temp["Volume"]

    benchmark_data = yf.download(benchmark, period=period)["Close"]
    price_data["Benchmark"] = benchmark_data

    price_data = price_data.ffill().dropna()
    volume_data = volume_data.ffill().dropna()
    return price_data, volume_data


# -----------------------------------
# 2. CALCULATE RETURNS
# -----------------------------------
def calculate_returns(data):
    return data.pct_change().dropna()


# -----------------------------------
# 3. SUMMARY METRICS (STATIC)
# -----------------------------------
def calculate_metrics(returns, risk_free_rate=0.05):

    rf_daily = risk_free_rate / 252
    benchmark = returns["Benchmark"]

    summary = pd.DataFrame()

    for col in returns.columns:
        if col == "Benchmark":
            continue

        fund = returns[col]

        mean_return = fund.mean()
        std_dev = fund.std()

        sharpe = (mean_return - rf_daily) / std_dev

        downside = fund[fund < 0].std()
        sortino = (mean_return - rf_daily) / downside

        beta = np.cov(fund, benchmark)[0][1] / np.var(benchmark)

        alpha = mean_return - (rf_daily + beta * (benchmark.mean() - rf_daily))

        treynor = (mean_return - rf_daily) / beta

        tracking_error = (fund - benchmark).std()

        info_ratio = (mean_return - benchmark.mean()) / tracking_error

        cum_returns = (1 + fund).cumprod()
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        summary.loc[col, "Daily Return"] = mean_return
        summary.loc[col, "Std Dev"] = std_dev
        summary.loc[col, "Sharpe"] = sharpe
        summary.loc[col, "Sortino"] = sortino
        summary.loc[col, "Beta"] = beta
        summary.loc[col, "Alpha"] = alpha
        summary.loc[col, "Treynor"] = treynor
        summary.loc[col, "Tracking Error"] = tracking_error
        summary.loc[col, "Information Ratio"] = info_ratio
        summary.loc[col, "Max Drawdown"] = max_drawdown

    return summary


# -----------------------------------
# 4. DAILY ROLLING RATIOS (TIME SERIES)
# -----------------------------------
def calculate_daily_ratios(returns, volume_data, window=30, risk_free_rate=0.05):

    rf_daily = risk_free_rate / 252
    benchmark = returns["Benchmark"]

    etf_data = {}

    for col in returns.columns:
        if col == "Benchmark":
            continue

        fund = returns[col]
        volume = volume_data[col]

        rolling_mean = fund.rolling(window).mean()
        rolling_std = fund.rolling(window).std()

        sharpe = (rolling_mean - rf_daily) / rolling_std

        beta = fund.rolling(window).cov(benchmark) / benchmark.rolling(window).var()

        alpha = rolling_mean - (rf_daily + beta * (benchmark.rolling(window).mean() - rf_daily))

        tracking_error = (fund - benchmark).rolling(window).std()

        info_ratio = (rolling_mean - benchmark.rolling(window).mean()) / tracking_error

        df = pd.DataFrame({
            "Return": fund,
            "Volume" : volume,
            "Volatility": rolling_std,
            "Sharpe": sharpe,
            "Beta": beta,
            "Alpha": alpha,
            "Tracking Error": tracking_error,
            "Information Ratio": info_ratio
        })

        df = df.dropna()

        etf_data[col] = df

    return etf_data


# -----------------------------------
# 5. ADD EXPENSE RATIO
# -----------------------------------
def add_expense_ratio(summary):

    expense_ratio = {
        "NIFTYBEES.NS": 0.0004,
        "ITBEES.NS": 0.0022
    }

    summary["Expense Ratio"] = summary.index.map(expense_ratio)

    return summary


# -----------------------------------
# 6. COMPLIANCE CHECK
# -----------------------------------
def compliance_check(summary):

    alerts = []

    for fund in summary.index:

        if summary.loc[fund, "Std Dev"] > 0.02:
            alerts.append(f"{fund}: High Risk")

        if summary.loc[fund, "Sharpe"] < 0.5:
            alerts.append(f"{fund}: Poor Risk-Return")

    return alerts


# -----------------------------------
# 7. EXPORT TO EXCEL
# -----------------------------------
def export_to_excel(data, returns, summary, etf_data, filename="ETF_Analysis1.xlsx"):

    with pd.ExcelWriter(filename, engine='openpyxl', mode='w') as writer:

        data.to_excel(writer, sheet_name="NAV_Prices")
        returns.to_excel(writer, sheet_name="Returns")
        summary.to_excel(writer, sheet_name="Summary")

        # Separate sheets per ETF
        for etf, df in etf_data.items():
            sheet_name = etf[:30]
            df.to_excel(writer, sheet_name=sheet_name)

    print(" Excel exported successfully")


# -----------------------------------
# MAIN FUNCTION
# -----------------------------------
def main():

    tickers = ["NIFTYBEES.NS", "ITBEES.NS"]
    benchmark = "^NSEI"

    print(" Fetching data...")
    data, volume_data = fetch_data(tickers, benchmark)

    print(" Calculating returns...")
    returns = calculate_returns(data)

    print(" Calculating summary metrics...")
    summary = calculate_metrics(returns)

    summary = add_expense_ratio(summary)

    print(summary)

    print("\n Calculating rolling daily ratios...")
    etf_data = calculate_daily_ratios(returns, volume_data)

    print("\n Compliance Alerts:")
    alerts = compliance_check(summary)
    for alert in alerts:
        print(alert)

    print("\n Exporting to Excel...")
    export_to_excel(data, returns, summary, etf_data)


# -----------------------------------
# RUN SCRIPT
# -----------------------------------
if __name__ == "__main__":
    main()