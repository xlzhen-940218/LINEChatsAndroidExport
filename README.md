# LINE Chat Exporter & Media Backup (ADB)
---

## 🇨🇳 简体中文

### 项目简介

这是一个基于 **ADB (Android Debug Bridge)** 的自动化 Python 脚本，旨在帮助用户将 Android 设备上 **LINE** 应用的聊天记录、图片和视频自动导出并备份到本地电脑。

### 🚀 功能特性

* **多语言界面**：支持 简体中文、English、日本語。
* **文本记录导出**：自动抓取聊天内容并按时间顺序存入 `chat_history.txt`。
* **媒体文件同步**：智能识别图片和视频，模拟点击下载并利用 `adb pull` 将原始文件同步至电脑。
* **自动遍历**：自动滑动联系人列表，逐一进入对话框处理历史记录。
* **结构化存储**：按联系人名称创建独立文件夹，方便整理。

### 🛠️ 环境准备

1. **Python 3.x**: 运行脚本的基础环境。
2. **ADB 工具**: 安装 Android Platform-Tools，并将 `adb` 加入系统环境变量。
3. **Android 手机**:
* 开启 **USB 调试**。
* 保持 LINE 已登录且处于聊天列表界面。
* 运行期间请保持屏幕常亮并解锁。



---

## 🇺🇸 English

### Project Overview

An automated Python script powered by **ADB (Android Debug Bridge)**, designed to export and back up **LINE** chat histories, images, and videos from an Android device to your local PC.

### 🚀 Key Features

* **i18n Support**: Command-line interface available in English, Chinese, and Japanese.
* **Text Extraction**: Scrapes chat messages and saves them chronologically to `chat_history.txt`.
* **Media Sync**: Detects images/videos, triggers the download UI, and uses `adb pull` to transfer files to your storage.
* **Auto-Navigation**: Automatically scrolls through contact lists and chat logs without manual intervention.
* **Organized Storage**: Creates individual folders per contact for clean data management.

### 🛠️ Prerequisites

1. **Python 3.x**: Required to run the script.
2. **ADB Tools**: Android Platform-Tools must be installed and added to your `PATH`.
3. **Android Device**:
* **USB Debugging** enabled.
* LINE app logged in and opened to the chat list.
* Screen must stay unlocked during the process.



---

## 🇯🇵 日本語

### プロジェクト概要

このツールは **ADB (Android Debug Bridge)** を利用した Python 自動化スクリプトです。Android 端末上の **LINE** トーク履歴、写真、および動画を自動的に抽出し、ローカル PC にバックアップします。

### 🚀 主な機能

* **多言語対応**: 日本語、英語、簡体字中国語をサポート。
* **トーク履歴の保存**: メッセージ内容を抽出して `chat_history.txt` に保存します。
* **メディア同期**: トーク内の写真や動画を自動で認識してダウンロードし、`adb pull` で PC に転送します。
* **自動スクロール**: 連絡先リストやトークルームを自動でスクロールして処理します。
* **フォルダ整理**: 連絡先名ごとにフォルダを作成し、データを整理して保存します。

### 🛠️ 準備事項

1. **Python 3.x**: 実行環境として必要です。
2. **ADB ツール**: Android Platform-Tools をインストールし、環境変数（Path）を通してください。
3. **Android 端末**:
* **USB デバッグ**を有効にする。
* LINE にログインし、トーク一覧画面を表示しておく。
* 実行中は画面のロックを解除し、点灯状態を維持してください。



---

## 📥 Installation & Usage / 安装与使用 / 使用方法

```bash
# 1. Clone the repository / 克隆仓库
git clone https://github.com/your-username/line-exporter.git
cd line-exporter

# 2. Connect device via USB / 连接手机
adb devices

# 3. Run the script / 运行脚本
python line_backup.py

```

## ⚠️ Disclaimer / 免责声明 / 免責事項

This tool is for personal backup and educational purposes only. Please comply with local laws and respect others' privacy.
本工具仅供个人备份与学习研究使用，请遵守当地法律法规并尊重他人隐私。
本ツールは個人情報のバックアップおよび学習目的のみを意図しています。現地の法律を遵守し、他人のプライバシーを尊重してください。
