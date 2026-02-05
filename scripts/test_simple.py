import requests
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

url = "https://www.binance.tr/open/v1/common/symbols"

print("1. Default requests (verify=False)")
try:
    resp = requests.get(url, verify=False)
    print(resp.json().get('code'))
except Exception as e:
    print(e)

print("\n2. With User-Agent (verify=False)")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
try:
    resp = requests.get(url, headers=headers, verify=False)
    print(resp.json().get('code'))
except Exception as e:
    print(e)

print("4. Default requests (verify=True)")
try:
    resp = requests.get(url, verify=True)
    print(resp.json().get('code'))
except Exception as e:
    print(e)

print("\n5. urllib.request")
import urllib.request
import ssl
import json
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req, context=ctx) as f:
        print(json.load(f).get('code'))
except Exception as e:
    print(e)
