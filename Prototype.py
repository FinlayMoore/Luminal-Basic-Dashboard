import pandas as pd
import json
import os
import sys
from collections import defaultdict
from datetime import datetime


class SpendingAnalyzer:
    def __init__(self, csv_path):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(csv_path)
        self.df = pd.read_csv(csv_path)
        self.warnings = []
        self.rankings = []
        self.recurring_payments = []
        self.transactions_with_ratings = []

        self._clean_and_validate_data()

        self.necessity_scores = {
            'groceries': 0.95,
            'food': 0.95,
            'rent': 0.95,
            'utilities': 0.95,
            'housing': 0.95,
            'healthcare': 0.90,
            'transport': 0.85,
            'transportation': 0.85,
            'insurance': 0.85,
            'education': 0.80,
            'childcare': 0.85,
            'phone': 0.70,
            'internet': 0.75,
            'income': 1.0,
            'salary': 1.0,
            'gym': 0.40,
            'entertainment': 0.30,
            'dining': 0.35,
            'eating out': 0.35,
            'hobbies': 0.25,
            'subscriptions': 0.20,
            'shopping': 0.15,
            'other': 0.50
        }

    def _clean_and_validate_data(self):
        # Dates
        if 'Date' in self.df.columns:
            try:
                self.df['Date'] = pd.to_datetime(self.df['Date'], errors='coerce')
                today = pd.to_datetime(datetime.today())
                future_mask = self.df['Date'] > today
                future_count = future_mask.sum()
                if future_count > 0:
                    self.warnings.append(f"⚠️  Removed {int(future_count)} future-dated transactions")
                self.df = self.df[~future_mask]
            except Exception as e:
                self.warnings.append(f"⚠️  Date parsing error: {e}")

        # Normalize columns
        if 'Amount' in self.df.columns:
            self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce').fillna(0)
        else:
            self.df['Amount'] = 0

        if 'Category' not in self.df.columns:
            self.df['Category'] = 'Other'
        else:
            self.df['Category'] = self.df['Category'].fillna('Other').astype(str)

        if 'Description' not in self.df.columns:
            self.df['Description'] = 'Unknown'
        else:
            self.df['Description'] = self.df['Description'].fillna('Unknown').astype(str)

        # Sanitize descriptions
        self.df['Description'] = self.df['Description'].apply(lambda x: ''.join(c if ord(c) < 128 else '?' for c in str(x)))

        # Income detection and sign correction
        income_keywords = ['salary', 'income', 'bonus', 'refund', 'deposit']
        self.df['IsIncome'] = self.df['Category'].str.lower().str.contains('|'.join(income_keywords), na=False)

        for idx, row in self.df.iterrows():
            if row['IsIncome'] and row['Amount'] < 0:
                self.df.at[idx, 'Amount'] = abs(row['Amount'])
                self.warnings.append(f"ℹ️  Corrected income sign at row {idx}")
            elif not row['IsIncome'] and row['Amount'] > 0:
                if 'refund' not in str(row['Description']).lower():
                    self.df.at[idx, 'Amount'] = -abs(row['Amount'])

        # Outlier detection (flag only)
        expense_df = self.df[self.df['Amount'] < 0]
        if len(expense_df) >= 4:
            q1 = expense_df['Amount'].quantile(0.25)
            q3 = expense_df['Amount'].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            extreme_outliers = expense_df[expense_df['Amount'] < lower_bound]
            if len(extreme_outliers) > 0:
                self.warnings.append(f"⚠️  Found {len(extreme_outliers)} extreme expense outliers")

        # Duplicates
        duplicates = self.df.duplicated(subset=['Date', 'Description', 'Amount'], keep=False)
        if duplicates.sum() > 0:
            self.warnings.append(f"⚠️  Found {int(duplicates.sum())} potential duplicate transactions")

    def get_necessity_score(self, category):
        cat = str(category).lower() if category is not None else 'other'
        return self.necessity_scores.get(cat, 0.50)

    def identify_recurring_payments(self):
        desc_map = defaultdict(list)
        for _, row in self.df.iterrows():
            desc = str(row.get('Description', '')).strip().lower()
            desc_map[desc].append(row)

        recurring = []
        for desc, items in desc_map.items():
            if len(items) >= 2:
                avg = sum(float(i['Amount']) for i in items) / len(items)
                recurring.append({
                    'description': desc,
                    'count': len(items),
                    'average_amount': round(avg, 2),
                    'category': items[0].get('Category', 'Other')
                })
        self.recurring_payments = sorted(recurring, key=lambda x: abs(x['average_amount']), reverse=True)
        return self.recurring_payments

    def predict_incoming_money(self):
        incomes = self.df[self.df['Amount'] > 0]
        if incomes.empty:
            return {'predicted_monthly_income': 0.0, 'transaction_count': 0}
        if 'Date' in self.df.columns:
            try:
                months = incomes['Date'].dt.to_period('M')
                monthly = incomes.groupby(months)['Amount'].sum()
                predicted_monthly = float(monthly.mean())
                transaction_count = len(incomes)
            except Exception:
                predicted_monthly = float(incomes['Amount'].sum())
                transaction_count = len(incomes)
        else:
            predicted_monthly = float(incomes['Amount'].sum())
            transaction_count = len(incomes)
        return {'predicted_monthly_income': round(predicted_monthly, 2), 'transaction_count': transaction_count}

    def rate_transaction_worth(self):
        self.transactions_with_ratings = []
        for _, row in self.df.iterrows():
            amount = float(row.get('Amount', 0))
            category = str(row.get('Category', 'Other'))
            necessity = self.get_necessity_score(category)
            worth_it_rating = abs(amount) * necessity
            waste_potential = abs(amount) * (1 - necessity)
            if necessity >= 0.9:
                assessment = '✓'
            elif necessity >= 0.7:
                assessment = '→'
            elif necessity >= 0.4:
                assessment = '?'
            else:
                assessment = '✗'
            self.transactions_with_ratings.append({
                'date': row.get('Date'),
                'description': row.get('Description'),
                'amount': amount,
                'necessity': round(necessity, 2),
                'worth_it_rating': round(worth_it_rating, 2),
                'waste_potential': round(waste_potential, 2),
                'assessment': assessment
            })
        return self.transactions_with_ratings

    def analyze_spending(self):
        expenses = self.df[self.df['Amount'] < 0].copy()
        if expenses.empty:
            return []
        by_cat = expenses.groupby(expenses['Category'].str.lower())['Amount'].sum()
        suggestions = []
        protected = ['rent', 'housing', 'mortgage']
        for cat, total in by_cat.items():
            total_abs = abs(float(total))
            necessity = self.get_necessity_score(cat)
            potential_cut = total_abs * (1 - necessity)
            if cat in protected and necessity >= 0.9:
                continue
            if potential_cut <= 1:
                continue
            suggestions.append({'category': cat, 'amount': round(total_abs, 2), 'potential_cut': round(potential_cut, 2), 'necessity': necessity})
        suggestions.sort(key=lambda x: x['potential_cut'], reverse=True)
        return suggestions

    def _generate_reason(self, category, amount, necessity):
        if necessity >= 0.9:
            return "High-necessity expense (essential) — not recommended to cut."
        if necessity >= 0.7:
            return "Important but could be reviewed for small savings."
        if necessity >= 0.4:
            return "Moderately necessary — consider trimming recurring or frequency."
        return "Low-necessity discretionary spend — good candidate to cut."

    def get_recommendations(self, top_n=5):
        cuts = self.analyze_spending()
        recs = []
        seen = set()
        for c in cuts:
            cat = c['category']
            if cat in seen:
                continue
            seen.add(cat)
            recs.append({'category': cat, 'amount': c['amount'], 'reason': self._generate_reason(cat, c['amount'], c['necessity'])})
            if len(recs) >= top_n:
                break
        return recs

    def _generate_summary(self):
        total_income = float(self.df[self.df['Amount'] > 0]['Amount'].sum())
        total_spent = float(self.df[self.df['Amount'] < 0]['Amount'].sum())
        net_balance = total_income + total_spent
        return {
            'total_income': round(total_income, 2),
            'total_spent': round(total_spent, 2),
            'net_balance': round(net_balance, 2),
            'transaction_count': len(self.df)
        }

    def generate_dashboard(self):
        summary = self._generate_summary()
        incoming = self.predict_incoming_money()
        recurring = self.identify_recurring_payments()
        self.rate_transaction_worth()
        spending_cuts = self.get_recommendations()
        top_questionable = self._get_top_questionable_transactions()
        investment_proj = self.investment_projection(spending_cuts)
        return {
            'summary': summary,
            'incoming_money': incoming,
            'recurring_payments': recurring,
            'spending_cuts': spending_cuts,
            'top_questionable_spending': top_questionable,
            'transaction_ratings': self.transactions_with_ratings,
            'investment_projection': investment_proj
        }

    

    def _get_top_questionable_transactions(self, top_n=8):
        """Get transactions with lowest worth-it ratings"""
        if not self.transactions_with_ratings:
            self.rate_transaction_worth()

        # Filter out essential/income transactions
        questionable = [t for t in self.transactions_with_ratings if t['necessity'] < 0.70]
        questionable.sort(key=lambda x: x['waste_potential'], reverse=True)

        return questionable[:top_n]

    def investment_projection(self, recommendations):
        """Calculate investment growth if you save money from recommended cuts."""
        monthly_savings = sum(c.get('amount', 0) for c in recommendations) / 12.0  # annualize to monthly
        
        scenarios = []
        for rate_pct in [5, 7, 10]:
            rate = rate_pct / 100.0
            monthly_rate = rate / 12.0
            
            projections = {}
            for years in [1, 2, 5]:
                months = years * 12
                # Future Value of Annuity: FV = PMT * [((1 + r)^n - 1) / r]
                fv = monthly_savings * (((1 + monthly_rate) ** months - 1) / monthly_rate)
                projections[years] = round(fv, 2)
            
            scenarios.append({
                'rate': rate_pct,
                'projections': projections
            })
        
        return {
            'monthly_savings': round(monthly_savings, 2),
            'scenarios': scenarios
        }

