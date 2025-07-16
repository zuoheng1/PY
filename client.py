import requests

def get_access_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('tenant_access_token')
    else:
        raise Exception(f"Failed to get access token. Status Code: {response.status_code}, Response: {response.text}")

# 替换为你的 app_id 和 app_secret
app_id = "cli_a702c225665e100d"
app_secret = "5D7PoQaMtb8Er1qqfUnGpfcYiFekaX2b"

try:
    access_token = get_access_token(app_id, app_secret)
    print('access_token:', access_token)
except Exception as e:
    print(e)