#!/usr/bin/env python3
"""
汽水音乐下载器 - Web 界面
启动后浏览器打开 http://localhost:5000，粘贴分享链接即可下载
"""

import re
import os
import sys
import time
import json
import tempfile
import subprocess
import threading
import requests
from flask import Flask, render_template_string, jsonify, request, send_from_directory
from DrissionPage import ChromiumPage, ChromiumOptions

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>汽水音乐下载器</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, 'Microsoft YaHei', sans-serif;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
  }
  .container {
    background: rgba(255,255,255,0.06); backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 20px;
    padding: 40px; width: 520px; max-width: 95vw;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  h1 {
    text-align: center; color: #fff; font-size: 24px; margin-bottom: 8px;
  }
  .subtitle {
    text-align: center; color: rgba(255,255,255,0.5); font-size: 13px; margin-bottom: 30px;
  }
  label { color: rgba(255,255,255,0.8); font-size: 14px; display: block; margin-bottom: 8px; }
  textarea {
    width: 100%; height: 80px; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 10px; color: #fff; font-size: 14px; padding: 12px; resize: none;
    outline: none; transition: border-color 0.3s;
  }
  textarea:focus { border-color: #7c5cfc; }
  textarea::placeholder { color: rgba(255,255,255,0.3); }
  .btn {
    width: 100%; margin-top: 16px; padding: 14px; border: none; border-radius: 10px;
    background: linear-gradient(135deg, #7c5cfc, #b44aff); color: #fff;
    font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s;
    position: relative; overflow: hidden;
  }
  .btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(124,92,252,0.4); }
  .btn:active { transform: translateY(0); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .btn .spinner {
    display: none; width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-right: 8px; vertical-align: middle;
  }
  .btn.loading .spinner { display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .status {
    margin-top: 20px; padding: 14px; border-radius: 10px; font-size: 13px;
    line-height: 1.6; display: none; word-break: break-all;
  }
  .status.info { display: block; background: rgba(124,92,252,0.15); color: #b8a9ff; border: 1px solid rgba(124,92,252,0.2); }
  .status.success { display: block; background: rgba(52,199,89,0.15); color: #7deca0; border: 1px solid rgba(52,199,89,0.2); }
  .status.error { display: block; background: rgba(255,69,58,0.15); color: #ff8a80; border: 1px solid rgba(255,69,58,0.2); }

  .history { margin-top: 24px; }
  .history h3 { color: rgba(255,255,255,0.6); font-size: 13px; margin-bottom: 10px; }
  .history-list { max-height: 200px; overflow-y: auto; }
  .history-item {
    display: flex; align-items: center;
    padding: 10px 14px; background: rgba(255,255,255,0.04); border-radius: 8px;
    margin-bottom: 6px; transition: background 0.2s;
  }
  .history-item:hover { background: rgba(255,255,255,0.08); }
  .history-item .cover { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; margin-right: 12px; flex-shrink: 0; background: rgba(255,255,255,0.1); }
  .history-item .info { flex: 1; min-width: 0; }
  .history-item .name { color: rgba(255,255,255,0.8); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .history-item .size { color: rgba(255,255,255,0.4); font-size: 12px; margin-top: 2px; }
  .empty-hint { color: rgba(255,255,255,0.25); font-size: 13px; text-align: center; padding: 20px; }
</style>
</head>
<body>
<div class="container">
  <h1>汽水音乐下载器</h1>
  <p class="subtitle">粘贴分享链接，自动下载 MP3</p>

  <label for="link">分享链接</label>
  <textarea id="link" placeholder="《歌曲名》@汽水音乐 https://qishui.douyin.com/s/xxx/"></textarea>

  <button class="btn" id="downloadBtn" onclick="startDownload()">
    <span class="spinner"></span>开始下载
  </button>

  <div class="status" id="status"></div>

  <div class="history">
    <h3>下载记录</h3>
    <div class="history-list" id="historyList">
      <div class="empty-hint">暂无下载记录</div>
    </div>
  </div>
</div>

<script>
let downloading = false;

async function startDownload() {
  const link = document.getElementById('link').value.trim();
  if (!link) { showStatus('error', '请粘贴分享链接'); return; }
  if (downloading) return;
  downloading = true;

  const btn = document.getElementById('downloadBtn');
  btn.classList.add('loading');
  btn.disabled = true;
  showStatus('info', '正在解析链接...');

  try {
    const resp = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ link })
    });
    const data = await resp.json();

    if (data.success) {
      let msg = '下载完成: ' + data.filename + ' (' + data.size + ')';
      if (data.cover) msg += ' + 封面图';
      if (data.lyrics) msg += ' + 歌词(' + data.lyrics_count + '行)';
      showStatus('success', msg);
      loadHistory();
    } else {
      showStatus('error', data.error || '下载失败');
    }
  } catch (e) {
    showStatus('error', '请求失败: ' + e.message);
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
    downloading = false;
  }
}

function showStatus(type, msg) {
  const el = document.getElementById('status');
  el.className = 'status ' + type;
  el.textContent = msg;
}

async function loadHistory() {
  try {
    const resp = await fetch('/api/history');
    const files = await resp.json();
    const list = document.getElementById('historyList');
    if (files.length === 0) {
      list.innerHTML = '<div class="empty-hint">暂无下载记录</div>';
      return;
    }
    list.innerHTML = files.map(f => {
      const coverHtml = f.cover
        ? '<img class="cover" src="/downloads/' + encodeURIComponent(f.cover) + '" onerror="this.style.display=\'none\'">'
        : '<div class="cover"></div>';
      return '<div class="history-item">' +
        coverHtml +
        '<div class="info">' +
          '<div class="name">' + f.name + '</div>' +
          '<div class="size">' + f.size + '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  } catch(e) {}
}

document.getElementById('link').addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') startDownload();
});

loadHistory();
</script>
</body>
</html>
"""


def parse_input(text):
    song_match = re.search(r'《(.*?)》', text)
    url_match = re.search(r'https://qishui\.douyin\.com/s/\S+', text)
    if not song_match:
        return None, None, '未找到歌曲名（《》内的内容）'
    if not url_match:
        return None, None, '未找到汽水音乐链接'
    return song_match.group(1).strip(), url_match.group(0).rstrip('/'), None


def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)


def fetch_timed_lyrics(track_id):
    """通过 CDP 获取带时间戳的歌词"""
    import subprocess
    import websocket

    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    debug_port = 9223
    user_data_dir = os.path.join(tempfile.gettempdir(), 'qishui_lyrics_debug')

    # 启动 Chrome
    chrome = subprocess.Popen([
        chrome_path,
        f'--remote-debugging-port={debug_port}',
        f'--user-data-dir={user_data_dir}',
        '--remote-allow-origins=*',
        '--no-first-run', '--no-default-browser-check',
        '--disable-gpu',
        '--window-size=1280,720',
    ])
    time.sleep(3)

    try:
        # 连接
        resp = requests.get(f'http://localhost:{debug_port}/json/version', timeout=5)
        if resp.status_code != 200:
            return []

        # 打开歌曲页
        url = f'https://music.douyin.com/qishui/share/track?track_id={track_id}'
        resp = requests.put(f'http://localhost:{debug_port}/json/new?{url}', timeout=10)
        target = resp.json()
        ws_url = target.get('webSocketDebuggerUrl', '')

        # 等待加载
        time.sleep(20)

        # 通过 CDP 执行 JS 搜索歌词
        ws = websocket.create_connection(ws_url, timeout=30)
        msg_id = int(time.time() * 1000) % 100000
        js_code = """
        (function() {
            var allElements = document.querySelectorAll('*');
            for (var i = 0; i < allElements.length; i++) {
                var el = allElements[i];
                var keys = Object.keys(el);
                for (var j = 0; j < keys.length; j++) {
                    if (keys[j].startsWith('__reactFiber') || keys[j].startsWith('__reactInternalInstance')) {
                        var fiber = el[keys[j]];
                        var current = fiber;
                        var depth = 0;
                        while (current && depth < 50) {
                            try {
                                if (current.memoizedState) {
                                    var s = current.memoizedState;
                                    var si = 0;
                                    while (s && si < 20) {
                                        if (s.memoizedState && s.memoizedState.lyrics && s.memoizedState.lyrics.sentences && s.memoizedState.lyrics.sentences.length > 0) {
                                            return JSON.stringify(s.memoizedState.lyrics);
                                        }
                                        s = s.next;
                                        si++;
                                    }
                                }
                            } catch(e) {}
                            current = current.return;
                            depth++;
                        }
                    }
                }
            }
            return JSON.stringify({error: 'not found'});
        })()
        """
        ws.send(json.dumps({'id': msg_id, 'method': 'Runtime.evaluate', 'params': {
            'expression': js_code, 'returnByValue': True
        }}))
        while True:
            result = json.loads(ws.recv())
            if result.get('id') == msg_id:
                break
        ws.close()

        value = result.get('result', {}).get('result', {}).get('value', '')
        data = json.loads(value)
        if 'sentences' in data:
            return data['sentences']
        return []

    except Exception:
        return []
    finally:
        # 关闭标签页和 Chrome
        try:
            requests.get(f'http://localhost:{debug_port}/json/close/{target.get("id")}', timeout=3)
        except:
            pass
        chrome.terminate()


def save_lyrics_as_lrc(lyrics, output_path):
    """将歌词保存为 LRC 格式"""
    if not lyrics:
        return False
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('[ti:]\n[ar:]\n[al:]\n[by:Qishui Downloader]\n\n')
        for line in lyrics:
            if isinstance(line, dict):
                # 带时间戳的歌词
                text = line.get('text', '')
                start_ms = line.get('startMs', line.get('start', 0))
                if start_ms > 1000:
                    total_seconds = start_ms / 1000
                else:
                    total_seconds = start_ms
                minutes = int(total_seconds) // 60
                seconds = total_seconds % 60
                f.write(f'[{minutes:02d}:{seconds:05.2f}]{text}\n')
            else:
                # 纯文本歌词
                f.write(f'{line}\n')
    return True


def capture_audio_url(short_url):
    co = ChromiumOptions()
    co.headless()
    co.set_argument('--disable-gpu')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--window-size=1920,1080')
    co.set_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    page = None
    audio_url = None
    cover_url = None
    lyrics = []
    try:
        page = ChromiumPage(co)
        page.get(short_url)
        time.sleep(10)

        # 从当前URL中提取 track_id
        current_url = page.url
        track_id = None
        tid_match = re.search(r'track_id=(\d+)', current_url)
        if tid_match:
            track_id = tid_match.group(1)

        play_selectors = [
            'css:[class*="play"]', 'css:[class*="Play"]',
            'css:button[class*="control"]', 'css:svg[class*="play"]',
            'css:[data-testid*="play"]', 'css:.play-btn',
            'css:[aria-label*="play"]', 'css:[aria-label*="Play"]',
        ]
        for sel in play_selectors:
            try:
                btn = page.ele(sel)
                if btn:
                    btn.click()
                    time.sleep(8)
                    break
            except Exception:
                continue

        html = page.html

        # 提取音频 URL
        for pattern in [
            r'(https?://[^\s"\'<>\\]+\.m4a[^\s"\'<>\\]*)',
            r'(https?://[^\s"\'<>\\]+\.mp3[^\s"\'<>\\]*)',
            r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)',
            r'"(https?://[^"]*audio[^"]*)"',
        ]:
            matches = re.findall(pattern, html)
            if matches:
                audio_url = matches[0]
                break

        if not audio_url:
            for tag in ['css:audio', 'css:source']:
                try:
                    el = page.ele(tag)
                    if el:
                        src = el.attr('src')
                        if src and src.startswith('http'):
                            audio_url = src
                            break
                except Exception:
                    continue

        # 提取封面 URL - 从 url_cover 数据中构建
        cover_match = re.search(r'"url_cover"\s*:\s*\{[^}]+\}', html)
        if cover_match:
            try:
                cover_data = json.loads(cover_match.group(0).replace('\\u002F', '/').replace('"url_cover":', ''))
                uri = cover_data.get('uri', '')
                urls = cover_data.get('urls', [])
                if uri and urls:
                    cover_url = urls[0] + uri + '~c5_375x375.jpg'
            except Exception:
                pass

        # 如果有 track_id，尝试获取带时间戳的歌词
        if track_id:
            lyrics = fetch_timed_lyrics(track_id)

        return audio_url, cover_url, lyrics
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass


def download_file(url, dest_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://qishui.douyin.com/',
    }
    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def find_ffmpeg():
    """查找 FFmpeg 可执行文件路径"""
    # 优先检查 PATH
    import shutil
    path = shutil.which('ffmpeg')
    if path:
        return path
    # 常见安装路径
    candidates = [
        r'C:\Users\zzx\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe',
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return 'ffmpeg'


FFMPEG_PATH = find_ffmpeg()


def convert_to_mp3(input_path, output_path):
    result = subprocess.run(
        [FFMPEG_PATH, '-y', '-i', input_path, '-acodec', 'libmp3lame', '-ab', '192k', output_path],
        capture_output=True, text=True, encoding='utf-8', errors='replace'
    )
    if result.returncode != 0:
        raise RuntimeError(f'FFmpeg 转换失败: {result.stderr[:200]}')


def do_download(link_text):
    song_name, short_url, err = parse_input(link_text)
    if err:
        raise ValueError(err)

    audio_url, cover_url, lyrics = capture_audio_url(short_url)
    if not audio_url:
        raise RuntimeError('未能获取到音频文件 URL')

    safe_name = sanitize_filename(song_name)
    timestamp = int(time.time())
    temp_dir = tempfile.gettempdir()
    m4a_path = os.path.join(temp_dir, f'temp_{timestamp}.m4a')
    mp3_path = os.path.join(DOWNLOAD_DIR, f'{safe_name}.mp3')
    cover_path = os.path.join(DOWNLOAD_DIR, f'{safe_name}.jpg')
    lrc_path = os.path.join(DOWNLOAD_DIR, f'{safe_name}.lrc')

    try:
        download_file(audio_url, m4a_path)
        convert_to_mp3(m4a_path, mp3_path)
        # 下载封面
        if cover_url:
            try:
                download_file(cover_url, cover_path)
            except Exception:
                pass
    finally:
        if os.path.exists(m4a_path):
            os.remove(m4a_path)

    # 保存歌词
    if lyrics:
        save_lyrics_as_lrc(lyrics, lrc_path)

    result = {'mp3': safe_name + '.mp3'}
    if cover_url and os.path.exists(cover_path):
        result['cover'] = safe_name + '.jpg'
    if lyrics:
        result['lyrics'] = safe_name + '.lrc'
        result['lyrics_count'] = len(lyrics)
    return result


def format_size(size_bytes):
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.1f} KB'
    else:
        return f'{size_bytes / (1024 * 1024):.1f} MB'


@app.route('/')
def index():
    return render_template_string(HTML_PAGE)


@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    link = data.get('link', '').strip()
    if not link:
        return jsonify(success=False, error='请输入分享链接')

    try:
        result = do_download(link)
        mp3_path = os.path.join(DOWNLOAD_DIR, result['mp3'])
        size = os.path.getsize(mp3_path)
        resp = {'success': True, 'filename': result['mp3'], 'size': format_size(size)}
        if 'cover' in result:
            resp['cover'] = result['cover']
        if 'lyrics' in result:
            resp['lyrics'] = result['lyrics']
            resp['lyrics_count'] = result['lyrics_count']
        return jsonify(resp)
    except Exception as e:
        return jsonify(success=False, error=str(e))


@app.route('/api/history')
def api_history():
    files = []
    if os.path.exists(DOWNLOAD_DIR):
        for f in sorted(os.listdir(DOWNLOAD_DIR), key=lambda x: os.path.getmtime(os.path.join(DOWNLOAD_DIR, x)), reverse=True):
            if f.endswith('.mp3'):
                size = os.path.getsize(os.path.join(DOWNLOAD_DIR, f))
                name = f[:-4]  # 去掉 .mp3
                cover = name + '.jpg'
                has_cover = os.path.exists(os.path.join(DOWNLOAD_DIR, cover))
                files.append({'name': f, 'size': format_size(size), 'cover': cover if has_cover else None})
    return jsonify(files)


@app.route('/downloads/<path:filename>')
def serve_download(filename):
    return send_from_directory(DOWNLOAD_DIR, filename)


if __name__ == '__main__':
    print('=' * 50)
    print('  汽水音乐下载器')
    print('  打开浏览器访问: http://localhost:5000')
    print('  按 Ctrl+C 停止')
    print('=' * 50)
    app.run(host='127.0.0.1', port=5000, debug=False)
