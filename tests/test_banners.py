"""لافتة كل لعبة تحمل عنوانها: كل أنواع المجموعات لها عنوان، ويُرسم بانر بعنوان لعبة محددة."""
from otaku_bot import card, live
from otaku_bot.group import KINDS


def test_every_game_type_has_a_banner_title():
    for kind in KINDS:
        assert kind in live.TITLES, kind
        ar, en = live.TITLES[kind]
        assert ar and en
    assert live.TITLES["mafia"][0] == "المافيا" and live.TITLES["spy"][0] == "برا السالفة"


def test_banner_renders_with_the_game_title():
    png = card.make_banner("ar", "@x", "المافيا", "MAFIA")
    assert png[:2] == b"\xff\xd8" and len(png) > 10_000        # JPEG صالح
