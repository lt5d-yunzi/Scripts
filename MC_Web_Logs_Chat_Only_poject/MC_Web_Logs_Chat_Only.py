from http.server import BaseHTTPRequestHandler, HTTPServer
import time
from collections import deque
import html
import os
import logging

logging.basicConfig(level=logging.DEBUG)

class LogHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("""
        <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>Minecraft Log</h1>
                <div id="log" style="">
        """.encode('utf-8'))

        if isolation == "y":
            log_path = f".minecraft/versions/{version}/logs/latest.log"
        else:
            log_path = ".minecraft/logs/latest.log"

        print(f"读取日志文件：{log_path}")
        logfile = open(log_path, "r", encoding="utf-8")
        loglines = follow(logfile)
        chatlines = deque(maxlen=10)
        for line in loglines:
            if "[CHAT]" in line:
                chatline = line.split("[CHAT]", 1)[1].strip()
                chatlines.append(chatline)
                log_content = ''.join(html.escape(chatline) + '<br>' for chatline in chatlines)
                self.wfile.write(f"""
                    <script>
                        document.getElementById("log").innerHTML = "{log_content}";
                    </script>
                """.encode('utf-8'))
                self.wfile.flush()
        logging.debug(f"收到HTTP请求：{self.command} {self.path}")


def follow(thefile):
    thefile.seek(0,2)
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

if __name__ == '__main__':
    if ".minecraft" in os.listdir():
        print("找到 .minecraft 文件夹")
    else:
        input("请将软件放在启动器目录下，按任意键退出...")
        exit()

    isolation = input("是否开启版本隔离？(y/n) ")
    if isolation == "y":
        versions_path = ".minecraft/versions"
        versions = [d for d in os.listdir(versions_path) if os.path.isdir(os.path.join(versions_path, d))]
        print("可用版本：")
        for i, version in enumerate(versions):
            print(f"{i + 1}. {version}")
        choice = int(input("请选择版本："))
        version = versions[choice - 1]

    server = HTTPServer(('0.0.0.0', 8080), LogHandler)
    print("web服务已经启动，按下组合键<Ctrl-C>停止服务")
    print("已经在8080开启服务，无法访问请检查防火墙是否放通8080端口")
    server.serve_forever()
