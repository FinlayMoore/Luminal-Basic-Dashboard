import os
import sys
import webbrowser
from pathlib import Path

from Prototype import SpendingAnalyzer


def format_currency(v):
    try:
        return f"${v:,.2f}"
    except Exception:
        return str(v)


def build_html(dashboard):
    summary = dashboard['summary']
    incoming = dashboard['incoming_money']
    recurring = dashboard['recurring_payments']
    cuts = dashboard['spending_cuts']
    questionable = dashboard['top_questionable_spending']
    tx = dashboard['transaction_ratings']
    investment = dashboard['investment_projection']

    html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Personal Finance Dashboard</title>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body { font-family: Inter, system-ui, -apple-system, sans-serif; background: #f8f9fa; padding: 20px 0; }
        .header { background: white; padding: 30px; margin-bottom: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .header h1 { font-size: 2.5rem; font-weight: 700; margin: 0; color: #1f2937; }
        .header p { margin: 5px 0 0 0; color: #6b7280; font-size: 1rem; }
        .card { border: none; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .card-title { font-weight: 700; color: #1f2937; margin-bottom: 15px; }
        .metric { padding: 15px 0; border-bottom: 1px solid #e5e7eb; }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #6b7280; font-size: 0.9rem; margin-bottom: 5px; }
        .metric-value { font-size: 1.5rem; font-weight: 700; color: #111827; }
        .table { margin-bottom: 0; }
        .table th { background: #f3f4f6; font-weight: 600; color: #1f2937; border: none; }
        .table td { padding: 12px; color: #374151; }
        .table tbody tr:hover { background: #fafbfc; }
        .badge-essential { background: #dcfce7; color: #166534; }
        .badge-important { background: #fef3c7; color: #92400e; }
        .badge-discretionary { background: #fecaca; color: #7f1d1d; }
        .recommended-cut { background: #fef2f2; padding: 15px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #ef4444; }
        .recommended-cut-title { font-weight: 600; color: #1f2937; margin-bottom: 5px; }
        .recommended-cut-amount { color: #ef4444; font-weight: 700; }
        .recommended-cut-reason { color: #6b7280; font-size: 0.9rem; margin-top: 5px; }
        .section-title { font-size: 1.3rem; font-weight: 700; color: #1f2937; margin-top: 30px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e5e7eb; }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>💰 Personal Finance Dashboard</h1>
        <p>Your spending summary and recommendations</p>
      </div>

      <div class="container">
        <!-- Summary Cards -->
        <div class="row mb-4">
          <div class="col-md-3">
            <div class="card p-4">
              <div class="metric">
                <div class="metric-label">Total Income</div>
                <div class="metric-value">""" + format_currency(summary['total_income']) + """</div>
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card p-4">
              <div class="metric">
                <div class="metric-label">Total Spent</div>
                <div class="metric-value" style="color: #dc2626;">""" + format_currency(summary['total_spent']) + """</div>
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card p-4">
              <div class="metric">
                <div class="metric-label">Net Balance</div>
                <div class="metric-value" style="color: """ + ('#16a34a' if summary['net_balance'] >= 0 else '#dc2626') + """;">""" + format_currency(summary['net_balance']) + """</div>
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="card p-4">
              <div class="metric">
                <div class="metric-label">Transactions</div>
                <div class="metric-value">""" + str(summary['transaction_count']) + """</div>
              </div>
            </div>
          </div>
        </div>

        <h3 class="section-title">📊 Incoming Money</h3>
        <div class="row mb-4">
          <div class="col-md-6">
            <div class="card p-4">
              <div class="metric">
                <div class="metric-label">Predicted Monthly Income</div>
                <div class="metric-value">""" + format_currency(incoming['predicted_monthly_income']) + """</div>
              </div>
              <div class="metric">
                <div class="metric-label">Income Transactions</div>
                <div class="metric-value">""" + str(incoming['transaction_count']) + """</div>
              </div>
            </div>
          </div>
        </div>

        <h3 class="section-title">🔁 Recurring Payments</h3>
        <div class="card p-4">
          <table class="table">
            <thead>
              <tr>
                <th>Description</th>
                <th class="text-end">Avg Amount</th>
                <th class="text-end">Count</th>
              </tr>
            </thead>
            <tbody>
    """

    for r in recurring[:10]:
        html += f"""
              <tr>
                <td>{r['description'].title()}</td>
                <td class="text-end">{format_currency(abs(r['average_amount']))}</td>
                <td class="text-end">{r['count']}</td>
              </tr>
        """

    total_recurring = sum(abs(r['average_amount']) for r in recurring)
    html += f"""
            </tbody>
          </table>
          <div style="padding-top: 15px; border-top: 1px solid #e5e7eb; font-weight: 600;">
            Total Monthly Recurring: {format_currency(total_recurring)}
          </div>
        </div>

        <h3 class="section-title">✂️ Top Recommended Cuts</h3>
        <div class="row">
    """

    for c in cuts[:6]:
        html += f"""
          <div class="col-md-6 mb-3">
            <div class="recommended-cut">
              <div class="recommended-cut-title">{c['category'].title()}</div>
              <div class="recommended-cut-amount">{format_currency(c['amount'])}</div>
              <div class="recommended-cut-reason">{c['reason']}</div>
            </div>
          </div>
        """

    html += """
        </div>

        <h3 class="section-title">⚠️ Top Questionable Transactions</h3>
        <div class="card p-4">
          <table class="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th class="text-end">Amount</th>
                <th class="text-center">Status</th>
              </tr>
            </thead>
            <tbody>
    """

    for t in questionable[:15]:
        date = str(t['date']).split()[0] if t['date'] is not None else ''
        assessment = t['assessment']
        if assessment == '✓':
            badge = 'badge-essential'
        elif assessment == '→':
            badge = 'badge-important'
        else:
            badge = 'badge-discretionary'
        html += f"""
              <tr>
                <td>{date}</td>
                <td>{t['description']}</td>
                <td class="text-end">{format_currency(t['amount'])}</td>
                <td class="text-center"><span class="badge {badge}">{assessment}</span></td>
              </tr>
        """

    html += """
            </tbody>
          </table>
        </div>

        <h3 class="section-title">⭐ All Transaction Ratings</h3>
        <div class="card p-4">
          <div style="max-height: 400px; overflow-y: auto;">
            <table class="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th class="text-end">Amount</th>
                  <th class="text-end">Necessity</th>
                  <th class="text-center">Rating</th>
                </tr>
              </thead>
              <tbody>
    """

    for t in tx[:50]:
        date = str(t['date']).split()[0] if t['date'] is not None else ''
        assessment = t['assessment']
        if assessment == '✓':
            badge = 'badge-essential'
        elif assessment == '→':
            badge = 'badge-important'
        else:
            badge = 'badge-discretionary'
        html += f"""
                <tr>
                  <td>{date}</td>
                  <td>{t['description']}</td>
                  <td class="text-end">{format_currency(t['amount'])}</td>
                  <td class="text-end">{t['necessity']}</td>
                  <td class="text-center"><span class="badge {badge}">{assessment}</span></td>
                </tr>
        """

    html += """
              </tbody>
            </table>
          </div>
        </div>

        <h3 class="section-title">📈 Investment Projections</h3>
        <div class="card p-4">
          <div style="margin-bottom: 15px;">
            <div class="metric-label">Monthly Savings Potential</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #16a34a;">""" + format_currency(investment['monthly_savings']) + """</div>
            <div style="color: #6b7280; font-size: 0.9rem; margin-top: 5px;">If you implement the recommended spending cuts above</div>
          </div>
          <table class="table" style="margin-top: 20px;">
            <thead>
              <tr>
                <th>Return Rate</th>
                <th class="text-end">1 Year</th>
                <th class="text-end">2 Years</th>
                <th class="text-end">5 Years</th>
              </tr>
            </thead>
            <tbody>
    """

    for scenario in investment['scenarios']:
        rate = scenario['rate']
        proj = scenario['projections']
        html += f"""
              <tr>
                <td><strong>{rate}% annual</strong></td>
                <td class="text-end">{format_currency(proj[1])}</td>
                <td class="text-end">{format_currency(proj[2])}</td>
                <td class="text-end">{format_currency(proj[5])}</td>
              </tr>
        """

    html += """
            </tbody>
          </table>
          <div style="padding-top: 15px; color: #6b7280; font-size: 0.9rem; font-style: italic;">
            💡 Projections assume you invest your monthly savings consistently. Returns are estimated based on historical averages for diversified portfolios.
          </div>
        </div>

        <div style="padding: 30px 0; text-align: center; color: #6b7280; font-size: 0.9rem;">
          Generated locally — your data stays private
        </div>
      </div>
    </body>
    </html>
    """
    return html


def main():
    default_csv = "synthetic_bank_data (1).txt"
    csv_file = sys.argv[1] if len(sys.argv) > 1 else default_csv
    if not os.path.exists(csv_file):
        print(f"CSV not found: {csv_file}")
        sys.exit(1)

    analyzer = SpendingAnalyzer(csv_file)
    dashboard = analyzer.generate_dashboard()
    html = build_html(dashboard)
    out = Path.cwd() / 'dashboard.html'
    out.write_text(html, encoding='utf-8')
    print(f"Wrote {out}")
    webbrowser.open('file://' + str(out))


if __name__ == '__main__':
    main()
