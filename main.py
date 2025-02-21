import sys
import json
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QLabel, QDesktopWidget, QScrollArea,
                            QMessageBox, QFileDialog, QMenuBar, QAction, QSystemTrayIcon, 
                            QMenu, QComboBox,QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QSettings, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap

# Настройка логирования
logging.basicConfig(filename="notes.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Путь к файлам
JSON_FILE = "notes.json"
BACKUP_FILE = "notes_backup.json"
SETTINGS_FILE = "settings.ini"

# Локализация (без изменений)
class Localization:
    def __init__(self, lang="ru"):
        self.lang = lang
        self.translations = {
            "ru": {
                "title": "Заметки",
                "expand": "Развернуть",
                "collapse": "Свернуть",
                "add": "+",
                "delete": "Удалить",
                "edit": "Редактировать",
                "search": "Поиск",
                "sort_date_asc": "Сортировать по дате (возр.)",
                "sort_date_desc": "Сортировать по дате (убыв.)",
                "sort_alpha": "Сортировать по алфавиту",
                "export": "Экспорт",
                "import": "Импорт",
                "settings": "Настройки",
                "themes":"Темы",
                "theme_light": "Светлая тема",
                "theme_dark": "Темная тема",
                "no_notes": "Заметок пока нет.",
                "saved": "Заметка сохранена!",
                "error": "Ошибка",
                "error_saving": "Ошибка при сохранении заметки!",
                "error_loading": "Ошибка при загрузке заметок!",
                "error_backup": "Ошибка при создании резервной копии!",
                "edit_note": "Редактировать заметку",
                "enter_note": "Введите заметку",
                "add_note": "Добавить заметку",
                "show_all_notes": "Показать все заметки",
                "show": "Показать",
                "quit": "Выход",
                "sort": "Сортировка"
            },
            "en": {
                "title": "Notes",
                "expand": "Expand",
                "collapse": "Collapse",
                "add": "+",
                "delete": "Delete",
                "edit": "Edit",
                "search": "Search",
                "sort_date_asc": "Sort by date (asc)",
                "sort_date_desc": "Sort by date (desc)",
                "sort_alpha": "Sort alphabetically",
                "export": "Export",
                "import": "Import",
                "settings": "Settings",
                "themes":"Themes",
                "theme_light": "Light theme",
                "theme_dark": "Dark theme",
                "no_notes": "No notes yet.",
                "saved": "Note saved!",
                "error": "Error",
                "error_saving": "Error saving note!",
                "error_loading": "Error loading notes!",
                "error_backup": "Error creating backup!",
                "edit_note": "Edit note",
                "enter_note": "Enter note",
                "add_note": "Add note",
                "show_all_notes": "Show all notes",
                "show": "Show",
                "quit": "Quit",
                "sort": "Sort"
            }
        }

    def get(self, key):
        return self.translations[self.lang].get(key, key)

class NoteWorker(QThread):
    noteSaved = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, notes, note, filename):
        super().__init__()
        self.notes = notes
        self.note = note
        self.filename = filename

    def run(self):
        try:
            self.notes.append(self.note)
            # Сохранение без шифрования
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
            self.noteSaved.emit()
        except Exception as e:
            logging.error(f"Error saving note: {e}")
            self.errorOccurred.emit(str(e))

