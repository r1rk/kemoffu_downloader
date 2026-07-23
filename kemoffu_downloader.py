from __future__ import annotations

import sys
import os
import json
import re
import hashlib
import urllib.request
import urllib.error
import psutil
import locale
import threading
import shutil
import subprocess
import random
import math
import time
import shlex

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QLabel, QLineEdit,
                             QPushButton, QCheckBox, QSpinBox, QComboBox,
                             QTextEdit, QFileDialog, QGroupBox, QSplitter,
                             QMessageBox, QStyleFactory, QMenu, QProgressBar,
                             QScrollArea, QDialog, QGridLayout, QSizePolicy, QTextBrowser, QFrame, QListWidget, QListWidgetItem)
from PyQt6.QtCore import (Qt, QProcess, QTimer, pyqtSignal, QObject, QByteArray, 
                          QUrl, QThread, QRunnable, QThreadPool, QMimeData, QRectF,
                          QPropertyAnimation, QEasingCurve, QPoint)
from PyQt6.QtGui import QPalette, QColor, QTextCursor, QDesktopServices, QPixmap, QIcon, QDrag, QPainter, QPen, QBrush, QPainterPath
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6 import sip

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile
    from PyQt6.QtNetwork import QNetworkCookie
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

# わかりやすそうなコメントはClaudeくんやGeminiくんのものもそのまま残しています
# 私的メモも置いてると逆に分かりにくくなりそうな部分以外はあえて残しています

def _version_tuple(v):
    # "1.10.2" -> (1, 10, 2) のように数値タプル化して比較できるようにする
    # (文字列のままの比較だと "1.10.0" < "1.2.0" と誤判定されるため)
    parts = []
    for chunk in str(v).split('.'):
        m = re.match(r'\d+', chunk)
        parts.append(int(m.group()) if m else 0)
    return tuple(parts)

def is_newer_version(latest, current):
    try:
        return _version_tuple(latest) > _version_tuple(current)
    except Exception:
        return False

CURRENT_VERSION = "1.0.0"
UPDATE_JSON_URL = "https://raw.githubusercontent.com/kemono-dl-gui/update/main/update.json"

# 実行時のカレントディレクトリ(CWD)に依存させないためのアプリ基準ディレクトリ。
# PyInstaller等でexe化されている場合はexeの場所、そうでなければこのスクリプトの場所を基準にする。
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

def app_path(*parts):
    return os.path.join(APP_DIR, *parts)

# app_path(APP_DIR)は「exeやスクリプト本体が置かれている場所」なので、
# kemono-dl.py本体の探索など読み取り専用の用途には引き続き使う。
# 一方、config.json等の書き込みが発生するファイルをここに置くと、
# Program Files配下等の管理者権限が必要な場所にインストールされた場合、
# UACに拒否されて保存できない(または仮想化されて分かりにくい場所に飛ぶ)。
# そのため、書き込みを伴うファイルはOS標準のユーザーデータ領域へ分離する。

def get_user_data_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    data_dir = os.path.join(base, "Kemoffu")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception:
        # 万一作成に失敗した場合は、動作継続を優先してAPP_DIRにフォールバックする
        return APP_DIR
    return data_dir

USER_DATA_DIR = get_user_data_dir()

def user_data_path(*parts):
    return os.path.join(USER_DATA_DIR, *parts)

CONFIG_FILE = user_data_path("config.json")

def get_system_lang():
    try:
        if os.name == 'nt':
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() == 0x0411:
                return "ja"
        code = os.environ.get('LANG', '') or locale.getlocale()[0]
        if code and (code.lower().startswith('ja') or 'japanese' in code.lower()):
            return "ja"
    except: pass
    return "en"

CURRENT_LANG = get_system_lang()

#メニューや細かい部分の日英対応辞書
TEXTS = {
    "ja": {
        "undo": "元に戻す (Undo)", "redo": "やり直し (Redo)", "cut": "切り取り (Cut)",
        "copy": "コピー (Copy)", "paste": "貼り付け (Paste)", "del": "削除 (Delete)",
        "selall": "すべて選択 (Select All)", "theme": "UIテーマ:",
        "theme_auto": "自動 (システム追従)", "theme_dark": "ダークテーマ", "theme_light": "ライトテーマ",
        "urls_ph": "https://kemono.cr/patreon/user/1234567\nhttps://pawchive.pw/fanbox/user/1234567",
        "proxies_ph": "プロキシを使用しない場合は空欄\nIP:Port@User:Pass に対応\n※Socksプロキシは必ず socks5://... から入力してください",
        "lbl_urls": "ダウンロード対象 URL (1行に1つ)", "lbl_proxies": "プロキシリスト (オプション)",
        "lbl_max_proc": "最大並行プロセス数:", "lbl_override": "保存先ルートフォルダを上書き指定する:",
        "btn_browse": "参照...", "btn_start": "ダウンロード開始", "btn_pause": "一時停止",
        "btn_resume": "再開 ", "btn_stop": "安全に停止",
        "btn_load_proxies": "ファイルから読み込み...",
        "msg_start": "=== ダウンロード管理を開始しました ===", "msg_done": "=== 全てのダウンロードタスクが完了しました ===",
        "msg_suspend": "=== ダウンロードを一時停止しています... ===",
        "msg_resume": "=== ダウンロードを再開しています... ===",
        "msg_stop": "=== 安全に停止しています... ===",
        "msg_suspend_task": "一時停止 (サスペンド) しました。", "msg_resume_task": "再開 (レジューム) しました。",
        "tab_target": "🎯 ターゲット指定", "tab_content": "📦 保存対象", "tab_filters": "🧰 フィルター",
        "tab_patterns": "🏷️ パターン・命名", "tab_net": "⚙️ 高度な設定",
        "tab_search": "🔍 検索",
        "tab_history": "🕘 履歴",
        "btn_refresh_history": "履歴を更新",
        "btn_open_archive": "archive.txt を開く",
        "msg_no_history": "履歴がありません。",
        "msg_history_err": "履歴読み込みエラー: ",
        "lbl_ext_filter": "簡易拡張子フィルター (許可する拡張子)",
        "menu_preview": "保存されたプレビューを表示 ",
        "msg_err_kemono_dl": "kemono-dl.py が見つかりません。",
        "msg_kemono_dl_missing": "kemono-dl.py が見つかりませんでした。\n動作に必要な kemono-dl.py（およびsrcフォルダ）がある場所を指定してください。",
        "msg_kemono_dl_missing_title": "kemono-dl.py の場所を指定",
        "msg_kemono_dl_src_missing": "選択された場所に、動作に必要な src フォルダが見つかりませんでした。\nこのまま続行しますか？（正しく動作しない可能性があります）",
        "msg_merge_start": "全てのダウンロードが完了しました。指定フォルダへ一括マージ(移動)しています...",
        "msg_merge_done": "指定フォルダへの一括マージが完了しました。",
        "msg_merge_err": "フォルダマージ中にエラーが発生しました:",
        "msg_proxy_dead": "プロキシの応答不能またはアクセス制限を検知。プロセスを強制終了します。",
        "msg_retry_auto": "警告: 未インポート(never imported)でスキップされました。強制取得モードで自動再試行します。",
        "msg_retry_auto_name": "取得スキップを検知しました。HTMLから名前('{name}')を補完し、強制取得モードで再試行します。",
        "msg_retry_prep": "自動再試行の準備中...",
        "msg_task_end": "タスク終了 (Exit: {})",
        "dlg_warn": "警告", "dlg_err": "エラー", "dlg_update": "アップデート", "dlg_cookie": "Cookieの要求",
        "msg_no_url": "ダウンロード対象のURL、またはお気に入りオプションが指定されていません。",
        "lbl_pending": "準備中 ",
        "msg_fav_task": "お気に入り一括取得 (Favorites)",
        "msg_downloading": "ダウンロード中:",
        "msg_all_posts_done": "すべての投稿処理が完了しました ({c}/{t})",
        "msg_group_progress": "投稿処理中: {c}/{t} 件完了 | {text}",
        "msg_api_fetching": "[{user_id}] クリエイター情報をAPIから取得中...",
        "msg_api_fetched": "[{user_id}] 計 {tasks} 件の投稿を展開しました。",
        "msg_api_err": "[{user_id}] API取得エラー: {e}",
        "msg_completed": "完了 (Completed)",
        "msg_error": "エラー / 中断 ",
        "msg_load_proxy": "プロキシリストを選択",
        "msg_load_err": "ファイルの読み込みに失敗しました",
        "msg_cookie_req": "ログインが必要なサイトが含まれていますが、Cookieが指定されていません。\nブラウザ機能を使うには 'pip install PyQt6-WebEngine' が必要です。\nそのまま続行しますか？",
        "msg_cookie_miss": "対象サイトでCookieを使う為のファイルが見つかりません。\nログイン・登録してCookieを取得しますか？",
        "btn_img_search": "画像検索モードを起動"
    },
    "en": {
        "undo": "Undo", "redo": "Redo", "cut": "Cut",
        "copy": "Copy", "paste": "Paste", "del": "Delete",
        "selall": "Select All", "theme": "UI Theme:",
        "theme_auto": "Auto (System)", "theme_dark": "Dark Theme", "theme_light": "Light Theme",
        "urls_ph": "https://kemono.cr/patreon/user/12345678\nhttps://pawchive.pw/fanbox/user/12345678",
        "proxies_ph": "Leave blank if not using proxy\nSupports IP:Port@User:Pass formats\n* SOCKS proxies must specify socks5://...",
        "lbl_urls": "Target URLs (One per line)", "lbl_proxies": "Proxy List (Optional)",
        "lbl_max_proc": "Max Concurrent Processes:", "lbl_override": "Override base destination folder:",
        "btn_browse": "Browse...", "btn_start": "Start Download", "btn_pause": "Pause",
        "btn_resume": "Resume", "btn_stop": "Graceful Stop",
        "btn_load_proxies": "Load from file...",
        "msg_start": "=== Started Download Management ===", "msg_done": "=== All download tasks completed ===",
        "msg_suspend": "=== Suspending downloads... ===",
        "msg_resume": "=== Resuming downloads... ===",
        "msg_stop": "=== Gracefully stopping... ===",
        "msg_suspend_task": "Suspended.", "msg_resume_task": "Resumed.",
        "tab_target": "🎯 Target", "tab_content": "📦 Content", "tab_filters": "🧰 Filters",
        "tab_patterns": "🏷️ Patterns", "tab_net": "⚙️ Advanced",
        "tab_search": "🔍 Search",
        "tab_history": "🕘 History",
        "btn_refresh_history": "Refresh History",
        "btn_open_archive": "Open archive.txt",
        "msg_no_history": "No history found.",
        "msg_history_err": "Error loading history: ",
        "lbl_ext_filter": "Quick Extension Filter (Allowed)",
        "menu_preview": "Show Saved Images",
        "msg_err_kemono_dl": "kemono-dl.py not found.",
        "msg_kemono_dl_missing": "kemono-dl.py could not be found.\nPlease locate the folder containing kemono-dl.py (and its required src folder).",
        "msg_kemono_dl_missing_title": "Locate kemono-dl.py",
        "msg_kemono_dl_src_missing": "The required 'src' folder was not found next to the selected file.\nContinue anyway? (It may not work correctly.)",
        "msg_merge_start": "All downloads completed. Merging files to the destination folder...",
        "msg_merge_done": "Files successfully merged to the destination folder.",
        "msg_merge_err": "Error during folder merge:",
        "msg_proxy_dead": "Proxy failure or rate limit detected. Forcing process termination.",
        "msg_retry_auto": "Warning: Skipped (never imported). Auto-retrying in forced fetch mode.",
        "msg_retry_auto_name": "Skipped post detected. Auto-retrying in forced fetch mode with name '{name}'.",
        "msg_retry_prep": "Preparing auto-retry...",
        "msg_task_end": "Task finished (Exit: {})",
        "dlg_warn": "Warning", "dlg_err": "Error", "dlg_update": "Update", "dlg_cookie": "Cookie Required",
        "msg_no_url": "No target URLs or favorite options specified.",
        "lbl_pending": "Pending...",
        "msg_fav_task": "Favorites Download",
        "msg_downloading": "Downloading:",
        "msg_all_posts_done": "All posts completed ({c}/{t})",
        "msg_group_progress": "{c}/{t} Posts Completed | {text}",
        "msg_api_fetching": "[{user_id}] Fetching creator info via API...",
        "msg_api_fetched": "[{user_id}] Expanded {tasks} posts.",
        "msg_api_err": "[{user_id}] API fetch error: {e}",
        "msg_completed": "Completed",
        "msg_error": "Error or Stopped",
        "msg_load_proxy": "Select Proxy File",
        "msg_load_err": "Failed to load file",
        "msg_cookie_req": "Sites require login but no cookie file is specified.\n'pip install PyQt6-WebEngine' is required to use the browser feature.\nContinue anyway?",
        "msg_cookie_miss": "Cookie file is missing.\nDo you want to login and fetch cookies now?",
        "btn_img_search": "Open Visual Search"
    }
}

def L(key):
    return TEXTS.get(CURRENT_LANG, TEXTS["en"]).get(key, key)

def normalize_proxy(proxy_str, disable_auto_socks=False, use_socks5h=True):
    p = proxy_str.strip()
    if not p: return ""
    scheme = "http://"

    has_scheme = False
    if "://" in p:
        scheme_match = re.match(r'^([a-zA-Z0-9]+)://', p)
        if scheme_match:
            has_scheme = True
            scheme = scheme_match.group(1) + "://"
            p = p[len(scheme):]

    if not has_scheme and not disable_auto_socks:
        if re.search(r':1080$', p) or re.search(r':1080@', p):
            scheme = "socks5://"
            has_scheme = True

    if use_socks5h and scheme == "socks5://":
        scheme = "socks5h://"

    if "@" in p:
        part1, part2 = p.split("@", 1)
        if re.search(r':\d+$', part1) and not re.search(r':\d+$', part2):
            p = f"{part2}@{part1}"
        else:
            p = f"{part1}@{part2}"
    return scheme + p

def mask_proxy_for_display(proxy_str):
    # ログ/UI表示用にプロキシのパスワード部分だけを隠す（scheme・ユーザー名・host:portは視認性のため残す）
    if not proxy_str:
        return proxy_str
    return re.sub(r'(://[^:@/\s]+):[^@/\s]+@', r'\1:***@', proxy_str)

