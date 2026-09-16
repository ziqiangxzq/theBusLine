#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公交到站查询 · 多站点实时到站
单文件 · 零依赖 · Python 3.7+

默认已内置 API Key,直接打开浏览器即可使用。

用法:
    1. python app.py
    2. 浏览器访问 http://localhost:8000
    3. 外网访问:
       - ngrok http 8000
       - cloudflared tunnel --url http://localhost:8000
       - 或部署到任意有公网 IP 的服务器

控制策略(节省额度):
    - 页面可见时每 60 秒刷新一次
    - 页面切到后台/最小化时暂停刷新
    - 切回页面时立即刷新一次
"""

import json
import os
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(os.environ.get('PORT', 8000))
API_URL = 'https://v1.apizero.cn/api/bus-realtime'

# 内置 API Key(也可由前端覆盖);优先读环境变量 BUS_API_KEY
DEFAULT_API_KEY = os.environ.get('BUS_API_KEY', '')

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#fbfbfd">
<title>公交到站查询</title>
<style>
:root{
    --bg:#fbfbfd;
    --bg-elevated:rgba(255,255,255,0.72);
    --text:#1d1d1f;
    --text-secondary:#6e6e73;
    --text-tertiary:#86868b;
    --accent:#0071e3;
    --accent-hover:#0077ed;
    --border:rgba(0,0,0,0.08);
    --success:#34c759;
    --warning:#ff9500;
    --danger:#ff3b30;
    --shadow:0 12px 32px rgba(0,0,0,0.06);
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;}
html,body{height:100%;}
body{
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue","PingFang SC","Microsoft YaHei",sans-serif;
    background:var(--bg);
    color:var(--text);
    min-height:100vh;
    padding:32px 20px 120px;
    background-image:
        radial-gradient(circle at 15% 10%,rgba(0,113,227,0.06) 0%,transparent 45%),
        radial-gradient(circle at 85% 90%,rgba(52,199,89,0.05) 0%,transparent 45%);
    line-height:1.4;
}
.container{max-width:980px;margin:0 auto;}

/* Tab 切换 */
.tabs{
    display:flex;
    justify-content:center;
    gap:4px;
    margin-bottom:24px;
    background:rgba(0,0,0,0.05);
    border-radius:12px;
    padding:4px;
    width:fit-content;
    margin-left:auto;
    margin-right:auto;
    animation:fadeUp 0.5s ease both;
}
.tab{
    padding:8px 18px;
    border:none;
    background:transparent;
    color:var(--text-secondary);
    font-size:14px;
    font-weight:500;
    cursor:pointer;
    border-radius:9px;
    font-family:inherit;
    transition:all 0.25s ease;
    white-space:nowrap;
}
.tab:hover{color:var(--text);}
.tab.active{
    background:#fff;
    color:var(--text);
    box-shadow:0 1px 3px rgba(0,0,0,0.08);
}

header{
    text-align:center;
    margin-bottom:28px;
    animation:fadeUp 0.6s ease both;
}
header h1{
    font-size:32px;
    font-weight:600;
    letter-spacing:-0.025em;
    margin-bottom:6px;
    background:linear-gradient(135deg,#1d1d1f 0%,#434343 100%);
    -webkit-background-clip:text;
    background-clip:text;
    -webkit-text-fill-color:transparent;
}
header .subtitle{
    font-size:14px;
    color:var(--text-secondary);
    font-weight:400;
}
header .subtitle .dir-badge{
    display:inline-block;
    margin-left:6px;
    padding:2px 8px;
    border-radius:6px;
    background:rgba(0,113,227,0.1);
    color:var(--accent);
    font-size:12px;
    font-weight:500;
}

/* 设置按钮 */
.settings-toggle{
    position:fixed;
    top:20px;
    right:20px;
    width:36px;
    height:36px;
    border-radius:50%;
    background:var(--bg-elevated);
    backdrop-filter:blur(20px);
    -webkit-backdrop-filter:blur(20px);
    border:1px solid var(--border);
    display:flex;
    align-items:center;
    justify-content:center;
    cursor:pointer;
    z-index:50;
    transition:transform 0.2s;
    color:var(--text);
}
.settings-toggle:hover{transform:rotate(45deg);}
.settings-toggle svg{width:18px;height:18px;}

.settings-panel{
    position:fixed;
    top:0;right:0;bottom:0;
    width:min(380px,100%);
    background:rgba(255,255,255,0.92);
    backdrop-filter:blur(40px) saturate(180%);
    -webkit-backdrop-filter:blur(40px) saturate(180%);
    border-left:1px solid var(--border);
    transform:translateX(100%);
    transition:transform 0.4s cubic-bezier(0.4,0,0.2,1);
    z-index:100;
    overflow-y:auto;
    padding:60px 24px 40px;
}
.settings-panel.open{transform:translateX(0);}
.settings-panel h2{font-size:22px;font-weight:600;margin-bottom:8px;letter-spacing:-0.02em;}
.settings-panel .sub{font-size:12px;color:var(--text-tertiary);margin-bottom:24px;}
.field{margin-bottom:18px;}
.field label{
    display:block;
    font-size:13px;
    color:var(--text-secondary);
    margin-bottom:6px;
    font-weight:500;
}
.field input,.field select{
    width:100%;
    padding:10px 12px;
    border:1px solid var(--border);
    border-radius:10px;
    background:#fff;
    font-size:14px;
    font-family:inherit;
    color:var(--text);
    outline:none;
    transition:border-color 0.2s;
}
.field input:focus,.field select:focus{border-color:var(--accent);}
.field .hint{font-size:11px;color:var(--text-tertiary);margin-top:4px;}
.divider{height:1px;background:var(--border);margin:20px 0;}

.settings-backdrop{
    position:fixed;inset:0;
    background:rgba(0,0,0,0.3);
    opacity:0;
    pointer-events:none;
    transition:opacity 0.3s;
    z-index:99;
}
.settings-backdrop.show{opacity:1;pointer-events:auto;}

.btn{
    background:var(--accent);
    color:#fff;
    border:none;
    padding:8px 16px;
    border-radius:980px;
    font-size:13px;
    font-weight:500;
    cursor:pointer;
    font-family:inherit;
    transition:all 0.2s ease;
    white-space:nowrap;
}
.btn:hover{background:var(--accent-hover);}
.btn:active{transform:scale(0.96);}
.btn.ghost{
    background:rgba(0,0,0,0.05);
    color:var(--text);
}
.btn.ghost:hover{background:rgba(0,0,0,0.08);}

/* 卡片网格 */
.card-grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
    gap:16px;
    animation:fadeUp 0.8s ease both;
}
@keyframes fadeUp{
    from{opacity:0;transform:translateY(12px);}
    to{opacity:1;transform:translateY(0);}
}

.card{
    background:var(--bg-elevated);
    backdrop-filter:blur(20px) saturate(180%);
    -webkit-backdrop-filter:blur(20px) saturate(180%);
    border:1px solid var(--border);
    border-radius:22px;
    padding:24px;
    transition:transform 0.3s ease,box-shadow 0.3s ease;
    position:relative;
    overflow:hidden;
}
.card::before{
    content:"";
    position:absolute;
    top:0;left:0;right:0;
    height:3px;
    background:linear-gradient(90deg,transparent,var(--accent),transparent);
    opacity:0;
    transition:opacity 0.3s;
}
.card:hover{
    transform:translateY(-3px);
    box-shadow:var(--shadow);
}
.card:hover::before{opacity:1;}

.card-header{
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:16px;
    gap:12px;
}
.line-badge{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    background:linear-gradient(135deg,var(--accent),#00a2ff);
    color:#fff;
    font-weight:600;
    font-size:16px;
    padding:6px 14px;
    border-radius:12px;
    letter-spacing:0.01em;
    box-shadow:0 2px 8px rgba(0,113,227,0.25);
}
.terminal{
    font-size:12px;
    color:var(--text-secondary);
    text-align:right;
    max-width:60%;
    line-height:1.3;
    word-break:break-all;
}

.stops-main{
    text-align:center;
    margin:20px 0 16px;
}
.stops-number{
    font-size:64px;
    font-weight:600;
    letter-spacing:-0.04em;
    line-height:1;
    background:linear-gradient(135deg,var(--accent) 0%,#00c6ff 100%);
    -webkit-background-clip:text;
    background-clip:text;
    -webkit-text-fill-color:transparent;
}
.stops-number.dim{opacity:0.25;-webkit-text-fill-color:var(--text-tertiary);background:none;}
.stops-unit{
    font-size:14px;
    color:var(--text-secondary);
    margin-top:6px;
    font-weight:500;
}

.bus-info{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:8px;
    padding-top:16px;
    border-top:1px solid var(--border);
}
.bus-info-item{display:flex;flex-direction:column;gap:3px;}
.bus-info-label{
    font-size:10px;
    text-transform:uppercase;
    letter-spacing:0.06em;
    color:var(--text-tertiary);
    font-weight:500;
}
.bus-info-value{
    font-size:13px;
    color:var(--text);
    font-weight:500;
    word-break:break-all;
}

.status-row{
    margin-top:14px;
    text-align:center;
}
.status-pill{
    display:inline-block;
    padding:5px 12px;
    border-radius:999px;
    font-size:12px;
    font-weight:500;
}
.status-pill.imminent{background:rgba(52,199,89,0.15);color:var(--success);}
.status-pill.soon{background:rgba(255,149,0,0.15);color:var(--warning);}
.status-pill.far{background:rgba(0,113,227,0.12);color:var(--accent);}
.status-pill.none{background:rgba(0,0,0,0.05);color:var(--text-tertiary);}

.spinner{
    width:28px;height:28px;
    border:3px solid rgba(0,113,227,0.15);
    border-top-color:var(--accent);
    border-radius:50%;
    animation:spin 0.8s linear infinite;
    margin:0 auto 12px;
}
@keyframes spin{to{transform:rotate(360deg);}}

.banner{
    text-align:center;
    padding:40px 16px;
    color:var(--text-secondary);
    font-size:14px;
    grid-column:1/-1;
}
.banner.error{color:var(--danger);}
.banner .sub{font-size:12px;color:var(--text-tertiary);margin-top:8px;}

footer{
    text-align:center;
    margin-top:40px;
    font-size:12px;
    color:var(--text-tertiary);
}
footer a{color:var(--accent);text-decoration:none;}
footer a:hover{text-decoration:underline;}

/* 底部刷新条 */
.refresh-bar{
    position:fixed;
    bottom:24px;
    left:50%;
    transform:translateX(-50%);
    background:rgba(255,255,255,0.85);
    backdrop-filter:blur(20px) saturate(180%);
    -webkit-backdrop-filter:blur(20px) saturate(180%);
    border:1px solid var(--border);
    border-radius:980px;
    padding:6px 6px 6px 20px;
    display:flex;
    align-items:center;
    gap:12px;
    box-shadow:0 8px 24px rgba(0,0,0,0.1);
    font-size:13px;
    color:var(--text-secondary);
    z-index:50;
    max-width:calc(100% - 32px);
}
.refresh-bar .update-info{
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    display:flex;
    align-items:center;
    gap:6px;
}
.refresh-bar .dot{
    display:inline-block;
    width:6px;height:6px;
    border-radius:50%;
    background:var(--success);
    animation:pulse 2s ease-in-out infinite;
    flex-shrink:0;
}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.4;}}
.refresh-bar .dot.loading{background:var(--text-tertiary);animation:none;}
.refresh-bar .dot.paused{background:var(--warning);animation:none;}
.refresh-bar button{
    background:var(--accent);
    color:#fff;
    border:none;
    padding:8px 18px;
    border-radius:980px;
    font-size:13px;
    cursor:pointer;
    font-family:inherit;
    font-weight:500;
    transition:all 0.2s;
}
.refresh-bar button:hover{background:var(--accent-hover);}
.refresh-bar button:active{transform:scale(0.96);}

@media (max-width:768px){
    body{
        padding:calc(env(safe-area-inset-top,0px) + 16px) 14px calc(env(safe-area-inset-bottom,0px) + 110px);
    }
    .container{max-width:100%;}

    /* Tab:占满宽度 + 横向滚动 */
    .tabs{
        width:100%;
        margin:0 0 20px;
        overflow-x:auto;
        -webkit-overflow-scrolling:touch;
        scrollbar-width:none;
    }
    .tabs::-webkit-scrollbar{display:none;}
    .tab{
        padding:10px 18px;
        font-size:14px;
        flex-shrink:0;
    }

    header{margin-bottom:22px;}
    header h1{font-size:26px;}
    header .subtitle{font-size:13px;}
    header .subtitle .dir-badge{font-size:11px;padding:2px 7px;}

    /* 卡片网格:移动端强制单列 */
    .card-grid{
        grid-template-columns:1fr;
        gap:12px;
    }
    .card{padding:20px;border-radius:20px;}
    .card-header{margin-bottom:12px;}
    .line-badge{font-size:15px;padding:5px 12px;border-radius:10px;}
    .terminal{font-size:11px;}
    .stops-main{margin:16px 0 12px;}
    .stops-number{font-size:56px;}
    .stops-unit{font-size:13px;margin-top:4px;}
    .bus-info{padding-top:14px;gap:6px;}
    .bus-info-label{font-size:9px;}
    .bus-info-value{font-size:12px;}
    .status-row{margin-top:12px;}
    .status-pill{font-size:11px;padding:4px 10px;}

    /* 顶部齿轮:加 safe-area,触摸目标加大 */
    .settings-toggle{
        top:calc(env(safe-area-inset-top,0px) + 14px);
        right:14px;
        width:40px;
        height:40px;
    }
    .settings-toggle svg{width:20px;height:20px;}

    /* 设置面板:移动端从底部抽屉滑入(更符合 iOS 习惯) */
    .settings-panel{
        top:auto;
        right:0;left:0;bottom:0;
        width:100%;
        max-height:88vh;
        border-left:none;
        border-top:1px solid var(--border);
        border-radius:24px 24px 0 0;
        transform:translateY(100%);
        transition:transform 0.4s cubic-bezier(0.4,0,0.2,1);
        padding:calc(env(safe-area-inset-bottom,0px) + 24px) 20px 32px;
    }
    .settings-panel::before{
        content:"";
        position:absolute;
        top:8px;left:50%;
        transform:translateX(-50%);
        width:36px;height:4px;
        background:rgba(0,0,0,0.15);
        border-radius:2px;
    }
    .settings-panel.open{transform:translateY(0);}
    .settings-panel h2{font-size:20px;margin-bottom:6px;}
    .settings-panel .sub{margin-bottom:20px;}
    .field{margin-bottom:16px;}
    .field input,.field select{
        padding:12px 14px;
        font-size:15px;  /* iOS 防 zoom:>=16px 才不会自动放大 */
        border-radius:12px;
    }
    .field label{font-size:13px;}
    .field .hint{font-size:11px;}

    .btn{padding:11px 18px;font-size:14px;}

    /* 底部刷新条:加 safe-area-bottom,避免被 home indicator 遮挡 */
    .refresh-bar{
        bottom:calc(env(safe-area-inset-bottom,0px) + 16px);
        left:14px;right:14px;
        transform:none;
        max-width:none;
        padding:8px 8px 8px 16px;
        font-size:13px;
    }
    .refresh-bar .update-info{min-width:0;}
    .refresh-bar button{
        padding:10px 18px;
        font-size:14px;
        flex-shrink:0;
    }

    footer{margin-top:32px;font-size:11px;}

    .banner{padding:32px 12px;font-size:13px;}
}

@media (max-width:480px){
    body{padding:calc(env(safe-area-inset-top,0px) + 12px) 10px calc(env(safe-area-inset-bottom,0px) + 100px);}
    header h1{font-size:22px;}
    .stops-number{font-size:48px;}
    .card{padding:16px;border-radius:18px;}
    .card-header{margin-bottom:10px;gap:8px;}
    .line-badge{font-size:14px;padding:4px 10px;}
    .stops-main{margin:12px 0 10px;}
    .bus-info-value{font-size:11px;}
    .tab{padding:9px 14px;font-size:13px;}
    .refresh-bar{font-size:12px;padding:6px 6px 6px 12px;}
    .refresh-bar button{padding:9px 14px;font-size:13px;}
}

/* 横屏模式:卡片回到双列,但字号缩小 */
@media (max-width:900px) and (orientation:landscape) and (max-height:500px){
    .card-grid{grid-template-columns:repeat(2,1fr);gap:10px;}
    .card{padding:14px;}
    .stops-number{font-size:40px;}
    .stops-main{margin:10px 0 8px;}
    .bus-info{padding-top:10px;}
    header{margin-bottom:16px;}
    header h1{font-size:22px;}
}

/* 大屏(平板)优化:卡片列数更多 */
@media (min-width:769px) and (max-width:1024px){
    .card-grid{grid-template-columns:repeat(2,1fr);}
}

@media (prefers-color-scheme:dark){
    :root{
        --bg:#000;
        --bg-elevated:rgba(28,28,30,0.72);
        --text:#f5f5f7;
        --text-secondary:#a1a1a6;
        --text-tertiary:#6e6e73;
        --border:rgba(255,255,255,0.1);
    }
    body{
        background-image:
            radial-gradient(circle at 15% 10%,rgba(0,113,227,0.12) 0%,transparent 45%),
            radial-gradient(circle at 85% 90%,rgba(52,199,89,0.08) 0%,transparent 45%);
    }
    .tabs{background:rgba(255,255,255,0.08);}
    .tab.active{background:rgba(28,28,30,0.9);}
    .field input,.field select{background:rgba(28,28,30,0.8);}
    .btn.ghost{background:rgba(255,255,255,0.08);color:var(--text);}
}
</style>
</head>
<body>
<div class="container">
    <div class="tabs" id="tabs"></div>

    <header>
        <h1 id="stationTitle">山大路和平路</h1>
        <div class="subtitle">
            <span id="directionLabel">往山东大学方向</span>
            <span class="dir-badge" id="dirBadge">方向 1</span>
        </div>
    </header>

    <div class="card-grid" id="cards"></div>

    <footer>
        数据来源:<a href="https://apizero.cn" target="_blank" rel="noopener">极数本源</a> · 可见时每 60 秒刷新 · 切后台暂停
    </footer>
</div>

<div class="settings-toggle" onclick="toggleSettings()" title="设置">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"></circle>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
    </svg>
</div>

<div class="settings-backdrop" id="backdrop" onclick="toggleSettings()"></div>
<aside class="settings-panel" id="settingsPanel">
    <h2>查询设置</h2>
    <div class="sub" id="settingsSub">当前站点配置</div>
    <div class="field">
        <label>城市</label>
        <input type="text" id="cityInput" />
        <div class="hint">官方城市名,如:济南</div>
    </div>
    <div class="field">
        <label>站点</label>
        <input type="text" id="stationInput" />
        <div class="hint">官方站名,如:山大路和平路</div>
    </div>
    <div class="field">
        <label>关注线路</label>
        <input type="text" id="linesInput" placeholder="逗号分隔,留空显示全部" />
        <div class="hint">逗号分隔(如 B16,K48,K112);留空显示该站所有线路</div>
    </div>
    <div class="field">
        <label>方向</label>
        <select id="directionInput">
            <option value="1">1 · 默认方向</option>
            <option value="2">2 · 反方向</option>
        </select>
        <div class="hint">若显示方向不对,请切换到另一方向</div>
    </div>
    <button class="btn" style="width:100%;padding:12px;margin-top:4px;" onclick="saveSettings()">保存并刷新</button>

    <div class="divider"></div>
    <div class="field">
        <label>API Key(可选,留空使用内置)</label>
        <input type="password" id="apiKeyInput" placeholder="留空使用服务端内置 Key" />
        <div class="hint">自定义 Key 会覆盖服务端默认 Key;保存到 localStorage</div>
    </div>
    <button class="btn ghost" style="width:100%;padding:10px;" onclick="saveKey()">保存 Key</button>
</aside>

<div class="refresh-bar">
    <span class="update-info">
        <span class="dot" id="statusDot"></span>
        <span id="lastUpdate">尚未查询</span>
    </span>
    <button onclick="refresh()">刷新</button>
</div>

<script>
const API_URL = '/api/bus';   // 本地代理,避免 CORS

// 多查询配置;localStorage 里没存的话用默认
const DEFAULT_QUERIES = [
    {
        id: 'shanda',
        tab: '山大路和平路',
        title: '山大路和平路',
        subtitle: '往山东大学方向',
        city: '济南',
        station: '山大路和平路',
        lines: 'B16,B112,K48',
        direction: 2,
    },
    {
        id: 'baoshan',
        tab: '鲍山站',
        title: '鲍山站',
        subtitle: '往飞跃大道凤华路方向',
        city: '济南',
        station: '地铁鲍山站',
        lines: '285,582,M4',
        direction: 1,
    },
];

const REFRESH_INTERVAL = 60000;  // 60 秒

let queries = loadQueries();
let activeId = queries[0].id;
let apiKey = localStorage.getItem('apizero_key') || '';
let timer = null;
let pausedByHidden = false;

function loadQueries(){
    // 配置版本号;改默认值时递增,旧浏览器 localStorage 会被强制刷新
    const CFG_VERSION = 3;
    try {
        const ver = parseInt(localStorage.getItem('bus_cfg_v') || '0', 10);
        if (ver >= CFG_VERSION){
            const s = localStorage.getItem('bus_queries');
            if (s){
                const arr = JSON.parse(s);
                if (Array.isArray(arr) && arr.length){
                    return arr.map(q => Object.assign({}, findDefault(q.id) || {}, q));
                }
            }
        }
    } catch(e){}
    try { localStorage.setItem('bus_cfg_v', '3'); } catch(e){}
    return JSON.parse(JSON.stringify(DEFAULT_QUERIES));
}
function findDefault(id){ return DEFAULT_QUERIES.find(q => q.id === id); }

function saveQueries(){
    localStorage.setItem('bus_queries', JSON.stringify(queries));
}

function activeQuery(){ return queries.find(q => q.id === activeId) || queries[0]; }

function init(){
    renderTabs();
    applyHeader();
    document.getElementById('apiKeyInput').value = apiKey;
    refresh();
    startAuto();
    document.addEventListener('visibilitychange', onVisibility);
    // 切回窗口时立即刷新一次
    window.addEventListener('focus', () => { if (pausedByHidden) refresh(); });
}

function renderTabs(){
    const el = document.getElementById('tabs');
    el.innerHTML = queries.map(q => `
        <button class="tab ${q.id === activeId ? 'active' : ''}" onclick="switchTab('${q.id}')">${escapeHtml(q.tab)}</button>
    `).join('');
}

function switchTab(id){
    activeId = id;
    renderTabs();
    applyHeader();
    refresh();
}

function applyHeader(){
    const q = activeQuery();
    document.getElementById('stationTitle').textContent = q.title;
    document.getElementById('directionLabel').textContent = q.subtitle || ('方向 ' + q.direction);
    document.getElementById('dirBadge').textContent = '方向 ' + q.direction;
}

function startAuto(){
    stopAuto();
    timer = setInterval(() => {
        // 仅在页面可见时才查询,节省额度
        if (!document.hidden) refresh();
        else setPausedStatus();
    }, REFRESH_INTERVAL);
}
function stopAuto(){
    if (timer){ clearInterval(timer); timer = null; }
}
function setPausedStatus(){
    const dot = document.getElementById('statusDot');
    dot.classList.add('paused');
    dot.classList.remove('loading');
    document.getElementById('lastUpdate').textContent = '页面不可见,已暂停';
}

function onVisibility(){
    if (document.hidden){
        pausedByHidden = true;
        setPausedStatus();
    } else if (pausedByHidden){
        pausedByHidden = false;
        refresh();  // 切回立即刷新一次
    }
}

function toggleSettings(){
    const p = document.getElementById('settingsPanel');
    const b = document.getElementById('backdrop');
    const open = !p.classList.contains('open');
    if (open){
        const q = activeQuery();
        document.getElementById('settingsSub').textContent = '当前:' + q.title;
        document.getElementById('cityInput').value = q.city;
        document.getElementById('stationInput').value = q.station;
        document.getElementById('linesInput').value = q.lines;
        document.getElementById('directionInput').value = q.direction;
    }
    p.classList.toggle('open', open);
    b.classList.toggle('show', open);
}

function saveSettings(){
    const q = activeQuery();
    q.city = document.getElementById('cityInput').value.trim() || q.city;
    q.station = document.getElementById('stationInput').value.trim() || q.station;
    q.lines = document.getElementById('linesInput').value.trim();
    q.direction = parseInt(document.getElementById('directionInput').value, 10) || 1;
    saveQueries();
    applyHeader();
    toggleSettings();
    refresh();
}

function saveKey(){
    apiKey = document.getElementById('apiKeyInput').value.trim();
    localStorage.setItem('apizero_key', apiKey);
    refresh();
}

function setStatus(text, loading, paused){
    const dot = document.getElementById('statusDot');
    dot.classList.remove('loading','paused');
    if (loading) dot.classList.add('loading');
    if (paused) dot.classList.add('paused');
    document.getElementById('lastUpdate').textContent = text;
}

async function refresh(){
    const q = activeQuery();
    // 决定目标线路列表
    let targets = q.lines ? q.lines.split(',').map(s => s.trim()).filter(Boolean) : [];
    renderLoading(targets, q);
    setStatus('查询中…', true, false);
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (apiKey) headers['Authorization'] = 'Bearer ' + apiKey;
        // 没填 Key 时,后端会自动用内置 Key
        const resp = await fetch(API_URL, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                type: 'query',
                city: q.city,
                station: q.station,
                direction: q.direction,
            }),
        });
        const body = await resp.json();
        if (body.code !== 0){
            renderError(body.msg || ('错误码 ' + body.code));
            setStatus('查询失败', false, false);
            return;
        }
        renderCards(body.data, targets);
        const ts = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        setStatus('更新于 ' + ts, false, false);
    } catch(e){
        renderError(e.message || '网络错误,请检查服务是否运行');
        setStatus('网络错误', false, false);
    }
}

function renderLoading(targets, q){
    if (targets.length === 0){
        // 没指定线路:占位 3 个
        targets = ['—','—','—'];
    }
    const html = targets.map(l => `
        <div class="card">
            <div class="card-header"><span class="line-badge">${escapeHtml(l)}</span></div>
            <div class="stops-main">
                <div class="spinner"></div>
                <div class="stops-unit">查询中</div>
            </div>
        </div>
    `).join('');
    document.getElementById('cards').innerHTML = html;
}

function renderError(msg){
    document.getElementById('cards').innerHTML = '<div class="banner error">' + escapeHtml(msg) + '</div>';
}

function renderCards(data, targets){
    const lines = data.lines || [];
    let html = '';

    if (targets.length === 0){
        // 显示全部线路
        if (!lines.length){
            html = '<div class="banner">该站暂无在途车辆<div class="sub">数据更新于 ' + escapeHtml(data.updated_at || '') + '</div></div>';
        } else {
            html = lines.map(l => cardHtml(l.line, (l.buses || [])[0], l)).join('');
        }
    } else {
        html = targets.map(target => {
            const t = target.replace(/路$/, '');
            const matched = lines.find(l => {
                const name = (l.line || '').replace(/路$/, '');
                return name === t || name.includes(t) || t.includes(name);
            });
            if (!matched || !matched.buses || !matched.buses.length){
                return cardHtml(target, null, matched);
            }
            return cardHtml(target, matched.buses[0], matched);
        }).join('');
    }
    document.getElementById('cards').innerHTML = html;
}

function cardHtml(target, bus, line){
    const stops = bus ? bus.stops_remaining : null;
    const status = bus ? (bus.status || (stops != null ? stops + '站' : '')) : '无在途车';
    let pillClass = 'none';
    if (stops != null){
        if (stops === 0) pillClass = 'imminent';
        else if (stops <= 3) pillClass = 'soon';
        else pillClass = 'far';
    }
    const arrival = bus && bus.arrival_time ? bus.arrival_time.slice(11, 16) : '--';
    const minutes = bus && bus.travel_minutes != null ? bus.travel_minutes + ' 分' : '--';
    const plate = bus && bus.bus_id ? bus.bus_id : '--';
    const terminal = line && line.terminal ? line.terminal : '—';

    return `
        <div class="card">
            <div class="card-header">
                <span class="line-badge">${escapeHtml(target)}</span>
                <span class="terminal">→ ${escapeHtml(terminal)}</span>
            </div>
            <div class="stops-main">
                <div class="stops-number ${stops == null ? 'dim' : ''}">${stops != null ? stops : '--'}</div>
                <div class="stops-unit">站</div>
            </div>
            <div class="bus-info">
                <div class="bus-info-item">
                    <span class="bus-info-label">车牌</span>
                    <span class="bus-info-value">${escapeHtml(plate)}</span>
                </div>
                <div class="bus-info-item">
                    <span class="bus-info-label">到站</span>
                    <span class="bus-info-value">${escapeHtml(arrival)}</span>
                </div>
                <div class="bus-info-item">
                    <span class="bus-info-label">用时</span>
                    <span class="bus-info-value">${escapeHtml(minutes)}</span>
                </div>
            </div>
            <div class="status-row">
                <span class="status-pill ${pillClass}">${escapeHtml(status)}</span>
            </div>
        </div>
    `;
}

function escapeHtml(s){
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

init();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html'):
            self._send_html(HTML)
        elif path == '/health':
            self._send_json({'ok': True})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/bus':
            self._proxy_bus()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def _send_html(self, content):
        body = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _resolve_auth(self):
        """优先用前端传的 Key,没有则用内置 Key"""
        auth = (self.headers.get('Authorization') or '').strip()
        if auth:
            return auth
        if DEFAULT_API_KEY:
            return 'Bearer ' + DEFAULT_API_KEY
        return ''

    def _proxy_bus(self):
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            payload = self.rfile.read(length) if length else b'{}'
            auth = self._resolve_auth()
            req = urllib.request.Request(
                API_URL,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': auth,
                },
                method='POST',
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except urllib.error.HTTPError as e:
                data = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self._send_json({'code': -1, 'msg': '代理错误: ' + str(e)}, 500)

    def log_message(self, fmt, *args):
        pass  # 静默日志


def main():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print('================================================')
    print('  公交到站查询 · 多站点')
    print('  - 山大路和平路(往山东大学方向): B16 / K48 / K112')
    print('  - 鲍山站(往飞跃大道凤华路方向): 全部线路')
    print('------------------------------------------------')
    print('  本地访问: http://localhost:%d' % PORT)
    print('  外网访问:')
    print('    ngrok http %d' % PORT)
    print('    cloudflared tunnel --url http://localhost:%d' % PORT)
    print('------------------------------------------------')
    print('  刷新策略: 页面可见时每 60 秒,切后台暂停')
    print('  内置 API Key: 已配置')
    print('  按 Ctrl+C 退出')
    print('================================================')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已退出')
        server.server_close()


if __name__ == '__main__':
    main()
