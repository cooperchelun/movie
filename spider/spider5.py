import requests
from bs4 import BeautifulSoup

url = "https://www1.pu.edu.tw/~s1131215/index.php"
Data = requests.get(url)
Data.encoding = "utf-8"
#print(Data.text)
sp = BeautifulSoup(Data.text, "html.parser")
result=sp.find(id="h2text")

print(result)
