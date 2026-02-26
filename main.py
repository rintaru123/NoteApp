import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QDesktopWidget,
                             QMessageBox, QFileDialog, QAction, QSystemTrayIcon,
                             QMenu, QCheckBox, QTextEdit, QFrame)
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QColor, QPainter, QPixmap

# --- Константы ---
TEXT_FILE = "notes.txt"
SETTINGS_FILE = "settings.ini"

# --- Функция для поиска ресурсов внутри EXE (PyInstaller) ---
def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller """
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Стили (Modern Palette) ---
STYLES = {
    "light": {
        "bg": "#FFFFFF",
        "text": "#333333",
        "input_bg": "#F0F2F5",
        "input_border": "#E1E4E8",
        "btn_bg": "#0078D4",
        "btn_hover": "#005A9E",
        "btn_text": "#FFFFFF",
    },
    "dark": {
        "bg": "#202124",
        "text": "#E8EAED",
        "input_bg": "#303134",
        "input_border": "#5F6368",
        "btn_bg": "#8AB4F8",
        "btn_hover": "#669DF6",
        "btn_text": "#202124",
    }
}

class Localization:
    def __init__(self, lang="ru"):
        self.lang = lang
        self.translations = {
            "ru": {
                "title": "NoteApp",
                "add": "@",
                "edit_mode": "Редактирование",
                "enter_note": "Заметка...",
                "show": "Показать",
                "quit": "Выход",
                "settings": "Настройки",
                "theme_light": "Светлая",
                "theme_dark": "Темная",
                "clear_file": "Очистить все",
                "confirm_clear": "Удалить все записи?",
                "export": "Экспорт",
                "language": "Язык (Language)",
                "about": "О программе"
            },
            "en": {
                "title": "NoteApp",
                "add": "@",
                "edit_mode": "Edit mode",
                "enter_note": "Note...",
                "show": "Show",
                "quit": "Quit",
                "settings": "Settings",
                "theme_light": "Light",
                "theme_dark": "Dark",
                "clear_file": "Clear all",
                "confirm_clear": "Delete all notes?",
                "export": "Export",
                "language": "Language",
                "about": "About"
            }
        }

    def get(self, key):
        return self.translations[self.lang].get(key, key)

    def set_language(self, new_lang):
        self.lang = new_lang

class SmallForm(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(SETTINGS_FILE, QSettings.IniFormat)
        self.lang = self.settings.value("language", "ru")
        self.theme_name = self.settings.value("theme", "light")
        self.loc = Localization(self.lang)
        self.large_form = None 
        self.old_pos = None 

        self.initUI()
        self.setup_tray()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 50)
        self.setWindowIcon(QIcon(resource_path("icon.png")))
        
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)
        
        layout = QHBoxLayout(self.central_widget)
        layout.setContentsMargins(8, 5, 8, 5) 
        layout.setSpacing(8)

        self.note_input = QLineEdit()
        self.note_input.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.note_input)

        self.add_button = QPushButton(self.loc.get("add"))
        self.add_button.setFixedSize(28, 28) 
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.save_note)
        layout.addWidget(self.add_button)

        self.expand_button = QPushButton("⤢")
        self.expand_button.setFixedSize(28, 28)
        self.expand_button.setCursor(Qt.PointingHandCursor)
        self.expand_button.clicked.connect(self.open_large_form)
        layout.addWidget(self.expand_button)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet("background: transparent; color: #999; font-weight: bold; border: none; font-size: 14px;")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        self.close_btn.setParent(self.central_widget)
        self.close_btn.move(360, 3) 

        self.apply_styles()
        self.load_position()
        self.update_ui_text()

    def apply_styles(self):
        s = STYLES[self.theme_name]
        self.central_widget.setStyleSheet(f"""
            #CentralWidget {{
                background-color: {s['bg']};
                border-radius: 10px;
                border: 1px solid {s['input_border']};
            }}
        """)
        self.note_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background-color: {s['input_bg']};
                border-radius: 6px;
                padding: 4px 8px;
                color: {s['text']};
            }}
        """)
        self.add_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {s['btn_bg']};
                color: {s['btn_text']};
                border-radius: 14px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{ background-color: {s['btn_hover']}; }}
        """)
        self.expand_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {s['text']};
                border: 1px solid {s['input_border']};
                border-radius: 14px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {s['input_bg']}; }}
        """)

    def update_ui_text(self):
        self.note_input.setPlaceholderText(self.loc.get("enter_note"))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.save_note()
        elif event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    def save_note(self):
        note_text = self.note_input.text().strip()
        if note_text:
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            new_note = f"[{current_time}] {note_text}"
            try:
                with open(TEXT_FILE, "a", encoding="utf-8") as f:
                    f.write(new_note + "\n")
                self.note_input.clear()
                self.flash_color()
            except Exception as e:
                print(e)

    def flash_color(self):
        original_style = self.central_widget.styleSheet()
        self.central_widget.setStyleSheet(original_style.replace(STYLES[self.theme_name]['input_border'], "#4CAF50").replace("1px", "2px"))
        QTimer.singleShot(400, lambda: self.central_widget.setStyleSheet(original_style))

    def open_large_form(self):
        if not self.large_form:
            self.large_form = LargeForm(self)
        self.large_form.load_file()
        self.large_form.show()
        self.hide()

    def load_position(self):
        pos = self.settings.value("pos_small", None)
        if pos:
            self.move(pos)
        else:
            ag = QDesktopWidget().availableGeometry()
            self.move(ag.width() - 400, ag.height() - 150)

    def closeEvent(self, event):
        self.settings.setValue("pos_small", self.pos())
        event.accept()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Используем resource_path для иконки
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
             self.tray_icon.setIcon(QIcon(icon_path))
        else:
             pix = QPixmap(16, 16)
             pix.fill(Qt.transparent)
             p = QPainter(pix)
             p.setBrush(QColor(STYLES['light']['btn_bg']))
             p.drawEllipse(0, 0, 16, 16)
             p.end()
             self.tray_icon.setIcon(QIcon(pix))

        tray_menu = QMenu()
        tray_menu.addAction(self.loc.get("show"), self.showNormal)
        
        # О программе в трее
        about_action = QAction(self.loc.get("about"), self)
        about_action.triggered.connect(self.show_about_dialog)
        tray_menu.addAction(about_action)

        tray_menu.addSeparator()
        tray_menu.addAction(self.loc.get("quit"), QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.Trigger else None)

    def show_about_dialog(self):
        if not self.large_form:
             self.large_form = LargeForm(self)
        self.large_form.show_about()