def fetch_creator_name(url):
    try:
        match = re.search(r'(https://[^/]+/[^/]+/user/[^/]+)', url)
        if not match: return None
        user_url = match.group(1)

        req = urllib.request.Request(user_url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        m = re.search(r'<title>Posts of (.*?) from', html)
        if m: return m.group(1).strip()
    except Exception:
        pass
    return None

class LocalizedTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 外部からのドラッグ＆ドロップを許可
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        # ドラッグされてきたデータが「テキスト（URL）」であれば受け入れを許可（禁止マークを消す）
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        # ドロップされた瞬間のテキスト（URL）を抽出し、末尾に自動追記する
        if event.mimeData().hasText():
            url = event.mimeData().text()
            current_urls = self.toPlainText().strip()
            if current_urls:
                self.setPlainText(current_urls + "\n" + url)
            else:
                self.setPlainText(url)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if not self.isReadOnly():
            undo_action = menu.addAction(L("undo")); undo_action.triggered.connect(self.undo); undo_action.setEnabled(self.document().isUndoAvailable())
            redo_action = menu.addAction(L("redo")); redo_action.triggered.connect(self.redo); redo_action.setEnabled(self.document().isRedoAvailable())
            menu.addSeparator()
            cut_action = menu.addAction(L("cut")); cut_action.triggered.connect(self.cut); cut_action.setEnabled(self.textCursor().hasSelection())
        copy_action = menu.addAction(L("copy")); copy_action.triggered.connect(self.copy); copy_action.setEnabled(self.textCursor().hasSelection())
        if not self.isReadOnly():
            paste_action = menu.addAction(L("paste")); paste_action.triggered.connect(self.paste); paste_action.setEnabled(self.canPaste())
            delete_action = menu.addAction(L("del")); delete_action.triggered.connect(lambda: self.textCursor().removeSelectedText()); delete_action.setEnabled(self.textCursor().hasSelection())
        menu.addSeparator()
        select_all_action = menu.addAction(L("selall")); select_all_action.triggered.connect(self.selectAll)
        menu.exec(event.globalPos())

class LocalizedLineEdit(QLineEdit):
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if not self.isReadOnly():
            undo_action = menu.addAction(L("undo")); undo_action.triggered.connect(self.undo); undo_action.setEnabled(self.isUndoAvailable())
            redo_action = menu.addAction(L("redo")); redo_action.triggered.connect(self.redo); redo_action.setEnabled(self.isRedoAvailable())
            menu.addSeparator()
            cut_action = menu.addAction(L("cut")); cut_action.triggered.connect(self.cut); cut_action.setEnabled(self.hasSelectedText())
        copy_action = menu.addAction(L("copy")); copy_action.triggered.connect(self.copy); copy_action.setEnabled(self.hasSelectedText())
        if not self.isReadOnly():
            paste_action = menu.addAction(L("paste")); paste_action.triggered.connect(self.paste)
            delete_action = menu.addAction(L("del")); delete_action.triggered.connect(self.del_); delete_action.setEnabled(self.hasSelectedText())
        menu.addSeparator()
        select_all_action = menu.addAction(L("selall")); select_all_action.triggered.connect(self.selectAll)
        menu.exec(event.globalPos())

# マウスカーソル合わせたときに表示されるtips用日英辞書
UI_DEFINITIONS = {
    "Tab_Input": [
        ("--cookies", "file", {"ja":"クッキーファイル","en":"Cookie File"}, "", {"ja":"ログイン必須機能やDDoS保護回避用のクッキーファイルを指定します。","en":"Cookie file for login features and DDoS bypass."}),
        ("--kemono-fav-users", "text", {"ja":"Kemonoお気に入りユーザー","en":"Kemono Fav Users"}, "", {"ja":"Kemono側のお気に入りユーザーを一括取得します。","en":"Fetch Kemono favorite users."}),
        ("--coomer-fav-users", "text", {"ja":"Coomerお気に入りユーザー","en":"Coomer Fav Users"}, "", {"ja":"Coomer側のお気に入りユーザーを一括取得します。","en":"Fetch Coomer favorite users."}),
        ("--pawchive-fav-users", "text", {"ja":"Pawchiveお気に入りユーザー","en":"Pawchive Fav Users"}, "", {"ja":"Pawchive側のお気に入りユーザーを一括取得します。","en":"Fetch Pawchive favorite users."}),
        ("--kemono-fav-posts", "bool", {"ja":"Kemonoお気に入り投稿取得","en":"Kemono Fav Posts"}, False, {"ja":"Kemono側でお気に入りに登録した投稿をすべてダウンロードします。","en":"Download Kemono favorite posts."}),
        ("--coomer-fav-posts", "bool", {"ja":"Coomerお気に入り投稿取得","en":"Coomer Fav Posts"}, False, {"ja":"Coomer側でお気に入りに登録した投稿をすべてダウンロードします。","en":"Download Coomer favorite posts."}),
        ("--pawchive-fav-posts", "bool", {"ja":"Pawchiveお気に入り投稿取得","en":"Pawchive Fav Posts"}, False, {"ja":"Pawchive側でお気に入りに登録した投稿をすべてダウンロードします。","en":"Download Pawchive favorite posts."}),
    ],
    "Tab_Content": [
        ("--inline", "bool", {"ja":"インライン画像保存","en":"Save Inline Images"}, False, {"ja":"投稿本文(HTML)の中に埋め込まれている画像をダウンロードします。","en":"Download inline images from post content."}),
        ("--content", "bool", {"ja":"本文(HTML)保存","en":"Save Content (HTML)"}, False, {"ja":"投稿のテキスト本文をHTMLファイルとして保存します。","en":"Save post text content as HTML."}),
        ("--comments", "bool", {"ja":"コメント保存","en":"Save Comments"}, False, {"ja":"投稿のコメント欄を取得し、HTMLファイルに組み込んで保存します。","en":"Include comments in the saved HTML."}),
        ("--json", "bool", {"ja":"JSON保存","en":"Save JSON"}, False, {"ja":"サイトから返された生の投稿データをJSONファイルとして保存します。","en":"Save raw post data as JSON."}),
        ("--extract-links", "bool", {"ja":"リンク抽出 (投稿)","en":"Extract Links (Post)"}, False, {"ja":"投稿本文内から抽出されたリンクURLをテキスト形式で保存します。","en":"Save extracted links from post content."}),
        ("--extract-all-links", "bool", {"ja":"リンク一括抽出 (ユーザー)","en":"Extract All Links"}, False, {"ja":"投稿者から抽出されたすべてのリンクを一括でユーザー名.txtに保存します。","en":"Save all extracted links to user.txt."}),
        ("--dms", "bool", {"ja":"DM履歴保存","en":"Save DMs"}, False, {"ja":"ユーザーのダイレクトメッセージ(DM)履歴をHTMLとして取得・保存します。","en":"Save DM history as HTML."}),
        ("--icon", "bool", {"ja":"アイコン保存","en":"Save Icon"}, False, {"ja":"ユーザーのプロフィールアイコン画像をダウンロードします。","en":"Download user profile icon."}),
        ("--banner", "bool", {"ja":"バナー保存","en":"Save Banner"}, False, {"ja":"ユーザーのプロフィール背景(バナー)画像をダウンロードします。","en":"Download user profile banner."}),
        ("--announcements", "bool", {"ja":"お知らせ保存","en":"Save Announcements"}, False, {"ja":"ユーザーへのお知らせテキストを取得し保存・上書きします。","en":"Download user announcements."}),
        ("--fancards", "bool", {"ja":"ファンカード保存","en":"Save Fancards"}, False, {"ja":"Fanbox等のファンカード情報をダウンロードします。","en":"Download Fanbox fancards."}),
        ("--yt-dlp", "bool", {"ja":"yt-dlp連携","en":"Use yt-dlp"}, False, {"ja":"投稿内の埋め込み動画を外部ツールのyt-dlpを用いて取得を試みます。","en":"Use yt-dlp for embedded videos."}),
        ("--skip-attachments", "bool", {"ja":"添付ファイルスキップ","en":"Skip Attachments"}, False, {"ja":"添付ファイルのダウンロードをスキップし、本文のみ等にします。","en":"Skip downloading main attachments."}),
        ("--overwrite", "bool", {"ja":"強制上書き","en":"Force Overwrite"}, False, {"ja":"既存のファイルがある場合でもスキップせず、強制的に上書きダウンロードします。","en":"Force overwrite existing files."}),
        ("--fetch-previews", "bool", {"ja":"実体不在(not imported)のプレビュー画像を強制取得","en":"Fetch Previews for Missing Posts"}, False, {"ja":"オリジナルファイルが取得不可の場合、裏側で公式APIを叩いてサムネイルの保存を試みます。","en":"Fallback to download thumbnail previews if original files are not imported."}),
        ("--preview-concurrency", "int", {"ja":"プレビュー並行取得数","en":"Preview Max Concurrency"}, 3, {"ja":"プレビュー画像を取得する際の同時接続数の上限です(回線が細い場合は下げてください)。","en":"Max concurrent downloads for preview images."}),
    ],
    "Tab_Filters": [
        ("--date", "text", {"ja":"指定日付のみ (YYYYMMDD)","en":"Specific Date (YYYYMMDD)"}, "", {"ja":"指定した当日の日付に投稿されたもののみをダウンロードします。","en":"Only download posts from this date."}),
        ("--datebefore", "text", {"ja":"指定日以前 (YYYYMMDD)","en":"Date Before (YYYYMMDD)"}, "", {"ja":"指定した日付以前に公開された投稿に制限します。","en":"Posts published before this date."}),
        ("--dateafter", "text", {"ja":"指定日以降 (YYYYMMDD)","en":"Date After (YYYYMMDD)"}, "", {"ja":"指定した日付以降に公開された投稿に制限します。","en":"Posts published after this date."}), # FIXED: 漢字の修正
        ("--fp-added", "bool", {"ja":"フィルター基準を追加日に変更","en":"Use Added Date for Filters"}, False, {"ja":"日付フィルターの基準を「公開日」ではなく「サイト追加日」に変更します。","en":"Filter by site added date instead of published date."}),
        ("--user-updated-datebefore", "text", {"ja":"ユーザー更新日(以前)","en":"User Updated Before"}, "", {"ja":"ユーザー情報自体が指定期間以前に更新されている場合のみダウンロードします。","en":"User was updated before this date."}),
        ("--user-updated-dateafter", "text", {"ja":"ユーザー更新日(以後)","en":"User Updated After"}, "", {"ja":"ユーザー情報自体が指定期間以後に更新されている場合のみダウンロードします。","en":"User was updated after this date."}),
        ("--min-filesize", "text", {"ja":"最小ファイルサイズ","en":"Min Filesize"}, "", {"ja":"指定容量より大きいファイルのみ保存します (例: 10mb, 500kb)。","en":"Min filesize (e.g., 10mb)."}),
        ("--max-filesize", "text", {"ja":"最大ファイルサイズ","en":"Max Filesize"}, "", {"ja":"指定容量より小さいファイルのみ保存します。","en":"Max filesize (e.g., 50mb)."}),
        ("--skip-filetypes", "text", {"ja":"除外する拡張子","en":"Skip Extensions"}, "", {"ja":"除外するファイル拡張子をカンマ区切りで指定します。","en":"Extensions to exclude."}),
        ("--only-postname", "text", {"ja":"必須タイトル文字列","en":"Required Title Text"}, "", {"ja":"投稿タイトルに特定の文字列を含むもののみダウンロードします。","en":"Title must contain this text."}),
        ("--skip-postname", "text", {"ja":"除外タイトル文字列","en":"Skip Title Text"}, "", {"ja":"投稿タイトルに特定の文字列を含むものを除外します。","en":"Skip if title contains this text."}),
        ("--only-filename", "text", {"ja":"必須ファイル文字列","en":"Required File Text"}, "", {"ja":"ファイル名に特定の文字列を含むもののみダウンロードします。","en":"Filename must contain this text."}),
        ("--skip-filename", "text", {"ja":"除外ファイル文字列","en":"Skip File Text"}, "", {"ja":"ファイル名に特定の文字列を含むものを除外します。","en":"Skip if filename contains this text."}),
    ],
    "Tab_Patterns": [
        ("--dirname-pattern", "text", {"ja":"サブフォルダ自動仕分け","en":"Dirname Pattern"}, "{service}/{username} [{user_id}]", {"ja":"保存先ルートフォルダ内に作られる自動仕分け用のフォルダ階層パターンです。","en":"Folder hierarchy pattern under the base destination."}),
        ("--filename-pattern", "text", {"ja":"添付ファイル命名規則","en":"Filename Pattern"}, "[{published}] [{id}] {title}/{index}_{filename}.{ext}", {"ja":"添付ファイルの名前の命名パターンを定義します。","en":"Naming pattern for attachments."}),
        ("--inline-filename-pattern", "text", {"ja":"インライン画像命名規則","en":"Inline Filename Pattern"}, "[{published}] [{id}] {title}/inline/{index}_{filename}.{ext}", {"ja":"本文埋め込み画像の名前の命名パターンを定義します。","en":"Naming pattern for inline images."}),
        ("--other-filename-pattern", "text", {"ja":"その他ファイル命名規則","en":"Other Filename Pattern"}, "[{published}] [{id}] {title}/[{id}]_{filename}.{ext}", {"ja":"本文、リンク、JSONファイルの名前の命名パターンを定義します。","en":"Naming pattern for contents, links, json."}),
        ("--user-filename-pattern", "text", {"ja":"ユーザーファイル命名規則","en":"User Filename Pattern"}, "[{user_id}]_{filename}.{ext}", {"ja":"アイコン、バナー、DMファイルの名前の命名パターンを定義します。","en":"Naming pattern for icons, banners, dms."}),
        ("--date-strf-pattern", "text", {"ja":"日付フォーマット","en":"Date Format"}, "%Y%m%d", {"ja":"パターン内で使用される日付変数の文字フォーマットを指定します。","en":"String format for date variables."}),
        ("--restrict-names", "bool", {"ja":"ASCII文字のみに制限","en":"Restrict to ASCII"}, False, {"ja":"フォルダ名やファイル名をASCII文字(英数字・記号)のみに制限し、互換性を高めます。","en":"Limit file/folder names to ASCII."}),
    ],
    "Tab_Network": [
        ("--retry", "int", {"ja":"再試行回数","en":"Retry Count"}, 5, {"ja":"ダウンロード失敗時に同一ファイルに対して再試行を行う最大回数です。","en":"Max retries on download failure."}),
        ("--retry-403", "int", {"ja":"403エラー再試行回数","en":"403 Retry Count"}, 0, {"ja":"403 Forbidden(DDoSガード等)に遭遇した際、セッションなしで試行する回数です。","en":"Retries without session on 403 Forbidden."}),
        ("--post-timeout", "int", {"ja":"投稿間待機時間(秒)","en":"Post Timeout(s)"}, 0, {"ja":"連続して投稿を処理する間に挟む待機時間を秒単位で指定します。","en":"Sleep time in seconds between posts."}),
        ("--ratelimit-sleep", "int", {"ja":"レートリミット待機(秒)","en":"Ratelimit Sleep(s)"}, 120, {"ja":"サイト側から429エラーを検知した際の自動スリープ秒数です。","en":"Sleep time on 429 Too Many Requests."}),
        ("--ratelimit-ms", "int", {"ja":"リクエスト間隔(ミリ秒)","en":"Request Interval(ms)"}, 300, {"ja":"次のリクエストを送るまでに最低限空けるミリ秒単位のインターバルです。","en":"Minimum ms interval between requests."}),
        ("--user-agent", "text", {"ja":"カスタムUser-Agent","en":"Custom User-Agent"}, "", {"ja":"通信時にサーバーへ通知するカスタムブラウザ識別文字列を設定します。","en":"Custom browser user-agent string."}),
        ("--local-hash", "bool", {"ja":"ローカルハッシュ検証","en":"Verify Local Hash"}, False, {"ja":"既存ファイルがある場合、スキップする前にローカルのハッシュ値を厳密に検証します。","en":"Strict hash check before skipping existing files."}),
        ("--dupe-check", "bool", {"ja":"重複防止チェック","en":"Dupe Check"}, True, {"ja":"類似するファイル名やインデックスからハッシュを比較し、重複保存を防止します。","en":"Prevent duplicate downloads via hash check."}),
        ("--dupe-check-pattern", "text", {"ja":"重複防止パターン","en":"Dupe Check Pattern"}, "{index}_*,*{id}*/{index}_*", {"ja":"重複チェックの際に検索対象とするフォルダ構造のパターンを指定します。","en":"Search pattern for duplicate check."}),
        ("--force-unlisted", "bool", {"ja":"未掲載ユーザー強制リクエスト","en":"Force Unlisted User Request"}, False, {"ja":"クリエイター一覧にない未掲載ユーザーでも、APIへ強制リクエストを試みます。(注意: 名前が取得できなくなります)","en":"Force API request even if user is not in creators list. (Warning: Username will be replaced by ID)"}),
        ("--cache-creators", "bool", {"ja":"クリエイターキャッシュ","en":"Cache Creators"}, True, {"ja":"クリエイター一覧データをローカルにキャッシュして起動速度を高速化します。","en":"Cache creators list locally to speed up startup."}),
        ("--cache-creators-expire", "int", {"ja":"キャッシュ有効期限(秒)","en":"Cache Expire(s)"}, 86400, {"ja":"クリエイターキャッシュの有効期限を秒単位で指定します(初期値:1日)。","en":"Cache expiration time in seconds."}),
        ("--archives-password", "bool", {"ja":"圧縮パスワード解析","en":"Parse Archive Passwords"}, False, {"ja":"圧縮ファイル(zip等)のパスワード解析を試み、発見時は.pwファイルを生成します。","en":"Try to find passwords for archives and save to .pw file."}),
        ("--part-files", "bool", {"ja":"中断用.partファイル生成","en":"Create .part Files"}, True, {"ja":"チェックを外すと.partファイルを生成しません。中断時のレジュームが不可になります。","en":"Create .part files for partial downloads."}),
        ("--simulate", "bool", {"ja":"シミュレーション(保存なし)","en":"Simulate (No Save)"}, False, {"ja":"実際のディスク書き込みを行わず、テスト実行のみを行います。","en":"Test run without writing to disk."}),
    ]
}

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)
    def run(self):
        try:
            req = urllib.request.Request(UPDATE_JSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as res:
                data = json.loads(res.read().decode('utf-8'))
                latest = data.get("version")
                url = data.get("url")
                if latest and is_newer_version(latest, CURRENT_VERSION):
                    self.update_available.emit(latest, url)
        except Exception:
            pass

class CacheUpdateWorker(QThread):
    finished_signal = pyqtSignal(list, list, dict)

    def __init__(self, targets):
        super().__init__()
        self.targets = targets

    def run(self):
        combined_cache = []
        error_messages = []
        site_counts = {}  # サイトごとの取得件数(成功したサイトのみキーが入る)

        for site_name, api_url in self.targets:
            try:
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as res:
                    data = json.loads(res.read().decode('utf-8'))
                    if isinstance(data, list):
                        # 各クリエイターデータに所属サイトの識別タグを論理的に付与
                        for item in data:
                            if isinstance(item, dict):
                                item["_site"] = site_name
                        combined_cache.extend(data)
                        site_counts[site_name] = len(data)
                    else:
                        # JSONとしては読めたがリスト形式ではない = WAF/Turnstileのチャレンジ応答等、
                        # 想定外のレスポンス。ここで無言でスキップすると「成功したサイトしか
                        # 分からない」状態になるため、明示的にエラーとして記録する。
                        error_messages.append(f"{site_name}(想定外の応答形式)" if CURRENT_LANG == "ja" else f"{site_name}(unexpected response format)")
            except Exception as e:
                error_messages.append(f"{site_name}({str(e)})")

        self.finished_signal.emit(combined_cache, error_messages, site_counts)

class PreviewTaskSignals(QObject):
    log = pyqtSignal(str, str)
    finished = pyqtSignal(str)

class ImageLoadSignals(QObject):
    loaded = pyqtSignal(str, QPixmap)

class ImageLoadWorker(QRunnable):
    def __init__(self, creator_id, img_url):
        super().__init__()
        self.creator_id = creator_id
        self.img_url = img_url
        self.signals = ImageLoadSignals()
        
    def run(self):
        try:
            req = urllib.request.Request(self.img_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                img_data = res.read()
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                self.signals.loaded.emit(self.creator_id, pixmap)
        except Exception:
            pass

# 確かプレビュー画像をも強制的に抜き出せるようにするためのクラス
class PreviewDownloadWorker(QRunnable):
    def __init__(self, task_id, domain, service, username, user_id, post_id, target_dir, dirname_pattern):
        super().__init__()
        self.task_id = task_id
        self.domain = domain
        self.service = service
        self.username = username
        self.user_id = user_id
        self.post_id = post_id
        self.target_dir = target_dir
        self.dirname_pattern = dirname_pattern
        self.signals = PreviewTaskSignals()

    def sanitize_filename(self, name):
        if not name: return ""
        return re.sub(r'[\\/:*?"<>|]', '_', str(name))

    def format_date(self, iso_date_str):
        if not iso_date_str: return ""
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})', iso_date_str)
        if m: return f"{m.group(1)}{m.group(2)}{m.group(3)}"
        return iso_date_str

    def run(self):
        try:
            api_url = f"https://{self.domain}/api/v1/{self.service}/user/{self.user_id}/post/{self.post_id}"
            req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode('utf-8'))
            
            paths = []
            if "file" in data and isinstance(data["file"], dict) and "path" in data["file"]:
                paths.append(data["file"]["path"])
            if "attachments" in data and isinstance(data["attachments"], list):
                for att in data["attachments"]:
                    if isinstance(att, dict) and "path" in att:
                        paths.append(att["path"])
            
            if not paths: return
            
            user_folder = self.dirname_pattern.replace("{service}", self.service)\
                                              .replace("{username}", self.sanitize_filename(self.username))\
                                              .replace("{user_id}", self.user_id)
            # ここで扱えるのは {service}/{username}/{user_id} の3つのみ。
            # kemono-dl.py本体がそれ以外のプレースホルダ({title}等)をサポートしていて
            # ユーザーがパターンに使っていた場合、本来の保存先フォルダと完全には
            # 一致しない可能性がある(既知の制約)。少なくとも "{xxx}" という
            # 壊れた文字列がそのままフォルダ名に残ることだけは避けるため、
            # 未対応のプレースホルダは空文字に畳み込んでおく。
            user_folder = re.sub(r'\{[^}]+\}', '', user_folder)
            user_folder = re.sub(r'[\\/]{2,}', os.sep, user_folder).strip(' \\/')
            
            published = self.format_date(data.get("published", ""))
            title = self.sanitize_filename(data.get("title", ""))
            post_folder = f"[{published}] [{self.post_id}] {title}".strip()
            
            preview_dir = os.path.join(self.target_dir, user_folder, post_folder)
            os.makedirs(preview_dir, exist_ok=True)
            
            for i, p in enumerate(paths):
                img_url = f"https://img.{self.domain}/thumbnail/data{p}"
                ext = p.split('.')[-1] if '.' in p else 'jpg'
                save_path = os.path.join(preview_dir, f"{i:02d}_preview.{ext}")
                
                if os.path.exists(save_path): continue
                
                req_img = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_img, timeout=15) as res_img:
                    with open(save_path, 'wb') as f:
                        f.write(res_img.read())
                        
            msg = f"[Preview] {self.post_id} のプレビュー画像を取得完了。" if CURRENT_LANG == "ja" else f"[Preview] Downloaded preview for {self.post_id}"
            self.signals.log.emit(self.task_id, msg)
        except Exception as e:
            err_msg = f"[Preview] プレビュー取得失敗 ({self.post_id}): {e}" if CURRENT_LANG == "ja" else f"[Preview] Failed ({self.post_id}): {e}"
            self.signals.log.emit(self.task_id, err_msg)
        finally:
            self.signals.finished.emit(self.task_id)

