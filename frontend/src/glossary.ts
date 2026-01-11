export type GlossaryTerm = {
  id: string;
  term: string;
  fullName?: string;
  definition: string;
  investopediaUrl: string;
}

export const glossaryTerms: GlossaryTerm[] = [
  // Valuation Terms
  {
    id: "dcf",
    term: "DCF",
    fullName: "Discounted Cash Flow",
    definition: "A valuation method that estimates the present value of an investment based on its expected future cash flows. It discounts projected cash flows back to today using a discount rate (typically WACC) to determine what those future earnings are worth in today's dollars.",
    investopediaUrl: "https://www.investopedia.com/terms/d/dcf.asp",
  },
  {
    id: "fcf",
    term: "FCF",
    fullName: "Free Cash Flow",
    definition: "The cash a company generates after accounting for capital expenditures needed to maintain or expand its asset base. It represents money available to pay dividends, reduce debt, or reinvest in the business.",
    investopediaUrl: "https://www.investopedia.com/terms/f/freecashflow.asp",
  },
  {
    id: "wacc",
    term: "WACC",
    fullName: "Weighted Average Cost of Capital",
    definition: "The average rate a company expects to pay to finance its assets. It weights the cost of equity and cost of debt by their proportions in the capital structure, representing the minimum return a company must earn to satisfy its investors.",
    investopediaUrl: "https://www.investopedia.com/terms/w/wacc.asp",
  },
  {
    id: "capm",
    term: "CAPM",
    fullName: "Capital Asset Pricing Model",
    definition: "A model that describes the relationship between systematic risk and expected return for assets. It calculates the expected return on an investment based on the risk-free rate, beta, and market risk premium.",
    investopediaUrl: "https://www.investopedia.com/terms/c/capm.asp",
  },
  {
    id: "intrinsic-value",
    term: "Intrinsic Value",
    definition: "The calculated or 'true' value of an asset based on fundamental analysis, independent of its market price. If intrinsic value exceeds market price, the asset may be undervalued.",
    investopediaUrl: "https://www.investopedia.com/terms/i/intrinsicvalue.asp",
  },
  {
    id: "enterprise-value",
    term: "Enterprise Value",
    fullName: "EV",
    definition: "A measure of a company's total value, often used as a more comprehensive alternative to market cap. It equals market cap plus debt, minus cash, representing the theoretical takeover price.",
    investopediaUrl: "https://www.investopedia.com/terms/e/enterprisevalue.asp",
  },
  {
    id: "equity-value",
    term: "Equity Value",
    definition: "The value of a company available to shareholders after all debts and obligations are paid. In DCF analysis, it equals enterprise value minus net debt.",
    investopediaUrl: "https://www.investopedia.com/terms/e/equity.asp",
  },
  {
    id: "terminal-value",
    term: "Terminal Value",
    definition: "The estimated value of a business beyond the explicit forecast period in a DCF model. It captures the value of all future cash flows after the projection period, typically calculated using the Gordon Growth Model.",
    investopediaUrl: "https://www.investopedia.com/terms/t/terminalvalue.asp",
  },
  {
    id: "terminal-growth",
    term: "Terminal Growth Rate",
    definition: "The perpetual growth rate assumed for a company's cash flows beyond the forecast period. It's typically set at or below long-term GDP growth (2-3%) since no company can grow faster than the economy forever.",
    investopediaUrl: "https://www.investopedia.com/terms/t/terminalvalue.asp",
  },
  {
    id: "net-debt",
    term: "Net Debt",
    definition: "Total debt minus cash and cash equivalents. It shows how much debt would remain if all cash were used to pay down borrowings. A negative net debt means the company has more cash than debt.",
    investopediaUrl: "https://www.investopedia.com/terms/n/netdebt.asp",
  },

  // Risk & Return Terms
  {
    id: "beta",
    term: "Beta",
    definition: "A measure of a stock's volatility relative to the overall market. A beta of 1 means the stock moves with the market; above 1 indicates higher volatility; below 1 indicates lower volatility.",
    investopediaUrl: "https://www.investopedia.com/terms/b/beta.asp",
  },
  {
    id: "risk-free-rate",
    term: "Risk-Free Rate",
    definition: "The theoretical return of an investment with zero risk, typically represented by government bond yields (like 10-year US Treasury). It serves as the baseline for calculating required returns.",
    investopediaUrl: "https://www.investopedia.com/terms/r/risk-freerate.asp",
  },
  {
    id: "market-risk-premium",
    term: "Market Risk Premium",
    definition: "The additional return investors expect for taking on the risk of investing in stocks versus risk-free assets. Historically around 5-7%, it's the difference between expected market return and the risk-free rate.",
    investopediaUrl: "https://www.investopedia.com/terms/m/marketriskpremium.asp",
  },
  {
    id: "discount-rate",
    term: "Discount Rate",
    definition: "The interest rate used to determine the present value of future cash flows. In DCF analysis, WACC is commonly used as the discount rate for valuing the entire firm.",
    investopediaUrl: "https://www.investopedia.com/terms/d/discountrate.asp",
  },
  {
    id: "cost-of-equity",
    term: "Cost of Equity",
    definition: "The return a company must offer to attract equity investors, calculated using CAPM. It represents the compensation investors demand for taking the risk of owning the company's stock.",
    investopediaUrl: "https://www.investopedia.com/terms/c/costofequity.asp",
  },
  {
    id: "cost-of-debt",
    term: "Cost of Debt",
    definition: "The effective rate a company pays on its borrowed funds. The after-tax cost of debt is used in WACC calculations since interest payments are tax-deductible.",
    investopediaUrl: "https://www.investopedia.com/terms/c/costofdebt.asp",
  },

  // Financial Statement Terms
  {
    id: "market-cap",
    term: "Market Cap",
    fullName: "Market Capitalization",
    definition: "The total market value of a company's outstanding shares, calculated as share price multiplied by shares outstanding. It represents what the market believes the company is worth.",
    investopediaUrl: "https://www.investopedia.com/terms/m/marketcapitalization.asp",
  },
  {
    id: "revenue",
    term: "Revenue",
    definition: "The total income generated from sales of goods or services before any expenses are deducted. Also called sales or top line, it's the starting point for most financial analysis.",
    investopediaUrl: "https://www.investopedia.com/terms/r/revenue.asp",
  },
  {
    id: "revenue-growth",
    term: "Revenue Growth",
    definition: "The percentage increase in a company's sales over a period. Consistent revenue growth indicates a company is expanding its market share or entering new markets.",
    investopediaUrl: "https://www.investopedia.com/terms/r/revenue.asp",
  },
  {
    id: "cagr",
    term: "CAGR",
    fullName: "Compound Annual Growth Rate",
    definition: "The mean annual growth rate of an investment over a specified time period longer than one year. It represents the rate at which an investment would have grown if it had grown at a steady rate each year.",
    investopediaUrl: "https://www.investopedia.com/terms/c/cagr.asp",
  },
  {
    id: "operating-margin",
    term: "Operating Margin",
    definition: "Operating income divided by revenue, expressed as a percentage. It shows how much profit a company makes from its core operations before interest and taxes.",
    investopediaUrl: "https://www.investopedia.com/terms/o/operatingmargin.asp",
  },
  {
    id: "ebit",
    term: "EBIT",
    fullName: "Earnings Before Interest and Taxes",
    definition: "A measure of a company's operating profit that excludes interest and tax expenses. It shows profitability from core operations regardless of capital structure or tax jurisdiction.",
    investopediaUrl: "https://www.investopedia.com/terms/e/ebit.asp",
  },
  {
    id: "ebitda",
    term: "EBITDA",
    fullName: "Earnings Before Interest, Taxes, Depreciation, and Amortization",
    definition: "A measure of operating performance that adds back non-cash expenses (D&A) to EBIT. Often used to compare profitability between companies with different capital structures.",
    investopediaUrl: "https://www.investopedia.com/terms/e/ebitda.asp",
  },
  {
    id: "nopat",
    term: "NOPAT",
    fullName: "Net Operating Profit After Tax",
    definition: "Operating profit (EBIT) minus taxes, representing the cash earnings available to all capital providers. NOPAT = EBIT × (1 - Tax Rate). It's the starting point for calculating Free Cash Flow.",
    investopediaUrl: "https://www.investopedia.com/terms/n/nopat.asp",
  },
  {
    id: "da",
    term: "D&A",
    fullName: "Depreciation and Amortization",
    definition: "Non-cash expenses that allocate the cost of assets over their useful lives. Depreciation applies to tangible assets (equipment), amortization to intangible assets (patents).",
    investopediaUrl: "https://www.investopedia.com/terms/d/depreciation.asp",
  },
  {
    id: "capex",
    term: "CapEx",
    fullName: "Capital Expenditure",
    definition: "Funds used to acquire, upgrade, or maintain physical assets like buildings, equipment, or technology. CapEx is subtracted from operating cash flow to calculate free cash flow.",
    investopediaUrl: "https://www.investopedia.com/terms/c/capitalexpenditure.asp",
  },
  {
    id: "working-capital",
    term: "Working Capital",
    definition: "Current assets minus current liabilities. It measures a company's short-term liquidity and ability to meet day-to-day operational expenses.",
    investopediaUrl: "https://www.investopedia.com/terms/w/workingcapital.asp",
  },
  {
    id: "tax-rate",
    term: "Tax Rate",
    definition: "The percentage of income paid as taxes. In valuation, the effective tax rate (actual taxes paid divided by pre-tax income) is used rather than the statutory rate.",
    investopediaUrl: "https://www.investopedia.com/terms/e/effectivetaxrate.asp",
  },
  {
    id: "shares-outstanding",
    term: "Shares Outstanding",
    definition: "The total number of shares currently held by all shareholders. Used to calculate market cap and per-share metrics like intrinsic value per share.",
    investopediaUrl: "https://www.investopedia.com/terms/o/outstandingshares.asp",
  },

  // Valuation Multiples
  {
    id: "pe-ratio",
    term: "P/E Ratio",
    fullName: "Price-to-Earnings Ratio",
    definition: "Share price divided by earnings per share. A high P/E may indicate a stock is overvalued or that investors expect high future growth.",
    investopediaUrl: "https://www.investopedia.com/terms/p/price-earningsratio.asp",
  },
  {
    id: "ev-ebitda",
    term: "EV/EBITDA",
    definition: "Enterprise value divided by EBITDA. This multiple compares a company's total value to its operating earnings, useful for comparing companies regardless of capital structure.",
    investopediaUrl: "https://www.investopedia.com/terms/e/ev-ebitda.asp",
  },
  {
    id: "ps-ratio",
    term: "P/S Ratio",
    fullName: "Price-to-Sales Ratio",
    definition: "Market cap divided by total revenue. Useful for valuing companies that aren't yet profitable, as it focuses on sales rather than earnings.",
    investopediaUrl: "https://www.investopedia.com/terms/p/price-to-salesratio.asp",
  },
  {
    id: "pb-ratio",
    term: "P/B Ratio",
    fullName: "Price-to-Book Ratio",
    definition: "Share price divided by book value per share. A low P/B may indicate an undervalued stock, though some industries naturally trade at higher P/B ratios.",
    investopediaUrl: "https://www.investopedia.com/terms/p/price-to-bookratio.asp",
  },
  {
    id: "earnings-yield",
    term: "Earnings Yield",
    definition: "Earnings per share divided by the stock price (the inverse of P/E). It represents the percentage of each dollar invested that was earned by the company, useful for comparing stocks to bonds.",
    investopediaUrl: "https://www.investopedia.com/terms/e/earningsyield.asp",
  },
  {
    id: "ev-revenue",
    term: "EV/Revenue",
    fullName: "Enterprise Value to Revenue",
    definition: "Enterprise value divided by total revenue. This multiple is useful for valuing high-growth companies that may not yet be profitable, as it focuses on sales rather than earnings.",
    investopediaUrl: "https://www.investopedia.com/terms/e/ev-revenue-multiple.asp",
  },

  // Dividend Metrics
  {
    id: "dividend-yield",
    term: "Dividend Yield",
    definition: "Annual dividends per share divided by the stock price. It shows the percentage return from dividends alone, important for income-focused investors.",
    investopediaUrl: "https://www.investopedia.com/terms/d/dividendyield.asp",
  },
  {
    id: "payout-ratio",
    term: "Payout Ratio",
    definition: "The proportion of earnings paid out as dividends to shareholders. A sustainable payout ratio (typically under 60%) suggests dividends can be maintained or grown.",
    investopediaUrl: "https://www.investopedia.com/terms/d/dividendpayoutratio.asp",
  },
  {
    id: "capital-returns-coverage",
    term: "FCF Coverage (Capital Returns)",
    definition: "Measures how well Free Cash Flow covers shareholder returns (dividends + buybacks). Coverage > 1.0x means FCF fully funds returns; < 1.0x suggests the company is borrowing or depleting cash to pay shareholders — a 'value trap' warning sign.",
    investopediaUrl: "https://www.investopedia.com/terms/f/freecashflow.asp",
  },

  // Profitability Ratios
  {
    id: "gross-margin",
    term: "Gross Margin",
    definition: "Gross profit divided by revenue, expressed as a percentage. It shows how efficiently a company produces its goods or services before operating expenses.",
    investopediaUrl: "https://www.investopedia.com/terms/g/grossmargin.asp",
  },
  {
    id: "net-margin",
    term: "Net Margin",
    fullName: "Net Profit Margin",
    definition: "Net income divided by revenue. It shows the percentage of revenue that translates into actual profit after all expenses, taxes, and interest.",
    investopediaUrl: "https://www.investopedia.com/terms/n/net_margin.asp",
  },
  {
    id: "roe",
    term: "ROE",
    fullName: "Return on Equity",
    definition: "Net income divided by shareholders' equity. It measures how effectively management uses shareholder capital to generate profits. Higher ROE generally indicates better capital efficiency.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnonequity.asp",
  },
  {
    id: "roa",
    term: "ROA",
    fullName: "Return on Assets",
    definition: "Net income divided by total assets. It measures how efficiently a company uses its assets to generate profit. Useful for comparing companies in capital-intensive industries.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnonassets.asp",
  },
  {
    id: "roic",
    term: "ROIC",
    fullName: "Return on Invested Capital",
    definition: "A measure of how well a company generates cash flow relative to the capital invested in its business. ROIC above WACC indicates the company is creating value.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnoninvestmentcapital.asp",
  },

  // Liquidity & Solvency Ratios
  {
    id: "current-ratio",
    term: "Current Ratio",
    definition: "Current assets divided by current liabilities. A ratio above 1 indicates the company can cover its short-term obligations. Too high may suggest inefficient use of assets.",
    investopediaUrl: "https://www.investopedia.com/terms/c/currentratio.asp",
  },
  {
    id: "quick-ratio",
    term: "Quick Ratio",
    fullName: "Acid-Test Ratio",
    definition: "Current assets minus inventory, divided by current liabilities. A more conservative liquidity measure than current ratio, as inventory may not be quickly convertible to cash.",
    investopediaUrl: "https://www.investopedia.com/terms/q/quickratio.asp",
  },
  {
    id: "debt-to-equity",
    term: "Debt-to-Equity",
    fullName: "D/E Ratio",
    definition: "Total debt divided by shareholders' equity. It measures financial leverage—higher ratios indicate more debt financing, which can amplify returns but also risk.",
    investopediaUrl: "https://www.investopedia.com/terms/d/debtequityratio.asp",
  },
  {
    id: "interest-coverage",
    term: "Interest Coverage",
    fullName: "Interest Coverage Ratio",
    definition: "EBIT divided by interest expense. It shows how easily a company can pay interest on its debt. A ratio below 1.5 may signal financial distress.",
    investopediaUrl: "https://www.investopedia.com/terms/i/interestcoverageratio.asp",
  },

  // Efficiency Ratios
  {
    id: "asset-turnover",
    term: "Asset Turnover",
    definition: "Revenue divided by total assets. It measures how efficiently a company uses its assets to generate sales. Higher turnover indicates better asset utilization.",
    investopediaUrl: "https://www.investopedia.com/terms/a/assetturnover.asp",
  },
  {
    id: "inventory-turnover",
    term: "Inventory Turnover",
    definition: "Cost of goods sold divided by average inventory. It shows how many times inventory is sold and replaced over a period. Higher turnover suggests efficient inventory management.",
    investopediaUrl: "https://www.investopedia.com/terms/i/inventoryturnover.asp",
  },
  {
    id: "cash-conversion-cycle",
    term: "Cash Conv. Cycle",
    fullName: "Cash Conversion Cycle",
    definition: "Days to convert inventory into cash: CCC = DSO + DIO - DPO. Measures working capital efficiency. Lower is better; negative CCC (like Amazon) means the company receives customer cash before paying suppliers.",
    investopediaUrl: "https://www.investopedia.com/terms/c/cashconversioncycle.asp",
  },

  // Technical Analysis Terms
  {
    id: "rsi",
    term: "RSI",
    fullName: "Relative Strength Index",
    definition: "A momentum oscillator that measures the speed and magnitude of price movements on a scale of 0-100. Readings above 70 suggest overbought conditions; below 30 suggests oversold.",
    investopediaUrl: "https://www.investopedia.com/terms/r/rsi.asp",
  },
  {
    id: "macd",
    term: "MACD",
    fullName: "Moving Average Convergence Divergence",
    definition: "A trend-following momentum indicator showing the relationship between two moving averages. Traders look for crossovers, divergences, and rapid rises/falls as signals.",
    investopediaUrl: "https://www.investopedia.com/terms/m/macd.asp",
  },
  {
    id: "sma",
    term: "SMA",
    fullName: "Simple Moving Average",
    definition: "The arithmetic mean of prices over a specific period. Common periods are 50-day and 200-day SMAs, used to identify trends and potential support/resistance levels.",
    investopediaUrl: "https://www.investopedia.com/terms/s/sma.asp",
  },
  {
    id: "ema",
    term: "EMA",
    fullName: "Exponential Moving Average",
    definition: "A moving average that gives more weight to recent prices, making it more responsive to new information than SMA. Often used in MACD calculations.",
    investopediaUrl: "https://www.investopedia.com/terms/e/ema.asp",
  },

  // Analysis Types
  {
    id: "sensitivity-analysis",
    term: "Sensitivity Analysis",
    definition: "A technique that examines how changes in input assumptions affect the output of a financial model. In DCF, it typically shows how varying the discount rate and growth rate impacts intrinsic value.",
    investopediaUrl: "https://www.investopedia.com/terms/s/sensitivityanalysis.asp",
  },
  {
    id: "scenario-analysis",
    term: "Scenario Analysis",
    definition: "A method of evaluating different possible future outcomes (bear, base, bull cases) by adjusting key assumptions. Each scenario is assigned a probability to calculate a weighted average value.",
    investopediaUrl: "https://www.investopedia.com/terms/s/scenario_analysis.asp",
  },
  {
    id: "comparable-analysis",
    term: "Comparable Analysis",
    fullName: "Comparable Company Analysis",
    definition: "A relative valuation method that compares a company's trading multiples (P/E, EV/EBITDA) to those of similar companies in the same industry to assess relative value.",
    investopediaUrl: "https://www.investopedia.com/terms/c/comparable-company-analysis-cca.asp",
  },
  {
    id: "monte-carlo",
    term: "Monte Carlo",
    fullName: "Monte Carlo Simulation",
    definition: "A computational technique that runs thousands of simulations with randomized inputs to produce a probability distribution of outcomes. Our app offers two modes: Quick (simplified FCF for fast intuition) and Decision (full DCF engine with bounded distributions, correlations, and decision metrics like CVaR for investment decisions).",
    investopediaUrl: "https://www.investopedia.com/terms/m/montecarlosimulation.asp",
  },
  {
    id: "percentile",
    term: "Percentile",
    definition: "A measure indicating the value below which a given percentage of observations fall. The 10th percentile means 10% of values are lower (bear case), while the 90th percentile means only 10% are higher (bull case).",
    investopediaUrl: "https://www.investopedia.com/terms/p/percentile.asp",
  },
  {
    id: "cvar",
    term: "CVaR",
    fullName: "Conditional Value at Risk",
    definition: "The expected loss in the worst X% of scenarios (also called Expected Shortfall). CVaR 10% represents the average value of the worst 10% of simulation outcomes—a key downside risk metric for investment decisions.",
    investopediaUrl: "https://www.investopedia.com/terms/c/conditional_value_at_risk.asp",
  },
  {
    id: "margin-of-safety",
    term: "Margin of Safety",
    definition: "The difference between intrinsic value and market price, expressed as a percentage. A positive margin of safety means the stock trades below calculated fair value, providing a buffer against estimation errors. Coined by Benjamin Graham, it's a cornerstone of value investing.",
    investopediaUrl: "https://www.investopedia.com/terms/m/marginofsafety.asp",
  },

  // Capital Efficiency Terms
  {
    id: "economic-profit",
    term: "Economic Profit",
    fullName: "Economic Value Added (EVA)",
    definition: "The dollar amount of value created or destroyed, calculated as (ROIC - WACC) × Invested Capital. Positive economic profit means the company is creating shareholder value; negative means it's destroying value despite accounting profits.",
    investopediaUrl: "https://www.investopedia.com/terms/e/economicprofit.asp",
  },
  {
    id: "value-spread",
    term: "Value Spread",
    definition: "The difference between ROIC and WACC. A positive spread indicates value creation—each dollar reinvested generates returns above the cost of capital. A negative spread means growth destroys value.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnoninvestmentcapital.asp",
  },
  {
    id: "reinvestment-rate",
    term: "Reinvestment Rate",
    definition: "The percentage of earnings a company reinvests for growth, calculated as Growth Rate / ROIC. High-ROIC companies can grow with lower reinvestment; low-ROIC companies must reinvest heavily.",
    investopediaUrl: "https://www.investopedia.com/terms/r/reinvestmentrate.asp",
  },
  {
    id: "invested-capital",
    term: "Invested Capital",
    definition: "The total amount of money invested in a company by shareholders and debt holders. It equals equity plus debt minus excess cash, representing the capital base used to generate returns.",
    investopediaUrl: "https://www.investopedia.com/terms/i/invested-capital.asp",
  },

  // Growth Model Terms
  {
    id: "multi-stage-growth",
    term: "Multi-Stage Growth",
    definition: "A DCF approach that uses different growth rates for different periods: typically high growth initially, fading to a stable rate, then terminal growth. More realistic than assuming constant growth forever.",
    investopediaUrl: "https://www.investopedia.com/terms/m/multistageddm.asp",
  },
  {
    id: "operating-leverage",
    term: "Operating Leverage",
    fullName: "Capacity Fill / Step Function Margins",
    definition: "For capital-intensive businesses (airlines, manufacturers, semiconductors), margins don't fade linearly. They behave as step functions: flat at low margin while capacity fills (high fixed costs spread over low volume), then jump when utilization exceeds threshold. Use 'Step' mode in multi-stage economics to model this — margins stay at the start value until the step year, then jump to the end value.",
    investopediaUrl: "https://www.investopedia.com/terms/o/operatingleverage.asp",
  },
  {
    id: "growth-decay",
    term: "Growth Decay",
    fullName: "Growth Fade",
    definition: "The gradual reduction of a company's growth rate over time as it matures. High-growth companies eventually face competition and market saturation, causing growth to fade toward the economy's growth rate.",
    investopediaUrl: "https://www.investopedia.com/terms/g/growthrates.asp",
  },

  // Institutional Risk Metrics
  {
    id: "rotic",
    term: "ROTIC",
    fullName: "Return on Tangible Invested Capital",
    definition: "ROIC excluding goodwill and intangible assets from the capital base. Shows the true return on core operating assets, particularly useful for companies with large acquisition-related intangibles.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnoninvestmentcapital.asp",
  },
  {
    id: "incremental-roic",
    term: "Inc. ROIC",
    fullName: "Incremental Return on Invested Capital",
    definition: "Change in NOPAT divided by change in invested capital (ΔNOPAT / ΔIC). Measures the return on NEW capital invested. If Inc. ROIC > ROIC, returns are improving; if Inc. ROIC < ROIC, the company is experiencing diminishing returns - a red flag for growth sustainability.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnoninvestmentcapital.asp",
  },
  {
    id: "altman-z-score",
    term: "Altman Z-Score",
    definition: "A bankruptcy prediction model using five financial ratios. Scores above 2.99 suggest financial safety ('safe zone'), below 1.81 indicate distress risk, and between is the 'grey zone' of uncertainty.",
    investopediaUrl: "https://www.investopedia.com/terms/a/altman.asp",
  },
  {
    id: "beneish-m-score",
    term: "Beneish M-Score",
    definition: "A statistical model to detect earnings manipulation. Scores above -1.78 suggest higher probability of earnings being manipulated. Uses 8 financial ratios comparing year-over-year changes.",
    investopediaUrl: "https://www.investopedia.com/terms/b/beneishmodel.asp",
  },
  {
    id: "accrual-ratio",
    term: "Accrual Ratio",
    definition: "Measures earnings quality by comparing net income to operating cash flow relative to total assets. High accruals (>10%) may indicate aggressive accounting; companies with cash earnings are more reliable.",
    investopediaUrl: "https://www.investopedia.com/terms/a/accruals.asp",
  },
  {
    id: "sbc-percent-revenue",
    term: "SBC % Revenue",
    fullName: "Stock-Based Compensation as % of Revenue",
    definition: "Stock-based compensation expressed as a percentage of revenue. High SBC (>10%) significantly dilutes existing shareholders. Adjusting FCF for SBC gives a truer picture of cash generation.",
    investopediaUrl: "https://www.investopedia.com/terms/s/stockcompensation.asp",
  },
  {
    id: "fcf-adjusted",
    term: "FCF (SBC-adjusted)",
    fullName: "Free Cash Flow Adjusted for Stock-Based Compensation",
    definition: "Free cash flow minus stock-based compensation. Since SBC is a real cost (dilution) but doesn't affect cash flow, subtracting it gives a more conservative and realistic FCF figure.",
    investopediaUrl: "https://www.investopedia.com/terms/s/stockcompensation.asp",
  },
  {
    id: "conservative-fcf",
    term: "Conservative FCF",
    fullName: "Conservative Free Cash Flow (FCF - SBC)",
    definition: "A DCF valuation mode that treats Stock-Based Compensation as a real expense. The formula becomes FCF = NOPAT + D&A - CapEx - ΔWC - SBC. This is more conservative because SBC represents value transferred from shareholders to employees through equity dilution, even though it doesn't reduce cash. Enter SBC as a percentage of revenue to project it forward.",
    investopediaUrl: "https://www.investopedia.com/terms/s/stockcompensation.asp",
  },
  {
    id: "vwap",
    term: "VWAP",
    fullName: "Volume Weighted Average Price",
    definition: "The average price weighted by volume throughout the trading period. Institutional traders use VWAP to assess execution quality—buying below VWAP is considered favorable.",
    investopediaUrl: "https://www.investopedia.com/terms/v/vwap.asp",
  },
  {
    id: "relative-volume",
    term: "Relative Volume",
    definition: "Current volume compared to average volume, expressed as a multiplier. Values above 1.2x indicate unusually high volume, confirming price moves. Below 0.8x suggests weak conviction.",
    investopediaUrl: "https://www.investopedia.com/terms/r/relativevolume.asp",
  },
  {
    id: "mfi",
    term: "MFI",
    fullName: "Money Flow Index",
    definition: "A volume-weighted RSI that measures buying and selling pressure. Above 80 indicates overbought (potential reversal down), below 20 indicates oversold (potential bounce). More reliable than price-only RSI because it incorporates volume.",
    investopediaUrl: "https://www.investopedia.com/terms/m/mfi.asp",
  },
  {
    id: "obv",
    term: "OBV",
    fullName: "On-Balance Volume",
    definition: "A cumulative indicator that adds volume on up days and subtracts on down days. Rising OBV suggests 'smart money' accumulation (bullish), falling OBV suggests distribution (bearish). OBV divergences from price often precede reversals.",
    investopediaUrl: "https://www.investopedia.com/terms/o/onbalancevolume.asp",
  },
  {
    id: "vwma",
    term: "VWMA",
    fullName: "Volume Weighted Moving Average",
    definition: "A moving average that weights prices by their trading volume. Higher volume days have more influence on the average. When price is above VWMA, trend is bullish; below VWMA, trend is bearish.",
    investopediaUrl: "https://www.investopedia.com/terms/v/vwap.asp",
  },
  {
    id: "momentum-bridge",
    term: "Momentum Bridge",
    fullName: "Value + Momentum Convergence",
    definition: "Combines intrinsic value (DCF) with momentum (200-day VWMA trend) for entry timing. A cheap stock in a downtrend is a 'falling knife' that often becomes 'dead money'. The bridge signals BUY only when value and momentum align: undervalued + (uptrend or flat). Signals WAIT when cheap but still falling.",
    investopediaUrl: "https://www.investopedia.com/articles/active-trading/052014/how-use-moving-average-buy-stocks.asp",
  },
  {
    id: "buyback-yield",
    term: "Buyback Yield",
    fullName: "Share Repurchase Yield",
    definition: "Annual share repurchases divided by market cap. Represents capital returned to shareholders via stock buybacks. Positive = company buying back shares (reduces float, boosts EPS). Negative = company issuing shares (dilution). Modern tech companies often prefer buybacks over dividends for tax efficiency.",
    investopediaUrl: "https://www.investopedia.com/terms/b/buyback.asp",
  },
  {
    id: "buyback-efficiency",
    term: "Buyback Efficiency",
    fullName: "Net Buyback Efficiency Ratio",
    definition: "SBC Expense ÷ Cash Spent on Buybacks. Measures if buybacks genuinely return value or just offset SBC dilution. Ratio > 1.0 means SBC exceeds buybacks ('defensive buybacks' - a value trap). Ratio < 1.0 means buybacks exceed SBC (genuine value return). Many tech companies show high buyback yields but are actually just offsetting employee stock compensation.",
    investopediaUrl: "https://www.investopedia.com/terms/b/buyback.asp",
  },
  {
    id: "total-shareholder-yield",
    term: "Total Shareholder Yield",
    fullName: "Dividend + Buyback Yield",
    definition: "The sum of Dividend Yield and Buyback Yield. Captures the true 'cash return' to shareholders. Many modern companies return more via buybacks than dividends, making dividend yield alone misleading. A TSY > 4% often indicates strong shareholder returns.",
    investopediaUrl: "https://www.investopedia.com/terms/s/shareholderyield.asp",
  },
  {
    id: "ceo-efficiency",
    term: "CEO Efficiency",
    fullName: "Incremental ROIC vs WACC Spread",
    definition: "Compares Incremental Return on Invested Capital to Weighted Average Cost of Capital. If Inc. ROIC > WACC, management creates value with new investments. If Inc. ROIC < WACC, growth destroys value — every dollar of new capital earns less than its cost. A negative spread means the CEO is actively burning shareholder capital by pursuing growth.",
    investopediaUrl: "https://www.investopedia.com/terms/r/returnoninvestmentcapital.asp",
  },
];

// Create a lookup map for quick access by ID
export const glossaryMap = new Map<string, GlossaryTerm>(
  glossaryTerms.map(term => [term.id, term])
);

// Get term by ID
export function getGlossaryTerm(id: string): GlossaryTerm | undefined {
  return glossaryMap.get(id);
}

