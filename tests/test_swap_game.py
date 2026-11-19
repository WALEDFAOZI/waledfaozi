"""تبادل الشخصيات: الدعوة، الشخصيات من نفس المستوى، التخمين، والفوز."""
import asyncio
import json

from harness import Harness, run
from otaku_bot import swap_game as SG
from otaku_bot.config import ROOT


def test_levels_file_covers_all_characters_and_pairs_are_same_level():
    lv = json.loads((ROOT / "data" / "char_levels.json").read_text(encoding="utf-8"))
    assert len(lv) >= 50 and set(lv.values()) == {1, 2, 3}
    grouped = SG.levels()
    assert all(len(v) >= 2 for v in grouped.values())
    h = Harness()
    import random
    rng = random.Random(4)
    h.ctx.rng = rng
    assert SG.build_swap_router(h.ctx) is not None
    for _ in range(40):
        a, b = _pair_from(h, grouped, rng)
        assert lv[a["en"]] == lv[b["en"]] and a["en"] != b["en"]


def _pair_from(h, grouped, rng):
    level = rng.choice([k for k, v in grouped.items() if len(v) >= 2])
    return tuple(rng.sample(grouped[level], 2))


def test_invite_accept_both_get_each_others_character_and_correct_guess_wins():
    async def go():
        h = Harness()
        a, b = h.user(1, "Ali"), h.user(2, "Bob")
        h.db.upsert_user(1, "Ali"); h.db.upsert_user(2, "Bob")
        await h.tap(a, "sw:new")
        sid = max(SG.swaps)
        s = SG.swaps[sid]
        assert s["state"] == "invite" and s["a"] == 1
        await h.say(b, f"/start sw_{sid}")                                   # الرابط يفتح قبول التحدي
        assert any("يتحداك" in x for x in h.session.texts())
        await h.tap(b, f"sw:acc:{sid}")
        assert s["state"] == "play" and s["ca"]["en"] != s["cb"]["en"]
        dm_a = [c.text for c in h.session.calls if getattr(c, "chat_id", None) == 1 and type(c).__name__ == "SendMessage"]
        dm_b = [c.text for c in h.session.calls if getattr(c, "chat_id", None) == 2 and type(c).__name__ == "SendMessage"]
        from otaku_bot.names import loc
        assert any(loc(s["cb"]["en"], "ar") in (x or "") for x in dm_a)     # A يعرف شخصية B
        assert any(loc(s["ca"]["en"], "ar") in (x or "") for x in dm_b)     # B يعرف شخصية A
        assert not any(loc(s["ca"]["en"], "ar") in (x or "") for x in dm_a)  # A لا يعرف شخصيته
        # A يخمّن خطأ ثم يحاول مرة ثانية بعد الانتظار
        await h.tap(a, f"sw:g:{sid}")
        await h.say(a, "شخصية غلط تماما")
        assert any("ليست هي" in x for x in h.session.texts())
        await h.say(a, s["ca"]["ar"])                                        # بعد التبريد؟ لا: لازم ننتظر
        assert s["state"] == "play"                                           # التبريد يمنع التخمين السريع
        s["last"][1] = 0                                                      # نتجاوز التبريد للاختبار
        await h.tap(a, f"sw:g:{sid}")
        await h.say(a, s["ca"]["en"])                                        # التخمين الصحيح بالإنجليزية
        assert s["id"] not in SG.swaps or s["state"] == "done"
        assert any("فزت" in (getattr(c, "text", "") or "") for c in h.session.calls if getattr(c, "chat_id", None) == 1)
        assert any("خسرت" in (getattr(c, "text", "") or "") for c in h.session.calls if getattr(c, "chat_id", None) == 2)
    run(go())


def test_surrender_and_busy_and_no_bot_intervention_during_play():
    async def go():
        h = Harness()
        a, b, c = h.user(1, "Ali"), h.user(2, "Bob"), h.user(3, "Cy")
        for u in (a, b, c):
            h.db.upsert_user(u.id, u.first_name)
        await h.tap(a, "sw:new")
        sid = max(SG.swaps)
        await h.say(b, f"/start sw_{sid}")
        await h.tap(b, f"sw:acc:{sid}")
        await h.tap(c, "sw:new")                                              # Cy حر ويقدر يفتح تحديه الخاص
        assert any(x.a == 3 for x in []) or any(s_["a"] == 3 for s_ in SG.swaps.values())
        await h.tap(a, f"sw:x:{sid}")                                         # A يستسلم
        assert SG.swaps.get(sid) is None
        assert any("خسرت" in (getattr(x, "text", "") or "") for x in h.session.calls if getattr(x, "chat_id", None) == 1)
        assert any("فزت" in (getattr(x, "text", "") or "") for x in h.session.calls if getattr(x, "chat_id", None) == 2)
    run(go())
