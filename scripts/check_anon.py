import json
import urllib.request

r = urllib.request.urlopen("http://127.0.0.1:8800/patients?agent=pharmacy")
data = json.loads(r.read())
for p in data[:5]:
    print(f'{p["patient_id"]}: {p["name"]} | {p["diagnosis"]}')
print(f"\nTotal pharmacy-compatible: {len(data)}")
print(f"All anonymized: {all(len(p['name']) <= 3 and '*' in p['name'] for p in data)}")
