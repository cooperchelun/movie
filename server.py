#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import urllib.parse
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class MovieHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_html()
        elif parsed_path.path == '/search':
            self.search_movie(parsed_path)
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/spider':
            self.spider_movie()
        else:
            self.send_error(404)
    
    def serve_html(self):
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                html = f.read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
    
    def search_movie(self, parsed_path):
        query = parse_qs(parsed_path.query)
        keyword = query.get('keyword', [''])[0]
        
        if not keyword:
            self.send_json_response({'error': '請提供關鍵字'}, 400)
            return
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, poster, detail_url, release_date
            FROM movies
            WHERE title LIKE ?
            ORDER BY release_date DESC
        ''', (f'%{keyword}%',))
        
        rows = cursor.fetchall()
        conn.close()
        
        movies = []
        for row in rows:
            movies.append({
                'id': row[0],
                'title': row[1],
                'poster': row[2] or '',
                'detail_url': row[3] or '',
                'release_date': row[4] or ''
            })
        
        self.send_json_response({
            'success': True,
            'keyword': keyword,
            'total': len(movies),
            'movies': movies
        })
    
    def spider_movie(self):
        try:
            # 爬取即將上映電影
            movies_data = self.fetch_upcoming_movies()
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 建立表格
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL UNIQUE,
                    poster TEXT,
                    detail_url TEXT,
                    release_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入或更新資料
            for movie in movies_data:
                try:
                    cursor.execute('''
                        INSERT INTO movies (title, poster, detail_url, release_date)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(title) DO UPDATE SET
                            poster = excluded.poster,
                            detail_url = excluded.detail_url,
                            release_date = excluded.release_date
                    ''', (movie['title'], movie['poster'], movie['detail_url'], movie['release_date']))
                except Exception as e:
                    print(f"插入錯誤 {movie['title']}: {e}")
            
            conn.commit()
            
            # 取得電影總數
            cursor.execute('SELECT COUNT(*) FROM movies')
            movie_count = cursor.fetchone()[0]
            conn.close()
            
            last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.send_json_response({
                'success': True,
                'lastUpdated': last_updated,
                'movieCount': movie_count,
                'message': f'成功爬取並儲存 {len(movies_data)} 部電影'
            })
            
        except Exception as e:
            self.send_json_response({'error': f'爬蟲失敗: {str(e)}'}, 500)
    
    def fetch_upcoming_movies(self):
        """從威秀影城網站爬取即將上映電影"""
        print("🕷️ 開始爬取威秀影城即將上映電影...")
        movies = []
        
        try:
            url = 'https://www.vscinemas.com.tw/film/coming.aspx'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"❌ 網頁請求失敗，狀態碼: {response.status_code}")
                return self.get_sample_movies()
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 方法1: 查找所有可能的電影項目
            movie_items = soup.find_all('div', class_=re.compile(r'film|movie|item', re.I))
            if not movie_items:
                movie_items = soup.find_all('li', class_=re.compile(r'film|movie|item', re.I))
            
            # 方法2: 從常見標籤中提取片名
            if not movie_items:
                potential_titles = soup.find_all(['a', 'h3', 'div', 'p'], string=re.compile(r'[\u4e00-\u9fff]+'))
                for tag in potential_titles:
                    title = tag.get_text().strip()
                    if title and len(title) > 1 and not any(x in title for x in ['首頁', '即將', '影城', '專線', '服務', 'LIVE', '數位']):
                        movie_data = {
                            'title': title,
                            'poster': '',
                            'detail_url': '',
                            'release_date': ''
                        }
                        if movie_data not in movies:
                            movies.append(movie_data)
            
            # 方法3: 直接從網頁文本提取 (較粗略)
            if len(movies) < 5:
                text = soup.get_text()
                title_pattern = r'([\u4e00-\u9fff]+(?:[\u4e00-\u9fff0-9a-zA-Z\s·:：]+)?)'
                found_titles = re.findall(title_pattern, text)
                for title in found_titles:
                    title = title.strip()
                    if (len(title) > 2 and len(title) < 50 and 
                        not any(x in title for x in ['首頁', '即將上映', '威秀', '影城', '電話', '專線', '服務', 
                                                      '請選擇', 'LOADING', 'LIVE', '數位', '很抱歉', '您的瀏覽器',
                                                      '下載最新版', '如果您是'])):
                        movie_data = {
                            'title': title,
                            'poster': '',
                            'detail_url': '',
                            'release_date': ''
                        }
                        if movie_data not in movies:
                            movies.append(movie_data)
            
            # 去重
            unique_movies = {m['title']: m for m in movies}.values()
            movies = list(unique_movies)[:30]
            
            if movies:
                print(f"✅ 成功爬取到 {len(movies)} 部威秀影城即將上映電影")
                for i, movie in enumerate(movies[:8], 1):
                    print(f"   {i}. {movie['title']}")
                if len(movies) > 8:
                    print(f"   ... 共 {len(movies)} 部")
            else:
                print("⚠️ 未爬取到電影資料，使用示例數據")
                return self.get_sample_movies()
                
        except Exception as e:
            print(f"❌ 爬蟲發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return self.get_sample_movies()
        
        # 為電影補充資訊
        for idx, movie in enumerate(movies):
            if not movie['detail_url']:
                encoded_title = urllib.parse.quote(movie['title'])
                movie['detail_url'] = f"https://www.google.com/search?q={encoded_title}+電影+威秀"
            if not movie['release_date']:
                movie['release_date'] = "即將上映"
            if not movie['poster']:
                movie['poster'] = "https://via.placeholder.com/200x300?text=No+Poster"
        
        return movies
    
    def get_sample_movies(self):
        """備用示例電影數據"""
        print("📋 使用備用示例電影數據")
        return [
            {
                'title': '超人再起',
                'poster': 'https://via.placeholder.com/200x300?text=超人再起',
                'detail_url': 'https://www.vscinemas.com.tw/film/detail.aspx',
                'release_date': '即將上映'
            },
            {
                'title': '曼達洛人與古古',
                'poster': 'https://via.placeholder.com/200x300?text=曼達洛人與古古',
                'detail_url': 'https://www.vscinemas.com.tw/film/detail.aspx',
                'release_date': '即將上映'
            },
            {
                'title': '後室',
                'poster': 'https://via.placeholder.com/200x300?text=後室',
                'detail_url': 'https://www.vscinemas.com.tw/film/detail.aspx',
                'release_date': '即將上映'
            },
            {
                'title': '真人快打II',
                'poster': 'https://via.placeholder.com/200x300?text=真人快打II',
                'detail_url': 'https://www.vscinemas.com.tw/film/detail.aspx',
                'release_date': '即將上映'
            },
            {
                'title': '開棺2：家族詛咒',
                'poster': 'https://via.placeholder.com/200x300?text=開棺2',
                'detail_url': 'https://www.vscinemas.com.tw/film/detail.aspx',
                'release_date': '即將上映'
            }
        ]
    
    def get_db_connection(self):
        conn = sqlite3.connect('movies.db')
        conn.row_factory = sqlite3.Row
        return conn
    
    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, MovieHandler)
    print(f'🎬 電影資訊系統啟動成功！')
    print(f'📡 伺服器運行於：http://localhost:{port}')
    print(f'🔍 請在瀏覽器開啟上方網址')
    print(f'📝 按 Ctrl+C 停止伺服器\n')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 伺服器已停止')
        httpd.server_close()

if __name__ == '__main__':
    run_server()
