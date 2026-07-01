#!/usr/bin/env python3
"""
汽水音乐歌曲下载器
解析分享链接 → DrissionPage加载页面 → 提取音频URL → 下载m4a → FFmpeg转MP3

依赖：
  pip install DrissionPage requests
  FFmpeg 需提前安装并加入系统 PATH
"""

import re
import os
import sys
import time
import json
import shutil
import tempfile
import subprocess
import requests
from DrissionPage import ChromiumPage, ChromiumOptions


def find_ffmpeg():
    """查找 FFmpeg 可执行文件路径"""
    path = shutil.which('ffmpeg')
    if path:
        return path
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


def parse_input(text):
    """从分享文本中解析歌曲名和链接"""
    song_match = re.search(r'《(.*?)》', text)
    url_match = re.search(r'https://qishui\.douyin\.com/s/\S+', text)

    if not song_match:
        print('[错误] 未找到歌曲名（《》内的内容）')
        sys.exit(1)
    if not url_match:
        print('[错误] 未找到汽水音乐链接')
        sys.exit(1)

    song_name = song_match.group(1).strip()
    url = url_match.group(0).rstrip('/')
    print(f'[解析] 歌曲名: {song_name}')
    print(f'[解析] 链接: {url}')
    return song_name, url


def sanitize_filename(name):
    """移除文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|]', '', name)


def fetch_timed_lyrics(track_id):
    """通过 CDP 获取带时间戳的歌词"""
    import subprocess
    import websocket

    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    debug_port = 9224
    user_data_dir = os.path.join(tempfile.gettempdir(), 'qishui_lyrics_debug')

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
        resp = requests.get(f'http://localhost:{debug_port}/json/version', timeout=5)
        if resp.status_code != 200:
            return []

        url = f'https://music.douyin.com/qishui/share/track?track_id={track_id}'
        resp = requests.put(f'http://localhost:{debug_port}/json/new?{url}', timeout=10)
        target = resp.json()
        ws_url = target.get('webSocketDebuggerUrl', '')

        time.sleep(20)

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
                f.write(f'{line}\n')
    return True
    return True


def capture_audio_url(short_url):
    """使用 DrissionPage 访问链接，从页面/JS中提取音频 URL 和封面 URL"""
    print('[浏览器] 正在启动 Chrome...')

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

        print(f'[浏览器] 访问: {short_url}')
        page.get(short_url)

        print('[浏览器] 等待页面加载...')
        time.sleep(10)

        # 从当前URL中提取 track_id
        current_url = page.url
        track_id = None
        tid_match = re.search(r'track_id=(\d+)', current_url)
        if tid_match:
            track_id = tid_match.group(1)

        # 尝试点击播放按钮
        play_selectors = [
            'css:[class*="play"]',
            'css:[class*="Play"]',
            'css:button[class*="control"]',
            'css:svg[class*="play"]',
            'css:[data-testid*="play"]',
            'css:.play-btn',
            'css:[aria-label*="play"]',
            'css:[aria-label*="Play"]',
        ]

        for sel in play_selectors:
            try:
                btn = page.ele(sel)
                if btn:
                    btn.click()
                    print(f'[浏览器] 已点击播放按钮: {sel}')
                    time.sleep(8)
                    break
            except Exception:
                continue

        # 提取音频 URL
        audio_url = extract_from_html(page)
        if not audio_url:
            audio_url = extract_from_js(page)
        if not audio_url:
            audio_url = extract_from_audio_tags(page)

        # 提取封面 URL
        html = page.html
        cover_match = re.search(r'"url_cover"\s*:\s*\{[^}]+\}', html)
        if cover_match:
            try:
                cover_data = json.loads(cover_match.group(0).replace('\\u002F', '/').replace('"url_cover":', ''))
                uri = cover_data.get('uri', '')
                urls = cover_data.get('urls', [])
                if uri and urls:
                    cover_url = urls[0] + uri + '~c5_375x375.jpg'
                    print(f'[提取] 封面 URL: {cover_url[:120]}...')
            except Exception:
                pass

        # 获取带时间戳的歌词
        if track_id:
            print(f'[歌词] track_id={track_id}，正在获取歌词...')
            lyrics = fetch_timed_lyrics(track_id)
            if lyrics:
                print(f'[歌词] 获取到 {len(lyrics)} 行歌词')
            else:
                print('[歌词] 无歌词（可能是纯音乐）')

        return audio_url, cover_url, lyrics

    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass
            print('[浏览器] 已关闭')


def extract_from_html(page):
    """从页面 HTML 中正则提取音频 URL"""
    try:
        html = page.html
        patterns = [
            r'(https?://[^\s"\'<>\\]+\.m4a[^\s"\'<>\\]*)',
            r'(https?://[^\s"\'<>\\]+\.mp3[^\s"\'<>\\]*)',
            r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)',
            r'"(https?://[^"]*audio[^"]*)"',
            r"'(https?://[^']*audio[^']*)'",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, html)
            if matches:
                url = matches[0]
                print(f'[提取] 从 HTML 找到音频: {url[:120]}...')
                return url
    except Exception as e:
        print(f'[提取] HTML 提取失败: {e}')
    return None


def extract_from_js(page):
    """从 JavaScript 变量中提取音频 URL"""
    js_queries = [
        # 常见的音乐播放器 JS 变量
        'return window.__INITIAL_STATE__',
        'return window.__NEXT_DATA__',
        'return window.__DATA__',
        'return window._SSR_DATA',
        'return window.__NUXT__',
        # 尝试获取 audio 元素的 src
        'var a = document.querySelector("audio"); return a ? a.src : null',
        'var s = document.querySelector("source"); return s ? s.src : null',
    ]

    for js in js_queries:
        try:
            result = page.run_js(js)
            if not result:
                continue

            # 如果是字典/对象，递归搜索
            if isinstance(result, dict):
                urls = find_urls_in_dict(result)
                for url in urls:
                    if '.m4a' in url or '.mp3' in url or '.m3u8' in url or 'audio' in url:
                        print(f'[提取] 从 JS 变量找到音频: {url[:120]}...')
                        return url

            # 如果是字符串且包含 URL
            elif isinstance(result, str) and result.startswith('http'):
                if '.m4a' in result or '.mp3' in result or 'audio' in result:
                    print(f'[提取] 从 JS 找到音频: {result[:120]}...')
                    return result

        except Exception:
            continue

    return None


def find_urls_in_dict(d, depth=0):
    """递归从字典中查找所有 URL"""
    if depth > 10:
        return []
    urls = []
    if isinstance(d, dict):
        for v in d.values():
            urls.extend(find_urls_in_dict(v, depth + 1))
    elif isinstance(d, list):
        for item in d:
            urls.extend(find_urls_in_dict(item, depth + 1))
    elif isinstance(d, str) and d.startswith('http'):
        urls.append(d)
    return urls


def extract_from_audio_tags(page):
    """从 <audio> 和 <source> 标签中提取"""
    try:
        audio = page.ele('css:audio')
        if audio:
            src = audio.attr('src')
            if src and src.startswith('http'):
                print(f'[提取] 从 <audio> 标签找到: {src[:120]}...')
                return src

        source = page.ele('css:source')
        if source:
            src = source.attr('src')
            if src and src.startswith('http'):
                print(f'[提取] 从 <source> 标签找到: {src[:120]}...')
                return src
    except Exception:
        pass
    return None


def download_file(url, dest_path):
    """下载文件"""
    print('[下载] 开始下载...')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://qishui.douyin.com/',
    }

    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()

    total = int(resp.headers.get('content-length', 0))
    downloaded = 0

    with open(dest_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded * 100 / total
                print(f'\r[下载] {pct:.1f}% ({downloaded}/{total} bytes)', end='', flush=True)

    print()
    print(f'[下载] 完成: {dest_path} ({downloaded} bytes)')


def convert_to_mp3(input_path, output_path):
    """使用 FFmpeg 将 m4a 转换为 mp3"""
    print('[转换] 正在调用 FFmpeg 转换为 MP3...')

    cmd = [
        FFMPEG_PATH, '-y',
        '-i', input_path,
        '-acodec', 'libmp3lame',
        '-ab', '192k',
        output_path
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    if result.returncode != 0:
        print(f'[转换] FFmpeg 错误:\n{result.stderr}')
        sys.exit(1)

    print(f'[转换] 完成: {output_path}')


def main():
    if len(sys.argv) < 2:
        print('用法: python main.py "《歌曲名》@汽水音乐 https://qishui.douyin.com/s/xxx/"')
        print('  或: python main.py   然后粘贴分享文本')
        sys.exit(1)

    input_text = ' '.join(sys.argv[1:])

    # 交互式输入
    if not re.search(r'https://qishui\.douyin\.com/s/', input_text):
        print('请粘贴汽水音乐分享文本:')
        input_text = sys.stdin.readline().strip()
        if not input_text:
            print('[错误] 未输入任何内容')
            sys.exit(1)

    # 1. 解析输入
    song_name, short_url = parse_input(input_text)

    # 2. 捕获音频 URL
    audio_url, cover_url, lyrics = capture_audio_url(short_url)
    if not audio_url:
        print('[错误] 未能获取到音频文件 URL，可能原因：')
        print('  - 页面需要登录或有其他限制')
        print('  - 页面结构已变更')
        print('  - 网络请求未被捕获')
        sys.exit(1)
    print(f'[成功] 音频 URL: {audio_url[:120]}...')

    # 3. 下载 m4a
    safe_name = sanitize_filename(song_name)
    timestamp = int(time.time())
    temp_dir = tempfile.gettempdir()
    m4a_path = os.path.join(temp_dir, f'temp_{timestamp}.m4a')
    mp3_path = os.path.join(os.getcwd(), f'{safe_name}.mp3')
    cover_path = os.path.join(os.getcwd(), f'{safe_name}.jpg')
    lrc_path = os.path.join(os.getcwd(), f'{safe_name}.lrc')

    try:
        download_file(audio_url, m4a_path)

        # 4. 转换为 mp3
        convert_to_mp3(m4a_path, mp3_path)
        print(f'\n[完成] MP3 已保存: {mp3_path}')

        # 5. 下载封面
        if cover_url:
            try:
                download_file(cover_url, cover_path)
                print(f'[完成] 封面已保存: {cover_path}')
            except Exception as e:
                print(f'[警告] 封面下载失败: {e}')

        # 6. 保存歌词
        if lyrics:
            save_lyrics_as_lrc(lyrics, lrc_path)
            print(f'[完成] 歌词已保存: {lrc_path} ({len(lyrics)}行)')
    finally:
        # 清理临时文件
        if os.path.exists(m4a_path):
            os.remove(m4a_path)
            print(f'[清理] 已删除临时文件: {m4a_path}')


if __name__ == '__main__':
    main()
