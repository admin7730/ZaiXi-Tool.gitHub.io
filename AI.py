import os
import sys
import json
import time
import threading
import subprocess
import requests
import pyperclip
import datetime
import webview  # 必须安装: pip install pywebview

# --- 配置与常量 ---
# 请确保 Key 是有效的。如果 Key 本身有问题，也会导致 400 或 401 错误。
API_KEY = "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"
SITE_URL = "https://zaixi-ai.tool" # 按照要求使用你的站点URL，或者保留 openrouter.ai
SITE_NAME = "ZaiXi AI CMD Tool GUI"

# 预设模型列表 (确保 ID 正确，如果有误请更换为 OpenRouter 上确切存在的 ID)
MODELS = [
    {"id": "qwen/qwen3-coder:free", "name": "Qwen: Qwen3-Coder (free)"},
    {"id": "tngtech/deepseek-r1t-chimera:free", "name": "DeepSeek R1T Chimera (free)"},
    {"id": "mistralai/devstral-2512:free", "name": "Mistral AI: Devstral 2512 (free)"},
    {"id": "xiaomi/mimo-v2-flash:free", "name": "Xiaomi: MiMo-V2-Flash (free)"},
    {"id": "nvidia/nemotron-3-nano-30b-a3b:free", "name": "NVIDIA: Nemotron 3 Nano 30B A3B (free)"}

]

# --- 前端代码 (HTML/CSS/JS 硬编码) ---
HTML_CODE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>载熙AI 领航工具</title>
    <style>
        :root {
            --bg-color: #05070a;
            --panel-bg: rgba(20, 24, 35, 0.65);
            --sidebar-bg: rgba(10, 12, 18, 0.85);
            --accent-color: #00f2ff;
            --secondary-color: #7000ff;
            --text-color: #e0e6ed;
            --success-color: #00ff9d;
            --glass-border: 1px solid rgba(255, 255, 255, 0.08);
            --neon-glow: 0 0 10px rgba(0, 242, 255, 0.3);
        }

        body {
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            overflow: hidden;
            background-image: 
                linear-gradient(rgba(0, 242, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 242, 255, 0.03) 1px, transparent 1px);
            background-size: 30px 30px;
        }

        /* --- 加载动画页 --- */
        #loading-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #000;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: opacity 0.8s ease;
        }

        .loader-content {
            text-align: center;
            width: 80%;
            max-width: 500px;
            position: relative;
        }

        .logo-text {
            font-size: 3.5rem;
            font-weight: 800;
            text-transform: uppercase;
            background: linear-gradient(90deg, #00f2ff, #bc00ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
            letter-spacing: 4px;
            filter: drop-shadow(0 0 15px rgba(0, 242, 255, 0.5));
        }

        .author-text {
            color: #888;
            font-size: 1.1rem;
            margin-bottom: 50px;
            letter-spacing: 2px;
            opacity: 0;
            animation: fadeIn 1.5s ease 0.5s forwards;
        }

        .progress-wrapper {
            width: 100%;
            height: 6px;
            background: #111;
            border-radius: 3px;
            overflow: hidden;
            position: relative;
            box-shadow: 0 0 10px rgba(0,0,0,0.5) inset;
        }

        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--secondary-color), var(--accent-color));
            width: 0%;
            transition: width 0.1s linear;
            box-shadow: 0 0 15px var(--accent-color);
        }

        .loading-status {
            margin-top: 15px;
            font-family: 'Consolas', monospace;
            font-size: 0.9rem;
            color: var(--accent-color);
            text-align: right;
            text-shadow: 0 0 5px rgba(0, 242, 255, 0.5);
        }

        /* --- 主界面 --- */
        #app-container {
            display: flex;
            height: 100vh;
            opacity: 0;
            transition: opacity 1s ease;
            backdrop-filter: blur(5px);
        }

        /* 侧边栏 */
        .sidebar {
            width: 70px;
            background: var(--sidebar-bg);
            border-right: var(--glass-border);
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 30px;
            z-index: 100;
            box-shadow: 5px 0 20px rgba(0,0,0,0.3);
        }

        .nav-btn {
            width: 46px;
            height: 46px;
            border-radius: 14px;
            margin-bottom: 25px;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: rgba(255, 255, 255, 0.03);
            font-size: 22px;
            color: #666;
            border: 1px solid transparent;
        }

        .nav-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            transform: scale(1.05);
            border-color: rgba(255,255,255,0.1);
        }

        .nav-btn.active {
            background: linear-gradient(135deg, rgba(112, 0, 255, 0.8), rgba(0, 242, 255, 0.8));
            color: #fff;
            box-shadow: 0 0 20px rgba(0, 242, 255, 0.4);
            border: 1px solid rgba(255,255,255,0.2);
        }

        /* 主内容区 */
        .main-content {
            flex: 1;
            padding: 25px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }

        .window-controls {
            display: flex;
            gap: 8px;
            margin-right: 20px;
        }
        
        .window-control-btn {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 8px;
            font-weight: bold;
            color: white;
            border: none;
            padding: 0;
        }
        
        .window-control-btn:hover {
            transform: scale(1.1);
        }
        
        .close-btn {
            background: #ff5f57;
        }
        
        .minimize-btn {
            background: #ffbd2e;
        }
        
        .maximize-btn {
            background: #28ca42;
        }
        
        .header {
            display: flex;
            align-items: center;
            padding-bottom: 15px;
            border-bottom: var(--glass-border);
            margin-bottom: 20px;
            cursor: default;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            flex: 1;
        }
        
        .header-right {
            display: flex;
            align-items: center;
        }

        .page-title {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(to right, #fff, #aaa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
        }

        .model-select {
            background: rgba(0, 0, 0, 0.5);
            border: var(--glass-border);
            color: var(--accent-color);
            padding: 8px 20px;
            border-radius: 20px;
            outline: none;
            cursor: pointer;
            font-family: 'Segoe UI', sans-serif;
            transition: all 0.3s;
        }
        
        .model-select:hover {
            border-color: var(--accent-color);
            box-shadow: 0 0 10px rgba(0, 242, 255, 0.2);
        }

        /* 内容面板 */
        .panel {
            background: var(--panel-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 20px;
            border: var(--glass-border);
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            animation: panelFadeIn 0.4s ease-out;
        }

        @keyframes panelFadeIn {
            from { opacity: 0; transform: translateY(20px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        /* 聊天模式 */
        .chat-history {
            flex: 1;
            overflow-y: auto;
            padding: 25px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .message {
            max-width: 80%;
            padding: 15px 20px;
            border-radius: 18px;
            line-height: 1.6;
            font-size: 1rem;
            position: relative;
            word-wrap: break-word;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }

        .message.user {
            align-self: flex-end;
            background: linear-gradient(135deg, #7000ff, #3d00cc);
            color: white;
            border-bottom-right-radius: 4px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .message.ai {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.05);
            border: var(--glass-border);
            border-bottom-left-radius: 4px;
            color: #ddd;
        }
        
        .message .sender-name {
            font-size: 0.75rem;
            opacity: 0.6;
            margin-bottom: 6px;
            display: block;
            font-weight: 600;
            text-transform: uppercase;
        }

        .input-area {
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            display: flex;
            gap: 15px;
            border-top: var(--glass-border);
        }

        input[type="text"] {
            flex: 1;
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255,255,255,0.1);
            padding: 14px 24px;
            border-radius: 30px;
            color: white;
            outline: none;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        input[type="text"]:focus {
            background: rgba(0, 0, 0, 0.6);
            border-color: var(--accent-color);
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.2);
        }

        button.send-btn {
            background: var(--accent-color);
            border: none;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            color: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.3s;
            font-size: 20px;
            box-shadow: 0 0 10px var(--accent-color);
        }

        button.send-btn:hover {
            transform: rotate(90deg) scale(1.1);
            background: #fff;
            box-shadow: 0 0 20px #fff;
        }

        /* CMD 模式 */
        .cmd-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            padding: 25px;
        }

        .shell-toggle {
            display: flex;
            background: rgba(0,0,0,0.4);
            border-radius: 12px;
            padding: 5px;
            width: fit-content;
            margin-bottom: 25px;
            border: var(--glass-border);
        }

        .shell-btn {
            padding: 8px 24px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.95rem;
            font-weight: 600;
            color: #888;
        }

        .shell-btn.active-cmd {
            background: #0078d7;
            color: white;
            box-shadow: 0 0 15px rgba(0, 120, 215, 0.4);
        }

        .shell-btn.active-ps {
            background: #3c4257;
            color: #00f2ff;
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.2);
            border: 1px solid rgba(0, 242, 255, 0.3);
        }
        
        .code-block {
            background: #0d0d0d;
            border: 1px solid #333;
            border-left: 4px solid var(--accent-color);
            border-radius: 8px;
            padding: 20px;
            font-family: 'Consolas', 'Monaco', monospace;
            color: #d4d4d4;
            margin: 15px 0;
            white-space: pre-wrap;
            position: relative;
            overflow-x: auto;
            box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
            font-size: 0.95rem;
        }

        .cmd-actions {
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }

        .action-btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: #ddd;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .action-btn:hover {
            background: rgba(255,255,255,0.15);
            transform: translateY(-2px);
        }

        .action-btn.run {
            border-color: rgba(0, 255, 157, 0.5);
            color: var(--success-color);
            background: rgba(0, 255, 157, 0.1);
        }
        
        .action-btn.run:hover {
            background: rgba(0, 255, 157, 0.2);
            box-shadow: 0 0 15px rgba(0, 255, 157, 0.2);
        }

        /* 工具分类按钮 */
        .tool-category-btn {
            padding: 8px 20px;
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255,255,255,0.1);
            color: #ddd;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }
        
        .tool-category-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--accent-color);
            color: white;
        }
        
        .tool-category-btn.active {
            background: linear-gradient(135deg, var(--secondary-color), var(--accent-color));
            color: white;
            border-color: var(--accent-color);
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.3);
        }
        
        /* 工具项样式 */
        .tool-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-align: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .tool-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            transition: left 0.6s ease;
        }
        
        .tool-item:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--accent-color);
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 35px rgba(0, 242, 255, 0.3);
        }
        
        .tool-item:hover::before {
            left: 100%;
        }
        
        .tool-icon {
            font-size: 2.8rem;
            margin-bottom: 15px;
            display: block;
            transition: transform 0.3s ease;
        }
        
        .tool-item:hover .tool-icon {
            transform: scale(1.1) rotate(5deg);
        }
        
        .tool-name {
            font-size: 1rem;
            font-weight: 600;
            color: white;
            margin-bottom: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            transition: color 0.3s ease;
        }
        
        .tool-item:hover .tool-name {
            color: var(--accent-color);
        }
        
        .tool-path {
            font-size: 0.8rem;
            color: #888;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            transition: color 0.3s ease;
        }
        
        .tool-item:hover .tool-path {
            color: #aaa;
        }
        
        /* 工具搜索框样式增强 */
        #tool-search {
            background: rgba(0, 0, 0, 0.4) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            padding: 12px 20px !important;
            border-radius: 25px !important;
            color: white !important;
            outline: none !important;
            font-size: 1rem !important;
            transition: all 0.3s ease !important;
        }
        
        #tool-search:focus {
            background: rgba(0, 0, 0, 0.6) !important;
            border-color: var(--accent-color) !important;
            box-shadow: 0 0 15px rgba(0, 242, 255, 0.2) !important;
        }
        
        /* 工具分类按钮增强 */
        .tool-category-btn {
            padding: 8px 20px !important;
            border-radius: 20px !important;
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            color: #ddd !important;
            cursor: pointer !important;
            white-space: nowrap !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            font-size: 0.9rem !important;
            position: relative !important;
            overflow: hidden !important;
        }
        
        .tool-category-btn:hover {
            background: rgba(255, 255, 255, 0.1) !important;
            border-color: var(--accent-color) !important;
            color: white !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 15px rgba(0, 242, 255, 0.2) !important;
        }
        
        .tool-category-btn.active {
            background: linear-gradient(135deg, var(--secondary-color), var(--accent-color)) !important;
            color: white !important;
            border-color: var(--accent-color) !important;
            box-shadow: 0 0 20px rgba(0, 242, 255, 0.4) !important;
            transform: translateY(-2px) !important;
        }
        
        /* 滚动条美化 */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.15);
            border-radius: 4px;
            transition: background 0.3s ease;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.3);
        }

        /* 动画关键帧 */
        @keyframes fadeIn { to { opacity: 1; } }

        /* Loader Spinner inside app */
        .typing-indicator {
            display: none;
            padding: 15px;
            font-style: italic;
            color: var(--accent-color);
            font-size: 0.9rem;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }

        /* 悬浮球 */
        .floating-ball {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-color), var(--secondary-color));
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0, 242, 255, 0.4);
            z-index: 9999;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
            /* 确保悬浮球始终在右下角 */
            margin: 0;
            padding: 0;
            border: none;
        }
        
        .floating-ball:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 30px rgba(0, 242, 255, 0.6);
        }
        
        .floating-content {
            font-size: 1.5rem;
            font-weight: bold;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        /* 开关控件 */
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 24px;
        }
        
        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        
        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255, 255, 255, 0.1);
            transition: .4s;
            border-radius: 24px;
        }
        
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        
        input:checked + .toggle-slider {
            background-color: var(--accent-color);
            box-shadow: 0 0 10px rgba(0, 242, 255, 0.4);
        }
        
        input:checked + .toggle-slider:before {
            transform: translateX(26px);
        }

    </style>
