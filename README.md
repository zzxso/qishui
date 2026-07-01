# 汽水音乐下载器

解析汽水音乐分享链接，自动提取音频、封面、歌词并转换为 MP3 格式。

> **免责声明：本项目仅供学习交流使用，请勿用于商业用途或任何其他用途。请尊重音乐版权，支持正版。**

## 功能

- 解析分享文本中的歌曲名和短链接
- 通过浏览器自动化访问页面，提取音频地址
- 下载音频文件并转换为 MP3 格式
- 自动下载专辑封面（JPG）
- 自动提取带时间戳的歌词（LRC 格式，精确到毫秒）
- 提供 Web 界面，粘贴链接即可下载

## 输出文件

每次下载会生成以下文件（保存在 `downloads/` 目录）：

| 文件 | 说明 |
|------|------|
| `{歌名}.mp3` | 音频文件（192kbps） |
| `{歌名}.jpg` | 专辑封面 |
| `{歌名}.lrc` | 歌词文件（LRC 格式，带时间戳） |

> 注：纯音乐歌曲无歌词，仅生成 MP3 和封面。

## 安装

```bash
pip install DrissionPage requests Flask websocket-client
```

FFmpeg 需提前安装并加入系统 PATH（推荐通过 `winget install Gyan.FFmpeg` 安装）。

## 使用

### Web 界面（推荐）

```bash
# 双击 启动下载器.bat
# 或手动运行
python app.py
```

浏览器打开 http://localhost:5000，粘贴分享链接点击下载。

### 命令行

```bash
python main.py "《歌曲名》@汽水音乐 https://qishui.douyin.com/s/xxx/"
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | Web 界面版本（Flask） |
| `main.py` | 命令行版本 |
| `启动下载器.bat` | 一键启动脚本 |
| `downloads/` | 下载目录 |

## 技术实现

- **音频提取**：DrissionPage 控制 Chrome 访问分享页面，从 HTML 中提取音频 URL
- **封面提取**：从页面 JSON 数据中提取 `url_cover` 构建封面图片 URL
- **歌词提取**：通过 DrissionPage 非 headless 模式访问 `music.douyin.com`，从 React Fiber 状态中读取带时间戳的 KRC 歌词数据
- **格式转换**：FFmpeg 将 m4a 转换为 MP3（libmp3lame, 192kbps）

## 依赖

- Python 3.8+
- DrissionPage
- requests
- Flask
- websocket-client
- FFmpeg
- Google Chrome
