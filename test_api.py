import requests

try:
    response = requests.get('http://localhost:5000/api/vulnerabilities', timeout=5)
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print(f'Total vulnerabilities: {data.get("total", 0)}')
        vulns = data.get('vulnerabilities', [])
        if vulns:
            print(f'\nFirst vulnerability:')
            v = vulns[0]
            print(f'  Host: {v.get("host")}')
            print(f'  CVE: {v.get("cve_id")}')
            print(f'  Severity: {v.get("severity")}')
        else:
            print('No vulnerabilities in response')
    else:
        print(f'Error: {response.text}')
        
except Exception as e:
    print(f'Connection error: {e}')
    print('Make sure Flask app is running: python app.py --web')
