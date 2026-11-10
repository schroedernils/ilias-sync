"""A complete application palette, updated by the OS color-scheme signal."""
from pathlib import Path
import re
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPalette, QFontInfo
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import isValid

from .control_colors import pause_colors

# Layered charcoal from Cursor Dark and the Grok Bot renderer: chrome under the pane, never pure black.
LIGHT = dict(window='#e8eae8', surface='#e8eae8', elevated='#f4f5f2', inset='#dfe3e0', text='#303936', muted='#57635e',
             faint='#637069', border='#c5cdc7', hover='#e0e6e1', accent='#a4cbe1', accent_hover='#b4d6e9',
             on_accent='#233e4d', selection='#d1dfd8', selected_text='#303936', disabled='#78827c', error='#a33850', error_fill='#a33850',
             success='#326d50', warning='#865b28', sidebar='#e0e4e0', input_border='#7b877f',
             card='#f2f3f0', field='#f7f7f3', link='#356983')
DARK = dict(window='#181818', surface='#181818', elevated='#1e1e1e', inset='#202020', text='#f0f0f0', muted='#b8b8b8',
            faint='#a2a2a2', border='#383838', hover='#262626', accent='#599ce7', accent_hover='#68a4e8',
            on_accent='#141414', selection='#313131', selected_text='#f0f0f0', disabled='#818181', error='#ff8da4', error_fill='#a6314e',
            success='#83cfa3', warning='#f1b467', sidebar='#141414', input_border='#818181')

# Frosted surfaces rely on the native Cocoa backdrop.
FROST = 0.82
MENU_OPACITY = 0.97
WORKSPACE_GUTTER = 22
CARD_INSET = 14
SYNC_CONTROL_HEIGHT = 40


def uses_native_backdrop(application):
    return application is not None and application.platformName() == 'cocoa'


def is_dark(palette):
    # Transparent item views expose a black Base/Window even in the light theme.
    return palette.color(QPalette.ColorRole.Text).lightness() > 128


def popup_color(palette):
    color = palette.color(QPalette.ColorRole.ToolTipBase)
    app = QApplication.instance()
    high_contrast = getattr(getattr(app, '_ilias_theme_manager', None), 'high_contrast', False)
    color.setAlphaF(MENU_OPACITY if uses_native_backdrop(app) and not high_contrast else 1.0)
    return color


def _frost(hex_color, alpha):
    if alpha == 1:
        return hex_color
    color = QColor(hex_color)
    return f'rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.2f})'


def _lift(hex_color, amount):
    """Same transparency, a few steps lighter. Light surfaces step darker so they still separate."""
    color = QColor(hex_color)
    step = -amount if color.lightness() > 180 else amount
    def channel(value):
        return max(0, min(255, value + step))
    return QColor(channel(color.red()), channel(color.green()), channel(color.blue())).name()


def _surface(color, base, opacity):
    """Keep a surface's contrast while allowing the common backdrop through."""
    surface, under = QColor(color), QColor(base)
    channels = [max(0, min(255, round(b + (s - b) / opacity)))
                for s, b in zip(surface.getRgb()[:3], under.getRgb()[:3])]
    return f'rgba({channels[0]}, {channels[1]}, {channels[2]}, {opacity:.2f})'


