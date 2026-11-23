"""لعبة «كت»: الكلمة تعطي سؤالًا، والزر يعطي غيره، والبنك فيه 1000 سؤال، ولا يتكرر حتى يُستنفد."""
import random

from harness import Harness, run
from otaku_bot import kt


def test_bank_has_1000_unique_bilingual_questions():
    qs = kt.questions()
    assert len(qs) == 1000
    assert len({q["ar"] for q in qs}) == 1000
    assert all(q["ar"] and q["en"] for q in qs)


def test_no_repeats_until_the_bank_is_used_up_then_it_restarts():
    qs = kt.questions()
    rng = random.Random(7)
    seen: set = set()
    first_round = [kt.next_question(qs, seen, rng)["id"] for _ in range(len(qs))]
    assert len(set(first_round)) == len(qs)                    # كل الأسئلة مرة واحدة دون تكرار
    again = kt.next_question(qs, seen, rng)                    # بعدها يبدأ من جديد
    assert again is not None and len(seen) == 1


def test_kt_word_sends_a_question_and_button_gives_a_different_one():
    async def go():
        h = Harness()
        h.db.fast_answer_ratio = lambda sid: 0.0
        u = h.user(71, "Ali")
        h.db.upsert_user(u.id, u.first_name)
        await h.say(u, "كت")
        first = h.session.texts()[-1]
        assert "كت" in first and "\n" not in first.strip()          # رسالة قصيرة في سطر واحد
        sent = [c for c in h.session.calls if type(c).__name__ == "SendMessage" and c.chat_id == u.id][-1]
        assert sent.reply_parameters is not None                    # ترد على رسالة الشخص
        assert sent.reply_markup is None                            # بلا زر تحتها
    run(go())
