import os
import subprocess
import xml.etree.ElementTree as ET
import re
import time
import hashlib
import sys

# ================= 国际化配置 =================
LANG_CONFIG = {
    "1": {
        "menu": "简体中文",
        "no_device": "未找到设备，请检查 ADB 连接",
        "locked": "错误: 屏幕已锁定，请手动解锁后再运行",
        "opened": "Line 已成功启动",
        "tab_nav": "正在尝试切换到『聊天』标签页...",
        "processing": "\n--- 正在处理联系人: {} ---",
        "media_found": "   > 发现媒体 ({})，执行查重下载...",
        "save_success": "   [新文件] 已同步: {}",
        "duplicate": "   [跳过] 该文件已在本地存在 (MD5 命中)",
        "next_page": "当前列表已处理完，正在翻页寻找更多联系人..."
    },
    "2": {
        "menu": "English",
        "no_device": "No device found",
        "locked": "Error: Screen locked",
        "opened": "Line opened",
        "tab_nav": "Navigating to Chats tab...",
        "processing": "\n--- Processing: {} ---",
        "media_found": "   > Media ({}) found, checking duplicates...",
        "save_success": "   [New] Pulled: {}",
        "duplicate": "   [Skip] File already exists (MD5 Match)",
        "next_page": "Scrolling list for more contacts..."
    },
    "3": {
        "menu": "日本語",
        "no_device": "デバイス未接続",
        "locked": "エラー：画面ロック中",
        "opened": "Lineを起動しました",
        "tab_nav": "トークタブに切り替えています...",
        "processing": "\n--- 処理中: {} ---",
        "media_found": "   > メディア ({}) を発見、重複確認中...",
        "save_success": "   [新規] 同期完了: {}",
        "duplicate": "   [重複] スキップしました (MD5一致)",
        "next_page": "次の連絡先を読み込み中..."
    }
}
T = {}

# ================= 配置与路径 =================
SAVE_ROOT_DIR = "line_backup_data"
ANDROID_PIC_DIR = "/sdcard/Pictures/LINE"
ANDROID_MOV_DIR = "/sdcard/Movies/LINE"


