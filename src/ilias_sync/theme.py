"""A complete application palette, updated by the OS color-scheme signal."""
from pathlib import Path
import re
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QPalette, QFontInfo

LIGHT = dict(window='#fafafa', surface='#ffffff', inset='#f0f1f3', text='#202124', muted='#60646b',
             border='#d2d6dc', hover='#e9edf2', accent='#1265be', on_accent='#ffffff', selection='#dce9fa',
             selected_text='#133f72', disabled='#8b9098', error='#b42318', success='#167347', warning='#8c5409', sidebar='#f0f2f5', input_border='#818893')
DARK = dict(window='#191a1c', surface='#242529', inset='#202124', text='#f0f1f3', muted='#abb1ba',
            border='#44484f', hover='#32363d', accent='#8ab4f8', on_accent='#132b4c', selection='#304765',
            selected_text='#e2edff', disabled='#858c96', error='#ffa49c', success='#87d8a8', warning='#ebbd79', sidebar='#171b22', input_border='#848c99')


def stylesheet(c):
    check = Path(__file__).parent / 'assets/icons/actions' / ('check-dark.svg' if QColor(c['on_accent']).lightness() < 128 else 'check-light.svg')
    accent = QColor(c['accent'])
    accent_hover = (accent.lighter(110) if accent.lightness() > 128 else accent.darker(110)).name()
    accent_pressed = (accent.darker(110) if accent.lightness() > 128 else accent.darker(125)).name()
    return f"""
QWidget {{ color: {c['text']}; font-size: 13px; }}
QMainWindow, QDialog, QWidget#dialogBody, QWidget#page {{ background: {c['window']}; }}
QWidget#formPane, QFrame#surface {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 12px; }}
QFrame#surface QLabel, QWidget#formPane QLabel {{ background: transparent; border: none; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {c['window']}; border: none; }}
QStackedWidget {{ background: transparent; border: none; }}
QTabWidget::pane {{ border: none; padding-top: 14px; background: {c['window']}; }}
QTabBar::tab {{ background: {c['inset']}; color: {c['muted']}; padding: 8px 20px; border-radius: 6px; margin-right: 6px; }}
QTabBar::tab:selected {{ background: {c['selection']}; color: {c['selected_text']}; }}
QTabBar#workspaceTabs::tab {{ padding: 7px 10px; margin-right: 4px; }}
QFrame#noticeRow {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 7px; }}
QFrame#noticeRow QLabel {{ border: none; background: transparent; }}
QTextBrowser {{ border: none; background: {c['window']}; padding: 0; }}
QTextBrowser:focus {{ border: none; padding: 0; }}
QLabel {{ background: transparent; }}
QLabel#eyebrow, QLabel#subtitle {{ color: {c['muted']}; }}
QLabel#eyebrow {{ font-size: 12px; font-weight: 600; }}
QLabel#title {{ font-size: 24px; font-weight: 650; }}
QMainWindow QLabel#title {{ font-size: 21px; font-weight: 650; }}
QLabel#appTitle {{ font-size: 19px; font-weight: 650; }}
QLabel#sidebarNote {{ color: {c['muted']}; font-size: 11px; }}
QLabel#statusTitle {{ font-size: 16px; font-weight: 600; }}
QLabel#statusMeta {{ color: {c['muted']}; font-size: 11px; }}
QFrame#sidebar {{ background: {c['sidebar']}; border: none; }}
QFrame#syncPanel {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 10px; }}
QFrame#syncPanel QLabel {{ background: transparent; border: none; }}
QFrame#compactSync {{ background: transparent; border: none; border-top: 1px solid {c['border']}; }}
QFrame#compactSync QLabel {{ border: none; }}
QFrame#compactSync[tone="error"] {{ background: rgba(180, 35, 24, 14); border: 1px solid {c['error']}; border-left: 3px solid {c['error']}; border-radius: 7px; }}
QFrame#compactSync[tone="error"] QLabel#compactStatusTitle {{ color: {c['error']}; font-weight: 650; }}
QLabel#compactStatusTitle {{ font-size: 12px; font-weight: 500; }}
QWidget#inlineReport {{ background: transparent; }}
QWidget#inlineReport QTabWidget::pane {{ padding-top: 5px; }}
QWidget#inlineReport QTabBar::tab {{ padding: 5px 9px; }}
QWidget#inlineReport QComboBox {{ padding: 5px 26px 5px 8px; }}
QWidget#libraryEmpty {{ background: {c['surface']}; }}
QProgressBar {{ background: {c['inset']}; border: none; border-radius: 1px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 1px; }}
QLabel#sectionTitle {{ font-size: 15px; font-weight: 600; }}
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
QPushButton#iconControl {{ background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 0; min-height: 0; }}
QPushButton#iconControl:hover {{ background: {c['hover']}; border-color: {c['border']}; }}
QPushButton#iconControl:checked {{ background: {c['selection']}; border-color: {c['accent']}; }}
QPushButton#iconControl:focus {{ border: 2px solid {c['accent']}; }}
QPushButton#sidebarAction {{ background: transparent; }}
QPushButton#sidebarAction:hover {{ background: {c['hover']}; }}
QPushButton#toolbarControl {{ padding: 6px 12px; min-height: 18px; }}
QPushButton#syncAction {{ background: {c['accent']}; color: {c['on_accent']}; border: 2px solid {c['accent']}; padding: 8px 20px; font-size: 14px; font-weight: 650; min-height: 22px; }}
QPushButton#syncAction:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#syncAction:pressed {{ background: {accent_pressed}; border-color: {accent_pressed}; }}
QPushButton#syncAction:focus {{ border-color: {c['on_accent']}; }}
QPushButton#syncAction:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QLineEdit#materialSearch {{ padding: 7px 10px; }}
QLineEdit#materialSearch:focus {{ padding: 6px 9px; }}
QPushButton#compactControl {{ padding: 5px 9px; font-size: 11px; min-height: 16px; }}
QPushButton#stopControl {{ background: #c53030; border-color: #c53030; color: #ffffff; padding: 0; min-height: 34px; }}
QPushButton#stopControl:hover {{ background: #ae2525; border-color: #ae2525; }}
QPushButton#stopControl:disabled {{ background: #773d3d; border-color: #773d3d; color: #dddddd; }}
QPushButton#primary:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#quiet {{ background: transparent; border-color: transparent; color: {c['accent']}; text-align: left; padding-left: 0; }}
QPushButton#quiet:hover {{ text-decoration: underline; }}
QLineEdit, QTextEdit, QComboBox, QTimeEdit {{ background: {c['surface']}; color: {c['text']}; padding: 9px 10px; border: 1px solid {c['input_border']}; border-radius: 7px; selection-background-color: {c['selection']}; selection-color: {c['selected_text']}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 2px solid {c['accent']}; padding: 8px 9px; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {c['disabled']}; background: {c['inset']}; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border: none; background: transparent; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['text']}; selection-background-color: {c['selection']}; selection-color: {c['selected_text']}; }}
QCheckBox {{ spacing: 9px; padding: 5px 0; background: transparent; }}
QCheckBox:disabled {{ color: {c['disabled']}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {c['input_border']}; border-radius: 4px; background: {c['surface']}; }}
QCheckBox::indicator:checked {{ border-color: {c['accent']}; background: {c['accent']}; image: url("{check.as_posix()}"); }}
QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
QListWidget {{ background: {c['inset']}; border: 0; padding: 8px; border-radius: 8px; }}
QListWidget::item {{ padding: 14px 12px; margin-bottom: 4px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {c['selection']}; color: {c['selected_text']}; }}
QListWidget#sourceList {{ background: transparent; padding: 0; border-radius: 0; }}
QListWidget#sourceList::item {{ padding: 0; margin: 0 0 5px 0; }}
QTreeWidget, QTableWidget {{ background: {c['surface']}; alternate-background-color: {c['inset']}; border: 1px solid {c['border']}; border-radius: 7px; gridline-color: {c['inset']}; }}
QTreeWidget::item:selected, QTableWidget::item:selected {{ background: {c['selection']}; color: {c['selected_text']}; }}
QTreeWidget#libraryNavigation {{ background: transparent; border: none; border-radius: 0; }}
QTreeWidget#libraryNavigation::item {{ height: 30px; padding: 0 5px; border-radius: 5px; }}
QTreeWidget#libraryNavigation::item:hover {{ background: {c['hover']}; }}
QTreeWidget#libraryNavigation::item:selected {{ background: {c['selection']}; color: {c['selected_text']}; }}
QTreeWidget#libraryNavigation::item:focus {{ border: 1px solid {c['accent']}; }}
QTableWidget::item {{ border: none; border-bottom: 1px solid {c['inset']}; padding: 0 12px; }}
QTableWidget::item:hover {{ background: {c['hover']}; }}
QHeaderView::section {{ background: {c['inset']}; color: {c['text']}; padding: 10px; border: none; font-weight: 600; }}
QMainWindow QHeaderView::section {{ padding: 6px 10px; }}
QTextEdit#activity {{ font-size: 12px; color: {c['muted']}; }}
QSplitter::handle {{ background: {c['border']}; width: 1px; }}
QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
"""


