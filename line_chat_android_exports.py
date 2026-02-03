import os
import subprocess
import xml.etree.ElementTree as ET
import re
import time
import sys

# ================= 国际化配置 (i18n) =================
LANG_CONFIG = {
    "1": {  # 中文
        "id": "zh",
        "menu_name": "简体中文",
        "no_device": "未找到设备，请检查 ADB 连接",
        "device_id": "已连接设备: ",
        "locked": "错误: 屏幕已锁定，请手动解锁",
        "opened": "Line 已启动",
        "tab_selected": "已进入聊天列表",
        "processing": "\n--- 正在处理联系人: {} ---",
        "scanning": ">>> 正在分析会话历史: {}",
        "next_page": "当前页处理完毕，向下滑动寻找更多联系人...",
        "no_tab": "未能定位到聊天主标签页",
        "media_found": "   > 发现媒体内容 ({}): 正在尝试下载...",
        "save_success": "   [成功] 保存至: {}"
    },
    "2": {  # English
        "id": "en",
        "menu_name": "English",
        "no_device": "No device found, please check ADB connection",
        "device_id": "Connected device: ",
        "locked": "Error: Screen is locked, please unlock manually",
        "opened": "Line started",
        "tab_selected": "Entered chat list",
        "processing": "\n--- Processing contact: {} ---",
        "scanning": ">>> Analyzing chat history: {}",
        "next_page": "Current page finished, scrolling for more...",
        "no_tab": "Could not locate the Chats tab",
        "media_found": "   > Media found ({}): Downloading...",
        "save_success": "   [Success] Saved to: {}"
    },
    "3": {  # 日本語
        "id": "ja",
        "menu_name": "日本語",
        "no_device": "デバイスが見つかりません。ADB接続を確認してください",
        "device_id": "接続済みデバイス: ",
        "locked": "エラー：画面がロックされています。解除してください",
        "opened": "Lineを起動しました",
        "tab_selected": "トークリストに入りました",
        "processing": "\n--- 連絡先を処理中: {} ---",
        "scanning": ">>> トーク履歴を分析中: {}",
        "next_page": "現在のページを完了、次を読み込み中...",
        "no_tab": "トークタブが見つかりません",
        "media_found": "   > メディアを発見 ({}): ダウンロード中...",
        "save_success": "   [成功] 保存先: {}"
    }
}

# 全局语言变量，由用户选择后初始化
T = {}


def select_language():
    global T
    print("========================================")
    print("  Please select a language / 请选择语言")
    print("  1. 简体中文")
    print("  2. English")
    print("  3. 日本語")
    print("========================================")
    choice = input("Choice (1/2/3): ").strip()
    if choice not in LANG_CONFIG:
        choice = "1"  # 默认中文
    T = LANG_CONFIG[choice]
    print(f"Selected: {T['menu_name']}\n")


# ================= 路径与参数配置 =================
SAVE_ROOT_DIR = "line_media_downloads"
SCROLL_SLEEP = 1.5
MEDIA_LOAD_SLEEP = 1.5
DOWNLOAD_TIMEOUT = 30
POLL_INTERVAL = 0.5
ANDROID_PIC_DIR = "/sdcard/Pictures/LINE"
ANDROID_MOV_DIR = "/sdcard/Movies/LINE"


# ================= 核心 ADB 功能 =================

def execute(command: str) -> list[str]:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        return result.stdout.split('\n')
    except:
        return []


def get_device_id() -> str | None:
    _lines = execute("adb devices")
    if len(_lines) > 1 and "device" in _lines[1]:
        return _lines[1].split("\t")[0]
    return None


def check_lock_screen(device_id: str) -> bool:
    _lines = execute(f"adb -s {device_id} shell dumpsys window policy")
    return any("showing=true" in line for line in _lines)


def open_line(device_id: str) -> bool:
    execute(f"adb -s {device_id} shell am start -n jp.naver.line.android/jp.naver.line.android.activity.SplashActivity")
    time.sleep(3)
    return True


def get_xml_dump(device_id):
    execute(f"adb -s {device_id} shell uiautomator dump /sdcard/uidump.xml")
    content_lines = execute(f"adb -s {device_id} shell cat /sdcard/uidump.xml")
    return "".join(content_lines).strip()


