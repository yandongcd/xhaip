import json
import urllib.request

r = urllib.request.urlopen('http://127.0.0.1:8800/agents')
data = json.loads(r.read())
print(f'Agents: {len(data)}')
for a in data[:5]:
    print(f'  {a["name"]}: {len(a["tools"])} tools')

# Test a call
req = urllib.request.Request('http://127.0.0.1:8800/call',
    data=json.dumps({"agent":"pharmacy","tool":"assess_nutrition",
                     "params":{"patient_id":"P001","weight_kg":55,"height_cm":170,
                               "lab_results":{"albumin":28,"crp":80},"age":78}}).encode(),
    headers={'Content-Type':'application/json'})
r2 = urllib.request.urlopen(req)
resp = json.loads(r2.read())
print(f'\nCall result: risk_level={resp.get("risk_level")}, nrs_score={resp.get("nrs_score")}')