class Theme(QObject):
    def __init__(self, application, mode='system'):
        super().__init__(application)
        self.app = application
        self.mode = mode
        self.hints = self.app.styleHints()
        self.accessibility = self.hints.accessibility()
        self.hints.colorSchemeChanged.connect(self.apply)
        self.accessibility.contrastPreferenceChanged.connect(lambda *_: self.apply())
        self.apply()

    def set_mode(self, mode):
        self.mode = mode if mode in {'system', 'light', 'dark'} else 'system'
        self.apply()

    def apply(self, scheme=None):
        scheme = scheme if isinstance(scheme, Qt.ColorScheme) else self.app.styleHints().colorScheme()
        dark = self.mode == 'dark' or (self.mode == 'system' and scheme == Qt.ColorScheme.Dark)
        c = DARK if dark else LIGHT
        self.high_contrast = self.accessibility.contrastPreference() == Qt.ContrastPreference.HighContrast
        if self.high_contrast:
            system = self.app.style().standardPalette()
            c = dict(c)
            for key, role in [('window', 'Window'), ('surface', 'Base'), ('inset', 'Window'), ('sidebar', 'Window'),
                              ('text', 'Text'), ('muted', 'Text'), ('border', 'Text'), ('input_border', 'Text'), ('hover', 'AlternateBase'),
                              ('accent', 'Highlight'), ('on_accent', 'HighlightedText'), ('selection', 'Highlight'),
                              ('selected_text', 'HighlightedText')]:
                c[key] = system.color(getattr(QPalette.ColorRole, role)).name()
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
        sheet = stylesheet(c)
        scale = max(1.0, QFontInfo(self.app.font()).pixelSize() / 13)
        sheet = re.sub(r'font-size: (\d+)px', lambda match: f'font-size: {round(int(match[1]) * scale)}px', sheet)
        self.app.setStyleSheet(sheet)
        self.dark = dark
