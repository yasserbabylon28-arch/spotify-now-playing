from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
import base64
import os
import json

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REFRESH_TOKEN = os.getenv('SPOTIFY_REFRESH_TOKEN')

def get_access_token():
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()
    
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {auth_base64}"},
        data={"grant_type": "refresh_token", "refresh_token": SPOTIFY_REFRESH_TOKEN}
    )
    return response.json().get('access_token')

def get_now_playing():
    if not SPOTIFY_REFRESH_TOKEN:
        return None
    token = get_access_token()
    response = requests.get(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code != 200:
        return None
    return response.json()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        if path == '/api':
            data = get_now_playing()
            if not data:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Not playing')
                return
            
            song = data['item']['name']
            artist = data['item']['artists'][0]['name']
            
            svg = f'''
            <svg width="600" height="200" xmlns="http://www.w3.org/2000/svg">
                <rect width="600" height="200" fill="#1a1a1a" rx="10"/>
                <text x="30" y="80" font-size="24" fill="#ffffff" font-family="Arial">{song[:30]}</text>
                <text x="30" y="120" font-size="18" fill="#b3b3b3" font-family="Arial">{artist[:30]}</text>
                <text x="30" y="160" font-size="16" fill="#1DB954" font-family="Arial">🎵 Now Playing</text>
            </svg>
            '''
            
            self.send_response(200)
            self.send_header('Content-type', 'image/svg+xml')
            self.end_headers()
            self.wfile.write(svg.encode())
            
        elif path == '/api/login':
            redirect_uri = f"https://{self.headers['Host']}/api/callback"
            auth_url = f"https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={redirect_uri}&scope=user-read-currently-playing"
            
            self.send_response(302)
            self.send_header('Location', auth_url)
            self.end_headers()
            
        elif path == '/api/callback':
            code = query.get('code', [None])[0]
            redirect_uri = f"https://{self.headers['Host']}/api/callback"
            
            auth_base64 = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
            response = requests.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
                headers={"Authorization": f"Basic {auth_base64}"}
            )
            
            refresh_token = response.json().get('refresh_token')
            
            html = f'''
            <html>
            <body style="background: #000; color: #0f0; font-family: monospace; padding: 50px;">
                <h1>✅ SUCCESS!</h1>
                <h2>Your Refresh Token:</h2>
                <p style="background: #111; padding: 20px; word-break: break-all; border: 2px solid #0f0;">{refresh_token}</p>
                <p>Add this to Vercel Environment Variables as: <strong>SPOTIFY_REFRESH_TOKEN</strong></p>
            </body>
            </html>
            '''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