def get_coords_from_bounds(bounds_str):
    if not bounds_str: return None
    coords = re.findall(r'\d+', bounds_str)
    if len(coords) < 4: return None
    x1, y1, x2, y2 = map(int, coords)
    return {"center": ((x1 + x2) // 2, (y1 + y2) // 2)}


def tap(device_id, x, y):
    execute(f"adb -s {device_id} shell input tap {x} {y}")


def swipe(device_id, start_x, start_y, end_x, end_y):
    execute(f"adb -s {device_id} shell input swipe {start_x} {start_y} {end_x} {end_y} 400")
    time.sleep(SCROLL_SLEEP)


# ================= 媒体处理逻辑 =================

def get_latest_remote_filename(device_id, remote_dir):
    cmd = f"adb -s {device_id} shell ls -t {remote_dir} | head -n 1"
    lines = execute(cmd)
    if lines and lines[0].strip() and "No such" not in lines[0]:
        return lines[0].strip()
    return None


def process_media(device_id, bounds_str, chat_name, msg_type):
    coords = get_coords_from_bounds(bounds_str)
    if not coords: return

    print(T["media_found"].format(msg_type))
    tap(device_id, coords['center'][0], coords['center'][1])
    time.sleep(MEDIA_LOAD_SLEEP)

    # 查找下载按钮
    xml = get_xml_dump(device_id)
    dl_btn_id = "jp.naver.line.android:id/chat_media_content_download_button"

    def find_dl_node(xml_text):
        try:
            root = ET.fromstring(xml_text)
            node = root.find(f".//node[@resource-id='{dl_btn_id}']")
            return node.get('bounds') if node is not None else None
        except:
            return None

    dl_bounds = find_dl_node(xml)
    if not dl_bounds:
        tap(device_id, 500, 1000)  # 唤醒UI
        time.sleep(0.8)
        dl_bounds = find_dl_node(get_xml_dump(device_id))

    if dl_bounds:
        target_dir = ANDROID_MOV_DIR if msg_type == "video" else ANDROID_PIC_DIR
        pre_file = get_latest_remote_filename(device_id, target_dir)

        c = get_coords_from_bounds(dl_bounds)
        tap(device_id, c['center'][0], c['center'][1])

        save_path = os.path.join(SAVE_ROOT_DIR, "".join(x for x in chat_name if x.isalnum() or x in (' ', '_')))
        if not os.path.exists(save_path): os.makedirs(save_path)

        # 监控文件变化并拉取
        start_t = time.time()
        while time.time() - start_t < DOWNLOAD_TIMEOUT:
            cur_file = get_latest_remote_filename(device_id, target_dir)
            if cur_file and cur_file != pre_file:
                local_path = os.path.join(save_path, f"{int(time.time())}_{cur_file}")
                execute(f"adb -s {device_id} pull \"{target_dir}/{cur_file}\" \"{local_path}\"")
                print(T["save_success"].format(local_path))
                break
            time.sleep(POLL_INTERVAL)

    execute(f"adb -s {device_id} shell input keyevent 4")
    time.sleep(1.0)


# ================= 聊天内容解析 =================

def fetch_chat_history(device_id, chat_name):
    print(T["scanning"].format(chat_name))
    processed_keys = set()
    prev_sig = None

    for _ in range(30):
        xml = get_xml_dump(device_id)
        try:
            root = ET.fromstring(xml)
            rows = root.findall(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_swipeable_framelayout']")
            curr_sig = rows[0].get('bounds') if rows else "empty"
        except:
            curr_sig = "err"

        if prev_sig == curr_sig: break
        prev_sig = curr_sig

        while True:
            found_new = False
            cur_xml = get_xml_dump(device_id)
            tree = ET.fromstring(cur_xml)
            rows = tree.findall(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_swipeable_framelayout']")
            for row in reversed(rows):
                t_node = row.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_timestamp']")
                m_key = f"{t_node.get('text') if t_node is not None else ''}_{row.get('bounds')}"
                if m_key in processed_keys: continue

                v = row.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_video_thumbnail']")
                img = row.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_image_thumbnail']") or \
                      row.find(".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_image_balloon_root']")

                if v is not None:
                    process_media(device_id, v.get('bounds'), chat_name, "video")
                    processed_keys.add(m_key);
                    found_new = True;
                    break
                elif img is not None:
                    process_media(device_id, img.get('bounds'), chat_name, "image")
                    processed_keys.add(m_key);
                    found_new = True;
                    break
                processed_keys.add(m_key)
            if not found_new: break

        swipe(device_id, 500, 600, 500, 1600)  # 向上滑


# ================= MAIN 函数 =================

if __name__ == '__main__':
    # 1. 选择语言
    select_language()

    # 2. 设备连接检查
    did = get_device_id()
    if not did:
        print(T["no_device"])
        sys.exit()

    print(f"{T['device_id']}{did}")

    # 3. 状态检查
    if check_lock_screen(did):
        print(T["locked"])
        sys.exit()

    # 4. 启动与导航
    if open_line(did):
        print(T["opened"])
        time.sleep(2)

        # 定位聊天 Tab
        xml = get_xml_dump(did)
        try:
            root = ET.fromstring(xml)
            chat_tab = root.find(".//node[@resource-id='jp.naver.line.android:id/bnb_chat']")
            if chat_tab is not None:
                c = get_coords_from_bounds(chat_tab.get('bounds'))
                tap(did, c['center'][0], c['center'][1])
                print(T["tab_selected"])

                # 5. 主处理循环
                processed_contacts = set()
                while True:
                    cur_xml = get_xml_dump(did)
                    root = ET.fromstring(cur_xml)
                    items = [n for n in root.iter('node') if n.get('resource-id') == "jp.naver.line.android:id/root"]

                    found_active = False
                    for item in items:
                        name_node = next((sub for sub in item.iter('node') if
                                          sub.get('resource-id') == "jp.naver.line.android:id/name"), None)
                        if name_node is not None:
                            c_name = name_node.get('text')
                            if c_name not in processed_contacts:
                                print(T["processing"].format(c_name))
                                pos = get_coords_from_bounds(item.get('bounds'))
                                tap(did, pos['center'][0], pos['center'][1])
                                time.sleep(2)

                                fetch_chat_history(did, c_name)

                                execute(f"adb -s {did} shell input keyevent 4")  # 返回列表
                                time.sleep(1.5)
                                processed_contacts.add(c_name)
                                found_active = True
                                break

                    if not found_active:
                        print(T["next_page"])
                        swipe(did, 500, 1600, 500, 400)  # 下拉列表
            else:
                print(T["no_tab"])
        except Exception as e:
            print(f"Error: {e}")