class CreatorFetchSignals(QObject):
    finished = pyqtSignal(list)
    log = pyqtSignal(str, str)
    waf_warning = pyqtSignal(str, str)

class CreatorFetchWorker(QRunnable):
    def __init__(self, target_url, domain, service, user_id, extracted_name, max_retry=3):
        super().__init__()
        self.target_url = target_url
        self.domain = domain
        self.service = service
        self.user_id = user_id
        self.extracted_name = extracted_name
        self.max_retry = max_retry  # 「高度な設定」タブの再試行回数(--retry)に追従(呼び出し元でメインスレッドから読んで渡す) 理由はこれを個別設定に分けるスペースがなかったので
        self.signals = CreatorFetchSignals()

    def run(self):
        msg = L("msg_api_fetching").replace("{user_id}", self.user_id)
        self.signals.log.emit("SYS", msg)
        offset = 0
        all_tasks = []
        
        group_id = hashlib.md5(self.target_url.encode('utf-8')).hexdigest()[:8]
        group_title = f"{self.extracted_name or self.user_id} ({self.domain}/{self.service})"
        creator_label = group_title
        
        while True:
            api_url = f"https://{self.domain}/api/v1/{self.service}/user/{self.user_id}?o={offset}"
            retry = 0
            page_data = None
            last_error = None

            # このページ(offset)単位で、個別インターバルを挟みながら再試行する。
            # 検索モードの画像取得と同じ方針: 429は0.5〜1秒、それ以外は0.1〜0.3秒。
            # QRunnable(バックグラウンドスレッド)内なのでtime.sleepで待ってもGUIはブロックしない。
            while retry <= self.max_retry:
                try:
                    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as res:
                        page_data = json.loads(res.read().decode('utf-8'))
                    break
                except Exception as e:
                    last_error = e
                    is_429 = "429" in str(e)
                    if retry >= self.max_retry:
                        break
                    delay = random.uniform(0.5, 1.0) if is_429 else random.uniform(0.1, 0.3)
                    time.sleep(delay)
                    retry += 1

            if page_data is None:
                # 再試行上限に達しても取得できなかった場合、明示的にログへ残す
                err_msg = L("msg_api_err").replace("{user_id}", self.user_id).replace("{e}", str(last_error))
                self.signals.log.emit("SYS", err_msg)
                self.signals.log.emit("SYS",
                    f"クリエイター情報の取得に失敗しました:[{creator_label}] 後ほど再試行してください。"
                    if CURRENT_LANG == "ja" else
                    f"Failed to fetch creator info: [{creator_label}] Please retry later.")
                if last_error is not None and "403" in str(last_error):
                    self.signals.waf_warning.emit(self.domain, str(last_error))
                break

            if not page_data:
                break

            for post in page_data:
                post_id = post.get("id")
                if post_id:
                    post_url = f"https://{self.domain}/{self.service}/user/{self.user_id}/post/{post_id}"
                    task_id = hashlib.md5(post_url.encode('utf-8')).hexdigest()[:8]
                    task = {
                        "id": task_id, 
                        "type": "url", 
                        "target": post_url, 
                        "status": "pending",
                        "extracted_name": self.extracted_name,
                        "group_id": group_id,
                        "group_title": group_title
                    }
                    all_tasks.append(task)
                    
            offset += 50
                
        end_msg = L("msg_api_fetched").replace("{user_id}", self.user_id).replace("{tasks}", str(len(all_tasks)))
        self.signals.log.emit("SYS", end_msg)
        self.signals.finished.emit(all_tasks)

class TaskWidget(QWidget):
    preview_requested = pyqtSignal(str)
    
    def __init__(self, task_id, title):
        super().__init__()
        self.task_id = task_id
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.lbl_title = QLabel(f"<b>[{task_id}]</b> {title}")
        self.lbl_title.setTextFormat(Qt.TextFormat.RichText)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.lbl_status = QLabel(L("lbl_pending"))
        self.lbl_status.setWordWrap(True)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_status)

        self.setMinimumHeight(75) 

        self.setStyleSheet("TaskWidget { border: 1px solid #777; border-radius: 4px; margin-bottom: 2px; }")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        preview_action = menu.addAction(L("menu_preview"))
        action = menu.exec(event.globalPos())
        if action == preview_action:
            self.preview_requested.emit(self.task_id)

    def update_progress(self, current, total, text):
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.lbl_status.setText(text)

    def set_finished(self, success):
        if success:
            self.lbl_status.setText(L("msg_completed"))
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        else:
            self.lbl_status.setText(L("msg_error"))
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")

