import os
import re
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许所有来源的跨域请求
log_data = ""  # 存储log信息的全局变量
socks_ip = ""  # 存储 SOCKS 代理 IP 的全局变量
socks_port = ""  # 存储 SOCKS 代理端口的全局变量

# Minecraft颜色代码与HTML颜色代码的映射
MC_COLOR_TO_HTML = {
    "§0": "#000000", "§1": "#0000AA", "§2": "#00AA00", "§3": "#00AAAA",
    "§4": "#AA0000", "§5": "#AA00AA", "§6": "#FFAA00", "§7": "#AAAAAA",
    "§8": "#555555", "§9": "#5555FF", "§a": "#55FF55", "§b": "#55FFFF",
    "§c": "#FF5555", "§d": "#FF55FF", "§e": "#FFFF55", "§f": "#FFFFFF",
}

def translate_mc_colors(text):
    # 将Minecraft颜色代码替换为对应的HTML颜色代码
    for mc_color, html_color in MC_COLOR_TO_HTML.items():
        text = text.replace(mc_color, f'<span style="color:{html_color};">')

    # 替换结束符
    text = text.replace("§r", "</span>")
    return text

def get_log_file_path(version=None):
    base_path = '.minecraft'
    if version:
        log_path = os.path.join(base_path, 'versions', version, 'logs', 'latest.log')
    else:
        log_path = os.path.join(base_path, 'logs', 'latest.log')

    return log_path

def read_log_file(log_path):
    global log_data
    with open(log_path, 'r', encoding='utf-8') as log_file:
        logs = log_file.readlines()

    chat_logs = []
    for line in logs:
        if '[CHAT]' in line:
            # 提取[CHAT]后面的信息并转译颜色代码
            chat_message = re.sub(r'^.*\[CHAT\]\s*', '', line)
            chat_message = translate_mc_colors(chat_message)
            chat_logs.append(chat_message)

    log_data = '<br>'.join(chat_logs)

    # 发送log信息到网页
    socketio.emit('log_update', {'log_data': log_data}, namespace='/')

# 处理保存设置的事件
@socketio.on('save_settings')
def handle_save_settings(data):
    global socks_ip, socks_port
    socks_ip = data.get('socks_ip', '')
    socks_port = data.get('socks_port', '')
    print(f"保存设置：SOCKS IP: {socks_ip}, 端口: {socks_port}")

# 处理清空日志的事件
@socketio.on('clear_log')
def handle_clear_log(data):
    global log_data
    log_data = ""
    socketio.emit('log_update', {'log_data': log_data}, namespace='/')

def start_log_monitoring(version=None):
    log_path = get_log_file_path(version)
    read_log_file(log_path)

    if not os.path.exists(log_path):
        log_data = "Log文件未找到。"
        return

    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class LogFileHandler(FileSystemEventHandler):
        def on_modified(self, event):
            read_log_file(log_path)

    event_handler = LogFileHandler()
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname(log_path), recursive=False)
    observer.start()

if __name__ == '__main__':
    version_isolated = input("是否开启版本隔离？(是/否) ").lower().strip()

    if version_isolated == '是':
        version = input("请选择版本: ")
    else:
        version = None

    start_log_monitoring(version)

    threading.Thread(target=socketio.run, args=(app, ), kwargs={'host': '0.0.0.0', 'port': 8080}).start()