def stylesheet(c, frost=1):
    check = Path(__file__).parent / 'assets/icons/actions' / ('check-dark.svg' if QColor(c['on_accent']).lightness() < 128 else 'check-light.svg')
    pane = _frost(c['window'], frost)
    # One window tint: nested layout carriers must not repeatedly attenuate
    # the native backdrop or make full pages opaque.
    carrier = 'transparent' if frost < 1 else pane
    night = QColor(c['text']).lightness() > 128
    rail_color = _lift(c['window'], 12) if night else c['sidebar']
    card_color = c.get('card', _lift(c['window'], 18))
    layer_opacity = 0.26 if night else 0.46
    rail = _surface(rail_color, c['window'], layer_opacity) if frost < 1 else rail_color
    card = _surface(card_color, c['window'], layer_opacity) if frost < 1 else card_color
    field = c.get('field', _lift(c['window'], 28))
    if frost < 1:
        field = _surface(field, c['window'], 0.70)
    input_fill = _surface(c['window'], c['window'], 0.55) if frost < 1 else c['window']
    search_fill = _surface(c['inset'], c['window'], 0.55) if frost < 1 else c['inset']
    search_hover = _surface(c['hover'], c['window'], 0.55) if frost < 1 else c['hover']
    sheet = _frost(c['elevated'], 1 if frost == 1 else MENU_OPACITY)
    tooltip_opacity = 255 if frost == 1 else 250
    accent = QColor(c['accent'])
    accent_pressed = (accent.darker(112) if accent.lightness() > 128 else accent.darker(125)).name()
    elevated = c.get('elevated', c['surface'])
    item_hover = 'rgba(255, 255, 255, 0.30)' if QColor(c['text']).lightness() > 128 else 'rgba(20, 20, 20, 0.08)'
    # The commit control is the lightest solid action, so Save stays findable on a dark sheet.
    commit = '#d7ebff' if night else c['accent']
    commit_pressed = '#c5dff8' if night else accent_pressed
    commit_ink = c['on_accent']
    pause_fill, _pause_hover, pause_pressed, pause_ink = pause_colors(night)
    stop_fill = '#6e1c34' if night else '#8d1234'
    stop_pressed = '#551428' if night else '#70102a'
    stop_ink = '#fff4f6'
    return f"""
QWidget {{ color: {c['text']}; font-size: 14px; }}
QDialog {{ background: {pane}; }}
QWidget#dialogBody, QDialog QScrollArea, QDialog QScrollArea > QWidget > QWidget {{ background: transparent; }}
QMainWindow {{ background: {pane}; }}
QWidget#page, QWidget#mainSurface {{ background: {carrier}; }}
QWidget#formPane, QFrame#surface {{ background: {carrier}; border: none; border-radius: 0; }}
QFrame#surface QLabel, QWidget#formPane QLabel {{ background: transparent; border: none; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {carrier}; border: none; }}
QTabWidget, QTabBar, QDialogButtonBox {{ background: transparent; border: none; }}
QStackedWidget {{ background: transparent; border: none; }}
QTabWidget::pane {{ border: none; border-top: 1px solid {c['border']}; padding-top: 16px; background: {carrier}; }}
QDialog#settingsDialog QTabWidget::pane {{ background: transparent; border: none; padding-top: 4px; }}
QDialog#settingsDialog QScrollArea, QDialog#settingsDialog QScrollArea > QWidget, QDialog#settingsDialog QWidget#dialogBody {{ background: transparent; border: none; }}
QTabBar::tab {{ background: transparent; color: {c['faint']}; padding: 6px 10px; margin: 8px 4px 8px 0; border: none; border-radius: 8px; font-weight: 500; }}
QTabBar::tab:hover {{ background: {c['hover']}; color: {c['text']}; }}
QTabBar::tab:selected {{ background: {c['selection']}; color: {c['text']}; border-radius: 8px; font-weight: 600; }}
QTabBar::tab:selected:hover {{ background: {c['selection']}; color: {c['text']}; }}
QTabBar#workspaceTabs::tab {{ padding: 6px 10px; margin-right: 6px; }}
QFrame#noticeRow, QFrame#textCard, QFrame#recentCard, QFrame#settingsCard, QFrame#compactSync {{ background: {card}; border: 1px solid {c['border']}; border-radius: 12px; }}
QFrame#noticeRow QLabel, QFrame#textCard QLabel, QFrame#recentCard QLabel, QFrame#settingsCard QLabel {{ border: none; background: transparent; }}
QTextBrowser {{ border: none; background: transparent; padding: 0; color: {c['text']}; selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QTextBrowser:focus {{ border: none; padding: 0; }}
QLabel {{ background: transparent; }}
QLabel#eyebrow, QLabel#subtitle {{ color: {c['muted']}; }}
QLabel#eyebrow {{ font-size: 13px; font-weight: 400; }}
QLabel#title {{ font-size: 22px; font-weight: 600; }}
QMainWindow QLabel#title {{ font-size: 20px; font-weight: 600; }}
QLabel#appTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#sidebarNote {{ color: {c['muted']}; font-size: 13px; }}
QLabel#statusTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#statusMeta {{ color: {c['faint']}; font-size: 12px; }}
QFrame#sidebar {{ background: {rail}; border: none; }}
QFrame#syncPanel {{ background: transparent; border: none; border-top: 1px solid {c['border']}; border-radius: 0; }}
QFrame#syncPanel QLabel {{ background: transparent; border: none; }}
QTableWidget#recentFiles {{ background: transparent; selection-background-color: transparent; outline: none; }}
QTableWidget#recentFiles::item, QTableWidget#recentFiles::item:selected, QTableWidget#recentFiles::item:selected:active, QTableWidget#recentFiles::item:focus {{ background: transparent; border: none; outline: none; }}
QFrame#compactSync QLabel {{ border: none; background: transparent; }}
QFrame#compactSync[tone="error"] {{ border-color: {c['error_fill']}; }}
QFrame#compactSync[tone="error"] QLabel#compactStatusTitle {{ color: {c['error']}; font-weight: 700; }}
QLabel#compactStatusTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#compactStatusDetail {{ font-size: 13px; color: {c['muted']}; }}
QWidget#inlineReport {{ background: transparent; }}
QWidget#inlineReport QTabWidget::pane {{ padding-top: 5px; }}
QWidget#inlineReport QTabBar::tab {{ padding: 5px 9px; }}
QWidget#inlineReport QComboBox {{ padding: 5px 26px 5px 8px; }}
QWidget#libraryEmpty {{ background: transparent; }}
QWidget#weekDay {{ border-bottom: 1px solid {c['border']}; }}
QWidget#weekDay QLabel, QWidget#weekDay QWidget {{ border: none; }}
QLabel#weekDayName {{ font-weight: 600; padding-top: 6px; }}
QTimeEdit#weekTimeEdit {{ padding: 5px 6px; border: 1px solid {c['input_border']}; border-radius: 6px; }}
QTimeEdit#weekTimeEdit:focus {{ border: 1px solid {c['accent']}; padding: 5px 6px; }}
QTimeEdit#weekTimeEdit QLineEdit {{ padding: 0; border: none; background: transparent; min-height: 0; }}
QPushButton#weekAdd {{ padding: 0; min-height: 0; background: transparent; border: none; font-size: 19px; color: {c['accent']}; }}
QPushButton#weekRemove {{ padding: 0; min-height: 0; background: transparent; border-color: transparent; color: {c['muted']}; font-size: 16px; }}
QPushButton#weekRemove:hover {{ background: transparent; color: {c['muted']}; }}
QPushButton#weekAdd:focus, QPushButton#weekRemove:focus {{ outline: none; }}
QProgressBar {{ background: {c['inset']}; border: none; border-radius: 2px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}
QLabel#sectionTitle {{ font-size: 15px; font-weight: 600; }}
QLabel#step {{ color: {c['accent']}; font-size: 12px; font-weight: 600; }}
QLabel#status {{ padding: 12px 14px; border-radius: 8px; background: {c['inset']}; }}
QLabel#error {{ color: {c['error']}; }}
QLabel#success {{ color: {c['success']}; }}
QPushButton {{ background: transparent; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 0 14px; min-height: 32px; font-weight: 600; }}
QPushButton:hover {{ background: transparent; }}
QPushButton:pressed {{ background: transparent; }}
QPushButton:focus {{ outline: none; }}
QPushButton:disabled {{ color: {c['disabled']}; background: transparent; border-color: {c['border']}; }}
QPushButton#primary {{ background: {c['accent']}; color: {c['on_accent']}; border: 1px solid {c['accent']}; border-radius: 10px; }}
QPushButton#primary:hover {{ background: {c['accent']}; border-color: {c['accent']}; }}
QPushButton#primary:pressed {{ background: {accent_pressed}; border-color: {accent_pressed}; }}
QPushButton#primary:focus {{ outline: none; }}
QPushButton#commit {{ background: {commit}; color: {commit_ink}; border: 1px solid {commit}; border-radius: 10px; font-weight: 600; }}
QPushButton#commit:hover {{ background: {commit}; color: {commit_ink}; border-color: {commit}; }}
QPushButton#commit:pressed {{ background: {commit_pressed}; color: {commit_ink}; border-color: {commit_pressed}; }}
QPushButton#commit:focus {{ outline: none; }}
QPushButton#commit:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#iconControl {{ background: transparent; border: 1px solid transparent; border-radius: 999px; padding: 0; min-height: 0; }}
QPushButton#iconControl:hover {{ background: transparent; border-color: transparent; }}
QPushButton#iconControl:checked {{ background: {c['hover']}; border-color: transparent; }}
QPushButton#iconControl:focus {{ outline: none; border-color: transparent; }}
QPushButton#sidebarAction {{ background: transparent; border: none; border-radius: 10px; text-align: left; padding: 0 12px; min-height: 32px; font-weight: 500; font-size: 14px; }}
QPushButton#sidebarAction:hover {{ background: transparent; }}
QPushButton#sidebarAction:focus {{ outline: none; border: none; }}
QPushButton#toolbarControl {{ padding: 0 14px; min-height: 32px; }}
QPushButton#syncAction, QPushButton#syncRecovery {{ background: {c['accent']}; color: {c['on_accent']}; border: 1px solid {c['accent']}; border-radius: 10px; padding: 0 14px; font-size: 14px; font-weight: 600; min-height: 36px; }}
QPushButton#syncAction:hover, QPushButton#syncRecovery:hover {{ background: {c['accent']}; border-color: {c['accent']}; }}
QPushButton#syncAction:pressed, QPushButton#syncRecovery:pressed {{ background: {accent_pressed}; border-color: {accent_pressed}; }}
QPushButton#syncAction:focus, QPushButton#syncRecovery:focus {{ outline: none; }}
QPushButton#syncAction:disabled, QPushButton#syncRecovery:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#syncAction[collapsing="true"]:disabled {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']}; }}
QPushButton#syncAction[shaped="true"], QPushButton#syncAction[shaped="true"]:disabled {{ background: transparent; border-color: transparent; color: {c['on_accent']}; }}
QPushButton#primary[shaped="true"], QPushButton#primary[shaped="true"]:disabled, QPushButton#pauseControl[shaped="true"], QPushButton#pauseControl[shaped="true"]:disabled, QPushButton#stopControl[shaped="true"], QPushButton#stopControl[shaped="true"]:disabled {{ background: transparent; border-color: transparent; }}
QLineEdit#materialSearch {{ background: {search_fill}; border: 1px solid {c['border']}; border-radius: 10px; padding: 0 10px; min-height: 36px; }}
QLineEdit#materialSearch:hover {{ background: {search_hover}; }}
QLineEdit#materialSearch:focus {{ background: {input_fill}; border-color: {c['accent']}; }}
QPushButton#exceptionDismiss {{ background: transparent; color: {c['muted']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 0 8px; min-height: 22px; font-size: 12px; font-weight: 500; }}
QPushButton#exceptionDismiss:hover {{ background: transparent; color: {c['text']}; }}
QPushButton#exceptionDismiss:focus {{ outline: none; }}
QPushButton#compactControl {{ background: transparent; border: none; border-radius: 10px; padding: 0 10px; font-size: 13px; font-weight: 600; min-height: 32px; color: {c['muted']}; }}
QPushButton#compactControl:hover {{ background: transparent; color: {c['text']}; }}
QPushButton#compactControl:focus {{ outline: none; border: none; }}
QPushButton#pauseControl {{ background: {pause_fill}; color: {pause_ink}; border: 1px solid {pause_fill}; padding: 0; min-height: 0; border-radius: 10px; }}
QPushButton#pauseControl:hover {{ background: {pause_fill}; border-color: {pause_fill}; color: {pause_ink}; }}
QPushButton#pauseControl:pressed {{ background: {pause_pressed}; border-color: {pause_pressed}; color: {pause_ink}; }}
QPushButton#pauseControl:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#stopControl {{ background: {stop_fill}; color: {stop_ink}; border: 1px solid {stop_fill}; padding: 0; min-height: 0; border-radius: 10px; }}
QPushButton#stopControl:hover {{ background: {stop_fill}; border-color: {stop_fill}; color: {stop_ink}; }}
QPushButton#stopControl:pressed {{ background: {stop_pressed}; border-color: {stop_pressed}; color: {stop_ink}; }}
QPushButton#stopControl:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#primary:disabled {{ background: {c['inset']}; color: {c['disabled']}; border-color: {c['border']}; }}
QPushButton#secondary {{ background: transparent; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 10px; padding: 0 12px; min-height: 32px; font-weight: 600; }}
QPushButton#secondary:hover {{ background: transparent; color: {c['text']}; }}
QPushButton#secondary:focus {{ outline: none; }}
QPushButton#quiet {{ background: transparent; border: none; color: {c['text']}; text-align: left; padding: 0; min-height: 28px; font-weight: 600; }}
QPushButton#quiet:hover {{ background: transparent; color: {c['text']}; }}
QPushButton#quiet:focus {{ border: none; }}
QLineEdit, QTextEdit, QComboBox, QTimeEdit {{ background: {input_fill}; color: {c['text']}; padding: 8px 12px; border: 1px solid {c['input_border']}; border-radius: 8px; selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 1px solid {c['accent']}; padding: 8px 12px; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {c['disabled']}; background: {c['inset']}; }}
QDialog#settingsDialog QLineEdit, QDialog#settingsDialog QComboBox, QDialog#settingsDialog QTimeEdit {{ background: {field}; }}
QDialog#settingsDialog QLineEdit:disabled, QDialog#settingsDialog QComboBox:disabled, QDialog#settingsDialog QTimeEdit:disabled {{ background: {c['inset']}; color: {c['disabled']}; }}
QDialog#settingsDialog QTimeEdit#weekTimeEdit QLineEdit {{ background: transparent; }}
QComboBox#libraryView {{ background: transparent; border: none; border-radius: 10px; padding: 0 28px 0 8px; min-height: 32px; font-weight: 600; }}
QComboBox#libraryView:hover {{ background: {c['hover']}; }}
QComboBox#libraryView:focus {{ outline: none; border: none; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border: none; background: transparent; }}
QComboBox QAbstractItemView {{ background: {sheet}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 12px; selection-background-color: transparent; selection-color: {c['text']}; outline: none; padding: 6px; }}
QComboBox QAbstractItemView::item {{ border-radius: 8px; min-height: 28px; padding: 4px 10px; background: transparent; }}
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {{ background: transparent; color: {c['text']}; }}
QCheckBox {{ spacing: 10px; padding: 6px 0; background: transparent; }}
QCheckBox:disabled {{ color: {c['disabled']}; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {c['input_border']}; border-radius: 4px; background: {c['window']}; }}
QCheckBox::indicator:checked {{ border-color: {c['accent']}; background: {c['accent']}; image: url("{check.as_posix()}"); }}
QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
QListWidget {{ background: transparent; border: none; padding: 0; border-radius: 0; outline: none; }}
QListWidget::item {{ padding: 10px 12px; margin: 0; border-radius: 8px; }}
QListWidget::item:selected {{ background: {c['selection']}; color: {c['text']}; }}
QListWidget::item:hover {{ background: {c['hover']}; }}
QListWidget#helpTopics::item {{ padding: 6px 8px; margin: 2px 0; border: 1px solid transparent; border-radius: 8px; }}
QListWidget#helpTopics::item:hover:!selected {{ background: {c['hover']}; }}
QListWidget#helpTopics::item:selected, QListWidget#helpTopics::item:selected:hover, QListWidget#helpTopics::item:selected:!active {{ background: {c['selection']}; color: {c['text']}; font-weight: 600; }}
QListWidget#helpTopics::item:focus {{ border-color: {c['accent']}; }}
QTextBrowser#helpContent {{ background: transparent; border: none; padding: 8px 12px; }}
QListWidget#sourceList {{ background: transparent; padding: 0; }}
QListWidget#sourceList::item {{ padding: 0; margin: 0 0 4px 0; }}
QTreeWidget, QTableWidget {{ background: {carrier}; alternate-background-color: {carrier}; border: none; border-radius: 0; gridline-color: transparent; outline: none; }}
QTreeWidget::item:selected {{ background: {c['selection']}; color: {c['text']}; }}
QTableWidget::item:selected, QTableWidget::item:selected:active, QTableWidget::item:selected:!active {{ background: transparent; color: {c['text']}; }}
QTreeWidget#libraryNavigation {{ background: transparent; border: none; border-radius: 0; outline: none; selection-background-color: transparent; selection-color: {c['text']}; }}
QTreeWidget#libraryNavigation::branch {{ background: transparent; border: none; border-image: none; image: none; }}
QTreeWidget#libraryNavigation::branch:selected, QTreeWidget#libraryNavigation::branch:selected:active, QTreeWidget#libraryNavigation::branch:hover, QTreeWidget#libraryNavigation::branch:has-children, QTreeWidget#libraryNavigation::branch:open, QTreeWidget#libraryNavigation::branch:closed {{ background: transparent; border: none; border-image: none; image: none; }}
QTreeWidget#libraryNavigation::item {{ height: 32px; padding: 0 10px; margin: 1px 8px; border-radius: 10px; color: {c['text']}; }}
QTreeWidget#libraryNavigation::item:hover {{ background: transparent; }}
QTreeWidget#libraryNavigation::item:selected, QTreeWidget#libraryNavigation::item:selected:active {{ background: transparent; color: {c['text']}; font-weight: 600; }}
QTreeWidget#libraryNavigation::item:focus {{ border: none; }}
QTableWidget::item {{ border: none; border-bottom: 1px solid {c['border']}; padding: 0 4px; color: {c['text']}; }}
QTableWidget::item:hover {{ background: transparent; }}
QTableWidget::item:selected, QTableWidget::item:focus {{ background: transparent; color: {c['text']}; border: none; border-bottom: 1px solid {c['border']}; outline: none; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: transparent; color: {c['muted']}; padding: 8px 4px; border: none; border-bottom: 1px solid {c['border']}; font-weight: 500; font-size: 13px; }}
QMainWindow QHeaderView::section {{ padding: 8px 4px; }}
QTextEdit#activity {{ font-size: 13px; color: {c['muted']}; border: none; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 10px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0,0,0,0), stop:0.42 rgba(0,0,0,0), stop:0.42 {c['border']}, stop:0.58 {c['border']}, stop:0.58 rgba(0,0,0,0), stop:1 rgba(0,0,0,0)); }}
QSplitter::handle:horizontal:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0,0,0,0), stop:0.42 rgba(0,0,0,0), stop:0.42 {c['muted']}, stop:0.58 {c['muted']}, stop:0.58 rgba(0,0,0,0), stop:1 rgba(0,0,0,0)); }}
QSplitter::handle:vertical {{ height: 10px; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,0), stop:0.42 rgba(0,0,0,0), stop:0.42 {c['border']}, stop:0.58 {c['border']}, stop:0.58 rgba(0,0,0,0), stop:1 rgba(0,0,0,0)); }}
QMenu {{ background: {sheet}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 12px; padding: 4px; font-size: 13px; font-weight: 500; }}
QMenu::item {{ padding: 6px 12px; margin: 1px 2px; border-radius: 10px; min-height: 20px; }}
QMenu::item:selected {{ background: {item_hover}; color: {c['text']}; border-radius: 8px; }}
QMenu::item:disabled {{ color: {c['faint']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}
QMenuBar {{ background: {c['window']}; color: {c['text']}; border: none; }}
QMenuBar::item {{ background: transparent; padding: 4px 8px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {c['hover']}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 4px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 4px; min-height: 32px; min-width: 32px; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; height: 0; width: 0; }}
QToolTip {{ background: {elevated}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 9px; padding: 9px 11px; font-size: 12px; font-weight: 400; opacity: {tooltip_opacity}; }}
"""


