"""اختبار نمط الشخصية: 4 محاور، كل محور يُظهر نسبة قربك من كل جانب، ثم شخصيات أنمي من نفس النمط.

الأسئلة مكتوبة من الصفر لهذا البوت (لا تُنسخ من أي اختبار آخر). التقييم بسيط وشفاف:
كل سؤال يضيف/ينقص من محوره حسب الإجابة (1..5)، ثم تُحوَّل النتيجة إلى نسبة لكل جانب.
"""
from __future__ import annotations

import json
from functools import lru_cache

from aiogram import F, Router
from aiogram.types import CallbackQuery

from .bot import btn, kb
from .config import ROOT
from .names import loc
from .texts import t

# المحاور: (جانب A، جانب B) بالرموز والأسماء العربية والإنجليزية
AXES = [
    ("E", "I", "اجتماعي", "انطوائي", "Extrovert", "Introvert"),
    ("S", "N", "واقعي", "حدسي", "Sensing", "Intuitive"),
    ("T", "F", "منطقي", "عاطفي", "Thinking", "Feeling"),
    ("J", "P", "منظّم", "مرن", "Organized", "Flexible"),
]

# (المحور, +1 يعني الموافقة تميل لجانب A، -1 لجانب B, نص عربي, نص إنجليزي)
QUESTIONS = [
    (0, +1, "أشعر بالحماس وسط مجموعة كبيرة من الناس.", "I feel energized in a big group of people."),
    (0, -1, "أحتاج وقتًا وحدي لأستعيد طاقتي بعد يوم مزدحم.", "I need time alone to recharge after a busy day."),
    (0, +1, "أبدأ الحديث مع الغرباء بسهولة.", "I start conversations with strangers easily."),
    (0, -1, "أفضّل مجموعة صغيرة من الأصدقاء على حفلة كبيرة.", "I prefer a small group of friends over a big party."),
    (0, +1, "أعرف الكثير من الناس وأتواصل معهم بانتظام.", "I know many people and keep in regular touch."),
    (0, -1, "أفكّر كثيرًا قبل أن أتكلم في مجموعة جديدة.", "I think a lot before speaking in a new group."),
    (1, +1, "أركّز على الحقائق والتفاصيل الملموسة أكثر من الاحتمالات.", "I focus on concrete facts and details over possibilities."),
    (1, -1, "أحب التفكير في الأفكار المجردة والمستقبل البعيد.", "I enjoy thinking about abstract ideas and the distant future."),
    (1, +1, "أثق بما جربته بنفسي أكثر مما أسمعه من النظريات.", "I trust what I've tried myself more than what I hear in theories."),
    (1, -1, "أستمتع بالبحث عن المعاني الخفية والرموز.", "I enjoy looking for hidden meanings and symbols."),
    (1, +1, "أفضّل التعليمات الواضحة خطوة بخطوة.", "I prefer clear step-by-step instructions."),
    (1, -1, "أتخيّل احتمالات مختلفة للموقف قبل أن يحدث.", "I imagine different possibilities before a situation happens."),
    (2, +1, "أتخذ قراراتي بالمنطق قبل المشاعر.", "I make decisions with logic before feelings."),
    (2, -1, "أراعي مشاعر الناس قبل أن أقول رأيي الصريح.", "I consider people's feelings before giving my blunt opinion."),
    (2, +1, "أرى أن الصدق الكامل أهم من تجنب إزعاج أحد.", "I think full honesty matters more than avoiding upsetting someone."),
    (2, -1, "أتأثر كثيرًا بقصص الناس وأحاول مساعدتهم.", "I'm deeply moved by people's stories and try to help them."),
    (2, +1, "أقيّم الأفكار بموضوعية ولا يهمني كثيرًا من قالها.", "I judge ideas objectively, regardless of who said them."),
    (2, -1, "أهتم بانسجام الفريق أكثر من الفوز بالنقاش.", "I care about team harmony more than winning an argument."),
    (3, +1, "أحب وضع خطة واضحة ثم أتبعها.", "I like making a clear plan and sticking to it."),
    (3, -1, "أفضّل ترك الأمور مفتوحة لأرى ما يحدث.", "I prefer leaving things open to see what happens."),
    (3, +1, "أنهي مهامي قبل مواعيدها بوقت كافٍ.", "I finish my tasks well before their deadlines."),
    (3, -1, "أعمل بشكل أفضل تحت ضغط الوقت القريب.", "I work best under close deadline pressure."),
    (3, +1, "أرتاح عندما تكون الأمور مرتبة ومحسومة.", "I feel at ease when things are organized and settled."),
    (3, -1, "أغيّر خططي بسهولة إذا ظهر خيار أفضل.", "I change my plans easily when a better option shows up."),

(0, +1, "أستمتع بالتعرف على أشخاص جدد في المناسبات.", "I enjoy meeting new people at events."),
    (0, -1, "أفضّل أن أتابع الحديث بعمق مع شخص واحد على أن أتنقل بين الجميع.", "I prefer deep talks with one person over mingling with everyone."),
    (1, +1, "أنتبه للتفاصيل الصغيرة التي يفوتها غيري.", "I notice small details others miss."),
    (1, -1, "أفكر كثيرًا في الصورة الكبيرة والأهداف البعيدة.", "I think a lot about the big picture and long-term goals."),
    (2, +1, "أحلل الخطأ بدقة لأعرف سببه قبل أن أهتم بمشاعر من ارتكبه.", "I analyze a mistake carefully to find its cause before worrying about feelings."),
    (2, -1, "أحس بالضيق عندما يتجاهل أحد مشاعر من حوله.", "I feel upset when someone ignores others' feelings."),
    (3, +1, "أحب أن تكون قائمة مهامي واضحة ومرتبة كل يوم.", "I like my to-do list to be clear and organized every day."),
    (3, -1, "أستمتع بالعفوية وأقرر في اللحظة ما أفعله.", "I enjoy spontaneity and decide what to do in the moment."),
    (0, +1, "أشعر بالراحة عندما أكون محاطًا بالناس طوال اليوم.", "I feel comfortable when surrounded by people all day."),
    (0, -1, "أشعر بالإرهاق سريعًا في الاجتماعات الطويلة.", "I get tired quickly in long social gatherings."),
    (1, +1, "أثق بالتجربة الواقعية أكثر من الأفكار النظرية.", "I trust real-world experience more than theoretical ideas."),
    (1, -1, "أحب اكتشاف الأنماط والعلاقات الخفية بين الأشياء.", "I love discovering hidden patterns and connections between things."),
    (2, +1, "أفضّل النقد المباشر الواضح على المجاملة.", "I prefer direct, clear criticism over politeness."),
    (2, -1, "أبحث عن الحل الذي يرضي الجميع حتى لو لم يكن الأدق.", "I look for a solution that pleases everyone, even if it isn't the most accurate."),
    (3, +1, "أكره ترك الأمور معلّقة دون قرار.", "I hate leaving things hanging without a decision."),
    (3, -1, "أستطيع التعايش مع الفوضى إذا كانت النتيجة جيدة.", "I can live with some mess if the outcome is good."),
]

