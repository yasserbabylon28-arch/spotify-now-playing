from flask import Flask, Response, request, redirect
import requests
import base64
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REFRESH_TOKEN = os.getenv('SPOTIFY_REFRESH_TOKEN')

def get_access_token():
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_str.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN
    }
    
    response = requests.post(url, headers=headers, data=data)
    return response.json().get('access_token')

def get_now_playing():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
    
    if response.status_code == 204 or not response.json():
        return None
    
    data = response.json()
    return {
        'song': data['item']['name'],
        'artist': data['item']['artists'][0]['name'],
        'album_art': data['item']['album']['images'][0]['url'],
        'is_playing': data['is_playing']
    }

@app.route('/api')
def api():
    data = get_now_playing()
    if not data:
        return Response("Not playing", status=200)
    
    # Create image
    img = Image.new('RGB', (600, 200), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    
    # Download album art
    album_response = requests.get(data['album_art'])
    album_img = Image.open(BytesIO(album_response.content))
    album_img = album_img.resize((150, 150))
    img.paste(album_img, (25, 25))
    
    # Draw text
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((200, 50), data['song'][:30], fill='#ffffff', font=font_large)
    draw.text((200, 90), data['artist'][:30], fill='#b3b3b3', font=font_small)
    draw.text((200, 130), "🎵 Now Playing" if data['is_playing'] else "⏸️ Paused", fill='#1DB954', font=font_small)
    
    # Save to bytes
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return Response(buf.getvalue(), mimetype='image/png')

@app.route('/api/login')
def login():
    scope = "user-read-currently-playing"
    redirect_uri = request.url_root + 'api/callback'
    
    auth_url = f"https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
    return redirect(auth_url)

@app.route('/api/callback')
def callback():
    code = request.args.get('code')
    redirect_uri = request.url_root + 'api/callback'
    
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_base64 = base64.b64encode(auth_str.encode()).decode()
    
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        },
        headers={"Authorization": f"Basic {auth_base64}"}
    )
    
    refresh_token = response.json().get('refresh_token')
    return f"<h1>Your Refresh Token:</h1><p>{refresh_token}</p><p>Add this to your Vercel Environment Variables as SPOTIFY_REFRESH_TOKEN</p>"
