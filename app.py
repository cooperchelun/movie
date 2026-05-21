from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

@app.route("/")
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
@app.route("/rate")
    def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text[5:]
    print(lastUpdate)
    print()

    result=sp.select(".filmList")

    for x in result:
        title = x.find("a").text
        introduce = x.find("p").text

        movie_id = x.find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = x.find(class_="runtime").text

        t1 = t.find("片長")
        t2 = t.find("分")
        showLength = t[t1+3:t2]

        t1 = t.find("上映日期")
        t2 = t.find("上映廳數")
        showDate = t[t1+5:t2-8]

        doc = {
            "title": title,
            "introduce": introduce,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": int(showLength),
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("本週新片含分級").document(movie_id)
        doc_ref.set(doc)
    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate

@app.route("/movie")
def movie():
    """爬取開眼電影網近期上映電影，直接顯示在網頁上（含海報）"""
    
    url = "https://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    # 取得網站最後更新時間
    last_update_tag = sp.find("div", class_="smaller09")
    lastUpdate = last_update_tag.text[5:] if last_update_tag else "未知"

    # 開始產生 HTML 結果
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>近期上映電影</title>
        <style>
            body {{
                font-family: 'Microsoft JhengHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px;
                margin: 0;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
            }}
            h1 {{
                color: white;
                text-align: center;
                margin-bottom: 10px;
            }}
            .update-info {{
                color: white;
                text-align: center;
                margin-bottom: 30px;
                opacity: 0.9;
            }}
            .movie-card {{
                background: white;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                display: flex;
                gap: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .movie-pic img {{
                width: 120px;
                border-radius: 10px;
                object-fit: cover;
            }}
            .movie-info {{
                flex: 1;
            }}
            .movie-title {{
                color: #667eea;
                margin-top: 0;
                margin-bottom: 10px;
            }}
            .movie-detail {{
                color: #555;
                margin: 8px 0;
            }}
            .movie-link a {{
                color: #ff6b6b;
                text-decoration: none;
            }}
            .back-link {{
                display: inline-block;
                margin: 20px 10px;
                padding: 10px 20px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 50px;
            }}
            .footer {{
                text-align: center;
            }}
            .search-box {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .search-box input {{
                padding: 12px;
                width: 250px;
                font-size: 16px;
                border: none;
                border-radius: 50px 0 0 50px;
                outline: none;
            }}
            .search-box button {{
                padding: 12px 20px;
                font-size: 16px;
                background: #ff6b6b;
                color: white;
                border: none;
                border-radius: 0 50px 50px 0;
                cursor: pointer;
            }}
            .search-box button:hover {{
                background: #ee5a52;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 近期上映電影</h1>
            <div class="update-info">📅 最後更新時間：{lastUpdate}</div>
            
            <div class="search-box">
                <form method="get" action="/search" style="display: inline-block;">
                    <input type="text" name="keyword" placeholder="輸入電影名稱關鍵字" required>
                    <button type="submit">🔍 搜尋</button>
                </form>
            </div>
    """

    for item in result:
        # 1. 抓取海報圖片
        img_tag = item.find("img")
        picture = img_tag.get("src") if img_tag else ""
        if picture and not picture.startswith("http"):
            picture = "http://www.atmovies.com.tw" + picture
        
        # 2. 抓取電影名稱與介紹頁連結
        title_tag = item.find("div", class_="filmtitle")
        title = title_tag.text if title_tag else "未知"
        a_tag = title_tag.find("a") if title_tag else None
        hyperlink = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
        
        # 3. 抓取上映日期與片長
        runtime_tag = item.find("div", class_="runtime")
        showDate = "未知"
        showLength = "未知"
        if runtime_tag:
            raw_text = runtime_tag.text
            clean_text = raw_text.replace("上映日期：", "").replace("片長：", "").replace("分", "")
            if len(clean_text) >= 10:
                showDate = clean_text[0:10]
            if len(clean_text) > 13:
                showLength = clean_text[13:]

        html += f"""
            <div class="movie-card">
                <div class="movie-pic">
                    <img src="{picture}" alt="{title}">
                </div>
                <div class="movie-info">
                    <h2 class="movie-title">🎬 {title}</h2>
                    <p class="movie-detail">📅 上映日期：{showDate}</p>
                    <p class="movie-detail">⏱️ 片長：{showLength} 分鐘</p>
                    <p class="movie-link">🔗 <a href="{hyperlink}" target="_blank">點我看詳細介紹</a></p>
                </div>
            </div>
        """

    html += """
            <div class="footer">
                <a href="/" class="back-link">🏠 回首頁</a>
                <a href="/vscinemas" class="back-link">🎬 威秀影城</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@app.route("/search")
def search():
    """搜尋電影（即時從網站爬取並過濾）"""
    
    keyword = request.args.get("keyword", "")
    
    if not keyword:
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>搜尋電影</title>
        <style>
            body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; margin: 0; }
            .box { background: white; border-radius: 20px; padding: 40px; text-align: center; }
            input { padding: 10px; width: 200px; }
            button { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; }
            a { color: #667eea; }
        </style>
        </head>
        <body>
            <div class="box">
                <h2>🔍 請輸入電影關鍵字</h2>
                <form method="get" action="/search">
                    <input type="text" name="keyword" placeholder="例如：蜘蛛人" required>
                    <button type="submit">搜尋</button>
                </form>
                <br><a href="/">回首頁</a>
            </div>
        </body>
        </html>
        """
    
    # 即時爬蟲
    url = "https://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>搜尋結果：{keyword}</title>
        <style>
            body {{
                font-family: 'Microsoft JhengHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px;
                margin: 0;
            }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ color: white; text-align: center; }}
            .result-card {{
                background: white;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                display: flex;
                gap: 20px;
            }}
            .result-pic img {{ width: 100px; border-radius: 10px; }}
            .result-info {{ flex: 1; }}
            .movie-title {{ color: #667eea; margin: 0 0 10px 0; }}
            .movie-detail {{ color: #555; margin: 5px 0; }}
            .back-link {{
                display: inline-block;
                margin: 20px 10px;
                padding: 10px 20px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 50px;
            }}
            .footer {{ text-align: center; }}
            .no-result {{ background: white; border-radius: 15px; padding: 40px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 搜尋「{keyword}」的結果</h1>
    """
    
    found = False
    for item in result:
        # 抓取電影名稱
        title_tag = item.find("div", class_="filmtitle")
        title = title_tag.text if title_tag else ""
        
        if keyword in title:
            found = True
            
            # 海報圖片
            img_tag = item.find("img")
            picture = img_tag.get("src") if img_tag else ""
            if picture and not picture.startswith("http"):
                picture = "http://www.atmovies.com.tw" + picture
            
            # 介紹頁連結
            a_tag = title_tag.find("a") if title_tag else None
            hyperlink = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
            
            # 上映日期與片長
            runtime_tag = item.find("div", class_="runtime")
            showDate = "未知"
            showLength = "未知"
            if runtime_tag:
                raw_text = runtime_tag.text
                clean_text = raw_text.replace("上映日期：", "").replace("片長：", "").replace("分", "")
                if len(clean_text) >= 10:
                    showDate = clean_text[0:10]
                if len(clean_text) > 13:
                    showLength = clean_text[13:]
            
            html += f"""
            <div class="result-card">
                <div class="result-pic">
                    <img src="{picture}" alt="{title}">
                </div>
                <div class="result-info">
                    <h2 class="movie-title">🎬 {title}</h2>
                    <p class="movie-detail">📅 上映日期：{showDate}</p>
                    <p class="movie-detail">⏱️ 片長：{showLength} 分鐘</p>
                    <p class="movie-detail">🔗 <a href="{hyperlink}" target="_blank">詳細介紹</a></p>
                </div>
            </div>
            """
    
    if not found:
        html += f"""
            <div class="no-result">
                <h2>❌ 找不到包含「{keyword}」的電影</h2>
                <p>請嘗試其他關鍵字</p>
            </div>
        """
    
    html += """
            <div class="footer">
                <a href="/" class="back-link">🏠 回首頁</a>
                <a href="/movie" class="back-link">🎬 看全部電影</a>
                <a href="/vscinemas" class="back-link">🎬 威秀影城</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# ================= 新增：威秀影城爬蟲 =================
@app.route("/vscinemas")
def vscinemas():
    """爬取威秀影城即將上映電影"""
    url = "https://www.vscinemas.com.tw/film/coming.aspx"
    try:
        # 發送請求，加上 headers 模仿瀏覽器，避免被拒絕
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, verify=False)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 找尋所有電影項目 - 根據威秀影城實際網頁結構調整
        # 方法1: 尋找所有包含電影資訊的 <a> 標籤，這些連結通常指向電影詳細頁面
        movies = []
        
        # 尋找所有連結中包含 '/film/' 的 <a> 標籤，這些通常是電影頁面
        all_links = soup.find_all('a', href=True)
        film_links = [link for link in all_links if '/film/' in link['href'] and link.get_text(strip=True)]
        
        for link in film_links:
            title = link.get_text(strip=True)
            # 過濾掉太短的標題或像是 "更多"、"詳細" 之類的文字
            if title and len(title) >= 2 and title not in ['更多', '詳細', 'more', 'detail']:
                href = link['href']
                if not href.startswith('http'):
                    href = 'https://www.vscinemas.com.tw' + href
                
                # 避免重複加入相同的電影
                if not any(m['title'] == title for m in movies):
                    movies.append({
                        'title': title,
                        'link': href
                    })
        
        # 如果上面的方法沒找到，嘗試另一種選擇器
        if not movies:
            # 備案：尋找 class 包含 'movie' 或 'film' 的區塊
            movie_blocks = soup.select('.movieItem, .filmItem, .movie_list_item, .coming_item')
            for block in movie_blocks:
                title_tag = block.find('a')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if title and len(title) >= 2:
                        href = title_tag.get('href', '')
                        if href:
                            if not href.startswith('http'):
                                href = 'https://www.vscinemas.com.tw' + href
                            movies.append({
                                'title': title,
                                'link': href
                            })
        
        # 開始產生 HTML 結果
        html = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>威秀影城 - 即將上映</title>
            <style>
                body {
                    font-family: 'Microsoft JhengHei', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 40px;
                    margin: 0;
                }
                .container {
                    max-width: 900px;
                    margin: 0 auto;
                }
                h1 {
                    color: white;
                    text-align: center;
                    margin-bottom: 10px;
                }
                .update-info {
                    color: white;
                    text-align: center;
                    margin-bottom: 30px;
                    opacity: 0.9;
                }
                .movie-card {
                    background: white;
                    border-radius: 15px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }
                .movie-info {
                    flex: 1;
                }
                .movie-title {
                    color: #667eea;
                    margin-top: 0;
                    margin-bottom: 10px;
                }
                .movie-detail {
                    color: #555;
                    margin: 8px 0;
                }
                .movie-link a {
                    color: #ff6b6b;
                    text-decoration: none;
                }
                .back-link {
                    display: inline-block;
                    margin: 20px 10px;
                    padding: 10px 20px;
                    background: white;
                    color: #667eea;
                    text-decoration: none;
                    border-radius: 50px;
                }
                .footer {
                    text-align: center;
                }
                .movie-count {
                    color: white;
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 1.1em;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎬 威秀影城 - 即將上映電影</h1>
                <div class="update-info">📅 資料來源：威秀影城官方網站 | 即時爬取</div>
                <div class="movie-count">📊 共找到 {} 部電影</div>
        """.format(len(movies))
        
        if not movies:
            html += '<div class="movie-card" style="text-align:center;"><p>⚠️ 目前無法獲取電影資料</p><p>可能原因：網站結構更新或連線問題</p><p>建議：<br>1. 檢查網路連線<br>2. 稍後再試<br>3. 聯繫開發者更新爬蟲程式</p></div>'
        else:
            for movie in movies:
                html += f"""
                <div class="movie-card">
                    <div class="movie-info">
                        <h2 class="movie-title">🎬 {movie['title']}</h2>
                        <p class="movie-link">🔗 <a href="{movie['link']}" target="_blank">點我看詳細介紹</a></p>
                    </div>
                </div>
                """
        
        html += """
                <div class="footer">
                    <a href="/" class="back-link">🏠 回首頁</a>
                    <a href="/movie" class="back-link">🎬 開眼電影網</a>
                </div>
            </div>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        # 發生錯誤時顯示錯誤訊息
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>爬蟲錯誤</title>
            <style>
                body {{
                    font-family: 'Microsoft JhengHei', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin: 0;
                    padding: 20px;
                }}
                .error-box {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    max-width: 500px;
                }}
                h1 {{ color: #ff6b6b; }}
                .back-link {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 50px;
                }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>⚠️ 爬蟲發生錯誤</h1>
                <p>錯誤訊息：{str(e)}</p>
                <p>可能原因：<br>
                - 網站暫時無法連線<br>
                - 網站結構已更新<br>
                - 網路連線問題</p>
                <a href="/" class="back-link">🏠 回首頁</a>
            </div>
        </body>
        </html>
        """
# ================= 威秀影城爬蟲結束 =================


if __name__ == "__main__":
    app.run(debug=True)
