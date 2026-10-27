from ilias_sync.i18n import message, set_language, t
from ilias_sync.policy import due, next_run


def test_course_names_and_file_names_are_not_interpreted_as_format_strings():
    set_language("de")
    assert message("Checking Mathe {A}") == "Prüfe Mathe {A}"
    assert message("Added: Set {a,b}.pdf") == "Neu: Set {a,b}.pdf"
    assert message("Downloading Set {a,b}.pdf") == "Lade Set {a,b}.pdf herunter"
    assert t("Prüfe {A}") == "Prüfe {A}"


def test_redacted_failure_has_an_action_in_both_languages():
    set_language("de")
    assert "Verbindung" in message("OSError: sync could not complete. Existing files were retained.")
    set_language("en")
    assert "try again" in message("OSError: sync could not complete. Existing files were retained.")
    set_language("de")


def test_native_interval_is_due_without_extra_jitter():
    next_time = next_run(6, clock=123)
    assert due({"next_run": next_time}, clock=123 + 6 * 3600)