class LargeForm(QMainWindow):
    def __init__(self, small_form):
        super().__init__()
        self.small_form = small_form
        self.loc = self.small_form.loc
        self.theme_name = self.small_form.theme_name
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.loc.get("title"))
        self.setWindowIcon(QIcon(resource_path("icon.png")))
        self.resize(600, 500)
        
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.create_menu()

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.text_edit)

        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText(self.loc.get("enter_note"))
        bottom_layout.addWidget(self.note_input)

        self.add_btn = QPushButton(self.loc.get("add"))
        self.add_btn.setFixedSize(28, 28)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_note)
        bottom_layout.addWidget(self.add_btn)

        self.edit_mode_chk = QCheckBox(self.loc.get("edit_mode"))
        self.edit_mode_chk.stateChanged.connect(self.toggle_edit)
        bottom_layout.addWidget(self.edit_mode_chk)

        layout.addWidget(bottom_widget)

        self.apply_styles()
        self.load_file()

    def create_menu(self):
        mb = self.menuBar()
        mb.clear()
        
        settings = mb.addMenu(self.loc.get("settings"))
        
        theme_menu = QMenu(self.loc.get("theme_light") if self.theme_name == 'dark' else self.loc.get("theme_dark"), self)
        act_light = QAction(self.loc.get("theme_light"), self)
        act_light.triggered.connect(lambda: self.change_theme("light"))
        act_dark = QAction(self.loc.get("theme_dark"), self)
        act_dark.triggered.connect(lambda: self.change_theme("dark"))
        settings.addAction(act_light)
        settings.addAction(act_dark)
        
        settings.addSeparator()
        
        lang_menu = QMenu(self.loc.get("language"), self)
        act_ru = QAction("Русский", self)
        act_ru.triggered.connect(lambda: self.change_lang("ru"))
        act_en = QAction("English", self)
        act_en.triggered.connect(lambda: self.change_lang("en"))
        settings.addMenu(lang_menu)
        lang_menu.addAction(act_ru)
        lang_menu.addAction(act_en)

        settings.addSeparator()
        act_clear = QAction(self.loc.get("clear_file"), self)
        act_clear.triggered.connect(self.clear_file)
        settings.addAction(act_clear)
        act_export = QAction(self.loc.get("export"), self)
        act_export.triggered.connect(self.export_file)
        settings.addAction(act_export)

        # Меню Справка
        help_menu = mb.addMenu("?")
        act_about = QAction(self.loc.get("about"), self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

    def show_about(self):
        msg = QMessageBox(self)
        msg.setWindowTitle(self.loc.get("about"))
        msg.setTextFormat(Qt.RichText)
        # Разрешаем кликать по ссылкам
        msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
        
        # HTML контент
        text = f"""
        <center>
            <h3 style='margin-bottom:0px;'>{self.loc.get("title")}</h3>
        </center>
        <p><b>Идея и улучшения:</b> <a href='https://github.com/rintaru123'>Rintaru123</a></p>
        <p><b>Разработка:</b> Gemini-3-pro</p>
        <hr>
        <p style='font-size:10px; color: #777;'>
            Icons by Bootstrap Authors, licensed under MIT License.<br>
            Source: <a href='https://icon-icons.com/pack/bootstrap/2645'>icon-icons.com</a>
        </p>
        """
        msg.setText(text)
        msg.exec_()

    def apply_styles(self):
        s = STYLES[self.theme_name]
        self.setStyleSheet(f"background-color: {s['bg']}; color: {s['text']};")
        self.text_edit.setStyleSheet(f"QTextEdit {{ background-color: {s['bg']}; color: {s['text']}; border: none; padding: 10px; }}")
        self.note_input.setStyleSheet(f"QLineEdit {{ border: 1px solid {s['input_border']}; border-radius: 5px; padding: 8px; background-color: {s['input_bg']}; color: {s['text']}; }}")
        self.add_btn.setStyleSheet(f"QPushButton {{ background-color: {s['btn_bg']}; color: {s['btn_text']}; border-radius: 14px; font-size: 16px; font-weight: bold; border: none; }} QPushButton:hover {{ background-color: {s['btn_hover']}; }}")

    def load_file(self):
        if os.path.exists(TEXT_FILE):
            with open(TEXT_FILE, "r", encoding="utf-8") as f:
                self.text_edit.setPlainText(f.read())
            self.text_edit.moveCursor(QTextCursor.End)

    def add_note(self):
        text = self.note_input.text().strip()
        if not text: return
        
        if self.edit_mode_chk.isChecked():
            self.save_full_text() 
        
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        new_entry = f"[{current_time}] {text}"
        
        with open(TEXT_FILE, "a", encoding="utf-8") as f:
            f.write(new_entry + "\n")
            
        self.note_input.clear()
        self.load_file()

    def toggle_edit(self, state):
        is_editing = (state == Qt.Checked)
        self.text_edit.setReadOnly(not is_editing)
        self.text_edit.setStyleSheet(f"border: {('1px solid #4CAF50' if is_editing else 'none')};")
        if not is_editing:
            self.save_full_text()

    def save_full_text(self):
        content = self.text_edit.toPlainText()
        with open(TEXT_FILE, "w", encoding="utf-8") as f:
            f.write(content)

    def clear_file(self):
        reply = QMessageBox.question(self, "Confirm", self.loc.get("confirm_clear"), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            open(TEXT_FILE, "w").close()
            self.text_edit.clear()

    def export_file(self):
        fn, _ = QFileDialog.getSaveFileName(self, self.loc.get("export"), "notes_export.txt", "Text Files (*.txt)")
        if fn:
            try:
                with open(fn, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
            except Exception as e:
                QMessageBox.critical(self, self.loc.get("error"), str(e))

    def change_theme(self, theme):
        self.theme_name = theme
        self.small_form.theme_name = theme
        self.apply_styles()
        self.small_form.apply_styles()
        self.create_menu()

    def change_lang(self, lang):
        self.small_form.loc.set_language(lang)
        self.small_form.lang = lang
        self.update_texts()
        self.small_form.update_ui_text()
        self.create_menu()

    def update_texts(self):
        self.setWindowTitle(self.loc.get("title"))
        self.note_input.setPlaceholderText(self.loc.get("enter_note"))
        self.edit_mode_chk.setText(self.loc.get("edit_mode"))

    def keyPressEvent(self, event):
        if (event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter):
            self.add_note()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.edit_mode_chk.isChecked():
            self.save_full_text()
        self.small_form.show()
        self.small_form.note_input.setFocus()
        self.small_form.activateWindow()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    form = SmallForm()
    form.show()
    sys.exit(app.exec_())