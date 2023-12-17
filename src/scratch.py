from urllib.parse import parse_qs
from urllib.parse import urlparse

url = "https://www.example.com/redirect?connectionArn=blah&referenceType=COMMIT&FullRepositoryId=hmrc/telemetry-terraform&Commit=a9e1670"
parsed_url = urlparse(url)
captured_value = parse_qs(parsed_url.query)["FullRepositoryId"][0]

print(captured_value)
