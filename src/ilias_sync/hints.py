"""Short, escaped hover help for controls whose purpose needs explanation."""
from html import escape


def hint_text(title, detail=''):
    heading = '<b>' + escape(title) + '</b>'
    if not detail:
        return '<qt>' + heading + '</qt>'
    return ('<qt><table width="280" cellspacing="0" cellpadding="0"><tr><td>'
            + heading + '<br>' + escape(detail).replace('\n', '<br>') + '</td></tr></table></qt>')


def set_hint(widget, title, detail=''):
    widget.setProperty('helpHint', True)
    widget.setToolTip(hint_text(title, detail))
    if detail:
        widget.setAccessibleDescription('' if detail == widget.accessibleName() else detail)