class SmallForm(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(SETTINGS_FILE, QSettings.IniFormat)
        self.lang = self.settings.value("language", "ru")
        self.theme = self.settings.value("theme", "light")
        self.loc = Localization(self.lang)
        self.notes = []
        self.initUI()
        self.load_notes()
        self.setup_tray()

    def initUI(self):
        self.setWindowTitle(self.loc.get("title"))
        self.setFixedSize(350, 60)  # Увеличен размер для лучшей читаемости
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon("icon.png"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Поле ввода заметки
        self.note_input = QLineEdit()
        self.note_input.setFont(QFont("Segoe UI", 11))
        self.note_input.setPlaceholderText(self.loc.get("enter_note"))
        self.note_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 8px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
                background-color: #f0f8ff;
            }
        """)
        main_layout.addWidget(self.note_input, stretch=1)

        # Кнопка добавления
        self.add_button = QPushButton(self.loc.get("add"))
        self.add_button.setFixedSize(32, 32)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.add_button.clicked.connect(self.save_note)
        self.add_button.setToolTip(self.loc.get("add_note"))
        main_layout.addWidget(self.add_button)

        # Кнопка расширения
        self.expand_button = QPushButton(self.loc.get("expand"))
        self.expand_button.setFixedSize(100, 32)
        self.expand_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:pressed {
                background-color: #3D8B40;
            }
        """)
        self.expand_button.clicked.connect(self.open_large_form)
        self.expand_button.setToolTip(self.loc.get("show_all_notes"))
        main_layout.addWidget(self.expand_button)

        self.apply_theme()
        self.load_position()
        self.start_animation()

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                background-color: #2D2D2D;
                color: #FFFFFF;
            """)
            self.note_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #555555;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #3C3C3C;
                    color: #FFFFFF;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                    background-color: #454545;
                }
            """)
        else:
            self.setStyleSheet("""
                background-color: #F5F5F5;
                color: #333333;
            """)

    def start_animation(self):
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setStartValue(QRect(self.x(), self.y() + 50, self.width(), self.height()))
        self.animation.setEndValue(QRect(self.x(), self.y(), self.width(), self.height()))
        self.animation.start()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        tray_menu = QMenu()

        show_action = tray_menu.addAction(self.loc.get("show"))
        show_action.triggered.connect(self.show)

        quit_action = tray_menu.addAction(self.loc.get("quit"))
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def position_near_taskbar(self):
        available_geometry = QDesktopWidget().availableGeometry()
        self.move(available_geometry.width() - self.width() - 15,
                 available_geometry.height() - self.height() - 15)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() & Qt.ShiftModifier:
            self.save_note()
            event.accept()
        else:
            super().keyPressEvent(event)

    def save_note(self):
        note_text = self.note_input.text().strip()
        if note_text:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            note = {"time": current_time, "text": note_text}
            worker = NoteWorker(self.notes, note, JSON_FILE)
            worker.noteSaved.connect(lambda: self.show_notification(self.loc.get("saved")))
            worker.errorOccurred.connect(self.handle_save_error)
            worker.start()
            self.note_input.clear()
            self.backup_notes()

    def handle_save_error(self, error_message):
        QMessageBox.critical(self, self.loc.get("error"), 
                           self.loc.get("error_saving") + f"\n{error_message}",
                           QMessageBox.Ok)

    def load_notes(self):
        try:
            if os.path.exists(JSON_FILE):
                with open(JSON_FILE, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
            else:
                self.notes = []
        except Exception as e:
            logging.error(f"Error loading notes: {e}")
            QMessageBox.critical(self, self.loc.get("error"), 
                               self.loc.get("error_loading") + f"\n{e}",
                               QMessageBox.Ok)
            self.notes = []

    def backup_notes(self):
        try:
            if os.path.exists(JSON_FILE):
                with open(JSON_FILE, "r", encoding="utf-8") as f:
                    data = f.read()
                with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                    f.write(data)
        except Exception as e:
            logging.error(f"Error backing up notes: {e}")
            QMessageBox.critical(self, self.loc.get("error"), 
                               self.loc.get("error_backup") + f"\n{e}",
                               QMessageBox.Ok)

    def show_notification(self, message):
        self.tray_icon.showMessage(self.loc.get("title"), 
                                 message, 
                                 QSystemTrayIcon.Information, 
                                 3000)

    def load_position(self):
        pos = self.settings.value("position", None)
        if pos:
            self.move(pos)
        else:
            self.position_near_taskbar()

    def closeEvent(self, event):
        self.settings.setValue("position", self.pos())
        self.settings.setValue("theme", self.theme)
        self.settings.setValue("language", self.lang)
        event.accept()

    def open_large_form(self):
        self.large_form = LargeForm(self)
        self.large_form.show()
        self.hide()

class LargeForm(QMainWindow):
    def __init__(self, small_form):
        super().__init__()
        self.small_form = small_form
        self.loc = self.small_form.loc
        self.theme = self.small_form.theme
        self.notes = self.small_form.notes
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.loc.get("title"))
        self.setMinimumSize(600, 400)
        self.setWindowIcon(QIcon("icon.png"))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Создаем меню
        self.create_menu_bar()

        # Панель поиска и сортировки
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.loc.get("search"))
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 6px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
                background-color: #f0f8ff;
            }
        """)
        self.search_input.textChanged.connect(self.filter_notes)  # Добавляем обработчик
        top_layout.addWidget(self.search_input)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            self.loc.get("sort_date_desc"),
            self.loc.get("sort_date_asc"),
            self.loc.get("sort_alpha")
        ])
        self.sort_combo.setFixedHeight(32)
        self.sort_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 6px;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        self.sort_combo.currentIndexChanged.connect(self.sort_notes)  # Добавляем обработчик сортировки
        top_layout.addWidget(self.sort_combo)

        main_layout.addWidget(top_panel)

        # Область заметок
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.notes_container = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_container)
        self.notes_layout.setAlignment(Qt.AlignTop)
        self.notes_layout.setSpacing(8)
        self.scroll_area.setWidget(self.notes_container)
        main_layout.addWidget(self.scroll_area)

        # Добавляем нижнюю панель с полем ввода и кнопкой
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        bottom_layout.setSpacing(8)

        self.note_input = QLineEdit()
        self.note_input.setFont(QFont("Segoe UI", 11))
        self.note_input.setPlaceholderText(self.loc.get("enter_note"))
        self.note_input.setFixedHeight(40)
        self.note_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 8px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
                background-color: #f0f8ff;
            }
        """)
        bottom_layout.addWidget(self.note_input, stretch=1)

        self.add_button = QPushButton(self.loc.get("add"))
        self.add_button.setFixedSize(32, 32)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.add_button.clicked.connect(self.save_note)
        self.add_button.setToolTip(self.loc.get("add_note"))
        bottom_layout.addWidget(self.add_button)

        main_layout.addWidget(bottom_panel)

        self.apply_theme()
        self.load_notes()
        self.center_on_screen()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu(self.loc.get("settings"))
        theme_menu = QMenu(self.loc.get("themes"), self)
        
        light_theme = QAction(self.loc.get("theme_light"), self)
        dark_theme = QAction(self.loc.get("theme_dark"), self)
        theme_menu.addAction(light_theme)
        theme_menu.addAction(dark_theme)
        file_menu.addMenu(theme_menu)

        export_action = QAction(self.loc.get("export"), self)
        import_action = QAction(self.loc.get("import"), self)
        file_menu.addAction(export_action)
        file_menu.addAction(import_action)

        light_theme.triggered.connect(lambda: self.change_theme("light"))
        dark_theme.triggered.connect(lambda: self.change_theme("dark"))
        export_action.triggered.connect(self.export_notes)
        import_action.triggered.connect(self.import_notes)

    
    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                background-color: #2D2D2D;
                color: #FFFFFF;
            """)
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #2D2D2D;
                    border: none;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #555555;
                    border-radius: 8px;
                    padding: 6px;
                    background-color: #3C3C3C;
                    color: #FFFFFF;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                    background-color: #454545;
                }
            """)
            self.note_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #555555;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #3C3C3C;
                    color: #FFFFFF;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                    background-color: #454545;
                }
            """)
            self.sort_combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #555555;
                    border-radius: 8px;
                    padding: 6px;
                    background-color: #3C3C3C;
                    color: #FFFFFF;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
            """)
        else:
            self.setStyleSheet("""
                background-color: #F5F5F5;
                color: #333333;
            """)
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #F5F5F5;
                    border: none;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #cccccc;
                    border-radius: 8px;
                    padding: 6px;
                    background-color: #ffffff;
                    color: #333333;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                    background-color: #f0f8ff;
                }
            """)
            self.note_input.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #cccccc;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #ffffff;
                    color: #333333;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                    background-color: #f0f8ff;
                }
            """)
            self.sort_combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #cccccc;
                    border-radius: 8px;
                    padding: 6px;
                    background-color: #ffffff;
                    color: #333333;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
            """)
    def sort_notes(self):
        sort_type = self.sort_combo.currentIndex()
        search_text = self.search_input.text().lower()
        
        # Фильтруем заметки перед сортировкой
        filtered_notes = [
            note for note in self.notes 
            if search_text.lower() in note['text'].lower() or 
            search_text.lower() in note['time'].lower()
        ]

        # Сортировка
        if sort_type == 0:  # По дате (убывание)
            filtered_notes.sort(key=lambda x: x['time'], reverse=True)
        elif sort_type == 1:  # По дате (возрастание)
            filtered_notes.sort(key=lambda x: x['time'])
        elif sort_type == 2:  # По алфавиту
            filtered_notes.sort(key=lambda x: x['text'].lower())

        # Обновляем отображение
        self.notes = [note for note in self.notes if note not in filtered_notes] + filtered_notes
        self.load_notes(search_text)

    def center_on_screen(self):
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2,
                 (screen.height() - size.height()) // 2)

    

    def load_notes(self, search_text=""):
        while self.notes_layout.count():
            item = self.notes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.notes:
            #print(self.notes)
            filtered_notes = [ note for note in self.notes if search_text.lower() in note['text'].lower() or search_text.lower() in note['time'].lower()]
        else:
            filtered_notes=[]

        if not filtered_notes:
            no_notes_label = QLabel(self.loc.get("no_notes"))
            no_notes_label.setAlignment(Qt.AlignCenter)
            no_notes_label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 14px;
                    padding: 20px;
                }
            """)
            self.notes_layout.addWidget(no_notes_label)
            return

        for note in filtered_notes:
            note_widget = QWidget()
            note_layout = QHBoxLayout(note_widget)
            note_layout.setContentsMargins(10, 10, 10, 10)

            # Создаем контейнер для текста заметки
            text_container = QWidget()
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            # QLabel для даты и времени (полужирный)
            date_label = QLabel(note['time'])
            date_label.setStyleSheet("""
                QLabel {
                    color: #333333;
                    font-size: 12px;
                    font-weight: bold;
                }
            """ if self.theme == "light" else """
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            text_layout.addWidget(date_label)

            # QLabel для текста заметки (обычный)
            text_label = QLabel(note['text'])
            text_label.setWordWrap(True)
            text_label.setStyleSheet("""
                QLabel {
                    color: #333333;
                    font-size: 12px;
                }
            """ if self.theme == "light" else """
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                }
            """)
            text_layout.addWidget(text_label)

            note_layout.addWidget(text_container)

            edit_button = QPushButton(self.loc.get("edit"))
            edit_button.setFixedSize(90, 24)
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 6px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #1565C0;
                }
            """)
            edit_button.clicked.connect(lambda _, n=note: self.edit_note(n))
            note_layout.addWidget(edit_button)

            delete_button = QPushButton(self.loc.get("delete"))
            delete_button.setFixedSize(60, 24)
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border-radius: 6px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
                QPushButton:pressed {
                    background-color: #C62828;
                }
            """)
            delete_button.clicked.connect(lambda _, n=note: self.delete_note(n))
            note_layout.addWidget(delete_button)

            note_widget.setStyleSheet("""
                QWidget {
                    background-color: #FFFFFF;
                    border-radius: 8px;
                    padding: 5px;
                }
            """ if self.theme == "light" else """
                QWidget {
                    background-color: #3C3C3C;
                    border-radius: 8px;
                    padding: 5px;
                }
            """)
            self.notes_layout.addWidget(note_widget)
            
    def filter_notes(self):
            search_text = self.search_input.text().lower()
            self.load_notes(search_text)  # Передаем поисковый запрос в load_notes
    def save_note(self):
        note_text = self.note_input.text().strip()
        if note_text:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            note = {"time": current_time, "text": note_text}
            self.notes.append(note)
            self.save_notes()
            self.note_input.clear()
            self.small_form.show_notification(self.loc.get("saved"))
            self.load_notes()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() & Qt.ShiftModifier:
            self.save_note()
            event.accept()
        else:
            super().keyPressEvent(event)

    def edit_note(self, note):
        text, ok = QInputDialog.getText(self, 
                                      self.loc.get("edit_note"),
                                      self.loc.get("enter_note"),
                                      QLineEdit.Normal,
                                      note['text'])
        if ok and text:
            note['text'] = text
            note['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_notes()
            self.load_notes()

    def delete_note(self, note):
        reply = QMessageBox.question(self,
                                   self.loc.get("delete"),
                                   f"{self.loc.get('delete')} {note['text']}?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.notes.remove(note)
            self.save_notes()
            self.load_notes()

    def save_notes(self):
        try:
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
            self.small_form.backup_notes()
        except Exception as e:
            logging.error(f"Error saving notes: {e}")
            QMessageBox.critical(self, self.loc.get("error"),
                               self.loc.get("error_saving") + f"\n{e}",
                               QMessageBox.Ok)

    def change_theme(self, theme):
        self.theme = theme
        self.small_form.theme = theme
        self.apply_theme()
        self.load_notes()
        self.small_form.apply_theme()

    def export_notes(self):
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                 self.loc.get("export"),
                                                 "",
                                                 "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(self.notes, f, ensure_ascii=False, indent=2)
            except Exception as e:
                QMessageBox.critical(self, self.loc.get("error"),
                                   self.loc.get("error_saving") + f"\n{e}",
                                   QMessageBox.Ok)

    def import_notes(self):
        file_name, _ = QFileDialog.getOpenFileName(self,
                                                 self.loc.get("import"),
                                                 "",
                                                 "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    imported_notes = json.load(f)
                self.notes.extend(imported_notes)
                self.save_notes()
                self.load_notes()
            except Exception as e:
                QMessageBox.critical(self, self.loc.get("error"),
                                   self.loc.get("error_loading") + f"\n{e}",
                                   QMessageBox.Ok)

    def closeEvent(self, event):
        self.small_form.show()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Установка глобального стиля приложения
    app.setStyle("Fusion")
    
    # Создание палитры для темной темы
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    # Создание и запуск главного окна
    small_form = SmallForm()
    small_form.show()

    sys.exit(app.exec_())