</head>
<body>

    <!-- 加载画面 -->
    <div id="loading-screen">
        <div class="loader-content">
            <div class="logo-text">ZAIXI AI</div>
            <div class="author-text">由 金在熙 制作</div>
            <div class="progress-wrapper">
                <div class="progress-bar" id="progress-bar"></div>
            </div>
            <div class="loading-status" id="loading-text">初始化核心系统...</div>
        </div>
    </div>

    <!-- 悬浮球 -->
    <div class="floating-ball" id="floating-ball" title="载熙AI">
        <div class="floating-content">AI</div>
    </div>

    <!-- 主应用 -->
    <div id="app-container">
        <!-- 侧边栏 -->
        <div class="sidebar">
            <div class="nav-btn active" onclick="switchMode('chat')" title="智能对话">💬</div>
            <div class="nav-btn" onclick="switchMode('cmd')" title="CMD领航">💻</div>
            <div class="nav-btn" onclick="switchMode('browser')" title="网页浏览">🌐</div>
            <div class="nav-btn" onclick="switchToTools()" title="工具箱">🧰</div>
            <div class="nav-btn" onclick="switchMode('settings')" title="设置">⚙️</div>
            <div class="nav-btn" onclick="switchMode('about')" title="关于">ℹ️</div>
            <div style="flex:1"></div>
            <div class="nav-btn" onclick="loadHistory()" title="加载记录">📂</div>
            <div class="nav-btn" onclick="saveHistory()" title="保存记录">💾</div>
        </div>

        <!-- 主内容 -->
        <div class="main-content">
            <div class="header" id="app-header">
                <div class="header-left">
                    <div class="window-controls">
                        <div class="window-control-btn close-btn" onclick="closeApp()" title="关闭"></div>
                        <div class="window-control-btn minimize-btn" onclick="minimizeApp()" title="最小化"></div>
                        <div class="window-control-btn maximize-btn" onclick="maximizeApp()" title="最大化"></div>
                    </div>
                    <div class="page-title" id="page-title">智能对话模式</div>
                </div>
                <div class="header-right">
                    <select class="model-select" id="model-selector">
                        <!-- Models injected by JS -->
                    </select>
                </div>
            </div>

            <!-- 聊天面板 -->
            <div class="panel" id="panel-chat">
                <div class="chat-history" id="chat-box">
                    <div class="message ai">
                        <span class="sender-name">ZaiXi AI</span>
                        你好！我是载熙AI，你的智能助手。<br>你可以问我任何问题，或者切换到左侧的“CMD领航”模式来操作电脑。
                    </div>
                </div>
                <div class="typing-indicator" id="chat-loading">✦ 载熙AI 正在思考...</div>
                <div class="input-area">
                    <input type="text" id="chat-input" placeholder="输入消息..." onkeypress="handleChatKey(event)">
                    <button class="send-btn" onclick="sendChat()">➤</button>
                </div>
            </div>

            <!-- CMD 面板 -->
            <div class="panel" id="panel-cmd" style="display: none;">
                <div class="cmd-container">
                    <div class="shell-toggle">
                        <div class="shell-btn active-cmd" id="btn-shell-cmd" onclick="setShell('cmd')">CMD</div>
                        <div class="shell-btn" id="btn-shell-ps" onclick="setShell('powershell')">PowerShell</div>
                    </div>
                    
                    <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; margin-bottom: 20px;" id="cmd-placeholder">
                        <h2 style="color: #eee; font-weight: 300; font-size: 2rem;">等待指令输入...</h2>
                        <p style="color: #666; font-size: 1.1rem; max-width: 500px; margin-top: 10px;">
                            请描述你想要完成的任务（例如：“帮我列出D盘所有文件”），我将为你生成可执行的系统命令。
                        </p>
                    </div>

                    <div id="cmd-result-area" style="display: none; width: 100%; display: flex; flex-direction: column; height: 100%; overflow: hidden;">
                        <div style="font-size: 0.9rem; color: #888; margin-bottom: 5px;">生成的命令:</div>
                        <div class="code-block" id="cmd-output"></div>
                        
                        <div class="cmd-actions">
                            <button class="action-btn run" onclick="runCurrentCmd()">⚡ 立即运行</button>
                            <button class="action-btn" onclick="copyCurrentCmd()">📋 复制命令</button>
                            <button class="action-btn" onclick="saveCurrentCmd()">💾 保存文件</button>
                        </div>
                        
                        <div style="flex: 1; margin-top: 15px; display: flex; flex-direction: column; min-height: 0;">
                            <div style="font-size: 0.9rem; color: #888; margin-bottom: 5px;">运行日志:</div>
                            <div class="code-block" id="run-output" style="background: #000; color: #00ff9d; flex: 1; overflow-y: auto; margin: 0; border-color: rgba(0,255,157,0.3);"></div>
                        </div>
                    </div>

                    <div class="typing-indicator" id="cmd-loading">⚡ 正在构建系统指令...</div>

                    <div class="input-area" style="margin-top: auto; width: 100%; box-sizing: border-box;">
                        <input type="text" id="cmd-input" placeholder="例如：查询当前IP地址..." onkeypress="handleCmdKey(event)">
                        <button class="send-btn" onclick="sendCmdGen()">⚡</button>
                    </div>
                </div>
            </div>

            <!-- 设置面板 -->
            <div class="panel" id="panel-settings" style="display: none; padding: 40px; overflow-y: auto;">
                <div style="max-width: 700px; margin: 0 auto;">
                    <h1 style="font-size: 2rem; margin-bottom: 40px; color: var(--accent-color);">设置</h1>
                    
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 15px; border: var(--glass-border); margin-bottom: 30px;">
                        <h3 style="color: #ddd; margin-bottom: 20px; font-size: 1.2rem;">界面设置</h3>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <div>
                                <div style="color: #eee; font-weight: 600;">开启悬浮球</div>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">在右下角显示可点击的悬浮球</div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="floating-ball-toggle" checked onchange="toggleFloatingBall(this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <div>
                                <div style="color: #eee; font-weight: 600;">深色主题</div>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">使用深色界面主题</div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="dark-theme-toggle" checked onchange="toggleDarkTheme(this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        
                        <div style="margin-bottom: 20px;">
                            <div style="color: #eee; font-weight: 600; margin-bottom: 10px;">窗口透明度</div>
                            <div style="color: #666; font-size: 0.9rem; margin-bottom: 10px;">调整应用窗口的透明度</div>
                            <input type="range" id="opacity-slider" min="50" max="100" value="90" step="5" onchange="changeOpacity(this.value)" style="width: 100%;">
                            <div style="text-align: center; color: #888; font-size: 0.9rem; margin-top: 5px;">
                                当前透明度: <span id="opacity-value">90%</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 15px; border: var(--glass-border); margin-bottom: 30px;">
                        <h3 style="color: #ddd; margin-bottom: 20px; font-size: 1.2rem;">系统设置</h3>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <div>
                                <div style="color: #eee; font-weight: 600;">开机自启动</div>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">Windows启动时自动运行程序</div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="startup-toggle" onchange="toggleStartup(this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                        
                        <div style="margin-bottom: 20px;">
                            <div style="color: #eee; font-weight: 600; margin-bottom: 10px;">默认浏览器首页</div>
                            <div style="color: #666; font-size: 0.9rem; margin-bottom: 10px;">设置网页浏览功能的默认首页</div>
                            <input type="text" id="browser-homepage" value="https://www.baidu.com" onchange="setBrowserHomepage(this.value)" style="width: 100%; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255,255,255,0.1); padding: 10px 15px; border-radius: 8px; color: white; outline: none;">
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <div>
                                <div style="color: #eee; font-weight: 600;">自动更新检查</div>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">启动时检查软件更新</div>
                            </div>
                            <label class="toggle-switch">
                                <input type="checkbox" id="auto-update-toggle" checked onchange="toggleAutoUpdate(this.checked)">
                                <span class="toggle-slider"></span>
                            </label>
                        </div>
                    </div>
                    
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 15px; border: var(--glass-border);">
                        <h3 style="color: #ddd; margin-bottom: 20px; font-size: 1.2rem;">关于</h3>
                        <div style="color: #666; font-size: 1rem;">
                            <p style="margin-bottom: 10px;">版本: 1.0.0</p>
                            <p style="margin-bottom: 10px;">作者: 金在熙</p>
                            <p style="margin-bottom: 10px;">© 2024 ZaiXi AI. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 网页浏览面板 -->
            <div class="panel" id="panel-browser" style="display: none;">
                <div style="display: flex; flex-direction: column; height: 100%;">
                    <div style="padding: 15px; background: rgba(0, 0, 0, 0.3); border-bottom: var(--glass-border); display: flex; align-items: center; gap: 10px;">
                        <button class="action-btn" onclick="browserBack()" title="后退">⬅️</button>
                        <button class="action-btn" onclick="browserForward()" title="前进">➡️</button>
                        <input type="text" id="browser-url" placeholder="输入网址..." value="https://www.baidu.com" style="flex: 1; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255,255,255,0.1); padding: 10px 15px; border-radius: 20px; color: white; outline: none;">
                        <button class="action-btn run" onclick="browserGo()" title="前往">🔍</button>
                        <button class="action-btn" onclick="browserRefresh()" title="刷新">🔄</button>
                    </div>
                    <div style="flex: 1; overflow: hidden;">
                        <iframe id="browser-iframe" src="https://www.baidu.com" style="width: 100%; height: 100%; border: none;"></iframe>
                    </div>
                    <div style="padding: 15px; background: rgba(0, 0, 0, 0.3); border-top: var(--glass-border); display: flex; justify-content: space-between; align-items: center;">
                        <div style="color: #888; font-size: 0.9rem;" id="browser-status">就绪</div>
                        <div style="display: flex; gap: 10px;">
                            <button class="action-btn" onclick="browserSummary()" title="AI总结">📝 总结</button>
                            <button class="action-btn" onclick="browserDownload()" title="下载">💾 下载</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 工具箱面板 -->
            <div class="panel" id="panel-tools" style="display: none; padding: 25px; overflow: hidden; display: flex; flex-direction: column;">
                <div style="display: flex; flex-direction: column; height: 100%;">
                    <script>
                        // 当工具箱面板显示时自动加载工具
                        setTimeout(loadTools, 100);
                    </script>
                    <!-- 工具搜索和分类选择 -->
                    <div style="padding-bottom: 20px; border-bottom: var(--glass-border); margin-bottom: 20px;">
                        <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 15px;">
                            <input type="text" id="tool-search" placeholder="搜索工具..." style="flex: 1; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 25px; color: white; outline: none; font-size: 1rem;">
                            <button class="action-btn" onclick="refreshTools()" title="刷新工具列表">🔄</button>
                        </div>
                        
                        <!-- 工具分类选择 -->
                        <div style="display: flex; gap: 10px; overflow-x: auto; padding: 10px 0;">
                            <div class="tool-category-btn active" onclick="selectCategory('all')" title="所有工具">全部</div>
                            <div class="tool-category-btn" onclick="selectCategory('processor')" title="处理器工具">处理器</div>
                            <div class="tool-category-btn" onclick="selectCategory('memory')" title="内存工具">内存</div>
                            <div class="tool-category-btn" onclick="selectCategory('gpu')" title="显卡工具">显卡</div>
                            <div class="tool-category-btn" onclick="selectCategory('disk')" title="硬盘工具">硬盘</div>
                            <div class="tool-category-btn" onclick="selectCategory('monitor')" title="显示器工具">显示器</div>
                            <div class="tool-category-btn" onclick="selectCategory('peripheral')" title="外设工具">外设</div>
                            <div class="tool-category-btn" onclick="selectCategory('stress')" title="烤鸡工具">烤鸡</div>
                            <div class="tool-category-btn" onclick="selectCategory('game')" title="游戏工具">游戏</div>
                            <div class="tool-category-btn" onclick="selectCategory('other')" title="其他工具">其他</div>
                        </div>
                    </div>
                    
                    <!-- 工具列表 -->
                    <div style="flex: 1; overflow-y: auto; padding-right: 10px;">
                        <div id="tool-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px;">
                            <!-- 工具项将通过JS动态添加 -->
                            <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #666;">
                                <div style="font-size: 4rem; margin-bottom: 20px;">🧰</div>
                                <div style="font-size: 1.2rem; margin-bottom: 10px;">工具箱初始化中...</div>
                                <div style="font-size: 0.9rem;">正在扫描可用工具，请稍候...</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 工具信息 -->
                    <div style="padding-top: 20px; border-top: var(--glass-border); margin-top: 20px; color: #888; font-size: 0.9rem;">
                        <div id="tool-info">选择工具查看详细信息</div>
                    </div>
                </div>
            </div>

            <!-- 关于面板 -->
            <div class="panel" id="panel-about" style="display: none; padding: 40px; overflow-y: auto;">
                <div style="max-width: 700px; margin: 0 auto; text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 20px; filter: drop-shadow(0 0 15px rgba(0, 242, 255, 0.5));">
                        💡 载熙AI
                    </div>
                    <h1 style="font-size: 2.5rem; margin-bottom: 10px; background: linear-gradient(to right, var(--accent-color), var(--secondary-color)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        ZaiXi AI
                    </h1>
                    <p style="color: #888; font-size: 1.2rem; margin-bottom: 40px;">智能助手与系统控制工具</p>
                    
                    <div style="display: flex; justify-content: center; gap: 30px; margin-bottom: 50px;">
                        <div style="text-align: center;">
                            <div style="font-size: 2.5rem; margin-bottom: 10px;">💬</div>
                            <div style="color: #ddd; font-weight: 600;">智能对话</div>
                            <div style="color: #666; font-size: 0.9rem;">自然语言交互</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2.5rem; margin-bottom: 10px;">💻</div>
                            <div style="color: #ddd; font-weight: 600;">CMD领航</div>
                            <div style="color: #666; font-size: 0.9rem;">系统命令生成</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 2.5rem; margin-bottom: 10px;">🌐</div>
                            <div style="color: #ddd; font-weight: 600;">网页浏览</div>
                            <div style="color: #666; font-size: 0.9rem;">AI网页总结</div>
                        </div>
                    </div>
                    
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 30px; border-radius: 15px; border: var(--glass-border); margin-bottom: 40px;">
                        <h3 style="color: var(--accent-color); margin-bottom: 20px; font-size: 1.4rem;">功能特点</h3>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; text-align: left;">
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>AI模型多选项支持</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>CMD/PowerShell命令生成</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>命令一键运行与复制</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>聊天记录保存与加载</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>网页浏览与AI总结</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>悬浮球快捷操作</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>开机自启动</span>
                            </div>
                            <div style="display: flex; gap: 10px;">
                                <span style="color: var(--success-color); font-size: 1.2rem;">✓</span>
                                <span>美观的现代化界面</span>
                            </div>
                        </div>
                    </div>
                    
                    <div style="color: #666; font-size: 1rem;">
                        <p style="margin-bottom: 10px;">版本: 1.0.0</p>
                        <p style="margin-bottom: 10px;">作者: 金在熙</p>
                        <p style="margin-bottom: 10px;">© 2024 ZaiXi AI. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentMode = 'chat';
        let currentShell = 'cmd';
        let currentGeneratedCmd = '';

        // --- 初始化 ---
        window.addEventListener('pywebviewready', function() {
            simulateLoading();
            loadModels();
        });

        function simulateLoading() {
            let progress = 0;
            const bar = document.getElementById('progress-bar');
            const text = document.getElementById('loading-text');
            const screen = document.getElementById('loading-screen');
            const app = document.getElementById('app-container');

            const steps = ["读取载熙AI配置文件...", "连接 OpenRouter 神经节点...", "构建 3D 渲染引擎...", "启动智能领航系统..."];
            
            const interval = setInterval(() => {
                progress += Math.random() * 8;
                if (progress > 100) progress = 100;
                
                bar.style.width = progress + '%';
                text.innerText = steps[Math.floor((progress / 100) * steps.length)] || "准备就绪";

                if (progress === 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        screen.style.opacity = 0;
                        setTimeout(() => screen.style.display = 'none', 800);
                        app.style.opacity = 1;
                    }, 500);
                }
            }, 50);
        }

        function loadModels() {
             window.pywebview.api.get_models().then(models => {
                const select = document.getElementById('model-selector');
                models.forEach(m => {
                    let opt = document.createElement('option');
                    opt.value = m.id;
                    opt.innerText = m.name;
                    select.appendChild(opt);
                });
             });
        }

        // --- 导航逻辑 ---
        function switchMode(mode) {
            currentMode = mode;
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
            
            if (mode === 'chat') {
                document.querySelector('.nav-btn[onclick="switchMode(\\'chat\\')"]').classList.add('active');
                document.getElementById('panel-chat').style.display = 'flex';
                document.getElementById('page-title').innerText = "智能对话模式";
            } else if (mode === 'cmd') {
                document.querySelector('.nav-btn[onclick="switchMode(\\'cmd\\')"]').classList.add('active');
                document.getElementById('panel-cmd').style.display = 'flex'; 
                document.getElementById('page-title').innerText = "CMD 领航模式";
                // 默认隐藏结果区，显示占位符
                if(!currentGeneratedCmd) {
                    document.getElementById('cmd-result-area').style.display = 'none';
                    document.getElementById('cmd-placeholder').style.display = 'flex';
                }
            } else if (mode === 'settings') {
                document.querySelector('.nav-btn[onclick="switchMode(\\'settings\\')"]').classList.add('active');
                document.getElementById('panel-settings').style.display = 'flex'; 
                document.getElementById('page-title').innerText = "设置";
            } else if (mode === 'browser') {
                document.querySelector('.nav-btn[onclick="switchMode(\\'browser\\')"]').classList.add('active');
                document.getElementById('panel-browser').style.display = 'flex'; 
                document.getElementById('page-title').innerText = "网页浏览";
            } else if (mode === 'about') {
                document.querySelector('.nav-btn[onclick="switchMode(\\'about\\')"]').classList.add('active');
                document.getElementById('panel-about').style.display = 'flex'; 
                document.getElementById('page-title').innerText = "关于";
            }
        }

        function setShell(shell) {
            currentShell = shell;
            document.getElementById('btn-shell-cmd').className = shell === 'cmd' ? 'shell-btn active-cmd' : 'shell-btn';
            document.getElementById('btn-shell-ps').className = shell === 'powershell' ? 'shell-btn active-ps' : 'shell-btn';
        }

        // --- 聊天逻辑 ---
        function handleChatKey(e) { if(e.key === 'Enter') sendChat(); }

        function appendMessage(role, text) {
            const box = document.getElementById('chat-box');
            const div = document.createElement('div');
            div.className = `message ${role}`;
            // 处理换行和简单的 Markdown 代码块展示
            let formatted = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            formatted = formatted.replace(/\\n/g, '<br>');
            formatted = formatted.replace(/```([\\s\\S]*?)```/g, '<div class="code-block">$1</div>');
            
            div.innerHTML = `<span class="sender-name">${role === 'user' ? 'User' : 'ZaiXi AI'}</span>${formatted}`;
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        function sendChat() {
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;

            appendMessage('user', text);
            input.value = '';
            document.getElementById('chat-loading').style.display = 'block';

            const modelId = document.getElementById('model-selector').value;

            // 使用异步处理，避免阻塞UI
            window.pywebview.api.chat_request(text, modelId).then(response => {
                document.getElementById('chat-loading').style.display = 'none';
                appendMessage('ai', response);
            }).catch(error => {
                document.getElementById('chat-loading').style.display = 'none';
                appendMessage('ai', `错误: ${error.message || '未知错误'}`);
            });
        }

        // --- CMD 逻辑 ---
        function handleCmdKey(e) { if(e.key === 'Enter') sendCmdGen(); }

        function sendCmdGen() {
            const input = document.getElementById('cmd-input');
            const text = input.value.trim();
            if (!text) return;

            // 界面状态切换
            document.getElementById('cmd-placeholder').style.display = 'none';
            document.getElementById('cmd-result-area').style.display = 'none';
            document.getElementById('cmd-loading').style.display = 'block';
            document.getElementById('run-output').innerText = ""; // 清空上次运行结果

            const modelId = document.getElementById('model-selector').value;

            window.pywebview.api.generate_cmd(text, currentShell, modelId).then(code => {
                document.getElementById('cmd-loading').style.display = 'none';
                document.getElementById('cmd-result-area').style.display = 'flex'; // Use flex for layout
                
                // 处理可能包含的markdown符号
                let cleanCode = code;
                if(code.startsWith("Error")) {
                    cleanCode = code; // 显示错误信息
                }
                
                document.getElementById('cmd-output').innerText = cleanCode;
                currentGeneratedCmd = cleanCode;
            });
        }

        function runCurrentCmd() {
            if(!currentGeneratedCmd) return;
            const outputBox = document.getElementById('run-output');
            outputBox.innerText = "正在初始化运行环境并执行...";
            
            window.pywebview.api.run_cmd(currentGeneratedCmd, currentShell).then(result => {
                outputBox.innerText = result;
            });
        }

        function copyCurrentCmd() {
            if(!currentGeneratedCmd) return;
            window.pywebview.api.copy_text(currentGeneratedCmd).then(() => {
                // 简单的视觉反馈
                const btn = document.querySelector('button[onclick="copyCurrentCmd()"]');
                const originalText = btn.innerText;
                btn.innerText = "✅ 已复制";
                setTimeout(() => btn.innerText = originalText, 1500);
            });
        }

        function saveCurrentCmd() {
             if(!currentGeneratedCmd) return;
             window.pywebview.api.save_cmd_file(currentGeneratedCmd, currentShell);
        }

        function saveHistory() {
             window.pywebview.api.save_history();
        }

        function loadHistory() {
            window.pywebview.api.load_history().then(history => {
                if (history && history.length > 0) {
                    // 清空当前聊天记录
                    const chatBox = document.getElementById('chat-box');
                    chatBox.innerHTML = '';
                    
                    // 重新加载聊天记录
                    history.forEach(msg => {
                        appendMessage(msg.role, msg.content);
                    });
                }
            });
        }

        // --- 窗口控制 ---        
        function closeApp() {
            window.pywebview.api.close_app();
        }
        
        function minimizeApp() {
            window.pywebview.api.minimize_app();
        }
        
        function maximizeApp() {
            window.pywebview.api.maximize_app();
        }

        // --- 悬浮球功能 ---        
        let isDragging = false;
        let offsetX, offsetY;
        let dragX = 0, dragY = 0;
        let animationFrameId = null;
        
        const floatingBall = document.getElementById('floating-ball');
        
        // 悬浮球点击事件
        floatingBall.addEventListener('click', function(e) {
            e.stopPropagation();
            // 切换应用窗口显示/隐藏
            const appContainer = document.getElementById('app-container');
            if (appContainer.style.display === 'none') {
                appContainer.style.display = 'flex';
            } else {
                // 这里可以添加最小化逻辑
                minimizeApp();
            }
        });
        
        // 悬浮球拖拽功能 - 优化版本
        floatingBall.addEventListener('mousedown', function(e) {
            e.stopPropagation();
            isDragging = true;
            const rect = floatingBall.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            floatingBall.style.cursor = 'grabbing';
        });
        
        // 使用requestAnimationFrame优化拖动性能
        function updateBallPosition() {
            if (isDragging) {
                floatingBall.style.left = dragX + 'px';
                floatingBall.style.top = dragY + 'px';
                floatingBall.style.bottom = 'auto';
                floatingBall.style.right = 'auto';
                animationFrameId = requestAnimationFrame(updateBallPosition);
            }
        }
        
        document.addEventListener('mousemove', function(e) {
            if (isDragging) {
                dragX = e.clientX - offsetX;
                dragY = e.clientY - offsetY;
                
                // 只在没有动画帧时启动新的动画帧
                if (!animationFrameId) {
                    animationFrameId = requestAnimationFrame(updateBallPosition);
                }
            }
        });
        
        document.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                floatingBall.style.cursor = 'pointer';
                // 取消动画帧
                if (animationFrameId) {
                    cancelAnimationFrame(animationFrameId);
                    animationFrameId = null;
                }
            }
        });

        // --- 设置功能 ---        
        function toggleFloatingBall(enabled) {
            const floatingBall = document.getElementById('floating-ball');
            if (enabled) {
                floatingBall.style.display = 'flex';
                window.pywebview.api.set_setting('floating_ball', true);
            } else {
                floatingBall.style.display = 'none';
                window.pywebview.api.set_setting('floating_ball', false);
            }
        }
        
        function toggleStartup(enabled) {
            window.pywebview.api.set_startup(enabled);
        }
        
        function toggleDarkTheme(enabled) {
            // 切换深色主题
            document.body.classList.toggle('dark-theme', enabled);
            window.pywebview.api.set_setting('dark_theme', enabled);
        }
        
        function changeOpacity(value) {
            // 改变窗口透明度
            document.getElementById('opacity-value').innerText = value + '%';
            // 注意：pywebview的窗口透明度设置可能需要特定API支持
            // 这里仅更新界面显示，实际透明度可能需要Python后端实现
            window.pywebview.api.set_setting('window_opacity', value);
        }
        
        function setBrowserHomepage(url) {
            // 设置浏览器默认首页
            window.pywebview.api.set_setting('browser_homepage', url);
        }
        
        function toggleAutoUpdate(enabled) {
            // 切换自动更新检查
            window.pywebview.api.set_setting('auto_update', enabled);
        }

        // --- 网页浏览功能 ---        
        function browserGo() {
            let url = document.getElementById('browser-url').value.trim();
            const iframe = document.getElementById('browser-iframe');
            const status = document.getElementById('browser-status');
            
            if (url) {
                // 检查是否是有效的URL，如果不是，默认使用百度搜索
                if (!url.startsWith('http://') && !url.startsWith('https://')) {
                    // 检查是否是IP地址或域名
                    if (/^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$/.test(url) || /^\\d+\\.\\d+\\.\\d+\\.\\d+$/.test(url)) {
                        url = 'https://' + url;
                    } else {
                        // 否则使用百度搜索
                        url = 'https://www.baidu.com/s?wd=' + encodeURIComponent(url);
                    }
                }
                
                status.innerText = '加载中...';
                // 清除之前的onload事件，避免重复绑定
                iframe.onload = null;
                // 设置新的onload事件
                iframe.onload = function() {
                    status.innerText = '加载完成';
                    // 加载完成后更新地址栏
                    document.getElementById('browser-url').value = iframe.src;
                    // 加载完成后处理页面内链接
                    setTimeout(handlePageLinks, 100);
                };
                // 处理iframe加载错误
                iframe.onerror = function() {
                    status.innerText = '加载失败';
                    console.error('iframe加载错误:', url);
                };
                // 设置iframe源
                iframe.src = url;
            }
        }
        
        // 处理页面内链接和表单提交
        function handlePageLinks() {
            const iframe = document.getElementById('browser-iframe');
            try {
                const doc = iframe.contentDocument || iframe.contentWindow.document;
                
                // 处理链接点击
                const links = doc.querySelectorAll('a');
                links.forEach(link => {
                    // 移除之前可能存在的事件监听器，避免重复绑定
                    const newLink = link.cloneNode(true);
                    link.parentNode.replaceChild(newLink, link);
                    
                    newLink.addEventListener('click', function(e) {
                        try {
                            const href = this.getAttribute('href');
                            if (href && !href.startsWith('#')) {
                                // 检查是否是相对路径或绝对路径
                                let targetUrl;
                                
                                if (href.startsWith('http://') || href.startsWith('https://')) {
                                    // 绝对路径
                                    targetUrl = href;
                                } else if (href.startsWith('/')) {
                                    // 根路径相对路径
                                    const currentUrl = new URL(iframe.src);
                                    targetUrl = currentUrl.origin + href;
                                } else {
                                    // 相对路径
                                    const currentUrl = new URL(iframe.src);
                                    const baseUrl = currentUrl.origin + currentUrl.pathname;
                                    targetUrl = new URL(href, baseUrl).href;
                                }
                                
                                // 阻止默认行为并在iframe中打开链接
                                e.preventDefault();
                                iframe.src = targetUrl;
                            }
                        } catch (error) {
                            // 忽略错误，让浏览器默认处理
                            console.log('链接处理错误:', error);
                        }
                    });
                });
                
                // 处理表单提交
                const forms = doc.querySelectorAll('form');
                forms.forEach(form => {
                    // 移除之前可能存在的事件监听器，避免重复绑定
                    const newForm = form.cloneNode(true);
                    form.parentNode.replaceChild(newForm, form);
                    
                    newForm.addEventListener('submit', function(e) {
                        try {
                            e.preventDefault();
                            const action = this.getAttribute('action') || '';
                            const method = this.getAttribute('method') || 'GET';
                            
                            // 收集表单数据
                            const formData = new FormData(this);
                            let params = new URLSearchParams();
                            formData.forEach((value, key) => {
                                params.append(key, value);
                            });
                            
                            // 构建提交URL
                            const currentUrl = new URL(iframe.src);
                            let formUrl;
                            
                            if (action.startsWith('http://') || action.startsWith('https://')) {
                                // 绝对URL
                                formUrl = new URL(action);
                            } else if (action.startsWith('/')) {
                                // 绝对路径
                                formUrl = new URL(action, currentUrl.origin);
                            } else {
                                // 相对路径
                                formUrl = new URL(action || currentUrl.pathname, currentUrl.href);
                            }
                            
                            if (method.toUpperCase() === 'GET') {
                                formUrl.search = params.toString();
                                iframe.src = formUrl.href;
                            } else {
                                // 对于POST请求，使用fetch发送
                                fetch(formUrl.href, {
                                    method: 'POST',
                                    body: formData,
                                    credentials: 'include', // 包含凭证
                                    headers: {
                                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                                    }
                                }).then(response => {
                                    if (!response.ok) {
                                        throw new Error('Network response was not ok');
                                    }
                                    return response.text();
                                }).then(html => {
                                    // 将响应内容直接写入iframe
                                    doc.open();
                                    doc.write(html);
                                    doc.close();
                                    // 重新处理新页面的链接和表单
                                    setTimeout(handlePageLinks, 100);
                                }).catch(error => {
                                    console.error('表单提交错误:', error);
                                    // 错误时让浏览器默认处理
                                    this.submit();
                                });
                            }
                        } catch (error) {
                            console.error('表单处理错误:', error);
                            // 忽略错误，让浏览器默认处理
                            this.submit();
                        }
                    });
                });
            } catch (error) {
                // 处理跨域访问错误
                console.log('无法访问页面内容（跨域限制）');
            }
        }
        
        function browserBack() {
            const iframe = document.getElementById('browser-iframe');
            iframe.contentWindow.history.back();
        }
        
        function browserForward() {
            const iframe = document.getElementById('browser-iframe');
            iframe.contentWindow.history.forward();
        }
        
        function browserRefresh() {
            const iframe = document.getElementById('browser-iframe');
            iframe.contentWindow.location.reload();
        }
        
        function browserSummary() {
            const iframe = document.getElementById('browser-iframe');
            const status = document.getElementById('browser-status');
            
            status.innerText = 'AI总结中...';
            
            // 获取网页内容
            const pageTitle = iframe.contentDocument.title;
            const pageContent = iframe.contentDocument.body.innerText;
            
            // 调用AI总结
            window.pywebview.api.summarize_webpage(pageTitle, pageContent).then(summary => {
                // 在聊天模式中显示总结
                switchMode('chat');
                appendMessage('ai', `## 网页总结\n\n**标题:** ${pageTitle}\n\n${summary}`);
                status.innerText = '总结完成';
            });
        }
        
        function browserDownload() {
            const iframe = document.getElementById('browser-iframe');
            const status = document.getElementById('browser-status');
            
            status.innerText = '准备下载...';
            
            try {
                // 获取当前页面URL
                const currentUrl = iframe.src;
                
                // 调用下载功能
                window.pywebview.api.download_webpage(currentUrl).then(() => {
                    status.innerText = '下载完成';
                }).catch(error => {
                    status.innerText = '下载失败';
                    console.error('下载错误:', error);
                });
            } catch (error) {
                status.innerText = '无法获取页面信息';
                console.error('下载错误:', error);
            }
        }
        
        // 专门处理工具箱模式的函数
        function switchToTools() {
            currentMode = 'tools';
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
            
            // 激活工具箱按钮
            document.querySelector('.nav-btn[onclick="switchToTools()"]').classList.add('active');
            // 显示工具箱面板
            document.getElementById('panel-tools').style.display = 'flex';
            // 更新标题
            document.getElementById('page-title').innerText = "工具箱";
            // 加载工具列表
            loadTools();
        }

        // --- 工具箱功能 ---
        let currentCategory = 'all';
        let allTools = [];
        
        // 加载工具列表
        function loadTools() {
            window.pywebview.api.get_tools().then(tools => {
                allTools = tools;
                renderTools();
            }).catch(error => {
                console.error('加载工具失败:', error);
                document.getElementById('tool-list').innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #ff6b6b;">
                        <div style="font-size: 4rem; margin-bottom: 20px;">❌</div>
                        <div style="font-size: 1.2rem; margin-bottom: 10px;">加载工具失败</div>
                        <div style="font-size: 0.9rem;">请检查文件权限或稍后重试</div>
                    </div>
                `;
            });
        }
        
        // 渲染工具列表
        function renderTools() {
            const toolList = document.getElementById('tool-list');
            const searchTerm = document.getElementById('tool-search').value.toLowerCase();
            
            // 过滤工具
            let filteredTools = allTools;
            
            // 按分类过滤
            if (currentCategory !== 'all') {
                filteredTools = filteredTools.filter(tool => tool.category === currentCategory);
            }
            
            // 按搜索词过滤
            if (searchTerm) {
                filteredTools = filteredTools.filter(tool => 
                    tool.name.toLowerCase().includes(searchTerm) ||
                    tool.path.toLowerCase().includes(searchTerm)
                );
            }
            
            // 渲染工具
            if (filteredTools.length === 0) {
                toolList.innerHTML = `
                    <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #666;">
                        <div style="font-size: 4rem; margin-bottom: 20px;">🔍</div>
                        <div style="font-size: 1.2rem; margin-bottom: 10px;">未找到工具</div>
                        <div style="font-size: 0.9rem;">尝试调整搜索条件或分类</div>
                    </div>
                `;
            } else {
                toolList.innerHTML = filteredTools.map(tool => `
                    <div class="tool-item" onclick="runTool('${tool.path}')" title="双击运行工具">
                        <div class="tool-icon">${getToolIcon(tool.category, tool.name)}</div>
                        <div class="tool-name">${tool.name}</div>
                        <div class="tool-path">${tool.path}</div>
                    </div>
                `).join('');
            }
        }
        
        // 获取工具图标
        function getToolIcon(category, name) {
            // 为特定工具设置专属图标
            const toolIcons = {
                'CPU-Z (32位)': '💻',
                'CPU-Z (64位)': '💻',
                'Core Temp (64位)': '🌡️',
                'Core Temp (32位)': '🌡️',
                'LinX': '⚡',
                'Prime95': '🔢',
                'ThrottleStop': '🛑',
                'Super PI': '🥧',
                'wPrime': '⚡',
                'Thaiphoon': '🧠',
                'ZenTimings': '⏱️',
                'MemTest': '🧪',
                'MemTest64': '🧪',
                'MemTestPro': '🧪',
                'TM5': '🔄',
                '魔方内存盘': '💿',
                'GPU-Z': '🎮',
                'GpuTest': '🎮',
                'GpuTest GUI': '🎮',
                'DXVAChecker': '🔍',
                'NVIDIA Inspector': '🎮',
                'NVIDIA Profile Inspector': '🎮',
                'AS SSD Benchmark': '💾',
                'ATTO 磁盘基准测试': '💾',
                'CrystalDiskInfo (32位)': '💾',
                'CrystalDiskInfo (64位)': '💾',
                'CrystalDiskMark (32位)': '💾',
                'CrystalDiskMark (64位)': '💾',
                'Defraggler': '🧹',
                'DiskGenius': '💾',
                'H2TestW': '🧪',
                'HD Tune': '🎵',
                'LLFTOOL': '🔧',
                'SSDZ': '💾',
                'UFO测试': '👽',
                '在线屏幕测试': '🖥️',
                '色域检测': '🎨',
                'Areson Mouse Test': '🖱️',
                'KeyTweak': '⌨️',
                'Keyboard Test Utility': '⌨️',
                'Mouse Rate': '🖱️',
                'Mouse Tester': '🖱️',
                '鼠标单击变双击测试器': '🖱️',
                'FurMark': '🔥',
                'CPU Burner': '🔥',
                'FurMark (64位 GUI)': '🔥',
                'FurMark (64位)': '🔥',
                'GameBuff': '🎮',
                'Steam 下载': '🎮',
                'Battle.net': '🎮',
                'EA App': '🎮',
                'Epic Games': '🎮',
                '小黑盒加速器': '🚀',
                '斧牛加速器': '🚀',
                '玩家动力': '🎮',
                '迅游加速器': '🚀',
                '迅雷加速器': '🚀',
                '雷神加速器': '⚡',
                '风灵月影': '🌙',
                '黑盒语音': '🎙️',
                'BatteryInfoView': '🔋',
                'DesktopOK': '🖥️',
                'DirectX Repair': '🔧',
                'Dism++ (ARM64)': '🔧',
                'Dism++ (x64)': '🔧',
                'Dism++ (x86)': '🔧',
                'Everything': '🔍',
                'Geek Uninstaller': '🧹',
                'UltraISO': '💿',
                'WinDbg': '🐛',
                'BlueScreenView (x64)': '🟦',
                'BlueScreenView (x86)': '🟦',
                'GifCam': '📷',
                'Next ITellyou': '💾',
                'Process Explorer': '🔍',
                'Process Explorer (64位)': '🔍',
                'Rufus': '📟',
                'Ventoy2Disk': '💿',
                'Ventoy Plugson': '💿'
            };
            
            // 如果工具有专属图标，返回它
            if (toolIcons[name]) {
                return toolIcons[name];
            }
            
            // 否则使用类别图标
            const categoryIcons = {
                processor: '💻',
                memory: '🧠',
                gpu: '🎮',
                disk: '💾',
                monitor: '🖥️',
                peripheral: '⌨️',
                stress: '🔥',
                game: '🎯',
                other: '📦'
            };
            
            return categoryIcons[category] || '📦';
        }
        
        // 选择分类
        function selectCategory(category) {
            currentCategory = category;
            document.querySelectorAll('.tool-category-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            renderTools();
        }
        
        // 运行工具
        function runTool(path) {
            window.pywebview.api.run_tool(path).then(result => {
                if (result.success) {
                    document.getElementById('tool-info').innerText = `工具已启动: ${result.message}`;
                } else {
                    document.getElementById('tool-info').innerText = `启动失败: ${result.message}`;
                }
            }).catch(error => {
                document.getElementById('tool-info').innerText = `错误: ${error.message}`;
            });
        }
        
        // 刷新工具列表
        function refreshTools() {
            document.getElementById('tool-list').innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #666;">
                    <div style="font-size: 4rem; margin-bottom: 20px;">🔄</div>
                    <div style="font-size: 1.2rem; margin-bottom: 10px;">刷新工具列表...</div>
                    <div style="font-size: 0.9rem;">正在重新扫描可用工具</div>
                </div>
            `;
            loadTools();
        }
        
        // 搜索工具
        document.getElementById('tool-search').addEventListener('input', renderTools);

    </script>
</body>
</html>
"""

# --- Python 后端逻辑 ---

class Api:
    def __init__(self):
        self.history = []
        self.tools_cache = None
        self.cache_timestamp = 0
        self.cache_duration = 300  # 缓存有效期（秒）

    def get_models(self):
        return MODELS

    def call_ai(self, messages, model_id, system_prompt=None):
        full_msgs = []
        if system_prompt:
            # 注意：某些模型可能不支持 system 角色，或者需要放在开头
            full_msgs.append({"role": "system", "content": system_prompt})
        full_msgs.extend(messages)
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": SITE_URL,
            "X-Title": SITE_NAME,
        }
        
        # 严格按照要求构建数据
        payload = {
            "model": model_id,
            "messages": full_msgs
        }

        try:
            # 打印调试信息
            print(f"\n=== API请求调试信息 ===")
            print(f"URL: https://openrouter.ai/api/v1/chat/completions")
            print(f"Headers: {json.dumps(headers, indent=2)}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            # 严格按照用户要求的格式构建请求
            resp = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30  # 添加30秒超时，避免网络请求阻塞
            )
            
            # 打印响应信息
            print(f"\n=== API响应调试信息 ===")
            print(f"状态码: {resp.status_code}")
            print(f"响应头: {json.dumps(dict(resp.headers), indent=2)}")
            print(f"响应内容: {resp.text}")
            
            # 如果状态码是 4xx/5xx，提供更友好的错误信息
            if resp.status_code >= 400:
                error_msg = f"API Error [{resp.status_code}]: {resp.text}"
                print(error_msg)
                
                # 针对常见错误码提供更友好的提示
                if resp.status_code == 400:
                    return f"请求错误 (400)：请求格式可能有问题。请检查输入内容或尝试更简单的表述。"
                elif resp.status_code == 401:
                    return f"认证错误 (401)：API Key 无效或已过期。请检查 API Key 设置。"
                elif resp.status_code == 402:
                    return f"付费错误 (402)：当前模型可能需要付费使用，请选择其他免费模型。"
                elif resp.status_code == 403:
                    return f"权限错误 (403)：您没有使用此模型的权限。"
                elif resp.status_code == 404:
                    return f"模型不存在 (404)：所选模型可能已被移除或名称错误。"
                elif resp.status_code == 429:
                    return f"请求过多 (429)：请求频率过高，请稍后重试或选择其他模型。"
                elif resp.status_code == 503:
                    return f"服务繁忙 (503)：API 服务器暂时繁忙，请稍后重试。"
                elif resp.status_code >= 500:
                    return f"服务器错误 ({resp.status_code})：API 服务器暂时不可用，请稍后重试。"
                else:
                    return f"API 错误 ({resp.status_code})：{resp.text}"

            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"网络/API 错误: {str(e)}"

    def chat_request(self, user_text, model_id):
        context = self.history[-5:] if self.history else []
        context.append({"role": "user", "content": user_text})
        
        response = self.call_ai(context, model_id)
        
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": response})
        return response

    def generate_cmd(self, user_text, shell_type, model_id):
        # 强化 Prompt，确保只输出代码
        system_prompt = (
            f"You are a Windows {shell_type} expert. "
            f"User will ask to perform a task. "
            f"You must output ONLY the raw {shell_type} code/command to achieve the task. "
            "When user asks to create '文本文档' or 'txt file', use echo command to create .txt files in CMD, or New-Item in PowerShell. "
            "IMPORTANT: Do NOT output markdown backticks (```). "
            "Do NOT output explanations. "
            "Do NOT output any intro or outro text. "
            "Just the raw executable code."
        )
        # 将用户请求包装，明确意图
        user_message = f"请给我生成一个 {shell_type} 命令: {user_text}"
        
        # 使用空的历史记录来确保纯净的生成
        response = self.call_ai([{"role": "user", "content": user_message}], model_id, system_prompt)
        
        # 清理可能存在的 Markdown 符号
        clean_code = response.replace("```bat", "").replace("```powershell", "").replace("```cmd", "").replace("```", "").strip()
        return clean_code

    def run_cmd(self, command, shell_type):
        """
        修复后的运行逻辑：使用临时文件执行，解决引号和转义问题。
        """
        try:
            timestamp = int(time.time())
            
            if shell_type == 'cmd':
                # 1. 创建临时 BAT 文件
                temp_file = f"_temp_run_{timestamp}.bat"
                # 强制使用 UTF-8 编码创建文件，并添加 chcp 65001 确保命令行使用 UTF-8
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write("@echo off\n") # 关闭回显
                    f.write("chcp 65001 > nul\n") # 切换到 UTF-8 防止中文乱码
                    f.write(command)

                # 2. 运行临时文件 - 使用 UTF-8 编码捕获输出
                res = subprocess.run([temp_file], capture_output=True, text=True, encoding='utf-8', errors='ignore', shell=True)
                
                # 3. 清理
                try: os.remove(temp_file) 
                except: pass

            else:
                # PowerShell 逻辑
                temp_file = f"_temp_run_{timestamp}.ps1"
                # 确保 PowerShell 文件使用 UTF-8 编码，并添加编码设置
                with open(temp_file, 'w', encoding='utf-8') as f:
                    # 添加 PowerShell UTF-8 编码设置
                    f.write("$OutputEncoding = [System.Text.UTF8Encoding]::UTF8\n")
                    f.write("[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8\n")
                    f.write(command)
                
                # Bypass 策略运行文件
                cmd_list = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_file]
                # 使用 UTF-8 编码捕获输出
                res = subprocess.run(cmd_list, capture_output=True, text=True, encoding='utf-8', errors='ignore')

                try: os.remove(temp_file) 
                except: pass
            
            # 格式化输出
            output = ""
            if res.stdout:
                output += f"{res.stdout}\n"
            if res.stderr:
                output += f"--- 错误信息 ---\n{res.stderr}"
            
            if not output.strip():
                output = "命令已执行 (无屏幕输出)"

            # 记录日志
            self.log_execution(shell_type, command, output)
            return output

        except Exception as e:
            return f"执行时发生严重错误: {str(e)}"

    def log_execution(self, shell, cmd, output):
        entry = {
            "timestamp": str(datetime.datetime.now()),
            "shell": shell,
            "command": cmd,
            "result": output
        }
        log_file = "execution_log.json"
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except: pass
        logs.append(entry)
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=4, ensure_ascii=False)
        except: pass

    def copy_text(self, text):
        pyperclip.copy(text)
        return True

    def save_cmd_file(self, content, shell_type):
        ext = "bat" if shell_type == 'cmd' else "ps1"
        file_types = ('Batch File (*.bat)', 'All files (*.*)') if shell_type == 'cmd' else ('PowerShell (*.ps1)', 'All files (*.*)')
        filename = window.create_file_dialog(webview.SAVE_DIALOG, allow_multiple=False, file_types=file_types, save_filename=f"script.{ext}")
        
        if filename:
            try:
                # 智能选择编码
                encoding = 'utf-8' if shell_type == 'powershell' else 'ansi'
                with open(filename, 'w', encoding=encoding) as f:
                    f.write(content)
                return True
            except Exception as e:
                return False
        return False

    def save_history(self):
        filename = window.create_file_dialog(webview.SAVE_DIALOG, save_filename=f"history_{datetime.datetime.now().strftime('%Y%m%d')}.jzxai")
        if filename:
            # 文件对话框返回元组，需要取第一个元素
            filename = filename[0]
            data = {"meta": {"author": "Jin Zaixi", "tool": SITE_NAME}, "history": self.history}
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    def load_history(self):
        filename = window.create_file_dialog(webview.OPEN_DIALOG, file_types=("JZXAI Files (*.jzxai)", "JSON Files (*.json)", "All Files (*.*)"))
        if filename:
            try:
                # 文件对话框返回元组，需要取第一个元素
                filename = filename[0]
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 兼容两种格式：有meta字段和没有meta字段的
                if isinstance(data, dict) and "history" in data:
                    self.history = data["history"]
                else:
                    # 直接是历史记录列表的情况
                    self.history = data
                
                return self.history
            except Exception as e:
                print(f"加载历史记录出错: {str(e)}")
                return []
        return []

    # --- 窗口控制方法 ---    
    def close_app(self):
        window.destroy()
    
    def minimize_app(self):
        window.minimize()
    
    def maximize_app(self):
        window.toggle_fullscreen()

    # --- 设置管理方法 ---    
    def set_setting(self, key, value):
        # 保存设置到配置文件
        config_file = "config.json"
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass
        
        config[key] = value
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except:
            pass
        
        return True
    
    def set_startup(self, enabled):
        # 设置开机自启动
        import winreg
        
        try:
            key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            if enabled:
                # 添加开机自启动
                exe_path = os.path.abspath(__file__)
                winreg.SetValueEx(key, 'ZaiXi AI', 0, winreg.REG_SZ, exe_path)
            else:
                # 删除开机自启动
                try:
                    winreg.DeleteValue(key, 'ZaiXi AI')
                except:
                    pass
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"设置开机自启动失败: {str(e)}")
            return False

    # --- 网页浏览方法 ---    
    def summarize_webpage(self, title, content):
        # 使用AI总结网页内容 - 优化版本
        system_prompt = "你是一个高效的网页内容总结助手，请用简洁明了的语言总结以下网页内容的核心要点。"
        
        # 进一步优化内容提取和长度限制
        # 只提取前2000个字符，提高处理速度
        user_message = f"标题: {title}\n\n内容: {content[:2000]}"  # 进一步限制内容长度
        
        # 使用默认模型进行总结
        response = self.call_ai([{"role": "user", "content": user_message}], MODELS[0]["id"], system_prompt)
        return response
    
    def download_webpage(self, url):
        # 下载网页内容
        import requests
        from urllib.parse import urlparse
        
        try:
            # 获取网页内容
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 解析文件名
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1]
            if not filename:
                filename = "webpage.html"
            elif not filename.endswith(('.html', '.htm', '.txt')):
                filename += ".html"
            
            # 保存文件
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return True
        except Exception as e:
            print(f"下载网页失败: {str(e)}")
            return False
    
    # --- 工具箱功能 ---
    def refresh_tool_cache(self):
        """
        刷新工具缓存
        """
        self.tools_cache = None
        self.cache_timestamp = 0
        return self.get_tools()
    
    def clear_tool_cache(self):
        """
        清除工具缓存
        """
        self.tools_cache = None
        self.cache_timestamp = 0
        return True
    
    def get_tools(self):
        """
        手动指定工具列表，确保每个工具都能正确加载
        """
        import os
        
        # 手动指定工具列表
        tools = [
            # 处理器工具
            {"name": "CPU-Z (32位)", "path": "处理器工具/CPUZ/cpuz_x32.exe", "category": "processor"},
            {"name": "CPU-Z (64位)", "path": "处理器工具/CPUZ/cpuz_x64.exe", "category": "processor"},
            {"name": "Core Temp (64位)", "path": "处理器工具/CoreTemp/Core Temp x64.exe", "category": "processor"},
            {"name": "Core Temp (32位)", "path": "处理器工具/CoreTemp/Core Temp x86.exe", "category": "processor"},
            {"name": "LinX", "path": "处理器工具/LinX/LinX.exe", "category": "processor"},
            {"name": "Prime95", "path": "处理器工具/Prime95/prime95.exe", "category": "processor"},
            {"name": "ThrottleStop", "path": "处理器工具/ThrottleStop/ThrottleStop.exe", "category": "processor"},
            {"name": "Super PI", "path": "处理器工具/superpi/Superpi.exe", "category": "processor"},
            {"name": "wPrime", "path": "处理器工具/wPrime/wPrime.exe", "category": "processor"},
            
            # 内存工具
            {"name": "Thaiphoon", "path": "内存工具/Thaiphoon/Thaiphoon.exe", "category": "memory"},
            {"name": "ZenTimings", "path": "内存工具/ZenTimings/ZenTimings.exe", "category": "memory"},
            {"name": "MemTest", "path": "内存工具/memtest/memtest.exe", "category": "memory"},
            {"name": "MemTest64", "path": "内存工具/memtest64/MemTest64.exe", "category": "memory"},
            {"name": "MemTestPro", "path": "内存工具/memtestpro/memtestpro.exe", "category": "memory"},
            {"name": "TM5", "path": "内存工具/tm5/TM5.exe", "category": "memory"},
            {"name": "魔方内存盘", "path": "内存工具/魔方内存盘/ramdisk.exe", "category": "memory"},
            
            # 显卡工具
            {"name": "GPU-Z", "path": "显卡工具/GPUZ/GPU-Z.exe", "category": "gpu"},
            {"name": "GpuTest", "path": "显卡工具/GpuTest_Windows x64/GpuTest.exe", "category": "gpu"},
            {"name": "GpuTest GUI", "path": "显卡工具/GpuTest_Windows x64/GpuTest_GUI.exe", "category": "gpu"},
            {"name": "DXVAChecker", "path": "显卡工具/dxvachecker/DXVAChecker.exe", "category": "gpu"},
            {"name": "NVIDIA Inspector", "path": "显卡工具/nvidiaInspector/nvidiaInspector.exe", "category": "gpu"},
            {"name": "NVIDIA Profile Inspector", "path": "显卡工具/nvidiaProfileInspector/nvidiaProfileInspector.exe", "category": "gpu"},
            
            # 硬盘工具
            {"name": "AS SSD Benchmark", "path": "硬盘工具/ASSSDBenchmark/ASSSDBenchmark.exe", "category": "disk"},
            {"name": "ATTO 磁盘基准测试", "path": "硬盘工具/ATTODISKBENCHMARK/ATTO 磁盘基准测试.exe", "category": "disk"},
            {"name": "CrystalDiskInfo (32位)", "path": "硬盘工具/CrystalDiskInfo/DiskInfo32S.exe", "category": "disk"},
            {"name": "CrystalDiskInfo (64位)", "path": "硬盘工具/CrystalDiskInfo/DiskInfo64S.exe", "category": "disk"},
            {"name": "CrystalDiskMark (32位)", "path": "硬盘工具/CrystalDiskMark/DiskMark32S.exe", "category": "disk"},
            {"name": "CrystalDiskMark (64位)", "path": "硬盘工具/CrystalDiskMark/DiskMark64S.exe", "category": "disk"},
            {"name": "Defraggler", "path": "硬盘工具/Defraggler/Defraggler.exe", "category": "disk"},
            {"name": "DiskGenius", "path": "硬盘工具/DiskGenius/DiskGenius.exe", "category": "disk"},
            {"name": "H2TestW", "path": "硬盘工具/H2testw/h2testw_1.4.exe", "category": "disk"},
            {"name": "HD Tune", "path": "硬盘工具/HDTune/HDTune.exe", "category": "disk"},
            {"name": "LLFTOOL", "path": "硬盘工具/LLFTOOL/LLFTOOL.exe", "category": "disk"},
            {"name": "SSDZ", "path": "硬盘工具/SSDZ/SSDZ.exe", "category": "disk"},
            
            # 显示器工具
            {"name": "UFO测试", "path": "显示器工具/UFO测试/Start.bat", "category": "monitor"},
            {"name": "在线屏幕测试", "path": "显示器工具/在线屏幕测试/在线屏幕测试.bat", "category": "monitor"},
            {"name": "色域检测", "path": "显示器工具/色域检测/monitorinfo.exe", "category": "monitor"},
            
            # 外设工具
            {"name": "Areson Mouse Test", "path": "外设工具/AresonMouseTest/鼠标测试软件AresonMouseTestProgram.exe", "category": "peripheral"},
            {"name": "KeyTweak", "path": "外设工具/KeyTweak/KeyTweak.exe", "category": "peripheral"},
            {"name": "Keyboard Test Utility", "path": "外设工具/Keyboard Test Utility/Keyboard Test Utility.exe", "category": "peripheral"},
            {"name": "Mouse Rate", "path": "外设工具/MOUSERATE/MOUSERATE.EXE", "category": "peripheral"},
            {"name": "Mouse Tester", "path": "外设工具/MouseTester/MouseTester.exe", "category": "peripheral"},
            {"name": "鼠标单击变双击测试器", "path": "外设工具/鼠标单机变双击测试器/鼠标单击变双击测试器V2.0.exe", "category": "peripheral"},
            
            # 烤鸡工具
            {"name": "FurMark", "path": "烤鸡工具/FurMark/FurMark.exe", "category": "stress"},
            {"name": "CPU Burner", "path": "烤鸡工具/FurMark/cpuburner.exe", "category": "stress"},
            {"name": "FurMark (64位 GUI)", "path": "烤鸡工具/FurMark_win64/FurMark_GUI.exe", "category": "stress"},
            {"name": "FurMark (64位)", "path": "烤鸡工具/FurMark_win64/furmark.exe", "category": "stress"},
            
            # 游戏工具
            {"name": "GameBuff", "path": "游戏工具/GameBuff/Start.bat", "category": "game"},
            {"name": "Steam 下载", "path": "游戏工具/Steam/下载Steam.bat", "category": "game"},
            {"name": "Battle.net", "path": "游戏工具/battle/Start.bat", "category": "game"},
            {"name": "EA App", "path": "游戏工具/eaapp/Start.bat", "category": "game"},
            {"name": "Epic Games", "path": "游戏工具/epic/Start.bat", "category": "game"},
            {"name": "小黑盒加速器", "path": "游戏工具/小黑盒加速器/小黑盒加速器.bat", "category": "game"},
            {"name": "斧牛加速器", "path": "游戏工具/斧牛加速器/Start.bat", "category": "game"},
            {"name": "玩家动力", "path": "游戏工具/玩家动力/Start.bat", "category": "game"},
            {"name": "迅游加速器", "path": "游戏工具/迅游加速器/Start.bat", "category": "game"},
            {"name": "迅雷加速器", "path": "游戏工具/迅雷加速器/Start.bat", "category": "game"},
            {"name": "雷神加速器", "path": "游戏工具/雷神加速器/Start.bat", "category": "game"},
            {"name": "风灵月影", "path": "游戏工具/风灵月影/Start.bat", "category": "game"},
            {"name": "黑盒语音", "path": "游戏工具/黑盒语音/黑盒语音.bat", "category": "game"},
            
            # 其他工具
            {"name": "BatteryInfoView", "path": "其他工具/BatteryInfoView/BatteryInfoView.exe", "category": "other"},
            {"name": "DesktopOK", "path": "其他工具/DesktopOK/DesktopOK.exe", "category": "other"},
            {"name": "DirectX Repair", "path": "其他工具/DirectX_Repair/DirectX Repair.exe", "category": "other"},
            {"name": "Dism++ (ARM64)", "path": "其他工具/Dism++/Dism++ARM64.exe", "category": "other"},
            {"name": "Dism++ (x64)", "path": "其他工具/Dism++/Dism++x64.exe", "category": "other"},
            {"name": "Dism++ (x86)", "path": "其他工具/Dism++/Dism++x86.exe", "category": "other"},
            {"name": "Everything", "path": "其他工具/Everything/everything.exe", "category": "other"},
            {"name": "Geek Uninstaller", "path": "其他工具/Geek Uninstaller/Geek Uninstaller.exe", "category": "other"},
            {"name": "UltraISO", "path": "其他工具/ULTRAISO/ULTRAISO.exe", "category": "other"},
            {"name": "WinDbg", "path": "其他工具/WinDbg/windbg.exe", "category": "other"},
            {"name": "BlueScreenView (x64)", "path": "其他工具/bluescreenview/BlueScreenViewx64.exe", "category": "other"},
            {"name": "BlueScreenView (x86)", "path": "其他工具/bluescreenview/BlueScreenViewx86.exe", "category": "other"},
            {"name": "GifCam", "path": "其他工具/gifcam/GifCam.exe", "category": "other"},
            {"name": "Next ITellyou", "path": "其他工具/next_itellyou/Start.bat", "category": "other"},
            {"name": "Process Explorer", "path": "其他工具/procexp/procexp.exe", "category": "other"},
            {"name": "Process Explorer (64位)", "path": "其他工具/procexp/procexp64.exe", "category": "other"},
            {"name": "Rufus", "path": "其他工具/rufus/rufus.exe", "category": "other"},
            {"name": "Ventoy2Disk", "path": "其他工具/ventoy/Ventoy2Disk.exe", "category": "other"},
            {"name": "Ventoy Plugson", "path": "其他工具/ventoy/VentoyPlugson.exe", "category": "other"}
        ]
        
        # 验证工具路径是否存在
        valid_tools = []
        for tool in tools:
            if os.path.exists(tool["path"]):
                valid_tools.append(tool)
            else:
                print(f"工具不存在: {tool['path']}")
        
        print(f"总共找到 {len(valid_tools)} 个有效工具")
        return valid_tools
    
    def run_tool(self, path):
        """
        运行指定路径的工具
        """
        import os
        import subprocess
        import sys
        
        try:
            # 获取绝对路径
            absolute_path = os.path.abspath(path)
            print(f"工具绝对路径: {absolute_path}")
            
            # 确保路径存在
            if not os.path.exists(absolute_path):
                return {"success": False, "message": "工具路径不存在"}
            
            # 获取工具所在目录
            tool_dir = os.path.dirname(absolute_path) or os.getcwd()
            print(f"运行工具: {absolute_path}，工作目录: {tool_dir}")
            
            # 尝试多种方式运行工具
            try:
                # 方式1: 使用os.startfile()（Windows特有，可能绕过权限限制）
                os.startfile(absolute_path)
                print("方式1: 使用os.startfile()成功")
                return {"success": True, "message": "工具已成功启动"}
            except Exception as e1:
                print(f"方式1运行失败: {str(e1)}")
                try:
                    # 方式2: 直接运行（使用creationflags创建新窗口）
                    subprocess.Popen([absolute_path], cwd=tool_dir, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                    print("方式2: 直接运行成功")
                    return {"success": True, "message": "工具已成功启动"}
                except Exception as e2:
                    print(f"方式2运行失败: {str(e2)}")
                    try:
                        # 方式3: 使用cmd.exe运行（管理员权限尝试）
                        cmd_command = f'"{absolute_path}"'
                        subprocess.Popen(["cmd.exe", "/c", cmd_command], cwd=tool_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
                        print("方式3: 使用cmd.exe成功")
                        return {"success": True, "message": "工具已成功启动"}
                    except Exception as e3:
                        print(f"方式3运行失败: {str(e3)}")
                        try:
                            # 方式4: 使用powershell运行（Bypass执行策略）
                            subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", absolute_path], cwd=tool_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
                            print("方式4: 使用powershell成功")
                            return {"success": True, "message": "工具已成功启动"}
                        except Exception as e4:
                            print(f"方式4运行失败: {str(e4)}")
                            try:
                                # 方式5: 使用powershell的Start-Process命令（可能绕过更多权限限制）
                                powershell_command = f'Start-Process "{absolute_path}" -WorkingDirectory "{tool_dir}"'
                                subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", powershell_command], creationflags=subprocess.CREATE_NEW_CONSOLE)
                                print("方式5: 使用Start-Process成功")
                                return {"success": True, "message": "工具已成功启动"}
                            except Exception as e5:
                                print(f"方式5运行失败: {str(e5)}")
                                try:
                                    # 方式6: 使用cmd.exe的start命令
                                    start_command = f'start "" "{absolute_path}"'
                                    subprocess.Popen(["cmd.exe", "/c", start_command], cwd=tool_dir, shell=True)
                                    print("方式6: 使用start命令成功")
                                    return {"success": True, "message": "工具已成功启动"}
                                except Exception as e6:
                                    print(f"方式6运行失败: {str(e6)}")
                                    return {"success": False, "message": f"运行失败: {str(e6)}"}
        except Exception as e:
            print(f"运行工具时出错: {str(e)}")
            return {"success": False, "message": str(e)}

# --- 主程序启动 ---
if __name__ == '__main__':
    api = Api()
    # 创建窗口
    window = webview.create_window(
        title=SITE_NAME,
        html=HTML_CODE,
        js_api=api,
        width=1100,
        height=800,
        resizable=True,
        background_color='#05070a', # 匹配新的背景色
        frameless=True,
        easy_drag=True
    )
    # 启动 GUI - 关闭调试模式
    webview.start(debug=False)
