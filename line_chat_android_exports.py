import os
import subprocess
import xml.etree.ElementTree as ET
import re
import time
import sys

# ================= 国际化配置 (i18n) =================
LANG_CONFIG = {
    "1": {
        "id": "zh",
        "menu_name": "简体中文",
        "no_device": "未找到设备，请检查 ADB 连接",
        "device_id": "已连接设备: ",
        "locked": "错误: 屏幕已锁定，请手动解锁",
        "opened": "Line 已启动",
        "tab_selected": "已进入聊天列表",
        "processing": "\n--- 正在处理联系人: {} ---",
        "scanning": ">>> 正在同步聊天记录与媒体: {}",
        "next_page": "当前页处理完毕，向下滑动寻找更多联系人...",
        "no_tab": "未能定位到聊天主标签页",
        "media_found": "   > 发现媒体 ({})，正在下载...",
        "save_success": "   [媒体成功] 已保存: {}",
        "log_saved": "   [记录成功] 文本已写入 chat_history.txt"
    },
    "2": {
        "id": "en",
        "menu_name": "English",
        "no_device": "No device found, please check ADB connection",
        "device_id": "Connected device: ",
        "locked": "Error: Screen is locked, please unlock manually",
        "opened": "Line started",
        "tab_selected": "Entered chat list",
        "processing": "\n--- Processing contact: {} ---",
        "scanning": ">>> Syncing chat history and media: {}",
        "next_page": "Current page finished, scrolling for more...",
        "no_tab": "Could not locate the Chats tab",
        "media_found": "   > Media found ({}), downloading...",
        "save_success": "   [Media Success] Saved: {}",
        "log_saved": "   [Log Success] Text written to chat_history.txt"
    },
    "3": {
        "id": "ja",
        "menu_name": "日本語",
        "no_device": "デバイスが見つかりません。ADB接続を確認してください",
        "device_id": "接続済みデバイス: ",
        "locked": "エラー：画面がロックされています。解除してください",
        "opened": "Lineを起動しました",
        "tab_selected": "トークリストに入りました",
        "processing": "\n--- 連絡先を処理中: {} ---",
        "scanning": ">>> トーク履歴とメディアを同期中: {}",
        "next_page": "現在のページを完了、次を読み込み中...",
        "no_tab": "トークタブが見つかりません",
        "media_found": "   > メディアを発見 ({})、ダウンロード中...",
        "save_success": "   [成功] 保存先: {}",
        "log_saved": "   [成功] トーク履歴を chat_history.txt に保存しました"
    }
}

T = {}


def select_language():
    global T
    print("1. 简体中文 | 2. English | 3. 日本語")
    choice = input("Select Language (1/2/3): ").strip()
    T = LANG_CONFIG.get(choice, LANG_CONFIG["1"])


# ================= 配置与路径 =================
SAVE_ROOT_DIR = "line_backup_data"
DOWNLOAD_TIMEOUT = 30
ANDROID_PIC_DIR = "/sdcard/Pictures/LINE"
ANDROID_MOV_DIR = "/sdcard/Movies/LINE"