# ترتيب العرض: محاور متداخلة حتى لا تتتابع أسئلة المحور نفسه
M = len(QUESTIONS) // 4                       # أسئلة لكل محور
_buckets = [[i for i, q in enumerate(QUESTIONS) if q[0] == a] for a in range(4)]
ORDER = [_buckets[a][k] for k in range(M) for a in range(4)]   # محاور متداخلة حتى لا تتتابع أسئلة المحور نفسه
N = len(QUESTIONS)


def compute(answers: str) -> dict:
    """answers: أرقام 1..5 بنفس ترتيب ORDER. يرجع النسب لكل محور ونمط الحروف."""
    raw = [0.0] * 4
    for pos, ch in enumerate(answers):
        qi = ORDER[pos]
        axis, sign, _, _ = QUESTIONS[qi]
        raw[axis] += sign * (int(ch) - 3)
    res = []
    for axis, (a, b, *_rest) in enumerate(AXES):
        pct_a = max(0, min(100, round(50 + raw[axis] / (2 * M) * 50)))   # كل سؤال أقصى ±2
        res.append({"a": a, "b": b, "pct_a": pct_a, "pct_b": 100 - pct_a,
                    "letter": a if pct_a >= 50 else b})
    return {"axes": res, "code": "".join(x["letter"] for x in res)}


