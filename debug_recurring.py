from Prototype import SpendingAnalyzer
import json
an = SpendingAnalyzer('synthetic_bank_data (1).txt')
d = an.generate_dashboard()
rec = d['recurring_payments']
print('RECURRING_COUNT=', len(rec))
print(json.dumps(rec[:12], indent=2))
labels = [r['description'].title() for r in rec[:8]]
vals = [abs(r['average_amount']) for r in rec[:8]]
print('LABELS_JSON=', json.dumps(labels))
print('VALUES_JSON=', json.dumps(vals))