def execute(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout.split('\n')
    except:
        return []


# ================= 核心工具函数 =================

def get_xml_dump(device_id):
    execute(f"adb -s {device_id} shell uiautomator dump /sdcard/uidump.xml")
    return "".join(execute(f"adb -s {device_id} shell cat /sdcard/uidump.xml")).strip()


def get_coords(bounds_str):
    coords = re.findall(r'\d+', bounds_str)
    x1, y1, x2, y2 = map(int, coords)
    return (x1 + x2) // 2, (y1 + y2) // 2


def save_chat_log(folder_path, sender, msg_time, msg_type, content):
    """保存聊天文字到本地文件"""
    file_path = os.path.join(folder_path, "chat_history.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        log_line = f"[{msg_time}] {sender}: ({msg_type}) {content}\n"
        f.write(log_line)


# ================= 媒体与内容处理 =================

def process_single_row(device_id, row_node, chat_name, folder_path, processed_keys):
    """处理单条聊天消息：保存文字并下载媒体"""
    # 提取基础信息
    time_node = row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_timestamp']")
    msg_time = time_node.get('text') if time_node is not None else "Unknown Time"

    sender = "Me"
    if row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_thumbnail']") is not None:
        sender = chat_name

    # 唯一标识该条消息
    unique_key = f"{msg_time}_{row_node.get('bounds')}"
    if unique_key in processed_keys:
        return False

    # 判定内容类型
    msg_type = "text"
    content = ""
    target_node = None

    text_node = row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_message_text']")
    video_node = row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_video_thumbnail']")
    image_node = row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_image_thumbnail']") or \
                 row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_image_balloon_root']")

    if text_node is not None:
        content = text_node.get('text')
    elif video_node is not None:
        msg_type, content, target_node = "video", "[Video File]", video_node
    elif image_node is not None:
        msg_type, content, target_node = "image", "[Image File]", image_node
    else:
        # 系统消息或表情
        layout = row_node.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_message_layout']")
        content = layout.get('content-desc', '[Other Media]') if layout is not None else "[System Message]"
        msg_type = "system/sticker"

    # 1. 保存文字记录
    save_chat_log(folder_path, sender, msg_time, msg_type, content)

    # 2. 如果是媒体，执行下载逻辑
    if target_node is not None:
        download_media(device_id, target_node.get('bounds'), folder_path, msg_type)

    processed_keys.add(unique_key)
    return True


def download_media(device_id, bounds, folder_path, msg_type):
    """点击下载按钮并同步文件"""
    print(T["media_found"].format(msg_type))
    x, y = get_coords(bounds)
    execute(f"adb -s {device_id} shell input tap {x} {y}")
    time.sleep(1.5)

    # 查找并点击下载按钮
    def get_dl_btn():
        xml = get_xml_dump(device_id)
        try:
            root = ET.fromstring(xml)
            node = root.find(".//node[@resource-id='jp.naver.line.android:id/chat_media_content_download_button']")
            return node.get('bounds') if node is not None else None
        except:
            return None

    dl_bounds = get_dl_btn()
    if not dl_bounds:
        execute(f"adb -s {device_id} shell input tap 500 1000")  # 唤醒
        time.sleep(0.5)
        dl_bounds = get_dl_btn()

    if dl_bounds:
        remote_dir = ANDROID_MOV_DIR if msg_type == "video" else ANDROID_PIC_DIR
        # 获取点之前的最新文件
        pre_file = execute(f"adb -s {device_id} shell ls -t {remote_dir} | head -n 1")[0].strip()

        dx, dy = get_coords(dl_bounds)
        execute(f"adb -s {device_id} shell input tap {dx} {dy}")

        # 监控新文件产生
        start_t = time.time()
        while time.time() - start_t < DOWNLOAD_TIMEOUT:
            cur_file = execute(f"adb -s {device_id} shell ls -t {remote_dir} | head -n 1")[0].strip()
            if cur_file and cur_file != pre_file and "No such" not in cur_file:
                local_path = os.path.join(folder_path, f"{int(time.time())}_{cur_file}")
                execute(f"adb -s {device_id} pull \"{remote_dir}/{cur_file}\" \"{local_path}\"")
                print(T["save_success"].format(cur_file))
                break
            time.sleep(0.5)

    execute(f"adb -s {device_id} shell input keyevent 4")  # 返回聊天页
    time.sleep(1.0)


# ================= 主流程 =================

def main():
    select_language()
    did = execute("adb devices")[1].split("\t")[0] if len(execute("adb devices")) > 1 else None
    if not did: print(T["no_device"]); return

    print(T["opened"])
    # 假定已在聊天列表或自动进入
    processed_contacts = set()

    while True:
        xml = get_xml_dump(did)
        root = ET.fromstring(xml)
        # 获取所有聊天项
        contacts = []
        for node in root.iter('node'):
            if node.get('resource-id') == "jp.naver.line.android:id/root":
                name = next((s.get('text') for s in node.iter('node') if
                             s.get('resource-id') == "jp.naver.line.android:id/name"), "Unknown")
                contacts.append({"name": name, "bounds": node.get('bounds')})

        action = False
        for person in contacts:
            if person['name'] in processed_contacts: continue

            print(T["processing"].format(person['name']))
            # 创建文件夹
            safe_name = "".join(x for x in person['name'] if x.isalnum() or x in (' ', '_'))
            folder_path = os.path.join(SAVE_ROOT_DIR, safe_name)
            if not os.path.exists(folder_path): os.makedirs(folder_path)

            # 点击进入
            x, y = get_coords(person['bounds'])
            execute(f"adb -s {did} shell input tap {x} {y}")
            time.sleep(2)

            # 抓取历史
            print(T["scanning"].format(person['name']))
            history_keys = set()
            prev_sig = ""
            for _ in range(20):  # 滑动次数
                cur_xml = get_xml_dump(did)
                try:
                    tree = ET.fromstring(cur_xml)
                    rows = tree.findall(
                        ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_swipeable_framelayout']")
                    if not rows or rows[0].get('bounds') == prev_sig: break
                    prev_sig = rows[0].get('bounds')

                    # 从下往上处理每一行，保证逻辑顺序
                    for r in reversed(rows):
                        process_single_row(did, r, person['name'], folder_path, history_keys)
                except:
                    break

                # 向上滑动看历史
                execute(f"adb -s {did} shell input swipe 500 800 500 1600 400")
                time.sleep(1.5)

            execute(f"adb -s {did} shell input keyevent 4")  # 返回列表
            processed_contacts.add(person['name'])
            action = True
            break

        if not action:
            print(T["next_page"])
            execute(f"adb -s {did} shell input swipe 500 1600 500 800 400")
            time.sleep(2)


if __name__ == "__main__":
    main()