@lru_cache(maxsize=1)
def anime_by_type() -> dict:
    try:
        return json.loads((ROOT / "data" / "personality_anime.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def bar(pct: int, n: int = 10) -> str:
    k = round(pct / 100 * n)
    return "▰" * k + "▱" * (n - k)


def question_text(pos: int, L: str) -> str:
    qi = ORDER[pos]
    _, _, ar, en = QUESTIONS[qi]
    return t(L, "ps_q", n=pos + 1, total=N, q=(ar if L == "ar" else en))


def question_markup(ans: str, L: str):
    row = [btn(str(i), f"pa:{ans}{i}") for i in range(1, 6)]
    rows = [row]
    if ans:
        rows.append([btn(t(L, "ps_back"), f"pb:{ans[:-1]}")])
    rows.append([btn(t(L, "btn_games_menu"), "m:games"), btn(t(L, "btn_menu"), "menu")])
    return kb(*rows)


def result_text(ans: str, uid_lang: str) -> str:
    L = uid_lang
    r = compute(ans)
    lines = [t(L, "ps_res_head", code=r["code"])]
    for idx, ax in enumerate(r["axes"]):
        name_a = AXES[idx][2 if L == "ar" else 4]
        name_b = AXES[idx][3 if L == "ar" else 5]
        lines.append(f"<b>{name_a}</b> {ax['pct_a']}%  {bar(ax['pct_a'])}  {ax['pct_b']}% <b>{name_b}</b>")
        lines.append(t(L, "ps_closer", side=name_a if ax["pct_a"] >= 50 else name_b,
                       pct=max(ax["pct_a"], ax["pct_b"])))
    names = anime_by_type().get(r["code"], [])
    if names:
        lines.append("")
        lines.append(t(L, "ps_anime_head", code=r["code"]))
        for i, item in enumerate(names[:10], 1):
            name, series = item[0], item[1]
            shown = loc(name, L) if L == "ar" else name
            lines.append(f"{i}. {shown} <i>({series})</i>")
    else:
        lines.append(t(L, "ps_anime_soon"))
    return "\n".join(lines)


def build_persona_router(ctx) -> Router:
    r = Router(name="persona")
    r.callback_query.filter(F.message.chat.type == "private")
    db = ctx.db

    def lang(uid: int) -> str:
        return db.get_lang(uid)

    @r.callback_query(F.data == "ps:s")
    async def start(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        await c.message.answer(t(L, "ps_intro", n=N), parse_mode="HTML", reply_markup=kb([btn(t(L, "ps_go"), "pa:")]))

    @r.callback_query(F.data.regexp(r"^pa:[1-5]{0,40}$"))
    async def answer(c: CallbackQuery):
        L = lang(c.from_user.id)
        ans = c.data[3:]
        if len(ans) >= N:
            await c.answer()
            await c.message.answer(result_text(ans, L), parse_mode="HTML", reply_markup=kb(
                [btn(t(L, "ps_again"), "pa:")], [btn(t(L, "btn_games_menu"), "m:games"), btn(t(L, "btn_menu"), "menu")]))
            return
        await c.answer()
        pos = len(ans)
        try:
            await c.message.edit_text(question_text(pos, L), parse_mode="HTML", reply_markup=question_markup(ans, L))
        except Exception:  # noqa: BLE001
            await c.message.answer(question_text(pos, L), parse_mode="HTML", reply_markup=question_markup(ans, L))

    @r.callback_query(F.data.regexp(r"^pb:[1-5]{0,39}$"))
    async def back(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        ans = c.data[3:]
        try:
            await c.message.edit_text(question_text(len(ans), L), parse_mode="HTML", reply_markup=question_markup(ans, L))
        except Exception:  # noqa: BLE001
            await c.message.answer(question_text(len(ans), L), parse_mode="HTML", reply_markup=question_markup(ans, L))
    return r
