"""A complete application palette, updated by the OS color-scheme signal."""
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QPalette

LIGHT = dict(window='#fafafa', surface='#ffffff', inset='#f0f1f3', text='#202124', muted='#60646b',
             border='#d2d6dc', hover='#e9edf2', accent='#1265be', on_accent='#ffffff', selection='#dce9fa',
             selected_text='#133f72', disabled='#8b9098', error='#b42318', success='#167347')
DARK = dict(window='#191a1c', surface='#242529', inset='#202124', text='#f0f1f3', muted='#abb1ba',
            border='#44484f', hover='#32363d', accent='#8ab4f8', on_accent='#132b4c', selection='#304765',
            selected_text='#e2edff', disabled='#858c96', error='#ffa49c', success='#87d8a8')


def stylesheet(c):
    return f"""
QWidget {{ color: {c['text']}; font-size: 13px; }}
QMainWindow, QDialog, QWidget#dialogBody, QWidget#page {{ background: {c['window']}; }}
QWidget#formPane, QFrame#surface {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px; }}
QFrame#surface QLabel, QWidget#formPane QLabel {{ background: transparent; border: none; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c['window']}; border: none; }}
QStackedWidget {{ background: transparent; border: none; }}
QLabel {{ background: transparent; }}
QLabel#eyebrow, QLabel#subtitle {{ color: {c['muted']}; }}
QLabel#eyebrow {{ font-size: 12px; font-weight: 600; }}
QLabel#title {{ font-size: 29px; font-weight: 700; }}
QLabel#sectionTitle {{ font-size: 16px; font-weight: 650; }}
QLabel#step {{ color: {c['accent']}; font-size: 12px; font-weight: 600; }}
QLabel#status {{ padding: 12px 14px; border-radius: 8px; background: {c['inset']}; }}
QLabel#error {{ color: {c['error']}; }}
QLabel#success {{ color: {c['success']}; }}
QPushButton {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 7px; padding: 8px 14px; min-height: 18px; }}
QPushButton:hover {{ background: {c['hover']}; }}
QPushButton:pressed {{ background: {c['selection']}; }}
QPushButton:focus {{ border: 2px solid {c['accent']}; padding: 7px 13px; }}
QPushButton:disabled {{ color: {c['disabled']}; background: {c['inset']}; }}
QPushButton#primary {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']}; font-weight: 600; }}
QPushButton#primary:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#quiet {{ background: transparent; border-color: transparent; color: {c['accent']}; text-align: left; padding-left: 0; }}
QPushButton#quiet:hover {{ text-decoration: underline; }}
QLineEdit, QTextEdit, QComboBox {{ background: {c['surface']}; color: {c['text']}; padding: 9px 10px; border: 1px solid {c['border']}; border-radius: 7px; selection-background-color: {c['selection']}; selection-color: {c['selected_text']}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 2px solid {c['accent']}; padding: 8px 9px; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {c['disabled']}; background: {c['inset']}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border: none; background: transparent; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['text']}; selection-background-color: {c['selection']}; selection-color: {c['selected_text']}; }}
QCheckBox {{ spacing: 9px; padding: 5px 0; background: transparent; }}
QCheckBox:disabled {{ color: {c['disabled']}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QListWidget {{ background: {c['inset']}; border: 0; padding: 8px; border-radius: 8px; }}
QListWidget::item {{ padding: 14px 12px; margin-bottom: 4px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {c['selection']}; color: {c['selected_text']}; }}
QTreeWidget, QTableWidget {{ background: {c['surface']}; alternate-background-color: {c['inset']}; border: 1px solid {c['border']}; border-radius: 7px; gridline-color: {c['inset']}; }}
QTreeWidget::item:selected, QTableWidget::item:selected {{ background: {c['selection']}; color: {c['selected_text']}; }}
QHeaderView::section {{ background: {c['inset']}; color: {c['text']}; padding: 10px; border: none; font-weight: 600; }}
QTextEdit#activity {{ font-size: 12px; color: {c['muted']}; }}
QSplitter::handle {{ background: {c['border']}; width: 1px; }}
QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
"""


class Theme(QObject):
    def __init__(self, application, mode='system'):
        super().__init__(application)
        self.app = application
        self.mode = mode
        self.app.styleHints().colorSchemeChanged.connect(self.apply)
        self.apply()

    def set_mode(self, mode):
        self.mode = mode if mode in {'system', 'light', 'dark'} else 'system'
        self.apply()

    def apply(self, scheme=None):
        scheme = scheme if isinstance(scheme, Qt.ColorScheme) else self.app.styleHints().colorScheme()
        dark = self.mode == 'dark' or (self.mode == 'system' and scheme == Qt.ColorScheme.Dark)
        c = DARK if dark else LIGHT
        palette = QPalette()
        roles = {'Window':'window', 'WindowText':'text', 'Base':'surface', 'AlternateBase':'inset',
                 'Text':'text', 'Button':'surface', 'ButtonText':'text', 'Highlight':'selection',
                 'HighlightedText':'selected_text', 'ToolTipBase':'surface', 'ToolTipText':'text',
                 'PlaceholderText':'muted', 'Link':'accent', 'Light':'border', 'Mid':'border', 'Dark':'inset'}
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
            for role, key in roles.items():
                color = c['disabled'] if group == QPalette.ColorGroup.Disabled and role in {'Text','WindowText','ButtonText'} else c[key]
                palette.setColor(group, getattr(QPalette.ColorRole, role), QColor(color))
        self.app.setPalette(palette)
        self.app.setStyleSheet(stylesheet(c))
        self.dark = dark
