"""Tests for display rendering."""

from custom_components.makerlink.display import View, fit, render


def test_idle():
    assert render(View()) == ("-MakerAustria-", "Karte bitte")


def test_priority_out_of_order_wins():
    assert render(View(out_of_order=True, admin=True, session_active=True))[0] == "AUSSER BETRIEB"


def test_countdown_line_fits():
    line1, line2 = render(View(shutdown_counter=59, user_name="Maximiliane Musterfrau"))
    assert line1 == "STOPPT:"
    assert len(line2) == 16 and line2.endswith("59s") and line2.startswith("Maximilian")


def test_active():
    assert render(View(session_active=True, user_name="Jürgen")) == ("EIN:", "Juergen")


def test_stop_screen_balance():
    assert render(View(stop_screen=3, balance=12.3)) == ("Schaltet aus", "Gut: 12.30 EUR")


def test_interlock():
    assert render(View(interlock_open=True))[0] == "TUER OFFEN"


def test_fit():
    assert fit("x" * 30) == "x" * 16
    assert fit("Größe") == "Groesse"