# Example usage
if __name__ == "__main__":
    # Determine CSV path from first CLI arg or use default placeholder
    default_csv = "synthetic_bank_data (1).txt"
    csv_file = sys.argv[1] if len(sys.argv) > 1 else default_csv

    # Friendly error if file missing
    if not os.path.exists(csv_file):
        print(f"\nError: CSV file not found: {csv_file}")
        print("Place your CSV in the repository root or pass the path as the first argument:")
        print("  python Prototype.py \"path/to/your.csv\"")
        sys.exit(1)

    # Initialize the analyzer
    analyzer = SpendingAnalyzer(csv_file)

    # Show any data warnings
    if analyzer.warnings:
        print("\n" + "="*80)
        print("⚠️  DATA QUALITY ALERTS".center(80))
        print("="*80)
        for warning in analyzer.warnings:
            print(f"  {warning}")

    # Generate comprehensive dashboard
    dashboard = analyzer.generate_dashboard()

    print("\n" + "="*80)
    print("💰 PERSONAL FINANCE DASHBOARD 💰".center(80))
    print("="*80 + "\n")

    # Summary Section
    print("📊 FINANCIAL SUMMARY")
    print("-" * 80)
    summary = dashboard['summary']
    print(f"  Total Income:        ${summary['total_income']:>10.2f}")
    print(f"  Total Spent:         ${summary['total_spent']:>10.2f}")
    print(f"  Net Balance:         ${summary['net_balance']:>10.2f}")
    print(f"  Transactions:        {summary['transaction_count']:>10}")

    # Incoming Money Section
    print("\n💵 INCOMING MONEY PREDICTIONS")
    print("-" * 80)
    income = dashboard['incoming_money']
    print(f"  Predicted Monthly:   ${income['predicted_monthly_income']:>10.2f}")
    print(f"  Transactions:        {income['transaction_count']:>10}")

    # Recurring Payments Section
    print("\n🔁 RECURRING PAYMENTS (Subscriptions, Rent, etc.)")
    print("-" * 80)
    for i, payment in enumerate(dashboard['recurring_payments'][:5], 1):
        print(f"  {i}. {payment['description'].title():<40} ${payment['average_amount']:>8.2f}/month")

    monthly_recurring = sum(p['average_amount'] for p in dashboard['recurring_payments'])
    print(f"\n  Total Recurring:     ${monthly_recurring:>10.2f}/month")

    # Spending Cuts Section
    print("\n✂️  TOP 5 RECOMMENDED SPENDING CUTS")
    print("-" * 80)
    for i, cut in enumerate(dashboard['spending_cuts'], 1):
        print(f"  {i}. {cut['category'].title():<30} ${cut['amount']:>8}")
        print(f"     → {cut['reason']}")

    # Optionally call AI for justifications if user requested --ai
    # AI justification removed — simple dashboard only

    # Questionable Spending Section
    print("\n⚠️  TOP QUESTIONABLE TRANSACTIONS (Low Worth-It Rating)")
    print("-" * 80)
    print(f"  {'Date':<12} {'Description':<30} {'Amount':>10} {'Rating':>8} {'Status':<15}")
    print("  " + "-" * 76)
    for txn in dashboard['top_questionable_spending'][:8]:
        print(f"  {str(txn['date']):<12} {txn['description'][:28]:<30} ${txn['amount']:>9.2f} {txn['worth_it_rating']:>7.2f} {txn['assessment']:<15}")

    # Transaction Ratings Detail
    print("\n⭐ TRANSACTION RATINGS (Worth-It Score = Amount × Necessity)")
    print("-" * 80)
    print(f"  {'Date':<12} {'Description':<25} {'Amount':>10} {'Necessity':>10} {'Rating':>10} {'Status':<12}")
    print("  " + "-" * 76)
    for txn in dashboard['transaction_ratings'][:15]:
        print(f"  {str(txn['date']):<12} {txn['description'][:23]:<25} ${txn['amount']:>9.2f} {txn['necessity']:>9.2f} {txn['worth_it_rating']:>9.2f} {txn['assessment']:<12}")

    print("\n" + "="*80)
    print("LEGEND: ✓ Essential | → Important | ? Discretionary | ✗ Could Cut".center(80))
    print("="*80 + "\n")