class Theme(QObject):
    def __init__(self, application, mode='system'):
        super().__init__(application)
        self.app = application
        previous = getattr(application, '_ilias_theme_manager', None)
        if previous is not None and isValid(previous):
            previous._active = False
            self.app.removeEventFilter(previous)
        application._ilias_theme_manager = self
        self._active = True
        self.mode = mode
        self.native_backdrop = uses_native_backdrop(application)
        self.app.setStyle('Fusion')
        self.hints = self.app.styleHints()
        self.accessibility = self.hints.accessibility()
        self.hints.colorSchemeChanged.connect(self.apply)
        self.accessibility.contrastPreferenceChanged.connect(lambda *_: self.apply())
        self.app.installEventFilter(self)
        self.apply()

    def eventFilter(self, watched, event):
        if self.native_backdrop and self._can_veil(watched):
            if event.type() == QEvent.Type.Polish:
                # Set client-area flags before Cocoa creates the window so Qt
                # can keep the pane frames in sync during a resize.
                hints = Qt.WindowType.ExpandedClientAreaHint | Qt.WindowType.NoTitleBarBackgroundHint
                if watched.windowFlags() & hints != hints:
                    watched.setWindowFlags(watched.windowFlags() | hints)
                watched.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            elif event.type() == QEvent.Type.Show and watched.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
                self._blur(watched)
        return super().eventFilter(watched, event)

    def _can_veil(self, widget):
        if not isinstance(widget, QWidget) or not widget.isWindow() or widget.__class__.__name__ == 'MotionMenu':
            return False
        return widget.__class__.__name__ == 'MainWindow' or widget.inherits('QDialog')

    def _blur(self, widget):
        from .native_compat import blur_window
        blur_window(int(widget.winId()), widget.palette().color(QPalette.ColorRole.Window).name())

    def set_mode(self, mode):
        self.mode = mode if mode in {'system', 'light', 'dark'} else 'system'
        self.apply()

    def apply(self, scheme=None):
        if not self._active:
            return
        scheme = scheme if isinstance(scheme, Qt.ColorScheme) else self.app.styleHints().colorScheme()
        dark = self.mode == 'dark' or (self.mode == 'system' and scheme == Qt.ColorScheme.Dark)
        c = DARK if dark else LIGHT
        self.high_contrast = self.accessibility.contrastPreference() == Qt.ContrastPreference.HighContrast
        if self.high_contrast:
            system = self.app.style().standardPalette()
            c = dict(c)
            for key, role in [('window', 'Window'), ('surface', 'Base'), ('elevated', 'Base'), ('card', 'Base'), ('field', 'Base'), ('inset', 'Window'), ('sidebar', 'Window'),
                              ('text', 'Text'), ('muted', 'Text'), ('faint', 'Text'), ('border', 'Text'), ('input_border', 'Text'), ('hover', 'AlternateBase'),
                              ('accent', 'Highlight'), ('accent_hover', 'Highlight'), ('on_accent', 'HighlightedText'), ('selection', 'Highlight'),
                              ('selected_text', 'HighlightedText'), ('error', 'Text'), ('error_fill', 'Text')]:
                c[key] = system.color(getattr(QPalette.ColorRole, role)).name()
        palette = QPalette()
        roles = {'Window':'window', 'WindowText':'text', 'Base':'window', 'AlternateBase':'inset',
                 'Text':'text', 'Button':'window', 'ButtonText':'text', 'Highlight':'accent',
                 'HighlightedText':'on_accent', 'ToolTipBase':'elevated', 'ToolTipText':'text',
                 'PlaceholderText':'muted', 'Link':'link' if 'link' in c else 'accent', 'Light':'border', 'Mid':'border', 'Dark':'inset'}
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
            for role, key in roles.items():
                color = c['disabled'] if group == QPalette.ColorGroup.Disabled and role in {'Text','WindowText','ButtonText'} else c[key]
                palette.setColor(group, getattr(QPalette.ColorRole, role), QColor(color))
        self.app.setPalette(palette)
        sheet = stylesheet(c, FROST if self.native_backdrop and not self.high_contrast else 1)
        scale = max(1.0, QFontInfo(self.app.font()).pixelSize() / 14)
        sheet = re.sub(r'font-size: (\d+)px', lambda match: f'font-size: {round(int(match[1]) * scale)}px', sheet)
        self.app.setStyleSheet(sheet)
        self.dark = dark
        if self.native_backdrop:
            for widget in self.app.topLevelWidgets():
                if self._can_veil(widget) and widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
                    self._blur(widget)
                    widget.update()
