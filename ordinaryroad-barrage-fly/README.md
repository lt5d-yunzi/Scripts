#基于python和让弹幕飞的弹幕朗读程序

#安装依赖
- 推荐使用python3.8.x
```
 pip install aiohttp pyttsx3 rsocket-py reactivestreams

```
#启动参数
```
  --uri URI     WebSocket 服务器地址
  -t T         任务id
  --enable-tts  启用 TTS 语音朗读
  --rate RATE   TTS语速，默认200
```
- 启动程序：
```
#可以连接多个平台
#示例↓↓↓↓
python .\ttsclient.py -t [任务id] -t  [任务id] -t  [任务id] --enable-tts --rate [语速]
```