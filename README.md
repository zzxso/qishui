# 汽水音乐下载器

解析汽水音乐分享链接，自动提取音频并转换为 MP3 格式。

> **免责声明：本项目仅供学习交流使用，请勿用于商业用途或任何其他用途。请尊重音乐版权，支持正版。**

## 功能

- 解析分享文本中的歌曲名和短链接
- 通过浏览器自动化访问页面，提取音频地址
- 下载音频文件并转换为 MP3 格式
- 提供 Web 界面，粘贴链接即可下载

## 安装

```bash
pip install DrissionPage requests Flask
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
| `downloads/` | MP3 下载目录 |

## 依赖

- Python 3.8+
- DrissionPage
- requests
- Flask
- FFmpeg
