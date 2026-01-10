import { formatNumber, formatPercent } from '../utils';
import { GlossaryRef } from './GlossaryRef';
import type { FinancialRatiosPeriod } from '../types';

interface Props {
  ratios: FinancialRatiosPeriod;
}

export function FinancialRatiosTable({ ratios }: Props) {
  if (!ratios || !ratios.valuation || !ratios.profitability || !ratios.liquidity || !ratios.efficiency) {
    return <p className="text-gray-500">No data available</p>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
      {/* Valuation */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Valuation</h3>
        <table className="w-full">
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">P/E<GlossaryRef id="pe-ratio" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.valuation.pe_ratio)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Earnings Yield<GlossaryRef id="earnings-yield" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.valuation.earnings_yield)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">P/S<GlossaryRef id="ps-ratio" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.valuation.ps_ratio)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">P/B<GlossaryRef id="pb-ratio" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.valuation.pb_ratio)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Profitability */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Profitability</h3>
        <table className="w-full">
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Gross Margin<GlossaryRef id="gross-margin" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.gross_margin)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Operating Margin<GlossaryRef id="operating-margin" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.operating_margin)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Net Margin<GlossaryRef id="net-margin" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.net_margin)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">ROE<GlossaryRef id="roe" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.roe)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">ROA<GlossaryRef id="roa" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.roa)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">ROIC<GlossaryRef id="roic" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.roic)}</td>
            </tr>
            {ratios.profitability.rotic != null && (
              <tr className="border-b border-gray-100">
                <td className="py-2 text-sm text-gray-500">ROTIC<GlossaryRef id="rotic" /></td>
                <td className="py-2 text-sm font-mono font-medium text-right">{formatPercent(ratios.profitability.rotic)}</td>
              </tr>
            )}
            {ratios.profitability.incremental_roic != null && (
              <tr className="border-b border-gray-100">
                <td className="py-2 text-sm text-gray-500">Inc. ROIC<GlossaryRef id="incremental-roic" /></td>
                <td className="py-2 text-sm font-mono font-medium text-right">
                  <span className={
                    ratios.profitability.roic != null && ratios.profitability.incremental_roic > ratios.profitability.roic
                      ? 'text-green-600'
                      : ratios.profitability.roic != null && ratios.profitability.incremental_roic < ratios.profitability.roic * 0.5
                      ? 'text-red-600'
                      : 'text-amber-600'
                  }>
                    {formatPercent(ratios.profitability.incremental_roic)}
                  </span>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Liquidity & Solvency */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">Liquidity</h3>
        <table className="w-full">
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Current Ratio<GlossaryRef id="current-ratio" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.liquidity.current_ratio)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Quick Ratio<GlossaryRef id="quick-ratio" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.liquidity.quick_ratio)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Debt/Equity<GlossaryRef id="debt-to-equity" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.liquidity.debt_to_equity)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Efficiency */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-teal-600 mb-4">Efficiency</h3>
        <table className="w-full">
          <tbody>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Asset Turnover<GlossaryRef id="asset-turnover" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.efficiency.asset_turnover)}</td>
            </tr>
            <tr className="border-b border-gray-100">
              <td className="py-2 text-sm text-gray-500">Inventory Turnover<GlossaryRef id="inventory-turnover" /></td>
              <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.efficiency.inventory_turnover)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Risk Metrics (institutional-grade) */}
      {ratios.risk && (ratios.risk.altman_z_score != null || ratios.risk.beneish_m_score != null || ratios.risk.accrual_ratio != null) && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-600 mb-4">Risk Analysis</h3>
          <table className="w-full">
            <tbody>
              {ratios.risk.altman_z_score != null && (
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-sm text-gray-500">Altman Z-Score<GlossaryRef id="altman-z-score" /></td>
                  <td className="py-2 text-sm font-mono font-medium text-right">
                    <span className={
                      ratios.risk.z_score_zone === 'safe' ? 'text-green-600' :
                      ratios.risk.z_score_zone === 'distress' ? 'text-red-600' :
                      'text-amber-600'
                    }>
                      {formatNumber(ratios.risk.altman_z_score)}
                    </span>
                  </td>
                </tr>
              )}
              {ratios.risk.beneish_m_score != null && (
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-sm text-gray-500">Beneish M-Score<GlossaryRef id="beneish-m-score" /></td>
                  <td className="py-2 text-sm font-mono font-medium text-right">
                    <span className={ratios.risk.m_score_zone === 'high_risk' ? 'text-red-600' : 'text-green-600'}>
                      {formatNumber(ratios.risk.beneish_m_score)}
                    </span>
                  </td>
                </tr>
              )}
              {ratios.risk.accrual_ratio != null && (
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-sm text-gray-500">Accrual Ratio<GlossaryRef id="accrual-ratio" /></td>
                  <td className="py-2 text-sm font-mono font-medium text-right">
                    <span className={
                      ratios.risk.accrual_quality === 'good' ? 'text-green-600' :
                      ratios.risk.accrual_quality === 'warning' ? 'text-red-600' :
                      'text-amber-600'
                    }>
                      {formatPercent(ratios.risk.accrual_ratio)}
                    </span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* SBC Analysis */}
      {ratios.sbc && ratios.sbc.sbc_percent_revenue != null && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-purple-600 mb-4">Stock-Based Comp</h3>
          <table className="w-full">
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-2 text-sm text-gray-500">SBC % Revenue<GlossaryRef id="sbc-percent-revenue" /></td>
                <td className="py-2 text-sm font-mono font-medium text-right">
                  <span className={
                    ratios.sbc.sbc_level === 'high' ? 'text-red-600' :
                    ratios.sbc.sbc_level === 'elevated' ? 'text-amber-600' :
                    'text-green-600'
                  }>
                    {formatPercent(ratios.sbc.sbc_percent_revenue)}
                  </span>
                </td>
              </tr>
              {ratios.sbc.fcf_adjusted != null && (
                <tr className="border-b border-gray-100">
                  <td className="py-2 text-sm text-gray-500">FCF (SBC-adj)<GlossaryRef id="fcf-adjusted" /></td>
                  <td className="py-2 text-sm font-mono font-medium text-right">{formatNumber(ratios.sbc.fcf_adjusted / 1e9, 1)}B</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