class ImagePreviewDialog(QDialog):
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.setWindowTitle("プレビュー (Preview)")
        self.resize(850, 650)
        
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        
        col_count = 3
        for i, img_path in enumerate(images):
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("border: 1px solid #555; background-color: #222;")
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                lbl.setPixmap(pixmap.scaled(260, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            grid.addWidget(lbl, i // col_count, i % col_count)
            
        scroll.setWidget(container)
        layout.addWidget(scroll)

class MiniBrowserDialog(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browser Preview")
        self.resize(1050, 750)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl(url))
        layout.addWidget(self.webview)

class HistoryBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.handle_link)
        self.setMouseTracking(True)

    def handle_link(self, url):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if HAS_WEBENGINE:
                dlg = MiniBrowserDialog(url.toString(), self)
                dlg.exec()
            else:
                QDesktopServices.openUrl(url)
                
    def mouseMoveEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor:
            tip_text = "Ctrl + 左クリックでプレビューを表示できます。" if CURRENT_LANG == "ja" else "Ctrl + Left Click to preview."
            from PyQt6.QtWidgets import QToolTip
            QToolTip.showText(event.globalPosition().toPoint(), tip_text, self)
        else:
            from PyQt6.QtWidgets import QToolTip
            QToolTip.hideText()
        super().mouseMoveEvent(event)

class SearchListItem(QWidget):
    def __init__(self, creator, main_gui):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        url = f"https://{creator['_domain']}/{creator['service']}/user/{creator['id']}"
        lbl = QLabel(f"[{creator['service'].capitalize()}] <b>{creator['name']}</b> ── <span style='color: gray;'>{url}</span>")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        btn = QPushButton("＋ 追加" if CURRENT_LANG == "ja" else "＋ Add")
        btn.clicked.connect(lambda: main_gui.add_url_to_list(url))
        layout.addWidget(lbl, 1)
        layout.addWidget(btn, 0)

class CreatorCard(QFrame):
    def __init__(self, creator, main_gui, pool):
        super().__init__()
        self.creator = creator
        self.main_gui = main_gui
        self.url = f"https://{creator['_domain']}/{creator['service']}/user/{creator['id']}"
        self.setFrameShape(QFrame.Shape.Box)
        
        app = QApplication.instance()
        is_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        if is_dark:
            self.setStyleSheet("CreatorCard { background-color: #1f1f1f; border: 1px solid #444; border-radius: 8px; }")
        else:
            self.setStyleSheet("CreatorCard { background-color: #fcfcfc; border: 1px solid #ccc; border-radius: 8px; }")
            
        self.setFixedSize(300, 100)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.lbl_img = QLabel()
        self.lbl_img.setFixedSize(80, 80)
        self.lbl_img.setStyleSheet("background-color: #333; border-radius: 6px;")
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img.setText("Loading")
        layout.addWidget(self.lbl_img)
        
        text_layout = QVBoxLayout()
        lbl_service = QLabel(creator.get('service', '').capitalize())
        lbl_service.setStyleSheet("color: #888; font-size: 10px;")
        
        lbl_name = QLabel()
        lbl_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        font_metrics = lbl_name.fontMetrics()
        elided_name = font_metrics.elidedText(creator.get('name', 'Unknown'), Qt.TextElideMode.ElideRight, 150)
        lbl_name.setText(elided_name)
        
        lbl_fav = QLabel(f"⭐ {creator.get('favorited', 0)} favorites")
        lbl_fav.setStyleSheet("color: #aaa; font-size: 11px;")
        
        text_layout.addWidget(lbl_service)
        text_layout.addWidget(lbl_name)
        text_layout.addWidget(lbl_fav)
        layout.addLayout(text_layout)
        
        btn_add = QPushButton("＋")
        btn_add.setFixedSize(32, 32)
        btn_add.setToolTip("メインのURLリストに追加" if CURRENT_LANG == "ja" else "Add to main URL list")
        btn_add.clicked.connect(lambda: self.main_gui.add_url_to_list(self.url))
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(btn_add)
        right_layout.addStretch()
        layout.addLayout(right_layout)
        
        icon_url = f"https://{creator['_domain']}/icons/{creator['service']}/{creator['id']}"
        worker = ImageLoadWorker(str(creator['id']), icon_url)
        worker.signals.loaded.connect(self.on_image_loaded)
        pool.start(worker)
        
    def on_image_loaded(self, cid, pixmap):
        if not pixmap.isNull():
            self.lbl_img.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            self.lbl_img.setText("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
            
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance(): return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.url)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

class CustomCardFrame(QFrame):
    # do_visual_search用のカード。以前は QFrame インスタンスに対して
    # paintEvent を動的に上書き(モンキーパッチ)していたが、可読性・保守性、
    # および参照関係が崩れた際の予期せぬ挙動を避けるため専用クラス化した。
    def __init__(self, parent=None):
        super().__init__(parent)
        self._background_pixmap = None
        self.setStyleSheet("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        if not hasattr(self, 'drag_start_pos'): return
        # OS標準のドラッグ開始距離（約4px）未満の移動なら無視する
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance(): return
        
        url = self.property("url")
        if url:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(url)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)

    def set_background_pixmap(self, pixmap):
        self._background_pixmap = pixmap
        self.update()  # paintEvent を安全に再トリガー

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(0.5, 0.5, w - 1, h - 1)

        # A. 基礎背景色（#222）と基礎枠線（#444）のネイティブ描画
        painter.setBrush(QBrush(QColor("#222")))
        painter.setPen(QPen(QColor("#444"), 1))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        # B. 非同期で画像が届いている場合のみ、角丸クリップして最背面に裏打ち描画
        if self._background_pixmap and not self._background_pixmap.isNull():
            painter.save()
            path = QPainterPath()
            path.addRoundedRect(rect, 6.0, 6.0)
            painter.setClipPath(path)

            painter.drawPixmap(0, 0, self._background_pixmap)
            painter.restore()

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawRoundedRect(rect, 6.0, 6.0)

        painter.end()

class NextPageCard(QFrame):
    # ページ末尾の中途半端に余ったグリッドの空きスロットに埋め込む「次ページへ」ボタン。
    # ホバー中は矢印が文字の直後から枠の右端へ繰り返し流れるアニメーションを行う。
    clicked = pyqtSignal()

    def __init__(self, card_w, card_h, parent=None):
        super().__init__(parent)
        self.setFixedSize(card_w, card_h)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            NextPageCard {
                background-color: #2a2a2a;
                border: 2px dashed #00BFFF;
                border-radius: 6px;
            }
            NextPageCard:hover {
                background-color: #333;
            }
        """)

        self.lbl_text = QLabel("次のページへ" if CURRENT_LANG == "ja" else "Next Page", self)
        self.lbl_text.setStyleSheet("color: #00BFFF; font-weight: bold; font-size: 15px; background: transparent; border: none;")
        self.lbl_text.adjustSize()
        
        # 1. 「次のページへ」テキストを中央に配置
        text_x = (card_w - self.lbl_text.width()) // 2
        text_y = (card_h - self.lbl_text.height()) // 2
        self.lbl_text.move(text_x, text_y)

        self.lbl_arrow = QLabel(">>", self)
        self.lbl_arrow.setStyleSheet("color: #00BFFF; font-weight: bold; font-size: 16px; background: transparent; border: none;")
        self.lbl_arrow.adjustSize()

        # 2. アニメーションの開始位置を「テキストのすぐ右（+6px）」、終了位置を「カード枠の右端手前（-12px）」に設定
        self._arrow_start_x = text_x + self.lbl_text.width() + 6
        self._arrow_end_x = card_w - self.lbl_arrow.width() - 12
        self._arrow_y = (card_h - self.lbl_arrow.height()) // 2
        self.lbl_arrow.move(self._arrow_start_x, self._arrow_y)

        self._anim = QPropertyAnimation(self.lbl_arrow, b"pos", self)
        self._anim.setDuration(450) # このぐらいの速度が一番よかった
        self._anim.setStartValue(QPoint(self._arrow_start_x, self._arrow_y))
        self._anim.setEndValue(QPoint(self._arrow_end_x, self._arrow_y))
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.setLoopCount(-1)  # ホバーしている間は「流れて→先頭に戻って→また流れる」を繰り返す

    def enterEvent(self, event):
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self.lbl_arrow.move(self._arrow_start_x, self._arrow_y)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ImageSearchDialog(QDialog):
    CARD_W = 280
    CARD_H = 105
    CARD_SPACING = 10
    GRID_MARGIN = 10
    DEFAULT_COLS = 3
    DEFAULT_ROWS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 閉じた際にC++/Pythonのメモリを確実に解放(🛠️3-②)
        self.parent = parent
        self.setWindowTitle("画像検索モード ※ドラッグ&ドロップ対応" if CURRENT_LANG == "ja" else "Visual Search Mode (Drag & Drop supported)")

        # 解決：非モーダル起動時、親ウィンドウの前面に常に固定させるフラグを設定
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # --- 検索・取得の状態管理 ---
        self.search_generation = 0       # ワードが変わるたびに増やし、古い取得を無効化する世代番号
        self.active_replies = []         # 現在飛んでいるQNetworkReply(ワード変更時に即座にabortする対象)
        self.page_size = 50              # 本家に合わせて1ページ50件
        self.current_page = 1
        self.all_matches = []            # 現在のクエリに合致する全クリエイター(ページネーション用)
        self.max_concurrent_creators = 10  # 同時に画像取得を行うクリエイター数の上限(アイコン+バナーで最大20リクエスト)
        self.network_manager = QNetworkAccessManager(self)
        self.image_retry_limit = self.parent.spin_image_retry.value() if hasattr(self.parent, "spin_image_retry") else 3
        self._current_cards = []         # 現在グリッドに並んでいるカードウィジェット(リサイズ時の再配置用)
        self._current_col_count = self.DEFAULT_COLS
        self._next_page_card = None  # ページ末尾の空きスロットに埋め込む「次へ」カード(遅延生成)

        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("クリエイター名やIDを入力...")
        self.search_input.setText(self.parent.search_input.text())
        self.search_input.setAcceptDrops(False)  # 自身の検索バーへの誤ドロップを防止
        top_layout.addWidget(self.search_input)

        btn_search = QPushButton("検索" if CURRENT_LANG == "ja" else "Search")
        btn_search.clicked.connect(lambda: self.do_visual_search(page=1))
        self.search_input.returnPressed.connect(lambda: self.do_visual_search(page=1))
        top_layout.addWidget(btn_search)
        layout.addLayout(top_layout)

        # 本家のように、入力が落ち着いたタイミングで自動的に検索を実行する(デバウンス方式)。
        # 単語が変わった瞬間には、まず進行中の取得を即座に破棄してから、新しい検索の実行を少し待つ。
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(lambda: self.do_visual_search(page=1))
        self.search_input.textChanged.connect(self._on_search_text_live_changed)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # けっこういい細かい修正
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setHorizontalSpacing(self.CARD_SPACING)
        self.grid.setVerticalSpacing(self.CARD_SPACING)
        self.grid.setContentsMargins(self.GRID_MARGIN, self.GRID_MARGIN, self.GRID_MARGIN, self.GRID_MARGIN)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)

        # --- ページネーションUI(本家の「Showing X - Y of Z」+ << < 1 2 3 > >> に準拠) ---
        self.lbl_pagination_info = QLabel("")
        self.lbl_pagination_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_pagination_info)

        pager_layout = QHBoxLayout()
        pager_layout.addStretch()
        self.btn_page_first = QPushButton("<<")
        self.btn_page_prev = QPushButton("<")
        self.page_number_buttons_layout = QHBoxLayout()
        self.btn_page_next = QPushButton(">")
        self.btn_page_last = QPushButton(">>")
        for b in (self.btn_page_first, self.btn_page_prev, self.btn_page_next, self.btn_page_last):
            b.setFixedWidth(36)
        self.btn_page_first.clicked.connect(lambda: self.do_visual_search(page=1))
        self.btn_page_prev.clicked.connect(lambda: self.do_visual_search(page=self.current_page - 1))
        self.btn_page_next.clicked.connect(lambda: self.do_visual_search(page=self.current_page + 1))
        self.btn_page_last.clicked.connect(lambda: self.do_visual_search(page=self._total_pages()))
        pager_layout.addWidget(self.btn_page_first)
        pager_layout.addWidget(self.btn_page_prev)
        pager_layout.addLayout(self.page_number_buttons_layout)
        pager_layout.addWidget(self.btn_page_next)
        pager_layout.addWidget(self.btn_page_last)
        pager_layout.addStretch()
        layout.addLayout(pager_layout)

        # 既定表示でカード端数による半端な余白が出ないよう、
        # 3列×4行がちょうど収まるサイズを構築時に計算してから開く(下は動的レイアウトに委ねる)
        self._apply_default_size()

    def _apply_default_size(self):
        col, row = self.DEFAULT_COLS, self.DEFAULT_ROWS
        scroll_w = col * self.CARD_W + (col - 1) * self.CARD_SPACING + self.GRID_MARGIN * 2
        scroll_h = row * self.CARD_H + (row - 1) * self.CARD_SPACING + self.GRID_MARGIN * 2
        scrollbar_w = self.style().pixelMetric(self.style().PixelMetric.PM_ScrollBarExtent) + 4
        chrome_h = 92  # 検索バー・ページネーション・余白などスクロール領域以外の高さ(実測に基づき調整)
        outer_margin = 24
        self.resize(scroll_w + scrollbar_w + outer_margin, scroll_h + chrome_h)

        if self.search_input.text().strip():
            QTimer.singleShot(100, lambda: self.do_visual_search(page=1))

    def _on_search_text_live_changed(self):
        # ワードが変わった時点で、進行中の取得を即座に破棄する(自マシンにも相手サーバーにも優しい設計)
        self._abort_inflight()
        self._debounce_timer.start(400)

    def _abort_inflight(self):
        self.search_generation += 1
        for r in self.active_replies:
            try:
                r.abort()
            except RuntimeError:
                pass
        self.active_replies = []

    def _total_pages(self):
        return max(1, math.ceil(len(self.all_matches) / self.page_size))

    def do_visual_search(self, page=None):
        self._abort_inflight()
        gen = self.search_generation

        # 1. 既存のグリッド内のカードを完全にクリア(次ページカードも含めて丸ごと破棄されるため参照もリセット)
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._next_page_card = None

        query = self.search_input.text().strip().lower()
        self.image_retry_limit = self.parent.spin_image_retry.value() if hasattr(self.parent, "spin_image_retry") else 3

        if not query or not hasattr(self.parent, "search_cache") or not self.parent.search_cache:
            self.all_matches = []
            self._update_pagination_ui()
            return

        allowed_sites = set()
        if self.parent.cb_search_k.isChecked(): allowed_sites.add("Kemono")
        if self.parent.cb_search_c.isChecked(): allowed_sites.add("Coomer")
        if self.parent.cb_search_p.isChecked(): allowed_sites.add("Pawchive")

        # 2. まず全件スキャンして合致件数を確定する(ページネーションの総数表示に必要)
        self.all_matches = []
        for item in self.parent.search_cache:
            site = item.get("_site", "Pawchive")
            if site not in allowed_sites:
                continue
            name = item.get("name", "")
            user_id = item.get("id", "")
            if query in name.lower() or query in str(user_id):
                self.all_matches.append(item)

        total_pages = self._total_pages()
        if page is not None:
            self.current_page = page
        self.current_page = max(1, min(self.current_page, total_pages))

        self._update_pagination_ui()

        # 3. このページ分のカードUIだけを構築する(通信はまだ開始しない)
        start_idx = (self.current_page - 1) * self.page_size
        page_items = self.all_matches[start_idx:start_idx + self.page_size]
        self._fetch_queue = []
        self._creator_state = {}
        self._active_fetch_count = 0
        self._current_cards = []

        for idx, item in enumerate(page_items):
            site = item.get("_site", "Pawchive")
            name = item.get("name", "")
            user_id = item.get("id", "")
            service = item.get("service", "")

            card, lbl_icon = self._build_card(site, name, user_id, service)
            self._current_cards.append(card)

            creator_key = f"{site}:{service}:{user_id}:{idx}"
            self._creator_state[creator_key] = {"icon_done": False, "banner_done": False}
            self._fetch_queue.append((creator_key, lbl_icon, card, site, service, user_id))

        # ウィンドウ幅から列数を計算してカードを配置(リサイズにも追従できる共通ロジック)
        self._relayout_grid(force=True)

        # 4. 同時取得数を上限(既定10人分=最大20リクエスト)に制限しつつ順次投入する。
        # 1人分の取得(アイコン・バナー両方)が終わり次第、空いた枠に次の1人を自動で入れる。
        for _ in range(min(self.max_concurrent_creators, len(self._fetch_queue))):
            self._start_next_creator_fetch(gen)

    def _calc_col_count(self):
        # スクロールエリアの表示幅から、1枚280px(+間隔)のカードが何列並べられるかを計算する
        viewport_w = self.scroll.viewport().width()
        available = viewport_w - self.GRID_MARGIN * 2
        col = max(1, (available + self.CARD_SPACING) // (self.CARD_W + self.CARD_SPACING))
        return int(col)

    def _relayout_grid(self, force=False):
        if not self._current_cards:
            return
        col_count = self._calc_col_count()
        if not force and col_count == self._current_col_count:
            return  # 列数が変わらないなら再配置は不要(リサイズ中の無駄な処理を避ける)
        self._current_col_count = col_count

        # 一旦グリッドから外してから、新しい列数で位置だけを付け直す(ウィジェット自体は再生成しない)
        for card in self._current_cards:
            self.grid.removeWidget(card)
        if self._next_page_card is not None and not sip.isdeleted(self._next_page_card):
            self.grid.removeWidget(self._next_page_card)
            self._next_page_card.hide()
        else:
            self._next_page_card = None

        for idx, card in enumerate(self._current_cards):
            r_pos, c_pos = idx // col_count, idx % col_count
            self.grid.addWidget(card, r_pos, c_pos)

        # 最終行に中途半端な空きスロットが残り、かつ次のページが存在する場合のみ、
        # その空きスロットに「次のページへ」ボタンを埋め込む(最終ページでは出さない)
        n = len(self._current_cards)
        has_gap = (n % col_count) != 0
        has_next_page = self.current_page < self._total_pages()
        if has_gap and has_next_page:
            if self._next_page_card is None:
                self._next_page_card = NextPageCard(self.CARD_W, self.CARD_H, self.scroll_content)
                self._next_page_card.clicked.connect(lambda: self.do_visual_search(page=self.current_page + 1))
            r_pos, c_pos = n // col_count, n % col_count
            self.grid.addWidget(self._next_page_card, r_pos, c_pos)
            self._next_page_card.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # リサイズ直後はまだレイアウトの再計算が完了していないことがあるため、
        # イベントループが一周した後(レイアウト確定後)に列数を計算し直す
        QTimer.singleShot(0, lambda: self._relayout_grid(force=False))

    def _update_pagination_ui(self):
        total = len(self.all_matches)
        total_pages = self._total_pages()
        if total == 0:
            self.lbl_pagination_info.setText("該当するクリエイターがいません" if CURRENT_LANG == "ja" else "No matching creators")
        else:
            start = (self.current_page - 1) * self.page_size + 1
            end = min(self.current_page * self.page_size, total)
            self.lbl_pagination_info.setText(
                f"{start} - {end} 件 / 全 {total} 件" if CURRENT_LANG == "ja" else f"Showing {start} - {end} of {total}"
            )

        self.btn_page_first.setEnabled(self.current_page > 1)
        self.btn_page_prev.setEnabled(self.current_page > 1)
        self.btn_page_next.setEnabled(self.current_page < total_pages)
        self.btn_page_last.setEnabled(self.current_page < total_pages)

        # ページ番号ボタンを現在ページ周辺のみ再構築(本家に近い簡易表示)
        while self.page_number_buttons_layout.count():
            item = self.page_number_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        window = 2
        lo = max(1, self.current_page - window)
        hi = min(total_pages, self.current_page + window)
        for p in range(lo, hi + 1):
            btn = QPushButton(str(p))
            btn.setFixedWidth(36)
            btn.setCheckable(True)
            btn.setChecked(p == self.current_page)
            btn.clicked.connect(lambda checked, pp=p: self.do_visual_search(page=pp))
            self.page_number_buttons_layout.addWidget(btn)

    def _build_card(self, site, name, user_id, service):
        card = CustomCardFrame()
        card.setFixedSize(280, 105)

        domain_map = {"Kemono": "kemono.cr", "Coomer": "coomer.st", "Pawchive": "pawchive.pw"}
        domain = domain_map.get(site, "pawchive.pw")
        creator_url = f"https://{domain}/{service}/user/{user_id}"
        card.setProperty("url", creator_url)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)

        lbl_icon = QLabel()
        lbl_icon.setFixedSize(55, 55)
        lbl_icon.setStyleSheet("background-color: #333; border-radius: 6px; border: 1px solid #555;")
        card_layout.addWidget(lbl_icon)

        info_layout = QVBoxLayout()
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("color: #fff; font-weight: bold; font-size: 13px; background: transparent; border: none; padding: 0px;")
        lbl_sub = f"{service} / ID: {user_id}"
        lbl_info = QLabel(lbl_sub)
        lbl_info.setStyleSheet("color: #bbb; font-size: 10px; background: transparent; border: none; padding: 0px;")
        info_layout.addWidget(lbl_name)
        info_layout.addWidget(lbl_info)
        card_layout.addLayout(info_layout)

        btn_add = QPushButton("＋")
        btn_add.setFixedSize(26, 26)
        btn_add.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 4px; border: none; } QPushButton:hover { background-color: #45a049; }")

        def make_add(url=creator_url):
            cur = self.parent.text_urls.toPlainText().strip()
            self.parent.text_urls.setPlainText((cur + "\n" + url) if cur else url)
            if hasattr(self.parent, "log"):
                self.parent.log("SYS", f"画像検索からURLを追加しました: {url}")
            elif hasattr(self.parent, "parent") and hasattr(self.parent.parent, "log"):
                try:
                    self.parent.parent.log("SYS", f"画像検索からURLを追加しました: {url}")
                except Exception:
                    print(f"[SYS] 画像検索からURLを追加しました: {url}")
            else:
                print(f"[SYS] 画像検索からURLを追加しました: {url}")

        btn_add.clicked.connect(lambda _, u=creator_url: make_add(u))
        card_layout.addWidget(btn_add)

        return card, lbl_icon

    def _setup_request(self, url_str, target_domain):
        req = QNetworkRequest(QUrl(url_str))
        req.setRawHeader(b"User-Agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        req.setRawHeader(b"Accept", b"image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8")
        req.setRawHeader(b"Referer", f"https://{target_domain}/".encode('utf-8'))
        return req

    def _start_next_creator_fetch(self, gen):
        if gen != self.search_generation or not getattr(self, "_fetch_queue", None):
            return
        creator_key, lbl_icon, card, site, service, user_id = self._fetch_queue.pop(0)
        self._active_fetch_count += 1

        domain_map = {"Kemono": "kemono.cr", "Coomer": "coomer.st", "Pawchive": "pawchive.pw"}
        domain = domain_map.get(site, "pawchive.pw")
        icon_url1 = f"https://img.kemono.cr/icons/{service}/{user_id}"
        icon_url2 = f"https://{domain}/icons/{service}/{user_id}"
        banner_url1 = f"https://img.kemono.cr/banners/{service}/{user_id}"
        banner_url2 = f"https://{domain}/banners/{service}/{user_id}"

        self._fetch_icon(icon_url1, icon_url2, domain, False, lbl_icon, creator_key, gen, 0)
        self._fetch_banner(banner_url1, banner_url2, domain, False, card, creator_key, gen, 0)

    # A. アイコン取得回路(個別リトライ対応)
    def _fetch_icon(self, url, fallback_url, domain, is_fallback, lbl_icon, creator_key, gen, retry):
        if gen != self.search_generation:
            return
        q_req = self._setup_request(url, domain if is_fallback else "kemono.cr")
        reply = self.network_manager.get(q_req)
        self.active_replies.append(reply)

        def handle_icon_finished():
            if reply in self.active_replies:
                self.active_replies.remove(reply)
            if gen != self.search_generation:
                reply.deleteLater()
                return
            try:
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    raw_data = reply.readAll().data()
                    pix = QPixmap()
                    if pix.loadFromData(raw_data):
                        lbl_icon.setPixmap(pix.scaled(55, 55, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        reply.deleteLater()
                        self._mark_done(creator_key, "icon_done", gen)
                        return

                status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                is_429 = (status == 429)
                reply.deleteLater()

                if not is_fallback:
                    # ミラー(img.kemono.cr)が駄目なら、間隔を空けずに即座に直リンクへ切り替える(既存挙動を維持)
                    self._fetch_icon(fallback_url, fallback_url, domain, True, lbl_icon, creator_key, gen, retry)
                    return

                if retry < self.image_retry_limit:
                    # 429はサーバーへの配慮のため長め、それ以外は短めのランダム間隔で、この1件だけを再試行する
                    delay_ms = int(random.uniform(500, 1000) if is_429 else random.uniform(100, 300))
                    QTimer.singleShot(delay_ms, lambda: self._fetch_icon(fallback_url, fallback_url, domain, True, lbl_icon, creator_key, gen, retry + 1))
                else:
                    self._mark_done(creator_key, "icon_done", gen)
            except RuntimeError:
                if reply in self.active_replies:
                    self.active_replies.remove(reply)

        reply.finished.connect(handle_icon_finished)

    # B. バナー取得回路(個別リトライ対応)
    def _fetch_banner(self, url, fallback_url, domain, is_fallback, card, creator_key, gen, retry):
        if gen != self.search_generation:
            return
        q_req = self._setup_request(url, domain if is_fallback else "kemono.cr")
        reply = self.network_manager.get(q_req)
        self.active_replies.append(reply)

        def handle_banner_finished():
            if reply in self.active_replies:
                self.active_replies.remove(reply)
            if gen != self.search_generation:
                reply.deleteLater()
                return
            try:
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    raw_data = reply.readAll().data()
                    pix = QPixmap()
                    if pix.loadFromData(raw_data):
                        # 280x105にジャストフィットさせるスケーリング
                        scaled_pix = pix.scaled(280, 105, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

                        # 切り抜き・シールド合成用のクリーンなキャンバスを生成
                        final_pix = QPixmap(280, 105)
                        final_pix.fill(Qt.GlobalColor.transparent)

                        p = QPainter(final_pix)
                        p.drawPixmap((280 - scaled_pix.width()) // 2, (105 - scaled_pix.height()) // 2, scaled_pix)
                        p.fillRect(0, 0, 280, 105, QColor(0, 0, 0, 150))
                        p.end()

                        card._background_pixmap = final_pix
                        card.update()

                        reply.deleteLater()
                        self._mark_done(creator_key, "banner_done", gen)
                        return

                status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                is_429 = (status == 429)
                reply.deleteLater()

                if not is_fallback:
                    self._fetch_banner(fallback_url, fallback_url, domain, True, card, creator_key, gen, retry)
                    return

                if retry < self.image_retry_limit:
                    delay_ms = int(random.uniform(500, 1000) if is_429 else random.uniform(100, 300))
                    QTimer.singleShot(delay_ms, lambda: self._fetch_banner(fallback_url, fallback_url, domain, True, card, creator_key, gen, retry + 1))
                else:
                    self._mark_done(creator_key, "banner_done", gen)
            except RuntimeError:
                if reply in self.active_replies:
                    self.active_replies.remove(reply)

        reply.finished.connect(handle_banner_finished)

    def _mark_done(self, creator_key, field, gen):
        if gen != self.search_generation:
            return
        state = self._creator_state.get(creator_key)
        if not state:
            return
        state[field] = True
        if state["icon_done"] and state["banner_done"]:
            # このクリエイターの取得(成功/リトライ上限による諦め、いずれでも)が完了したので枠を1つ空け、
            # 待機列があれば次の1人を投入する
            self._active_fetch_count -= 1
            self._start_next_creator_fetch(gen)

# 2番目にでかいメインワーカークラス
class WorkerProcess(QObject):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(str, float, float, str)
    finished_signal = pyqtSignal(str, dict, bool, bool)
    preview_signal = pyqtSignal(str, str, str, str, str, str, str, str)

    def __init__(self, task, proxy, base_args, is_custom_dest, final_dest_dir, dirname_pattern, fetch_previews=False, kemono_dl_path=None):
        super().__init__()
        self.task = task
        self.task_id = task["id"]
        self.proxy = proxy
        self.base_args = base_args
        
        self.is_custom_dest = is_custom_dest
        self.final_dest_dir = final_dest_dir
        self.dirname_pattern = dirname_pattern
        self.fetch_previews = fetch_previews
        self.kemono_dl_path = kemono_dl_path or app_path("kemono-dl.py")
        
        self.current_domain = "kemono.cr"
        self.current_service = None
        self.current_username = "unknown"
        self.current_user_id = None
        self.cli_finished = False
        self.active_preview_tasks = 0
        self.exit_code = -1
        self.success = False
        
        if task["type"] == "url":
            m_url = re.search(r'https://([^/]+)/([^/]+)/user/([^/]+)', task["target"])
            if m_url: self.current_domain, self.current_service, self.current_user_id = m_url.groups()
        
        if self.is_custom_dest:
            self.staging_dir = user_data_path("_temp_staging_batch")
            # os.path.join()は第2引数が絶対パス(ドライブレター付き、または先頭が\や/)だと
            # 第1引数を無視して第2引数だけを返してしまう。
            # dirname_patternに絶対パスに見える値が来ても必ずstaging_dir配下に
            # 収まるよう、先頭のドライブレター・パス区切り文字を取り除いてから結合する。
            safe_pattern = re.sub(r'^[a-zA-Z]:', '', self.dirname_pattern)
            safe_pattern = safe_pattern.lstrip('\\/')
            self.cli_dirname_pattern = os.path.join(self.staging_dir, safe_pattern)
        else:
            self.staging_dir = None
            self.cli_dirname_pattern = self.dirname_pattern
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.finished.connect(self.handle_finished)
        
        self.buffer = QByteArray()
        self.error_count_403 = 0
        self.error_count_429 = 0
        self.proxy_dead = False
        self.skipped_never_imported = False
        self.psutil_proc = None

        self.last_progress_time = time.time()
        self.watchdog_timer = QTimer()
        self.watchdog_timer.timeout.connect(self.check_stall)

    def start(self):
        args = []
        extracted_name = self.task.get("extracted_name")
        
        for arg in self.base_args:
            if extracted_name and "{username}" in arg:
                args.append(arg.replace("{username}", extracted_name))
            else:
                args.append(arg)
        
        dirname_pattern = self.cli_dirname_pattern
        if extracted_name:
            dirname_pattern = dirname_pattern.replace("{username}", extracted_name)
            
        args.extend(["--dirname-pattern", dirname_pattern])
        
        if self.task.get("force_unlisted") and "--force-unlisted" not in args:
            args.append("--force-unlisted")
        
        if self.proxy:
            args.extend(["--proxy", self.proxy])
            
        if self.task["type"] == "url":
            args.extend(["--links", self.task["target"]])
            t_name = self.task["target"]
        elif self.task["type"] == "favorites":
            args.extend(self.task["args"])
            t_name = L("msg_fav_task")
            
        retry_msg = " (強制取得モード)" if self.task.get("force_unlisted") else ""
        proxy_display = mask_proxy_for_display(self.proxy) if self.proxy else 'None'
        self.log_signal.emit(self.task_id, f"{'開始' if CURRENT_LANG=='ja' else 'Started'}: {t_name}{retry_msg} (Proxy: {proxy_display})")
        
        script_dir = os.path.dirname(self.kemono_dl_path) or APP_DIR
        self.process.setWorkingDirectory(script_dir)
        self.process.start(sys.executable, [self.kemono_dl_path] + args)
        self.watchdog_timer.start(5000)

    def handle_output(self):
        data = self.process.readAllStandardOutput()
        self.buffer.append(data)

        # 改行が来ないまま大量のデータが溜まり続けるとメモリを圧迫するため上限を設ける。
        # 通常のCLI出力は行単位で改行を伴うので、ここに達するのは異常系(バイナリ混入等)のみの想定。
        MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 10MB
        if self.buffer.size() > MAX_BUFFER_SIZE:
            self.log_signal.emit(self.task_id, "警告: 改行のない出力が異常に大きいためバッファを破棄しました。" if CURRENT_LANG == "ja" else "Warning: discarded buffer due to abnormally large output with no line break.")
            self.buffer.clear()
            return
        
        while True:
            rn_idx = self.buffer.indexOf(b'\r\n')
            r_idx = self.buffer.indexOf(b'\r')
            n_idx = self.buffer.indexOf(b'\n')
            
            idxs = [i for i in (rn_idx, r_idx, n_idx) if i != -1]
            if not idxs: break
                
            split_idx = min(idxs)
            line = self.buffer.left(split_idx).data().decode('utf-8', errors='replace')
            
            is_progress = False
            if split_idx == r_idx and (rn_idx == -1 or r_idx < rn_idx):
                is_progress = True
                self.buffer.remove(0, split_idx + 1)
            elif split_idx == rn_idx:
                self.buffer.remove(0, split_idx + 2)
            else:
                self.buffer.remove(0, split_idx + 1)
                
            if line.strip():
                self.parse_line(line, is_progress)
            
    def parse_line(self, line, is_progress):
        self.last_progress_time = time.time()
        
        m_info = re.search(r'INFO:Downloading posts from ([^\s\|]+)\s*\|\s*([^\s\|]+)\s*\|\s*([^\|]+?)\s*\|\s*([^\s\|]+)', line)
        if m_info:
            self.current_domain, self.current_service, self.current_username, self.current_user_id = [x.strip() for x in m_info.groups()]

        if is_progress or line.startswith("[="):
            m = re.search(r'\[.*\]\s+([\d\.]+)/([\d\.]+)\s+([KMG]?B)\s+at\s+(.+/s)\s+ETA\s+(.+)', line)
            if m:
                try:
                    current = float(m.group(1))
                    total = float(m.group(2))
                    status_text = f"{current}/{total} {m.group(3)} @ {m.group(4)} (ETA: {m.group(5)})"
                    self.progress_signal.emit(self.task_id, current, total, status_text)
                except: pass
        else:
            if line.startswith("INFO:Downloading: "):
                filename = line.replace("INFO:Downloading: ", "").strip()
                self.progress_signal.emit(self.task_id, 0, 0, f"{L('msg_downloading')} {filename}")
            
            self.log_signal.emit(self.task_id, line)
            
            if "never imported" in line.lower():
                self.skipped_never_imported = True
            
            if self.fetch_previews and ("not imported" in line.lower() or "skipping post" in line.lower()):
                m_skip = re.search(r'skipping post\s+(\d+)', line.lower())
                p_id = m_skip.group(1) if m_skip else None
                if p_id and self.current_service and self.current_user_id:
                    target_dir = self.staging_dir if self.staging_dir else (self.final_dest_dir if self.final_dest_dir else APP_DIR)
                    self.preview_signal.emit(self.task_id, self.current_domain, self.current_service, 
                                             self.current_username, self.current_user_id, p_id, target_dir, self.dirname_pattern)
        
        line_lower = line.lower()
        if "403 forbidden" in line_lower:
            self.error_count_403 += 1
        if "429 too many requests" in line_lower:
            self.error_count_429 += 1
            
        proxy_fatal_errors = ["max retries exceeded", "connectionerror", "ttl expired", "proxyerror", "failed to establish a new connection"]
        has_fatal_proxy_err = any(err in line_lower for err in proxy_fatal_errors)

        if self.error_count_403 >= 3 or self.error_count_429 >= 5 or has_fatal_proxy_err:
            self.log_signal.emit(self.task_id, L("msg_proxy_dead"))
            self.proxy_dead = True
            self.stop(force=True)

    def handle_finished(self, exit_code, exit_status):
        self.exit_code = exit_code
        self.success = (exit_code == 0) and not self.proxy_dead
        if self.skipped_never_imported and not self.task.get("force_unlisted"):
            self.success = False
            
        self.cli_finished = True
        self.check_and_finalize()

    def check_and_finalize(self):
        if not self.cli_finished: return
        if self.active_preview_tasks > 0: return 
        
        success = self.success
        if not success and self.skipped_never_imported:
            pass
        else:
            self.log_signal.emit(self.task_id, L("msg_task_end").format(self.exit_code))
        
        self.finished_signal.emit(self.task_id, self.task, success, self.skipped_never_imported)

    def _get_psutil_proc(self):
        if not self.psutil_proc and self.process.state() == QProcess.ProcessState.Running:
            try:
                self.psutil_proc = psutil.Process(self.process.processId())
            except psutil.NoSuchProcess:
                pass
        return self.psutil_proc

    def suspend(self):
        p = self._get_psutil_proc()
        if p:
            try:
                for child in p.children(recursive=True):
                    try: child.suspend()
                    except: pass
                p.suspend()
                self.log_signal.emit(self.task_id, L("msg_suspend_task"))
            except Exception as e:
                self.log_signal.emit(self.task_id, f"Suspend Failed: {e}")

    def resume(self):
        p = self._get_psutil_proc()
        if p:
            try:
                for child in p.children(recursive=True):
                    try: child.resume()
                    except: pass
                p.resume()
                self.log_signal.emit(self.task_id, L("msg_resume_task"))
            except Exception as e:
                self.log_signal.emit(self.task_id, f"Resume Failed: {e}")

    def check_stall(self):
        if time.time() - self.last_progress_time > 30:
            self.log_signal.emit(self.task_id, "通信のタイムアウトを検知しました。プロセスを再起動します。" if CURRENT_LANG == "ja" else "Network stall detected. Restarting process.")
            self.proxy_dead = True
            self.stop(force=True)

    def stop(self, force=False):
        self.watchdog_timer.stop()
        if force:
            self.process.kill()
        else:
            p = self._get_psutil_proc()
            if p:
                try: p.terminate()
                except: self.process.terminate()

class WafCheckDialog(QDialog):
    # 403が閾値を超えた際に、プロキシではなくサイト側のWAF/Turnstile等のアクセス制限を
    # 疑うケース向けに、実際のブラウザエンジンでそのドメインを開いて人間が確認・突破できる
    # ようにするための軽量ダイアログ。自動でチャレンジを解こうとするものではない。
    # Claudeくんはこう書いてますがブラウザが立ち上がればおそらく甘い設定であれば自動で突破できるかと思われます
    def __init__(self, domain, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(f"アクセス制限の確認 (WAF/Turnstile Check) - {domain}")
        self.resize(1000, 720)
        layout = QVBoxLayout(self)

        info = QLabel(
            f"{domain} への情報取得(検索キャッシュ/クリエイター情報)が403エラーで失敗しました。\n"
            "サイト側のアクセス制限(WAF・Turnstile等)が働いている可能性があります。下のブラウザで\n"
            "実際にサイトを開き、必要であればチェック(Turnstile等)を通過してから再試行してください。"
            if CURRENT_LANG == "ja" else
            f"Fetching info from {domain} (search cache / creator info) failed with a 403 error.\n"
            "This may indicate a site-wide access restriction (WAF/Turnstile).\n"
            "Use the browser below to open the site and pass any challenge if needed, then retry."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(f"https://{domain}/"))
        layout.addWidget(self.browser, 1)

        btn_close = QPushButton("閉じる" if CURRENT_LANG == "ja" else "Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

class CookieLoginDialog(QDialog):
    def __init__(self, parent=None, is_auto_prompt=False):
        super().__init__(parent)
        self.setWindowTitle(L("dlg_cookie"))
        self.resize(1000, 700)
        self.parent_gui = parent

        layout = QVBoxLayout(self)

        nav_layout = QGridLayout()
        nav_layout.setSpacing(5)
        
        btn_k_login = QPushButton("Kemono ログイン" if CURRENT_LANG == "ja" else "Kemono Login")
        btn_k_login.clicked.connect(lambda: self.webview.setUrl(QUrl("https://kemono.cr/authentication/login")))
        btn_k_reg = QPushButton("Kemono 登録" if CURRENT_LANG == "ja" else "Kemono Register")
        btn_k_reg.clicked.connect(lambda: self.webview.setUrl(QUrl("https://kemono.cr/authentication/register")))
        
        btn_c_login = QPushButton("Coomer ログイン" if CURRENT_LANG == "ja" else "Coomer Login")
        btn_c_login.clicked.connect(lambda: self.webview.setUrl(QUrl("https://coomer.st/authentication/login")))
        btn_c_reg = QPushButton("Coomer 登録" if CURRENT_LANG == "ja" else "Coomer Register")
        btn_c_reg.clicked.connect(lambda: self.webview.setUrl(QUrl("https://coomer.st/authentication/register")))
        
        btn_p_login = QPushButton("Pawchive ログイン" if CURRENT_LANG == "ja" else "Pawchive Login")
        btn_p_login.clicked.connect(lambda: self.webview.setUrl(QUrl("https://pawchive.pw/account/login")))
        btn_p_reg = QPushButton("Pawchive 登録" if CURRENT_LANG == "ja" else "Pawchive Register")
        btn_p_reg.clicked.connect(lambda: self.webview.setUrl(QUrl("https://pawchive.pw/account/register")))

        nav_layout.addWidget(btn_k_login, 0, 0)
        nav_layout.addWidget(btn_k_reg, 0, 1)
        nav_layout.addWidget(btn_c_login, 0, 2)
        nav_layout.addWidget(btn_c_reg, 0, 3)
        nav_layout.addWidget(btn_p_login, 0, 4)
        nav_layout.addWidget(btn_p_reg, 0, 5)
        layout.addLayout(nav_layout)

        self.webview = QWebEngineView()
        self.profile = QWebEngineProfile.defaultProfile()
        self.webview.setUrl(QUrl("https://kemono.cr/authentication/login"))
        layout.addWidget(self.webview, 1)

        bottom_layout = QHBoxLayout()
        self.cb_never_show = QCheckBox("二度と表示しない" if CURRENT_LANG == "ja" else "Never show again")
        if not is_auto_prompt:
            self.cb_never_show.setVisible(False)
            
        self.btn_save_cookie = QPushButton("Cookieを保存して閉じる" if CURRENT_LANG == "ja" else "Save Cookies & Close")
        self.btn_save_cookie.clicked.connect(self.extract_cookies_and_close)

        bottom_layout.addWidget(self.cb_never_show)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_save_cookie)
        layout.addLayout(bottom_layout)

    def extract_cookies_and_close(self):
        self.btn_save_cookie.setEnabled(False)
        self.btn_save_cookie.setText("保存中..." if CURRENT_LANG=="ja" else "Saving...")
        self.extracted_cookies = []
        self._cookies_written = False

        # QWebEngineCookieStoreには「全件ロード完了」を通知するシグナルが存在しないため、
        # 固定時間待ちではなく「cookieAddedが一定時間発火しなくなったら完了とみなす」
        # デバウンス方式にする。cookieが届くたびにタイマーを延長し、届かなくなって
        # から400ms経ったら書き込む。万一延々と届き続けるケースに備え、絶対上限も設ける。
        self._cookie_quiet_timer = QTimer(self)
        self._cookie_quiet_timer.setSingleShot(True)
        self._cookie_quiet_timer.timeout.connect(self.write_cookies)

        self._cookie_hard_limit_timer = QTimer(self)
        self._cookie_hard_limit_timer.setSingleShot(True)
        self._cookie_hard_limit_timer.timeout.connect(self.write_cookies)
        self._cookie_hard_limit_timer.start(5000)

        self.cookie_store = self.profile.cookieStore()
        self.cookie_store.cookieAdded.connect(self.on_cookie_added)
        self.cookie_store.loadAllCookies()

        self._cookie_quiet_timer.start(400)

    def on_cookie_added(self, cookie: QNetworkCookie):
        self.extracted_cookies.append(cookie)
        if hasattr(self, "_cookie_quiet_timer"):
            self._cookie_quiet_timer.start(400)  # 新着があるたびに静寂タイマーを延長

    def write_cookies(self):
        # 静寂タイマー・絶対上限タイマーのどちらが先に発火しても呼ばれうるため、
        # 実際の書き込みは一度だけに制限する。
        if getattr(self, "_cookies_written", False):
            return
        self._cookies_written = True
        if hasattr(self, "_cookie_quiet_timer"):
            self._cookie_quiet_timer.stop()
        if hasattr(self, "_cookie_hard_limit_timer"):
            self._cookie_hard_limit_timer.stop()

        lines = ["# Netscape HTTP Cookie File", "# This is a generated file!  Do not edit.", ""]
        for c in self.extracted_cookies:
            domain = c.domain()
            path = c.path()
            secure = "TRUE" if c.isSecure() else "FALSE"
            expires = str(c.expirationDate().toSecsSinceEpoch()) if not c.isSessionCookie() else "0"
            name = bytearray(c.name()).decode('utf-8', errors='ignore')
            value = bytearray(c.value()).decode('utf-8', errors='ignore')
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            lines.append(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}")

        cookie_path = user_data_path("cookies.txt")
        try:
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            if self.parent_gui:
                self.parent_gui.widgets_map["--cookies"]["widget"].setText(cookie_path)
                if self.cb_never_show.isChecked():
                    self.parent_gui.config["skip_cookie_warning"] = True
                    self.parent_gui.save_config()
        except Exception as e:
            QMessageBox.critical(self, L("dlg_err"), f"Failed to save cookies: {e}")

        self.accept()

class MigrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 閉じたら確実に解放(ImageSearchDialogと同種のリーク対策)
        self.setWindowTitle("お引っ越しツール / Migration Tool (Kemono <-> Pawchive)")
        self.resize(1100, 750)
        
        self.captured_artists = []
        self.captured_posts = []
        self.nav_btns = []
        
        layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()
        for name, url in [("Kemono", "https://kemono.cr/"), ("Pawchive", "https://pawchive.pw/")]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, u=url: self.browser.setUrl(QUrl(u)))
            self.nav_btns.append(btn)
            nav_layout.addWidget(btn)
        left_layout.addLayout(nav_layout)
        
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://kemono.cr/"))
        left_layout.addWidget(self.browser)
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        self.lbl_status = QLabel("メモリ保存状況 (Saved in Memory):\n0 Authors, 0 Posts")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 14px; color: #20b2aa;")
        right_layout.addWidget(self.lbl_status)
        
        self.btn_capture = QPushButton("📥 1. 現在のサイトからお気に入りを取得\n(Capture from Current Site)")
        self.btn_capture.setStyleSheet("padding: 10px; font-weight: bold; font-size: 13px;")
        self.btn_capture.clicked.connect(self.do_capture)
        right_layout.addWidget(self.btn_capture)
        
        self.btn_apply = QPushButton("📤 2. 現在のサイトへお気に入りを適用\n(Apply to Current Site)")
        self.btn_apply.setStyleSheet("padding: 10px; font-weight: bold; font-size: 13px;")
        self.btn_apply.clicked.connect(self.do_apply)
        self.btn_apply.setEnabled(False)
        right_layout.addWidget(self.btn_apply)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)
        
        self.prog = QProgressBar()
        self.prog.setValue(0)
        right_layout.addWidget(self.prog)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        right_widget.setFixedWidth(350)
        
        layout.addWidget(left_widget, 1)
        layout.addWidget(right_widget)
        
    def log(self, msg):
        self.log_area.append(msg)
        
    def toggle_nav(self, state):
        for btn in self.nav_btns: btn.setEnabled(state)
        
    def do_capture(self):
        self.btn_capture.setEnabled(False)
        self.toggle_nav(False)
        self.log("=== キャプチャ開始 (Starting Capture) ===")
        self.log("Authorsを取得中...")
        script = "fetch('/api/v1/account/favorites?type=artist').then(r=>r.json()).catch(e=>[])"
        self.browser.page().runJavaScript(script, self.on_capture_artists)
        
    def on_capture_artists(self, res):
        self.captured_artists = res if isinstance(res, list) else []
        self.log(f"-> {len(self.captured_artists)}件のAuthorを取得。Postsを取得中...")
        script = "fetch('/api/v1/account/favorites?type=post').then(r=>r.json()).catch(e=>[])"
        self.browser.page().runJavaScript(script, self.on_capture_posts)
        
    def on_capture_posts(self, res):
        self.captured_posts = res if isinstance(res, list) else []
        self.log(f"-> {len(self.captured_posts)}件のPostを取得完了。")
        self.lbl_status.setText(f"メモリ保存状況 (Saved in Memory):\n{len(self.captured_artists)} Authors, {len(self.captured_posts)} Posts")
        self.btn_capture.setEnabled(True)
        self.toggle_nav(True)
        if self.captured_artists or self.captured_posts:
            self.btn_apply.setEnabled(True)
            self.log("適用先(移行先)のサイトへ移動し、適用ボタンを押してください。")
            
    def do_apply(self):
        self.btn_apply.setEnabled(False)
        self.btn_capture.setEnabled(False)
        self.toggle_nav(False)
        self.apply_queue = []
        for a in self.captured_artists:
            self.apply_queue.append({"type": "artist", "data": a})
        for p in self.captured_posts:
            self.apply_queue.append({"type": "post", "data": p})
        
        self.apply_total = len(self.apply_queue)
        self.apply_done = 0
        self.prog.setMaximum(self.apply_total)
        self.prog.setValue(0)
        
        self.log(f"=== 適用開始: 合計 {self.apply_total} 件 ===")
        self.apply_next()
        
    def safe_run_javascript(self, script, callback):
        # WA_DeleteOnCloseにより、200ms待つ間にダイアログが閉じられ
        # self.browser (QWebEngineView) のC++実体が既に破棄されている可能性があるため、
        # 実行直前に生存確認をしてから触る。破棄後にアクセスするとクラッシュしうる。
        if sip.isdeleted(self):
            return
        try:
            self.browser.page().runJavaScript(script, callback)
        except RuntimeError:
            pass  # 直前で閉じられた場合など、C++側が既に破棄されているケース

    def apply_next(self):
        if not self.apply_queue:
            self.log("=== 全ての適用が完了しました！ (Apply Finished) ===")
            self.btn_apply.setEnabled(True)
            self.btn_capture.setEnabled(True)
            self.toggle_nav(True)
            return
            
        item = self.apply_queue.pop(0)
        self.apply_done += 1
        self.prog.setValue(self.apply_done)
        
        if item["type"] == "artist":
            d = item["data"]
            service, uid = d.get('service'), d.get('id')
            name = d.get('name', uid)
            self.log(f"適用中(Author): {service}/{name}")
            script = f"fetch('/api/v1/favorites/creator/{service}/{uid}', {{method:'POST'}}).then(r=>r.ok).catch(e=>false)"
        else:
            d = item["data"]
            service, user, pid = d.get('service'), d.get('user'), d.get('id')
            title = d.get('title', pid)
            self.log(f"適用中(Post): {service}/{user}/{title}")
            script = f"fetch('/api/v1/favorites/post/{service}/{user}/{pid}', {{method:'POST'}}).then(r=>r.ok).catch(e=>false)"
            
        QTimer.singleShot(200, lambda: self.safe_run_javascript(script, self.on_apply_result))
        
    def on_apply_result(self, res):
        if not res:
            self.log(" -> [スキップ] 既に存在するか、認証エラーです。")
        self.apply_next()

# 一番でっかいメインのクラス
class KemonoDLGUI(QMainWindow):
    merge_log_signal = pyqtSignal(str, str)
    merge_finished_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kemoffu Downloader")
        self.resize(1050, 600)
        self.merge_log_signal.connect(self.log)
        self.merge_finished_signal.connect(self.finish_all_tasks)
        self.widgets_map = {}
        self.active_workers = {}
        self.task_widgets = {}
        self.task_queue = []
        self.group_stats = {}
        self.ext_checkboxes = {}
        self.is_paused = False
        self.is_running = False
        self.config = {"skip_cookie_warning": False, "shortcut_prompt_shown": False}
        self.tray_icon = None
        self.all_creators_cache = []

        self.init_ui()
        self.load_config()
        self.apply_theme(self.combo_theme.currentText() if self.combo_theme.currentText() else "自動 (システム追従)")

        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.manage_queue)

        self.preview_pool = QThreadPool()
        self.api_pool = QThreadPool()
        self.active_api_fetches = 0

        QTimer.singleShot(500, self.post_init_routines)

    def post_init_routines(self):
        if not self.config.get("shortcut_prompt_shown", False):
            msg = QMessageBox(self)
            msg.setWindowTitle("Setup & Privacy Info" if CURRENT_LANG == "en" else "初回セットアップとプライバシーに関するお知らせ")
            text_ja = (
                "<b>【ショートカットの作成】</b><br>"
                "本ツールはCLI実行ファイルと同一フォルダ内で動作する必要があります。<br>"
                "利便性のため、デスクトップに起動用ショートカット(.lnk)を作成しますか？<br><br>"
                "<hr>"
                "<b>【プライバシーと通信仕様について】</b><br>"
                "本ツールは起動時に、アップデートの有無を確認するため外部サーバー(GitHub)の静的ファイルへ自動的にアクセスします。<br>"
                "この通信において、IPアドレスなどの個人情報や利用環境データが開発者側へ送信・収集されることは<b>一切ありません。</b><br>"
                "（アクセス数を利用推計にのみ役立てます）"
            )
            text_en = (
                "<b>[Create Shortcut]</b><br>"
                "Do you want to create a desktop shortcut (.lnk) for convenience?<br><br>"
                "<hr>"
                "<b>[Privacy & Network Usage]</b><br>"
                "This tool silently checks an external server (GitHub) for updates on startup.<br>"
                "<b>No personal data or IP addresses are collected</b> during this process.<br>"
                "(Anonymous requests simply help estimate active users.)"
            )
            msg.setText(text_ja if CURRENT_LANG == "ja" else text_en)
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            cb_never = QCheckBox("今後、この画面を表示しない" if CURRENT_LANG == "ja" else "Never show this again")
            cb_never.setChecked(True)
            msg.setCheckBox(cb_never)

            if msg.exec() == QMessageBox.StandardButton.Yes:
                self.create_desktop_shortcut()

            if cb_never.isChecked():
                self.config["shortcut_prompt_shown"] = True
                self.save_config()

        if self.widgets_map.get("--auto-update", {}).get("widget", QCheckBox()).isChecked():
            self.update_checker = UpdateChecker()
            self.update_checker.update_available.connect(self.on_update_available)
            self.update_checker.start()
            
        self.refresh_history()
        # 起動時にローカルキャッシュをチェック＆ロード
        self.init_creator_cache()

    def create_desktop_shortcut(self):
        try:
            desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            path = os.path.join(desktop, 'Kemono-DL GUI.lnk')
            target = sys.executable
            args = os.path.abspath(sys.argv[0])
            work_dir = os.path.dirname(args)

            vbs_script = f'''
Set ws = WScript.CreateObject("WScript.Shell")
Set link = ws.CreateShortcut("{path}")
link.TargetPath = "{target}"
link.Arguments = "{args}"
link.WorkingDirectory = "{work_dir}"
link.Save
'''
            vbs_path = os.path.join(work_dir, "temp_create_shortcut.vbs")
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_script)

            if os.name == 'nt':
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                subprocess.run(["cscript", "//Nologo", vbs_path], creationflags=flags)
                os.remove(vbs_path)
                self.log("SYS", "デスクトップにショートカットを作成しました。" if CURRENT_LANG == "ja" else "Created desktop shortcut.")
        except Exception as e:
            self.log("SYS", f"{'ショートカット作成失敗' if CURRENT_LANG=='ja' else 'Shortcut creation failed'}: {e}")

    def on_update_available(self, version, url):
        msg = f"新しいバージョン ({version}) が利用可能です。\nダウンロードページを開きますか？" if CURRENT_LANG == "ja" else f"New version ({version}) is available.\nOpen download page?"
        reply = QMessageBox.question(self, L("dlg_update"), msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(url))

# 苦労したウィジェット部分の調整など
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_layout = QHBoxLayout()
        self.btn_migration = QPushButton("✨ Migration Tool" if CURRENT_LANG == "en" else "✨ お引っ越しツール")
        self.btn_migration.clicked.connect(self.open_migration_tool)
        header_layout.addWidget(self.btn_migration)
        
        header_layout.addStretch()
        header_layout.addWidget(QLabel(L("theme")))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([L("theme_auto"), L("theme_dark"), L("theme_light")])
        self.combo_theme.currentTextChanged.connect(self.apply_theme)
        header_layout.addWidget(self.combo_theme)
        main_layout.addLayout(header_layout, 0)

        url_group = QGroupBox(L("lbl_urls"))
        url_layout = QVBoxLayout()
        self.text_urls = LocalizedTextEdit()
        self.text_urls.setPlaceholderText(L("urls_ph"))
        self.text_urls.setMaximumHeight(120)  # 無限に広がるのを防ぎ、適正な高さを維持
        url_layout.addWidget(self.text_urls)
        url_group.setLayout(url_layout)
        main_layout.addWidget(url_group, 0)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel(L("lbl_max_proc")))
        self.spin_concurrency = QSpinBox()
        self.spin_concurrency.setRange(1, 100)
        self.spin_concurrency.setValue(5)
        ctrl_layout.addWidget(self.spin_concurrency)
        ctrl_layout.addStretch()
        main_layout.addLayout(ctrl_layout, 0)

        self.tabs = QTabWidget()
        self.tabs.setFixedHeight(385) # スクロールバー解消のため拡張
        
        self.build_option_tabs()
        
        # 検索タブを既存機能に統合
        self.tabs.addTab(self.build_search_tab(), L("tab_search"))
        self.tabs.addTab(self.build_history_tab(), L("tab_history"))
        main_layout.addWidget(self.tabs, 0)

        dest_layout = QHBoxLayout()
        self.cb_custom_dest = QCheckBox(L("lbl_override"))
        self.cb_custom_dest.toggled.connect(self.toggle_custom_dest)

        self.edit_dest_dir = LocalizedLineEdit()
        self.edit_dest_dir.setText(os.path.join(os.path.expanduser("~"), "Downloads", "Kemoffu"))
        self.edit_dest_dir.setEnabled(False)

        self.btn_browse_dest = QPushButton(L("btn_browse"))
        self.btn_browse_dest.clicked.connect(lambda: self.browse_folder(self.edit_dest_dir))
        self.btn_browse_dest.setEnabled(False)

        dest_layout.addWidget(self.cb_custom_dest)
        dest_layout.addWidget(self.edit_dest_dir)
        dest_layout.addWidget(self.btn_browse_dest)
        main_layout.addLayout(dest_layout, 0)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton(L("btn_start"))
        self.btn_start.clicked.connect(self.check_cookie_and_start)
        self.btn_pause = QPushButton(L("btn_pause"))
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_stop = QPushButton(L("btn_stop"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_all)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        main_layout.addLayout(btn_layout, 0)

        bottom_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setMinimumHeight(100) # ウィジェットが完全に押し潰されるのを防止
        
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.task_scroll.setWidget(self.task_container)
        bottom_splitter.addWidget(self.task_scroll)

        self.console = LocalizedTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(80) # ログエリアの最低限の視認性を確保
        bottom_splitter.addWidget(self.console)

        bottom_splitter.setSizes([150, 100])
        main_layout.addWidget(bottom_splitter, 1)

    def build_search_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 1段目: 画像検索（本家UI）起動ボタン
        btn_img_search = QPushButton(L("btn_img_search"))
        btn_img_search.setStyleSheet("padding: 8px; font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        btn_img_search.clicked.connect(self.open_image_search_dialog)
        layout.addWidget(btn_img_search)
        
        # 2段目: 超高速テキスト検索コントロール
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("クリエイター名やIDを素早くテキスト検索..." if CURRENT_LANG == "ja" else "Fast text search by name or ID...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_input)
        
        # Kemono/Coomerの現在全員に返している403エラーを回避するため、初期状態はPawchiveのみTrueに設定
        self.cb_search_k = QCheckBox("Kemono"); self.cb_search_k.setChecked(False)
        self.cb_search_c = QCheckBox("Coomer"); self.cb_search_c.setChecked(False)
        self.cb_search_p = QCheckBox("Pawchive"); self.cb_search_p.setChecked(True)
        self.cb_search_k.toggled.connect(self.on_search_text_changed)
        self.cb_search_c.toggled.connect(self.on_search_text_changed)
        self.cb_search_p.toggled.connect(self.on_search_text_changed)
        
        search_layout.addWidget(self.cb_search_k)
        search_layout.addWidget(self.cb_search_c)
        search_layout.addWidget(self.cb_search_p)
        
        self.btn_update_cache = QPushButton("🔄 キャッシュ手動更新" if CURRENT_LANG == "ja" else "🔄 Refresh Cache")
        self.btn_update_cache.clicked.connect(lambda: self.init_creator_cache(force=True))
        search_layout.addWidget(self.btn_update_cache)
        
        layout.addLayout(search_layout)

        # 画像検索モードでのアイコン・バナー取得リトライ回数(ネットワーク環境に応じてユーザーが調整可能)
        retry_layout = QHBoxLayout()
        lbl_retry = QLabel("画像取得リトライ回数:" if CURRENT_LANG == "ja" else "Image fetch retry count:")
        retry_layout.addWidget(lbl_retry)
        self.spin_image_retry = QSpinBox()
        self.spin_image_retry.setRange(0, 10)
        self.spin_image_retry.setValue(3)
        self.spin_image_retry.setToolTip(
            "画像検索モードでアイコン・バナーの取得に失敗した際、何回まで再試行するかの設定です。"
            "429(レート制限)は0.5〜1秒、それ以外のエラーは0.1〜0.3秒のランダムな間隔で1件ずつ個別に再試行します。"
            if CURRENT_LANG == "ja" else
            "How many times to retry fetching an icon/banner in Visual Search mode after a failure. "
            "429 (rate limit) retries wait 0.5-1s; other errors wait 0.1-0.3s, each item retried individually."
        )
        retry_layout.addWidget(self.spin_image_retry)
        retry_layout.addStretch()
        layout.addLayout(retry_layout)
        
        # 3段目: ステータスと検索結果リスト
        self.lbl_search_status = QLabel("キャッシュを準備中... (Loading cache...)")
        layout.addWidget(self.lbl_search_status)
        
        from PyQt6.QtWidgets import QListWidget
        self.search_list = QListWidget()
        layout.addWidget(self.search_list)
        
        return widget

    def init_creator_cache(self, force=False):
        cache_file = user_data_path("creators_cache.json")
        
        # クラス変数として更新中フラグを初期化（存在しない場合のみ）
        if not hasattr(self, "is_updating_cache"):
            self.is_updating_cache = False

        # 1. 24時間以内の有効なキャッシュがあれば超高速ローカルロード
        if not force and os.path.exists(cache_file):
            try:
                mtime = os.path.getmtime(cache_file)
                if time.time() - mtime < 86400:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        self.search_cache = json.load(f)
                    self.lbl_search_status.setText(f"キャッシュをローカルから読み込みました ({len(self.search_cache)}件)" if CURRENT_LANG == "ja" else f"Loaded cache from local ({len(self.search_cache)} items)")
                    if hasattr(self, "on_search_text_changed"):
                        self.on_search_text_changed()
                    return
            except:
                pass

        # 更新中フラグをアクティブにし、無駄なポップアップを抑制
        self.is_updating_cache = True
        self.lbl_search_status.setText("キャッシュを取得中... (Updating cache...)")
        
        # 2. チェックボックスの選択状態をスキャン
        target_apis = []
        if self.cb_search_k.isChecked():
            target_apis.append(("Kemono", "https://kemono.cr/api/v1/creators"))
        if self.cb_search_c.isChecked():
            target_apis.append(("Coomer", "https://coomer.st/api/v1/creators"))
        if self.cb_search_p.isChecked():
            target_apis.append(("Pawchive", "https://pawchive.pw/api/v1/creators"))

        if not target_apis:
            self.lbl_search_status.setText("対象サイトが選択されていません。" if CURRENT_LANG == "ja" else "No target sites selected.")
            self.is_updating_cache = False
            return

        if hasattr(self, "cache_worker") and self.cache_worker and self.cache_worker.isRunning():
            self.cache_worker.terminate()
            self.cache_worker.wait()

        self.cache_worker = CacheUpdateWorker(target_apis)
        
        def on_worker_finished(combined_cache, error_messages, site_counts):
            if combined_cache:
                self.search_cache = combined_cache
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(combined_cache, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    if hasattr(self, "log"):
                        self.log("SYS", f"キャッシュファイルの書き込みに失敗しました: {e}" if CURRENT_LANG == "ja" else f"Failed to write cache file: {e}")
            
            # キャッシュの更新処理が完全に終了したためフラグを解除
            self.is_updating_cache = False
            
            # サイトごとの内訳を常に組み立てる(成功したサイトの件数も、失敗したサイトの理由も両方出す)
            site_domains = {name: re.sub(r'^https?://([^/]+)/.*$', r'\1', url) for name, url in target_apis}
            breakdown_parts = []
            for site_name, _ in target_apis:
                if site_name in site_counts:
                    count = site_counts[site_name]
                    part = f"{site_name}:{count}件" if CURRENT_LANG == "ja" else f"{site_name}:{count}"
                else:
                    fail_reason = next((e for e in error_messages if e.startswith(site_name + "(")), None)
                    reason_text = fail_reason.split("(", 1)[1] if fail_reason else ")"  # "サイト名(理由)" の"(理由)"部分だけを取り出す
                    label = "失敗" if CURRENT_LANG == "ja" else "failed"
                    part = f"{site_name}:{label}({reason_text}" if fail_reason else f"{site_name}:{label}(不明{reason_text}" if CURRENT_LANG == "ja" else f"{site_name}:{label}(unknown{reason_text}"
                    # 情報取得APIが403で失敗した場合、サイト側のアクセス制限(WAF/Turnstile)を疑い
                    # 手動確認できるブラウザを提示する(ダウンロード中には出さない方針)
                    if fail_reason and "403" in fail_reason:
                        self.check_waf_and_offer_browser(site_domains.get(site_name, ""), fail_reason)
                breakdown_parts.append(part)
            breakdown = " / ".join(breakdown_parts)
            
            if error_messages:
                msg = f"一部取得失敗 [{breakdown}] | 計 {len(combined_cache)}件保持" if CURRENT_LANG == "ja" else f"Partial failure [{breakdown}] | {len(combined_cache)} items kept"
            else:
                msg = f"キャッシュ更新完了 [{breakdown}]" if CURRENT_LANG == "ja" else f"Cache updated [{breakdown}]"
            
            # ログにも残しておく(この直後のon_search_text_changed()がラベルを上書きしても、
            # ここだけは消えずに確認できる)
            self.log("SYS", msg)
            
            # 先に検索結果リストを新しいキャッシュで更新してから、最後にこの内訳メッセージを
            # ラベルに反映する(逆順だとon_search_text_changed側の汎用メッセージで即座に
            # 上書きされ、内訳が一切表示されないまま消えてしまうため)
            if hasattr(self, "on_search_text_changed"):
                self.on_search_text_changed()
            self.lbl_search_status.setText(msg)

        self.cache_worker.finished_signal.connect(on_worker_finished)
        self.cache_worker.start()

    def on_search_text_changed(self):
        # 1. 安全弁：取得中であれば警告ポップアップで邪魔せず、ラベル表示のみで静かに処理を流す
        if getattr(self, "is_updating_cache", False):
            self.lbl_search_status.setText("現在キャッシュ更新中です。しばらくお待ちください... (Updating cache...)")
            return

        if not hasattr(self, "search_cache") or not self.search_cache:
            self.search_list.clear()
            return

        # 2. 検索キーワードの取得と正規化
        query = self.search_input.text().strip().lower()
        self.search_list.clear()

        if not query:
            self.lbl_search_status.setText(f"ローカルキャッシュ: 全{len(self.search_cache)}件保持中" if CURRENT_LANG == "ja" else f"Local cache: {len(self.search_cache)} items total")
            return
        
        # 3. 画面上のチェックボックスから、検索対象とするサイトの判定セットを論理的に構築
        allowed_sites = set()
        if self.cb_search_k.isChecked(): allowed_sites.add("Kemono")
        if self.cb_search_c.isChecked(): allowed_sites.add("Coomer")
        if self.cb_search_p.isChecked(): allowed_sites.add("Pawchive")

        match_count = 0
        max_display = 100 # 大量の描画によるUIのプチフリーズを防ぐための表示上限制限

        # 4. インメモリの高速フィルタリングループ
        for item in self.search_cache:
            if match_count >= max_display:
                break

            site = item.get("_site", "Pawchive") # メタデータがない場合はPawchiveをフォールバック
            if site not in allowed_sites:
                continue

            name = item.get("name", "")
            user_id = item.get("id", "")
            service = item.get("service", "")

            # 名前またはIDに部分一致するか判定
            if query in name.lower() or query in str(user_id):
                match_count += 1
                
                # リストアイテムの表示用コンテナウィジェットの生成
                from PyQt6.QtWidgets import QListWidgetItem
                list_item = QListWidgetItem(self.search_list)
                
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(5, 2, 5, 2)
                
                # クリエイター情報のテキスト整形
                info_text = f"[{site} / {service}]  {name} ({user_id})"
                lbl_info = QLabel(info_text)
                row_layout.addWidget(lbl_info)
                row_layout.addStretch()
                
                # 一発追加用ボタンの配置
                btn_add = QPushButton("＋ リストに追加" if CURRENT_LANG == "ja" else "+ Add to List")
                btn_add.setStyleSheet("padding: 2px 8px; font-size: 11px;")
                
                # 各サイトの論理ドメインマッピング
                domain_map = {"Kemono": "kemono.cr", "Coomer": "coomer.st", "Pawchive": "pawchive.pw"}
                domain = domain_map.get(site, "pawchive.pw")
                creator_url = f"https://{domain}/{service}/user/{user_id}"
                
                # ボタンクリック時に最上部のURLテキストエディタへ改行付きで追記するクロージャを接続
                def make_add_shortcut(url=creator_url):
                    current_urls = self.text_urls.toPlainText().strip()
                    if current_urls:
                        self.text_urls.setPlainText(current_urls + "\n" + url)
                    else:
                        self.text_urls.setPlainText(url)
                    self.log("SYS", f"検索からURLを追加しました: {url}" if CURRENT_LANG == "ja" else f"Added URL from search: {url}")

                btn_add.clicked.connect(lambda _, u=creator_url: make_add_shortcut(u))
                row_layout.addWidget(btn_add)
                
                # QListWidgetの行にカスタムUIを物理マージ
                list_item.setSizeHint(row_widget.sizeHint())
                self.search_list.addItem(list_item)
                self.search_list.setItemWidget(list_item, row_widget)

        self.lbl_search_status.setText(f"検索結果: {match_count} 件を表示中 (上限100件)" if CURRENT_LANG == "ja" else f"Search results: {match_count} items displayed (Max 100)")

    def add_url_to_list(self, url):
        # 検索結果やカードから一発でURLを追加する為のハブ関数
        current_text = self.text_urls.toPlainText()
        if url not in current_text:
            if current_text and not current_text.endswith('\n'):
                self.text_urls.setPlainText(current_text + "\n" + url)
            elif current_text:
                self.text_urls.setPlainText(current_text + url)
            else:
                self.text_urls.setPlainText(url)
            # 自動で一番下へスクロール
            scrollbar = self.text_urls.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def open_image_search_dialog(self):
        if getattr(self, "is_updating_cache", False):
            self.lbl_search_status.setText("現在キャッシュ更新中です... (Updating cache...)")
            return

        if not hasattr(self, "search_cache") or not self.search_cache:
            self.init_creator_cache(force=True)
            return

        # 解決：モーダル(exec)ではなく非モーダル(show)で開き、メインUIへのドロップ入力を解放する
        # スコープ生存のため、インスタンスを永続的なクラス変数として保持

        self.search_dlg = ImageSearchDialog(self)
        self.search_dlg.show()

    def open_migration_tool(self):
        if not HAS_WEBENGINE:
            QMessageBox.warning(self, L("dlg_warn"), "WebEngine is required for this feature. (pip install PyQt6-WebEngine)")
            return
        dlg = MigrationDialog(self)
        dlg.exec()

    def build_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.history_text = HistoryBrowser()
        self.history_text.setReadOnly(True)
        layout.addWidget(self.history_text)
        
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton(L("btn_refresh_history"))
        btn_refresh.clicked.connect(self.refresh_history)
        btn_open = QPushButton(L("btn_open_archive"))
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(user_data_path("archive.txt"))))
        
        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_open)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        return widget

    def refresh_history(self):
        if os.path.exists(user_data_path("archive.txt")):
            try:
                with open(user_data_path("archive.txt"), "r", encoding="utf-8") as f:
                    lines = f.readlines()
                html = "<div style='font-family: monospace; white-space: nowrap;'>"
                for line in lines:
                    line = line.strip()
                    if line.startswith("http"):
                        html += f'<a href="{line}" style="color: #4CAF50; text-decoration: none;">{line}</a><br>'
                    else:
                        html += f"{line}<br>"
                html += "</div>"
                self.history_text.setHtml(html)
                
                scrollbar = self.history_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            except Exception as e:
                self.history_text.setPlainText(L("msg_history_err") + str(e))
        else:
            self.history_text.setPlainText(L("msg_no_history"))

    def load_proxies_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, L("msg_load_proxy"), "", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                current = self.text_proxies.toPlainText().strip()
                if current:
                    self.text_proxies.setPlainText(current + "\n" + content)
                else:
                    self.text_proxies.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, L("dlg_err"), f"{L('msg_load_err')}:\n{e}")

    def build_option_tabs(self):
        tab_names = {
            "Tab_Input": L("tab_target"),
            "Tab_Content": L("tab_content"),
            "Tab_Filters": L("tab_filters"),
            "Tab_Patterns": L("tab_patterns"),
            "Tab_Proxy": "プロキシ設定" if CURRENT_LANG == "ja" else "Proxy Settings",
            "Tab_Network": L("tab_net")
        }
        
        ext_list = ["JPG", "JPEG", "PNG", "GIF", "WEBP", "MP4", "ZIP", "7Z", "RAR", "PDF", "TXT", "MP3"]

        for key, tab_title in tab_names.items():
            base_widget = QWidget()
            base_layout = QVBoxLayout(base_widget)
            base_layout.setContentsMargins(0, 0, 0, 0)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame) 
            
            content_widget = QWidget()
            layout = QVBoxLayout(content_widget)
            
            if key == "Tab_Proxy":
                proxy_btn_layout = QHBoxLayout()
                self.btn_load_proxies = QPushButton(L("btn_load_proxies"))
                self.btn_load_proxies.clicked.connect(self.load_proxies_from_file)
                proxy_btn_layout.addWidget(self.btn_load_proxies)
                proxy_btn_layout.addStretch()
                layout.addLayout(proxy_btn_layout)

                self.text_proxies = LocalizedTextEdit()
                self.text_proxies.setPlaceholderText(L("proxies_ph"))
                layout.addWidget(self.text_proxies)
                
                options_layout = QVBoxLayout()
                options_layout.setSpacing(5)
                
                proxy_options = [
                    ("--disable-socks-auto", {"ja":"SOCKSプロキシの自動判定を行わない","en":"Disable SOCKS Auto-detection"}, False, {"ja":"ポート1080入力時に自動でsocks5://を付与するお節介機能を無効化します。","en":"Disable prepending socks5:// for port 1080 automatically."}),
                    ("--use-socks5h", {"ja":"SOCKSプロキシでの名前解決(SOCKS5h)を優先する","en":"Use SOCKS5h for DNS Resolution"}, True, {"ja":"チェックを入れると、DNSの名前解決もプロキシ側で行い安全性を高めます(socks5h://を適用)。","en":"Resolve DNS on the proxy side to prevent DNS leaks (uses socks5h://)."}),
                    ("--proxy-report", {"ja":"プロキシエラーレポート出力","en":"Output Proxy Error Report"}, False, {"ja":"全タスク終了時、各プロキシのエラーレートを proxy_report.txt に出力します。","en":"Output proxy error rates to proxy_report.txt upon completion."})
                ]
                
                for arg, label_dict, default, tooltip_dict in proxy_options:
                    label_str = label_dict.get(CURRENT_LANG, label_dict["en"])
                    tooltip = tooltip_dict.get(CURRENT_LANG, tooltip_dict["en"])
                    cb = QCheckBox(label_str)
                    cb.setChecked(default)
                    cb.setToolTip(tooltip)
                    self.widgets_map[arg] = {"widget": cb, "type": "bool"}
                    options_layout.addWidget(cb)
                    
                layout.addLayout(options_layout)

            else:
                grid_layout = QVBoxLayout()
                row_layout = None

                for idx, item in enumerate(UI_DEFINITIONS.get(key, [])):
                    if idx % 2 == 0:
                        row_layout = QHBoxLayout()
                        grid_layout.addLayout(row_layout)

                    arg, ui_type, label_dict, default, tooltip_dict = item
                    label_str = label_dict.get(CURRENT_LANG, label_dict["en"])
                    tooltip = tooltip_dict.get(CURRENT_LANG, tooltip_dict["en"])

                    container = QWidget()
                    h_layout = QHBoxLayout(container)
                    h_layout.setContentsMargins(0, 0, 0, 0)

                    lbl = QLabel(label_str)
                    lbl.setToolTip(tooltip)

                    if ui_type == "bool":
                        cb = QCheckBox()
                        cb.setChecked(default)
                        cb.setToolTip(tooltip)
                        self.widgets_map[arg] = {"widget": cb, "type": "bool"}
                        h_layout.addWidget(cb)
                        h_layout.addWidget(lbl)
                        h_layout.addStretch()
                    elif ui_type == "text":
                        le = LocalizedLineEdit()
                        le.setText(default)
                        le.setToolTip(tooltip)
                        self.widgets_map[arg] = {"widget": le, "type": "text"}
                        h_layout.addWidget(lbl)
                        h_layout.addWidget(le)
                    elif ui_type == "int":
                        sb = QSpinBox()
                        sb.setRange(0, 999999)
                        sb.setValue(default)
                        sb.setToolTip(tooltip)
                        self.widgets_map[arg] = {"widget": sb, "type": "int"}
                        h_layout.addWidget(lbl)
                        h_layout.addWidget(sb)
                    elif ui_type == "file":
                        le = LocalizedLineEdit()
                        le.setText(default)
                        btn = QPushButton(L("btn_browse"))
                        btn.clicked.connect(lambda checked, l=le: self.browse_file(l))
                        self.widgets_map[arg] = {"widget": le, "type": "text"}
                        h_layout.addWidget(lbl)
                        h_layout.addWidget(le)
                        h_layout.addWidget(btn)
                        
                        if arg == "--cookies" and HAS_WEBENGINE:
                            btn_login = QPushButton("🌐 ブラウザログイン" if CURRENT_LANG == "ja" else "🌐 Browser Login")
                            btn_login.clicked.connect(lambda: CookieLoginDialog(self, is_auto_prompt=False).exec())
                            h_layout.addWidget(btn_login)

                    row_layout.addWidget(container)

                if len(UI_DEFINITIONS.get(key, [])) % 2 != 0:
                    row_layout.addWidget(QWidget())

                layout.addLayout(grid_layout)
                
                if key == "Tab_Filters":
                    ext_group = QGroupBox("簡易拡張子フィルター (許可する拡張子)" if CURRENT_LANG == "ja" else "Extension Filter")
                    ext_layout = QGridLayout()
                    self.ext_checkboxes = {}
                    for idx, ext in enumerate(ext_list):
                        r = idx // 4
                        c = idx % 4
                        cb = QCheckBox(ext)
                        cb.setChecked(True)
                        ext_layout.addWidget(cb, r, c)
                        self.ext_checkboxes[ext.lower()] = cb
                    ext_group.setLayout(ext_layout)
                    layout.addWidget(ext_group)

                if key == "Tab_Network":
                    group = QGroupBox("手動コマンドモード" if CURRENT_LANG == "ja" else "Manual Command Mode")
                    g_layout = QVBoxLayout()
                    self.cb_manual = QCheckBox("有効にする - ※高度な利用者向け" if CURRENT_LANG == "ja" else "Enable (Advanced Users Only)")
                    self.le_manual = QLineEdit()
                    self.le_manual.setPlaceholderText("--restrict-names --server 127.0.0.1")
                    self.le_manual.setEnabled(False)
                    self.cb_manual.toggled.connect(self.le_manual.setEnabled)
                    g_layout.addWidget(self.cb_manual)
                    g_layout.addWidget(self.le_manual)
                    group.setLayout(g_layout)
                    layout.addWidget(group)
                    
            layout.addStretch()
            scroll.setWidget(content_widget)
            base_layout.addWidget(scroll)
            self.tabs.addTab(base_widget, tab_title)

    def toggle_custom_dest(self, checked):
        self.edit_dest_dir.setEnabled(checked)
        self.btn_browse_dest.setEnabled(checked)

    def browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, L("btn_browse"))
        if path: line_edit.setText(path)

    def browse_folder(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, L("btn_browse"))
        if path: line_edit.setText(path)

    def log(self, task_id, text):
        if text.startswith("==="):
            self.console.append(text)
            return
        self.console.append(f"[{task_id}] {text}")
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def apply_theme(self, theme_text):
        if L("theme_dark") in theme_text:
            self.set_dark_theme()
            self.update_console_style(dark_theme_active=True)
        elif L("theme_light") in theme_text:
            self.set_light_theme()
            self.update_console_style(dark_theme_active=False)
        else:
            app = QApplication.instance()
            is_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
            if is_dark: self.set_dark_theme()
            else: self.set_light_theme()
            self.update_console_style(dark_theme_active=is_dark)

    def update_console_style(self, dark_theme_active):
        if dark_theme_active:
            self.console.setStyleSheet("""
                QTextEdit { background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; border: 1px solid #333; }
                QScrollBar:vertical { background: #2d2d2d; width: 14px; margin: 0px; }
                QScrollBar::handle:vertical { background: #6e6e6e; min-height: 20px; border-radius: 7px; }
                QScrollBar::handle:vertical:hover { background: #8e8e8e; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            """)
            self.task_scroll.setStyleSheet("QScrollArea { background-color: #2b2b2b; border: 1px solid #444; }")
            self.history_text.setStyleSheet("""
                QTextBrowser { background-color: #1e1e1e; color: #d4d4d4; font-family: monospace; border: 1px solid #333; }
            """)
        else:
            self.console.setStyleSheet("""
                QTextEdit { background-color: #ffffff; color: #1a1a1a; font-family: monospace; border: 1px solid #ccc; }
                QScrollBar:vertical { background: #f0f0f0; width: 14px; margin: 0px; }
                QScrollBar::handle:vertical { background: #a0a0a0; min-height: 20px; border-radius: 7px; }
                QScrollBar::handle:vertical:hover { background: #808080; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            """)
            self.task_scroll.setStyleSheet("QScrollArea { background-color: #f9f9f9; border: 1px solid #ccc; }")
            self.history_text.setStyleSheet("""
                QTextBrowser { background-color: #ffffff; color: #1a1a1a; font-family: monospace; border: 1px solid #ccc; }
            """)

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(62, 160, 240))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(62, 160, 240))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.instance().setPalette(palette)

    def set_light_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Button, QColor(225, 225, 225))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        QApplication.instance().setPalette(palette)

    def save_config(self):
        self.config["lang"] = CURRENT_LANG
        self.config["max_concurrency"] = self.spin_concurrency.value()
        self.config["custom_dest_enabled"] = self.cb_custom_dest.isChecked()
        self.config["dest_dir"] = self.edit_dest_dir.text()
        self.config["theme"] = self.combo_theme.currentText()
        self.config["proxies"] = self.text_proxies.toPlainText()
        self.config["image_retry_count"] = self.spin_image_retry.value()

        for arg, data in self.widgets_map.items():
            if data["type"] == "bool":
                self.config[arg] = data["widget"].isChecked()
            elif data["type"] == "text":
                self.config[arg] = data["widget"].text()
            elif data["type"] == "int":
                self.config[arg] = data["widget"].value()

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def load_config(self):
        global CURRENT_LANG
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                self.config.update(loaded)

            if "lang" in self.config: CURRENT_LANG = self.config["lang"]
            if "max_concurrency" in self.config: self.spin_concurrency.setValue(self.config["max_concurrency"])
            if "custom_dest_enabled" in self.config: self.cb_custom_dest.setChecked(self.config["custom_dest_enabled"])
            if "dest_dir" in self.config: self.edit_dest_dir.setText(self.config["dest_dir"])
            if "theme" in self.config: self.combo_theme.setCurrentText(self.config["theme"])
            if "proxies" in self.config: self.text_proxies.setPlainText(self.config["proxies"])
            if "image_retry_count" in self.config: self.spin_image_retry.setValue(self.config["image_retry_count"])

            for arg, data in self.widgets_map.items():
                if arg in self.config:
                    if data["type"] == "bool": data["widget"].setChecked(self.config[arg])
                    elif data["type"] == "text": data["widget"].setText(self.config[arg])
                    elif data["type"] == "int": data["widget"].setValue(self.config[arg])
        except Exception as e:
            self.log("SYS", f"設定ロードエラー: {e}")

    def build_base_args(self):
        args = []
        for arg, data in self.widgets_map.items():
            if arg in ["--dirname-pattern", "--cookies", "--fetch-previews", "--preview-concurrency", "--disable-socks-auto", "--use-socks5h", "--proxy-report", "--auto-update", "--desktop-notify"]: continue
            if arg in ["--kemono-fav-posts", "--coomer-fav-posts", "--pawchive-fav-posts", "--kemono-fav-users", "--coomer-fav-users", "--pawchive-fav-users"]: continue

            if data["type"] == "bool":
                if data["widget"].isChecked(): args.append(arg)
            elif data["type"] == "text":
                val = data["widget"].text().strip()
                if val: args.extend([arg, val])
            elif data["type"] == "int":
                args.extend([arg, str(data["widget"].value())])

        cookie_file = self.widgets_map["--cookies"]["widget"].text().strip()
        if cookie_file:
            args.extend(["--cookies", cookie_file])

        if hasattr(self, 'ext_checkboxes'):
            all_checked = all(cb.isChecked() for cb in self.ext_checkboxes.values())
            if not all_checked:
                allowed = [ext for ext, cb in self.ext_checkboxes.items() if cb.isChecked()]
                if allowed:
                    args.extend(["--only-filetypes", ",".join(allowed)])
                else:
                    args.extend(["--only-filetypes", "none"])

        if hasattr(self, 'cb_manual') and self.cb_manual.isChecked():
            cmd = self.le_manual.text().strip()
            if cmd:
                try:
                    args.extend(shlex.split(cmd))
                except Exception as e:
                    self.log("SYS", f"Manual Command Parse Error: {e}")

        return args

    def resolve_kemono_dl_path(self):
        # 1) 前回このダイアログで指定して保存済みのパスがあれば優先
        saved_path = self.config.get("kemono_dl_path", "")
        if saved_path and os.path.exists(saved_path):
            return saved_path

        # 2) デフォルトの配置場所（GUI本体と同じフォルダ）
        default_path = app_path("kemono-dl.py")
        if os.path.exists(default_path):
            return default_path

        # 3) どちらにも無い場合はユーザーに手動で場所を指定してもらう
        QMessageBox.warning(self, L("dlg_warn"), L("msg_kemono_dl_missing"))
        chosen, _ = QFileDialog.getOpenFileName(
            self, L("msg_kemono_dl_missing_title"), APP_DIR, "Python Files (*.py);;All Files (*)"
        )
        if not chosen:
            return None

        chosen = os.path.abspath(chosen)
        src_dir = os.path.join(os.path.dirname(chosen), "src")
        if not os.path.isdir(src_dir):
            reply = QMessageBox.question(
                self, L("dlg_warn"), L("msg_kemono_dl_src_missing"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return None

        self.config["kemono_dl_path"] = chosen
        self.save_config()
        return chosen

    def check_cookie_and_start(self):
        kemono_dl_path = self.resolve_kemono_dl_path()
        if not kemono_dl_path:
            return
        self.kemono_dl_path = kemono_dl_path

        urls_text = self.text_urls.toPlainText()
        
        needs_cookie = ("kemono.su" in urls_text or "coomer.su" in urls_text or "kemono.cr" in urls_text or "coomer.st" in urls_text or
                        self.widgets_map["--kemono-fav-posts"]["widget"].isChecked() or
                        self.widgets_map["--coomer-fav-posts"]["widget"].isChecked() or
                        self.widgets_map["--kemono-fav-users"]["widget"].text().strip() != "" or
                        self.widgets_map["--coomer-fav-users"]["widget"].text().strip() != "")

        cookie_file = self.widgets_map["--cookies"]["widget"].text().strip()

        if needs_cookie and not cookie_file and not self.config.get("skip_cookie_warning", False):
            if not HAS_WEBENGINE:
                reply = QMessageBox.question(self, L("dlg_cookie"), L("msg_cookie_req"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No: return
                self.start_download_actual()
            else:
                reply = QMessageBox.question(self, L("dlg_cookie"), L("msg_cookie_miss"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    dlg = CookieLoginDialog(self, is_auto_prompt=True)
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        self.start_download_actual()
                else:
                    self.start_download_actual()
        else:
            self.start_download_actual()

    def start_download_actual(self):
        self.save_config()
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.is_running = True
        self.is_paused = False
        self.log("SYS", L("msg_start"))
        
        for tw in self.task_widgets.values():
            self.task_layout.removeWidget(tw)
            tw.deleteLater()
        self.task_widgets.clear()
        
        proxies_raw = self.text_proxies.toPlainText().splitlines()
        
        disable_auto = False
        use_socks5h = True
        if "--disable-socks-auto" in self.widgets_map:
            disable_auto = self.widgets_map["--disable-socks-auto"]["widget"].isChecked()
        if "--use-socks5h" in self.widgets_map:
            use_socks5h = self.widgets_map["--use-socks5h"]["widget"].isChecked()
            
        self.proxy_pool = [normalize_proxy(p, disable_auto, use_socks5h) for p in proxies_raw if p.strip()]
        self.dead_proxies = set()
        self.active_proxies = set()

        self.proxy_total_counts = {p: 0 for p in self.proxy_pool}
        self.proxy_error_counts = {p: 0 for p in self.proxy_pool}
        
        new_queue = []
        self.active_api_fetches = 0
        
        urls = [u.strip() for u in self.text_urls.toPlainText().splitlines() if u.strip()]
        for u in urls:
            m_post = re.search(r'https://([^/]+)/([^/]+)/user/([^/]+)/post/([^/]+)', u)
            m_creator = re.search(r'https://([^/]+)/([^/]+)/user/([^/]+)/?$', u)
            
            if m_post:
                task_id = hashlib.md5(u.encode('utf-8')).hexdigest()[:8]
                new_queue.append({"id": task_id, "type": "url", "target": u, "status": "pending"})
            elif m_creator:
                domain, service, user_id = m_creator.groups()
                ext_name = fetch_creator_name(u)
                self.active_api_fetches += 1
                worker = CreatorFetchWorker(u, domain, service, user_id, ext_name,
                                             max_retry=self.widgets_map["--retry"]["widget"].value())
                worker.signals.log.connect(self.log)
                worker.signals.finished.connect(self.on_creator_fetched)
                worker.signals.waf_warning.connect(self.check_waf_and_offer_browser)
                self.api_pool.start(worker)
            else:
                task_id = hashlib.md5(u.encode('utf-8')).hexdigest()[:8]
                new_queue.append({"id": task_id, "type": "url", "target": u, "status": "pending"})
            
        fav_args = []
        if self.widgets_map["--kemono-fav-posts"]["widget"].isChecked(): fav_args.append("--kemono-fav-posts")
        if self.widgets_map["--coomer-fav-posts"]["widget"].isChecked(): fav_args.append("--coomer-fav-posts")
        if self.widgets_map["--pawchive-fav-posts"]["widget"].isChecked(): fav_args.append("--pawchive-fav-posts")
        k_users = self.widgets_map["--kemono-fav-users"]["widget"].text().strip()
        if k_users: fav_args.extend(["--kemono-fav-users", k_users])
        c_users = self.widgets_map["--coomer-fav-users"]["widget"].text().strip()
        if c_users: fav_args.extend(["--coomer-fav-users", c_users])
        p_users = self.widgets_map["--pawchive-fav-users"]["widget"].text().strip()
        if p_users: fav_args.extend(["--pawchive-fav-users", p_users])
        
        if fav_args:
            fav_id = hashlib.md5(str(fav_args).encode('utf-8')).hexdigest()[:8]
            new_queue.append({"id": fav_id, "type": "favorites", "args": fav_args, "status": "pending"})
            
        if not new_queue and self.active_api_fetches == 0:
            QMessageBox.warning(self, L("dlg_warn"), L("msg_no_url"))
            self.stop_all()
            return
            
        self.task_queue = new_queue
        self.base_cli_args = self.build_base_args()
        
        archive_path = user_data_path("archive.txt")
        self.base_cli_args.extend(["--archive", archive_path])
        
        self.queue_timer.start(1000)

    def on_creator_fetched(self, tasks):
        self.active_api_fetches -= 1
        if tasks:
            group_id = tasks[0]["group_id"]
            self.group_stats[group_id] = {"total": len(tasks), "completed_ids": set()}
        self.task_queue.extend(tasks)

    def update_task_progress(self, task_id, current, total, text):
        task = next((t for t in self.task_queue if t["id"] == task_id), None)
        if not task: return
        
        group_id = task.get("group_id")
        ui_task_id = task.get("group_id", task_id)
        
        if ui_task_id in self.task_widgets:
            tw = self.task_widgets[ui_task_id]
            
            if group_id and group_id in self.group_stats:
                c = len(self.group_stats[group_id]["completed_ids"])
                t = self.group_stats[group_id]["total"]
                
                if CURRENT_LANG == "ja":
                    tw.lbl_status.setText(f"投稿処理中: {c}/{t} 件完了 | {text}")
                else:
                    tw.lbl_status.setText(f"Processing: {c}/{t} Completed | {text}")
            else:
                tw.lbl_status.setText(text)

    def manage_queue(self):
        if self.is_paused or not self.is_running: return

        pending_tasks = [t for t in self.task_queue if t["status"] in ("pending", "error")]

        if not pending_tasks and len(self.active_workers) == 0 and self.preview_pool.activeThreadCount() == 0 and self.active_api_fetches == 0:
            self.queue_timer.stop()
            
            is_custom_dest = self.cb_custom_dest.isChecked()
            final_dest_dir = self.edit_dest_dir.text().strip()
            staging_dir = user_data_path("_temp_staging_batch")
            
            if is_custom_dest and os.path.exists(staging_dir):
                self.log("SYS", L("msg_merge_start"))
                
                def do_merge():
                    try:
                        failed = self._smart_merge_move(staging_dir, final_dest_dir)
                        if failed:
                            # 失敗したファイルがstaging_dir側に残ったままなので、
                            # rmtreeで巻き添え削除しないようここで打ち切る。
                            names = ", ".join(os.path.basename(p) for p, _ in failed[:5])
                            more = f" 他{len(failed)-5}件" if len(failed) > 5 else ""
                            self.merge_log_signal.emit("SYS",
                                (f"マージは完了しましたが、{len(failed)}件のファイルを移動できませんでした({names}{more})。"
                                 f"該当ファイルは {staging_dir} に残っています。") if CURRENT_LANG == "ja" else
                                (f"Merge finished, but {len(failed)} file(s) could not be moved ({names}{more}). "
                                 f"They remain in {staging_dir}."))
                        else:
                            shutil.rmtree(staging_dir)
                            self.merge_log_signal.emit("SYS", L("msg_merge_done"))
                    except Exception as e:
                        self.merge_log_signal.emit("SYS", f"{L('msg_merge_err')} {e}")
                    finally:
                        self.merge_finished_signal.emit()
                
                threading.Thread(target=do_merge, daemon=True).start()
            else:
                self.finish_all_tasks()
            return

        max_concurrency = self.spin_concurrency.value()
        
        fetch_previews = False
        if "--fetch-previews" in self.widgets_map:
            fetch_previews = self.widgets_map["--fetch-previews"]["widget"].isChecked()

        for task in pending_tasks:
            if len(self.active_workers) >= max_concurrency: break

            assigned_proxy = None
            if self.proxy_pool:
                available = [p for p in self.proxy_pool if p not in self.dead_proxies and p not in self.active_proxies]
                if not available: break
                assigned_proxy = random.choice(available)
                self.active_proxies.add(assigned_proxy)
                self.proxy_total_counts[assigned_proxy] = self.proxy_total_counts.get(assigned_proxy, 0) + 1

            task["status"] = "running"
            task_id = task["id"]

            ui_task_id = task.get("group_id", task_id)
            title = task.get("group_title", task["target"] if task["type"] == "url" else L("msg_fav_task"))
            
            if ui_task_id not in self.task_widgets:
                tw = TaskWidget(ui_task_id, title)
                tw.preview_requested.connect(self.show_task_preview)
                self.task_layout.addWidget(tw)
                self.task_widgets[ui_task_id] = tw

            dirname_pattern = self.widgets_map["--dirname-pattern"]["widget"].text().strip()
            is_custom_dest = self.cb_custom_dest.isChecked()
            final_dest_dir = self.edit_dest_dir.text().strip()

            worker = WorkerProcess(
                task, assigned_proxy, self.base_cli_args,
                is_custom_dest, final_dest_dir, dirname_pattern, fetch_previews,
                kemono_dl_path=getattr(self, 'kemono_dl_path', None)
            )
            worker.log_signal.connect(self.log)
            worker.progress_signal.connect(self.update_task_progress)
            worker.finished_signal.connect(self.on_worker_finished)
            worker.preview_signal.connect(self.on_preview_needed)

            self.active_workers[task_id] = worker
            worker.start()

    def _smart_merge_move(self, src_dir, dst_dir, failed_items=None):
        if failed_items is None:
            failed_items = []
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
            
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(dst_dir, item)
            
            if os.path.isdir(src_path):
                m = re.search(r'\[([^\]]+)\]$', item)
                if m:
                    user_id_str = f"[{m.group(1)}]"
                    if os.path.exists(dst_dir):
                        for existing_item in os.listdir(dst_dir):
                            if os.path.isdir(os.path.join(dst_dir, existing_item)) and existing_item.endswith(user_id_str):
                                dst_path = os.path.join(dst_dir, existing_item)
                                break
                self._smart_merge_move(src_path, dst_path, failed_items)
            else:
                try:
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                    shutil.move(src_path, dst_path)
                except Exception as e:
                    # 1ファイルの失敗(ロック中など)でバッチ全体を中断させず、
                    # 失敗した事実は握りつぶさず記録して次のファイルへ進む。
                    # (呼び出し元はfailed_itemsが空でない限りstagingを削除してはいけない)
                    failed_items.append((src_path, str(e)))
        return failed_items

    def finish_all_tasks(self):
        from PyQt6.QtWidgets import QSystemTrayIcon
        self.log("SYS", L("msg_done"))
        self.stop_all()
        self.refresh_history()
        
        if self.widgets_map.get("--desktop-notify", {}).get("widget", QCheckBox()).isChecked():
            if QSystemTrayIcon.isSystemTrayAvailable():
                if not hasattr(self, "tray_icon") or not self.tray_icon:
                    self.tray_icon = QSystemTrayIcon(self)
                    icon_pixmap = QPixmap("kemoffu_logo.png")
                    if icon_pixmap.isNull():
                        icon_pixmap = QPixmap(64, 64)
                        icon_pixmap.fill(QColor("#4CAF50"))
                    self.tray_icon.setIcon(QIcon(icon_pixmap))
                    self.tray_icon.show()
                self.tray_icon.showMessage(
                    "Kemoffu Downloader", 
                    "すべてのタスクが完了しました！" if CURRENT_LANG == "ja" else "All tasks completed!",
                    QSystemTrayIcon.MessageIcon.Information, 
                    5000
                )

    def show_task_preview(self, ui_task_id):
        post_id = None
        if ui_task_id in self.group_stats:
            completed = self.group_stats[ui_task_id]["completed_ids"]
            if completed:
                sample_task_id = list(completed)[-1]
                task = next((t for t in self.task_queue if t["id"] == sample_task_id), None)
                if task:
                    m = re.search(r'/post/([^/]+)', task.get("target", ""))
                    post_id = m.group(1) if m else None
        else:
            task = next((t for t in self.task_queue if t["id"] == ui_task_id), None)
            if task:
                m = re.search(r'/post/([^/]+)', task.get("target", ""))
                post_id = m.group(1) if m else None
        
        base_dir = user_data_path("_temp_staging_batch") if self.cb_custom_dest.isChecked() else self.edit_dest_dir.text().strip()
        if not os.path.exists(base_dir): base_dir = APP_DIR
        
        search_token = f"[{post_id}]" if post_id else None
        if not search_token and ui_task_id in self.group_stats:
             task = next((t for t in self.task_queue if t.get("group_id") == ui_task_id), None)
             m = re.search(r'/user/([^/]+)', task.get("target", ""))
             if m: search_token = f"[{m.group(1)}]"
             
        if not search_token:
            QMessageBox.information(self, "Preview", "プレビュー対象を特定できません。" if CURRENT_LANG == "ja" else "Target unidentified.")
            return

        candidates = []
        for root, dirs, files in os.walk(base_dir):
            for d in dirs:
                if search_token in d:
                    candidates.append(os.path.join(root, d))
                    
        if not candidates:
            QMessageBox.information(self, "Preview", "まだファイルが保存されていないか、見つかりません。" if CURRENT_LANG == "ja" else "Files not found.")
            return
            
        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        target_folder = candidates[0]

        media_files = []
        for root, dirs, files in os.walk(target_folder):
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    media_files.append(os.path.join(root, f))
                    if len(media_files) >= 50: break
            if len(media_files) >= 50: break

        if not media_files:
            QMessageBox.information(self, "Preview", "対象のフォルダに画像が見つかりません。" if CURRENT_LANG == "ja" else "No images found.")
            return

        dlg = ImagePreviewDialog(media_files, self)
        dlg.exec()

    def on_preview_needed(self, task_id, domain, service, username, user_id, post_id, target_dir, dirname_pattern):
        worker_proc = self.active_workers.get(task_id)
        if worker_proc:
            worker_proc.active_preview_tasks += 1

        worker = PreviewDownloadWorker(task_id, domain, service, username, user_id, post_id, target_dir, dirname_pattern)
        worker.signals.log.connect(self.log)
        worker.signals.finished.connect(self.on_preview_finished)
        self.preview_pool.start(worker)

    def on_preview_finished(self, task_id):
        worker_proc = self.active_workers.get(task_id)
        if worker_proc:
            worker_proc.active_preview_tasks -= 1
            worker_proc.check_and_finalize()

    def check_waf_and_offer_browser(self, domain, error_text):
        # 検索キャッシュ取得・クリエイター情報の事前取得など、「情報取得APIそのものが
        # 動作しない」場面専用。ダウンロード中(WorkerProcess)には意図的に組み込まない
        # (ダウンロードのたびに手動でTurnstileを解かされるのは体験として不満が残るため)。
        if not domain or "403" not in error_text:
            return
        # 同一ドメインについて短時間に何度もダイアログを出さないようクールダウンを設ける
        now = time.time()
        cooldown_key = f"_waf_dialog_shown_{domain}"
        if getattr(self, cooldown_key, 0) > now - 60:
            return
        setattr(self, cooldown_key, now)

        if not HAS_WEBENGINE:
            self.log("SYS",
                f"{domain} への情報取得APIが403で失敗しました。サイト側のアクセス制限(WAF/Turnstile)の可能性があります。"
                "(ブラウザでの手動確認にはPyQt6-WebEngineが必要です: pip install PyQt6-WebEngine)"
                if CURRENT_LANG == "ja" else
                f"API request to {domain} failed with 403. This may be a site-wide WAF/Turnstile block. "
                "(PyQt6-WebEngine is required to open a browser: pip install PyQt6-WebEngine)")
            return

        dlg = WafCheckDialog(domain, self)
        dlg.show()

    def on_worker_finished(self, task_id, task, success, skipped_never_imported):
        worker = self.active_workers.pop(task_id, None)
        if worker and worker.proxy in self.active_proxies:
            self.active_proxies.remove(worker.proxy)
            if worker.proxy_dead:
                self.dead_proxies.add(worker.proxy)
                self.proxy_error_counts[worker.proxy] = self.proxy_error_counts.get(worker.proxy, 0) + 1

        group_id = task.get("group_id")
        ui_task_id = group_id if group_id else task_id

        if not success and skipped_never_imported and not task.get("force_unlisted"):
            def auto_retry():
                name = None
                if task.get("type") == "url":
                    name = fetch_creator_name(task["target"])

                for q in self.task_queue:
                    if q["id"] == task_id:
                        if name: q["extracted_name"] = name
                        q["force_unlisted"] = True
                        q["status"] = "pending"
                        break

                msg = L("msg_retry_auto_name").replace("{name}", name) if name else L("msg_retry_auto")
                QTimer.singleShot(0, lambda: self.log("SYS", f"[{task_id}] {msg}"))
                if ui_task_id in self.task_widgets:
                    QTimer.singleShot(0, lambda: self.task_widgets[ui_task_id].update_progress(0, 0, L("msg_retry_prep")))

            threading.Thread(target=auto_retry, daemon=True).start()
            return

        for q in self.task_queue:
            if q["id"] == task_id:
                q["status"] = "completed" if success else "error"
                break

        group_id = task.get("group_id")
        ui_task_id = task.get("group_id", task_id)

        if group_id and group_id in self.group_stats:
            if success:
                self.group_stats[group_id]["completed_ids"].add(task_id)
                
            c = len(self.group_stats[group_id]["completed_ids"])
            t = self.group_stats[group_id]["total"]
            
            if ui_task_id in self.task_widgets:
                tw = self.task_widgets[ui_task_id]
                
                progress_percent = int((c / t) * 100) if t > 0 else 0
                tw.progress_bar.setValue(progress_percent)
                
                if CURRENT_LANG == "ja":
                    tw.lbl_status.setText(f"投稿処理中: {c}/{t} 件完了")
                else:
                    tw.lbl_status.setText(f"{c}/{t} Posts Completed")
                    
                if c >= t:
                    tw.set_finished(True)

    def toggle_pause(self):
        if not self.is_running: return

        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.setText(L("btn_resume"))
            self.log("SYS", L("msg_suspend"))
            for worker in list(self.active_workers.values()): worker.suspend()
        else:
            self.btn_pause.setText(L("btn_pause"))
            self.log("SYS", L("msg_resume"))
            for worker in list(self.active_workers.values()): worker.resume()

    def write_proxy_report(self):
        if "--proxy-report" not in self.widgets_map or not self.widgets_map["--proxy-report"]["widget"].isChecked():
            return
            
        if not hasattr(self, 'proxy_total_counts') or not self.proxy_total_counts:
            return

        report_data = []
        for proxy, total in self.proxy_total_counts.items():
            if total == 0: continue
            errors = self.proxy_error_counts.get(proxy, 0)
            rate = (errors / total) * 100
            report_data.append({"proxy": proxy, "total": total, "errors": errors, "rate": rate})
            
        if not report_data:
            return

        report_data.sort(key=lambda x: (-x["rate"], x["proxy"]))
        
        lines = ["=== PROXY ERROR RATE REPORT ==="] # ここはめんどくさかったので英語のみでの出力。意味理解できるのでよいでしょう
        for d in report_data:
            lines.append(f"{d['proxy']} ERROR RATE : {d['rate']:.1f}% ({d['errors']}/{d['total']})")
            
        try:
            with open(user_data_path("proxy_report.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.log("SYS", "プロキシエラーレポートを proxy_report.txt に出力しました。" if CURRENT_LANG == "ja" else "Saved proxy error report to proxy_report.txt")
        except Exception as e:
            self.log("SYS", f"レポート出力エラー: {e}" if CURRENT_LANG == "ja" else f"Report output error: {e}")

    def stop_all(self):
        self.queue_timer.stop()
        self.is_running = False
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

        self.log("SYS", L("msg_stop"))
        for worker in list(self.active_workers.values()):
            if self.is_paused: worker.resume()
            worker.stop()

        self.btn_pause.setText(L("btn_pause"))
        self.is_paused = False
        self.write_proxy_report()

if __name__ == '__main__':
    from PyQt6.QtGui import QPixmap, QColor
    from PyQt6.QtWidgets import QSplashScreen
    from PyQt6.QtCore import Qt
    
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    
    splash_image_path = "kemoffu_logo.png"
    original_pixmap = QPixmap(splash_image_path)
    
    if not original_pixmap.isNull():
        pixmap = original_pixmap.scaled(700, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    else:
        pixmap = QPixmap(600, 350)
        pixmap.fill(QColor("#2b2b2b"))
        
    # スプラッシュ入れて体感起動のUX速くしてみたり

    splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    
    splash.showMessage(
        "ツールを起動しています..." if get_system_lang() == "ja" else "Loading modules...", 
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, 
        Qt.GlobalColor.white
    )
    app.processEvents()
    
    gui = KemonoDLGUI()
    
    splash.finish(gui)
    gui.show()
    
    sys.exit(app.exec())