def execute(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout.split('\n')
    except:
        return []


# ================= 基础工具 =================

def get_file_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_xml_dump(device_id):
    execute(f"adb -s {device_id} shell uiautomator dump /sdcard/uidump.xml")
    return "".join(execute(f"adb -s {device_id} shell cat /sdcard/uidump.xml")).strip()


def get_coords(bounds_str):
    coords = re.findall(r'\d+', bounds_str)
    x1, y1, x2, y2 = map(int, coords)
    return (x1 + x2) // 2, (y1 + y2) // 2


# ================= 逻辑功能 =================

def check_lock_screen(device_id):
    lines = execute(f"adb -s {device_id} shell dumpsys window policy")
    return any("showing=true" in line for line in lines)


def open_line(device_id):
    execute(f"adb -s {device_id} shell am start -n jp.naver.line.android/jp.naver.line.android.activity.SplashActivity")
    time.sleep(4)
    return True


def save_chat_log(folder_path, sender, msg_time, msg_type, content):
    file_path = os.path.join(folder_path, "chat_history.txt")
    log_line = f"[{msg_time}] {sender}: ({msg_type}) {content}\n"
    # 简单的末尾查重
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines and log_line in lines[-5:]: return
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(log_line)


def download_media_smart(device_id, bounds, folder_path, msg_type):
    """带清理、MD5去重的下载逻辑"""
    x, y = get_coords(bounds)
    execute(f"adb -s {device_id} shell input tap {x} {y}")
    time.sleep(2)

    remote_dir = ANDROID_MOV_DIR if msg_type == "video" else ANDROID_PIC_DIR
    execute(f"adb -s {device_id} shell rm -f {remote_dir}/*")  # 先清空

    def find_dl():
        try:
            root = ET.fromstring(get_xml_dump(device_id))
            node = root.find(".//node[@resource-id='jp.naver.line.android:id/chat_media_content_download_button']")
            return node.get('bounds') if node is not None else None
        except:
            return None

    dl_bounds = find_dl() or (execute(f"adb -s {device_id} shell input tap 500 1000") or find_dl())

    if dl_bounds:
        dx, dy = get_coords(dl_bounds)
        execute(f"adb -s {device_id} shell input tap {dx} {dy}")

        start_t = time.time()
        while time.time() - start_t < 15:
            files = [f.strip() for f in execute(f"adb -s {device_id} shell ls {remote_dir}") if
                     f.strip() and "No" not in f]
            if files:
                remote_name = files[0]
                temp_path = os.path.join(folder_path, f"temp_{remote_name}")
                execute(f"adb -s {device_id} pull \"{remote_dir}/{remote_name}\" \"{temp_path}\"")

                # MD5 校验
                this_md5 = get_file_md5(temp_path)
                is_dup = False
                for exist in os.listdir(folder_path):
                    if not exist.startswith("temp_") and exist != "chat_history.txt":
                        if get_file_md5(os.path.join(folder_path, exist)) == this_md5:
                            is_dup = True
                            break

                if is_dup:
                    print(T["duplicate"])
                    os.remove(temp_path)
                else:
                    final_path = os.path.join(folder_path, remote_name)
                    os.rename(temp_path, final_path)
                    print(T["save_success"].format(remote_name))
                break
            time.sleep(1)

    execute(f"adb -s {device_id} shell input keyevent 4")
    time.sleep(1)


# ================= 主控制逻辑 =================

def main():
    global T
    print("1. 中文 | 2. English | 3. 日本語")
    c = input("Choice: ").strip()
    T = LANG_CONFIG.get(c, LANG_CONFIG["1"])

    # 1. 连接与锁屏检测
    did = execute("adb devices")[1].split("\t")[0] if len(execute("adb devices")) > 1 else None
    if not did:
        print(T["no_device"])
        return
    if check_lock_screen(did):
        print(T["locked"])
        return

    # 2. 启动 LINE
    if open_line(did):
        print(T["opened"])

        # 3. 定位『聊天』标签页 (bnb_chat)
        print(T["tab_nav"])
        xml = get_xml_dump(did)
        root = ET.fromstring(xml)
        chat_tab = root.find(".//node[@resource-id='jp.naver.line.android:id/bnb_chat']")
        if chat_tab is not None:
            tx, ty = get_coords(chat_tab.get('bounds'))
            execute(f"adb -s {did} shell input tap {tx} {ty}")
            time.sleep(2)

        # 4. 遍历处理联系人
        processed_contacts = set()
        while True:
            root = ET.fromstring(get_xml_dump(did))
            items = [n for n in root.iter('node') if n.get('resource-id') == "jp.naver.line.android:id/root"]

            action_flag = False
            for item in items:
                name_node = next(
                    (sub for sub in item.iter('node') if sub.get('resource-id') == "jp.naver.line.android:id/name"),
                    None)
                if name_node is not None:
                    name = name_node.get('text')
                    if name not in processed_contacts:
                        print(T["processing"].format(name))
                        safe_path = os.path.join(SAVE_ROOT_DIR,
                                                 "".join(x for x in name if x.isalnum() or x in (' ', '_')))
                        if not os.path.exists(safe_path): os.makedirs(safe_path)

                        ix, iy = get_coords(item.get('bounds'))
                        execute(f"adb -s {did} shell input tap {ix} {iy}")
                        time.sleep(2)

                        # 深度抓取聊天记录与媒体
                        history_keys = set()
                        p_sig = ""
                        for _ in range(15):  # 向上滑动的次数
                            c_xml = get_xml_dump(did)
                            try:
                                tree = ET.fromstring(c_xml)
                                rows = tree.findall(
                                    ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_swipeable_framelayout']")
                                if not rows or rows[0].get('bounds') == p_sig: break
                                p_sig = rows[0].get('bounds')

                                for row in reversed(rows):
                                    t_node = row.find(
                                        ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_timestamp']")
                                    m_time = t_node.get('text') if t_node is not None else "00:00"
                                    m_sig = f"{m_time}_{row.get('bounds')}"
                                    if m_sig in history_keys: continue

                                    # 解析消息
                                    who = name if row.find(
                                        ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_thumbnail']") is not None else "Me"
                                    txt_node = row.find(
                                        ".//node[@resource-id='jp.naver.line.android:id/chat_ui_message_text']")
                                    v_node = row.find(
                                        ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_video_thumbnail']")
                                    i_node = row.find(
                                        ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_image_thumbnail']") or \
                                             row.find(
                                                 ".//node[@resource-id='jp.naver.line.android:id/chat_ui_row_image_balloon_root']")

                                    if txt_node is not None:
                                        save_chat_log(safe_path, who, m_time, "text", txt_node.get('text'))
                                    elif v_node is not None:
                                        save_chat_log(safe_path, who, m_time, "video", "[Video]")
                                        download_media_smart(did, v_node.get('bounds'), safe_path, "video")
                                    elif i_node is not None:
                                        save_chat_log(safe_path, who, m_time, "image", "[Image]")
                                        download_media_smart(did, i_node.get('bounds'), safe_path, "image")

                                    history_keys.add(m_sig)
                            except:
                                break
                            execute(f"adb -s {did} shell input swipe 500 800 500 1600 400")  # 滑向过去
                            time.sleep(1.5)

                        execute(f"adb -s {did} shell input keyevent 4")
                        time.sleep(1.5)
                        processed_contacts.add(name)
                        action_flag = True
                        break

            if not action_flag:
                print(T["next_page"])
                execute(f"adb -s {did} shell input swipe 500 1600 500 800 400")
                time.sleep(2)


if __name__ == "__main__":
    main()