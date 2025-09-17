# Stay-Hungry - 服药提醒小程序

这是一个简单的命令行工具，帮助老年人按时服药。程序会读取 JSON 配置文件，按照设定的时间循环提醒。

## 快速开始

1. 创建一个配置文件（例如 `medications.json`）：

   ```json
   {
     "check_interval_minutes": 1,
     "medications": [
       {
         "name": "降压药",
         "dosage": "1片",
         "times": ["08:00", "20:00"],
         "notes": "饭后服用"
       },
       {
         "name": "维生素D",
         "dosage": "2滴",
         "times": ["09:00"],
         "notes": "晒完太阳后服用"
       }
     ]
   }
   ```

2. 在终端中运行提醒程序：

   ```bash
   python medication_reminder.py medications.json
   ```

   默认会展示接下来一天的所有提醒，并开始定时轮询。按下 `Ctrl+C` 可安全退出。

## 功能特点

- 支持多个药品与多个提醒时间。
- 每次提醒会在终端发出响铃并显示剂量、备注信息。
- 可通过 `check_interval_minutes` 调整检查间隔，确保提醒及时。
- 启动前自动列出指定天数内的服药安排，方便家属确认。

## 开发与测试

项目包含一组 `pytest` 单元测试，验证时间解析和提醒生成的核心逻辑。

```bash
pytest
```

欢迎根据家庭成员的实际情况调整配置文件，以便提供贴心的用药提醒。
