import requests, re, csv
url = "https://support.google.com/analytics/topic/9143232?hl=zh-Hans"
html = requests.get(url).text
qa = re.findall(r'<a[^>]*>([^<]+)</a>.*?<div[^>]*>([^<]+)</div>', html, flags=re.S)

with open('ga_qa.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['问题', '答案', '来源链接'])
    for q, a in qa:
        writer.writerow([q.strip(), a.strip(), url])