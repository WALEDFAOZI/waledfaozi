"""اختبار نمط الشخصية: 4 محاور، كل محور يُظهر نسبة قربك من كل جانب، ثم شخصيات أنمي من نفس النمط.

الأسئلة مكتوبة من الصفر لهذا البوت (لا تُنسخ من أي اختبار آخر). التقييم بسيط وشفاف:
كل سؤال يضيف/ينقص من محوره حسب الإجابة (1..5)، ثم تُحوَّل النتيجة إلى نسبة لكل جانب.
"""
from __future__ import annotations

import json
import random
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
    (0, +1, "أحب أن أكون في قلب الحدث حين يكون هناك جمع من الناس.", "I like being at the center of the action when a crowd gathers."),
    (0, -1, "أتعب من الثرثرة الكثيرة وأفضّل الصمت المريح.", "I get tired of too much chatter and prefer comfortable silence."),
    (0, +1, "أتكلم بحرية أمام من لا أعرفه.", "I speak freely in front of people I don't know."),
    (0, -1, "أستمتع بالوقت الهادئ أكثر من الأمسيات الصاخبة.", "I enjoy quiet time more than loud evenings."),
    (0, +1, "أبادر بالدعوة إلى لقاء أو نشاط جماعي.", "I take the initiative to invite people to a gathering or activity."),
    (0, -1, "أشعر أن المكالمات الجماعية تستنزفني.", "Group calls drain my energy."),
    (0, +1, "أجد متعة في تعريف الناس ببعضهم في المناسبات.", "I enjoy introducing people to each other at events."),
    (0, -1, "أفضّل الرسائل الهادئة على اللقاءات المفاجئة.", "I prefer calm messages over surprise meetups."),
    (0, +1, "أشعر بالنشاط بعد لقاء اجتماعي طويل.", "I feel energized after a long social meeting."),
    (0, -1, "أحتاج أن أنسحب من المكان المزدحم بعد فترة قصيرة.", "I need to step away from a crowded place after a short while."),
    (1, +1, "أنجذب إلى الوصفات والإجراءات المجربة التي تعطي نتيجة معروفة.", "I'm drawn to tested methods that give a known result."),
    (1, -1, "أتحمس للفكرة الجديدة التي لم يجربها أحد بعد.", "I get excited about a new idea nobody has tried yet."),
    (1, +1, "أحب أن أرى الأرقام والدلائل قبل أن أصدّق شيئًا.", "I like seeing numbers and evidence before I believe something."),
    (1, -1, "أفكر في ما يمكن أن يتحقق لاحقًا أكثر من النتائج الحالية.", "I think about what could happen later more than current results."),
    (1, +1, "أفضّل العمل على المشاريع الملموسة التي أرى نتائجها.", "I prefer working on tangible projects whose results I can see."),
    (1, -1, "أجد الرموز والاستعارات في الفنون أكثر إثارة من الشرح المباشر.", "Symbols and metaphors in art excite me more than direct explanations."),
    (1, +1, "أتابع التفاصيل الصغيرة للعمل حتى أنتهي منه بدقة.", "I follow small details of a task until I finish it accurately."),
    (1, -1, "أجد نفسي أحلم بعوالم وأفكار بعيدة عن الواقع.", "I catch myself daydreaming about worlds and ideas far from reality."),
    (1, +1, "أفضّل أن أعرف الواقع كما هو بدل أن أتخيله.", "I'd rather know reality as it is than imagine it."),
    (1, -1, "أحب الأسئلة التي لا جواب واضح لها.", "I love questions that have no clear answer."),
    (2, +1, "أحترم الحكم المنطقي حتى لو كان قاسيًا.", "I respect logical judgment even when it's harsh."),
    (2, -1, "ألاحظ تأثير قراري على الناس قبل أي شيء آخر.", "I notice how my decision affects people before anything else."),
    (2, +1, "أفضّل الحجة القوية على الكلام اللطيف.", "I prefer a strong argument over gentle words."),
    (2, -1, "أحاول أن أجعل الجميع يشعرون بالتقدير حتى في الخلاف.", "I try to make everyone feel valued even during a disagreement."),
    (2, +1, "أرى أن النتائج الواقعية تُحكم بها الأمور أكثر من النوايا.", "I judge matters by real results more than by intentions."),
    (2, -1, "أتأثر بسرعة بالكلام الذي يلمس قلبي.", "I'm quickly moved by words that touch my heart."),
    (2, +1, "أتجاوز المشاعر في العمل لأصل إلى النتيجة الصحيحة.", "I set feelings aside at work to reach the right result."),
    (2, -1, "أحس بالذنب إذا جرحت أحدًا دون قصد.", "I feel guilty if I hurt someone without meaning to."),
    (2, +1, "أفضّل تحليل المشكلة بهدوء قبل أن أحكم على أحد.", "I prefer to calmly analyze a problem before judging anyone."),
    (2, -1, "أتفهّم الدوافع الإنسانية حتى عندما تكون خاطئة.", "I understand human motives even when they're wrong."),
    (3, +1, "أكره أن أبدأ عملًا دون أن أعرف كيف سينتهي.", "I hate starting a task without knowing how it will end."),
    (3, -1, "أفضّل أن أقرر بعد أن تتضح الظروف، لا قبلها.", "I prefer to decide once the circumstances are clear, not before."),
    (3, +1, "أشعر بالراحة عندما أنهي الأشياء وأغلقها بالكامل.", "I feel relieved when I fully finish and close things."),
    (3, -1, "أستمتع بتأجيل القرار حتى اللحظة الأخيرة لأرى الخيارات.", "I enjoy delaying decisions until the last moment to see the options."),
    (3, +1, "أضع لنفسي مواعيد واضحة وألتزم بها.", "I set clear deadlines for myself and stick to them."),
    (3, -1, "أغيّر اتجاهي بسرعة إذا تغيّرت المعطيات.", "I change direction quickly when the facts change."),
    (3, +1, "أحب أن أعرف ما سيحدث في يومي قبل أن يبدأ.", "I like knowing what will happen in my day before it starts."),
    (3, -1, "أترك لنفسي مساحة للتجربة دون خطة محددة.", "I leave myself room to experiment without a fixed plan."),
    (3, +1, "أتابع جدولي وأعيد ترتيبه عند الحاجة.", "I follow my schedule and rearrange it when needed."),
    (3, -1, "أفضّل أن أترك القرار للحظة التي تأتي فيها الفكرة.", "I prefer to leave the decision to the moment the idea comes."),
]

# كل اختبار يعرض 30 سؤالًا من البنك (80). الاختيار يعتمد على "بذرة" (0..9) يحملها الزر،
# فيختلف الاختبار من مرة لأخرى مع بقائه متوازنًا بين المحاور وبين الجانبين.
SHOW = 30


def order_for(seed: int) -> list[int]:
    rng = random.Random(seed * 7919 + 13)
    buckets = []
    for axis in range(4):
        pos = [i for i, q in enumerate(QUESTIONS) if q[0] == axis and q[1] > 0]
        neg = [i for i, q in enumerate(QUESTIONS) if q[0] == axis and q[1] < 0]
        rng.shuffle(pos)
        rng.shuffle(neg)
        mixed = []
        for x, y in zip(pos, neg):
            mixed += [x, y]
        buckets.append(mixed)
    order = []
    for k in range(max(len(x) for x in buckets)):
        for axis in range(4):
            if k < len(buckets[axis]):
                order.append(buckets[axis][k])
    # نأخذ من كل محور عددًا متساويًا تقريبًا، ثم نرتّب التناوب بين المحاور
    picked = order[:SHOW]
    rng.shuffle(picked)
    return picked


ORDER = order_for(0)
N = SHOW


def compute(answers: str, seed: int = 0) -> dict:
    """answers: أرقام 1..5 بنفس ترتيب order_for(seed). يرجع النسب لكل محور ونمط الحروف."""
    order = order_for(seed)
    raw = [0.0] * 4
    count = [0] * 4
    for pos, ch in enumerate(answers):
        qi = order[pos]
        axis, sign, _, _ = QUESTIONS[qi]
        raw[axis] += sign * (int(ch) - 3)
        count[axis] += 1
    res = []
    for axis, (a, b, *_rest) in enumerate(AXES):
        denom = 2 * max(1, sum(1 for i in order if QUESTIONS[i][0] == axis))
        pct_a = max(0, min(100, round(50 + raw[axis] / denom * 50)))
        res.append({"a": a, "b": b, "pct_a": pct_a, "pct_b": 100 - pct_a,
                    "letter": a if pct_a >= 50 else b})
    return {"axes": res, "code": "".join(x["letter"] for x in res)}


@lru_cache(maxsize=1)
def anime_by_type() -> dict:
    try:
        return json.loads((ROOT / "data" / "personality_anime.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


PERSONA_KEY = "persona:{uid}"


def saved_type(db, uid: int) -> str | None:
    return db.get_setting(PERSONA_KEY.format(uid=uid)) or None


def profile_lines(db, uid: int, L: str, top: int = 5) -> list[str]:
    """أسطر النمط في الملف الشخصي: النمط المحفوظ، وشخصيات من نفس النمط."""
    code = saved_type(db, uid)
    if not code:
        return []
    out = [t(L, "pf_persona", code=code)]
    names = anime_by_type().get(code, [])[:top]
    if names:
        out.append(t(L, "pf_persona_same"))
        for item in names:
            shown = loc(item[0], L) if L == "ar" else item[0]
            out.append(f"• {shown} <i>({item[1]})</i>")
    return out


def bar(pct: int, n: int = 10) -> str:
    k = round(pct / 100 * n)
    return "▰" * k + "▱" * (n - k)


def question_text(pos: int, L: str, seed: int = 0) -> str:
    qi = order_for(seed)[pos]
    _, _, ar, en = QUESTIONS[qi]
    return t(L, "ps_q", n=pos + 1, total=N, q=(ar if L == "ar" else en))


def question_markup(seed: int, ans: str, L: str):
    row = [btn(str(i), f"pa:{seed}{ans}{i}") for i in range(1, 6)]
    rows = [row]
    if ans:
        rows.append([btn(t(L, "ps_back"), f"pb:{seed}{ans[:-1]}")])
    rows.append([btn(t(L, "btn_games_menu"), "m:games"), btn(t(L, "btn_menu"), "menu")])
    return kb(*rows)


def result_text(seed: int, ans: str, uid_lang: str) -> str:
    L = uid_lang
    r = compute(ans, seed)
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
        seed = random.randrange(10)
        await c.message.answer(t(L, "ps_intro", n=N), parse_mode="HTML",
                               reply_markup=kb([btn(t(L, "ps_go"), f"pa:{seed}")]))

    @r.callback_query(F.data.regexp(r"^pa:\d[1-5]{0,%d}$" % (N)))
    async def answer(c: CallbackQuery):
        L = lang(c.from_user.id)
        seed, ans = int(c.data[3]), c.data[4:]
        await c.answer()
        if len(ans) >= N:
            code = compute(ans, seed)["code"]
            db.set_setting(PERSONA_KEY.format(uid=c.from_user.id), code)     # يُحفظ في الملف الشخصي
            await c.message.answer(result_text(seed, ans, L) + "\n\n" + t(L, "ps_saved"), parse_mode="HTML", reply_markup=kb(
                [btn(t(L, "ps_again"), "ps:s")], [btn(t(L, "btn_games_menu"), "m:games"), btn(t(L, "btn_menu"), "menu")]))
            return
        pos = len(ans)
        try:
            await c.message.edit_text(question_text(pos, L, seed), parse_mode="HTML", reply_markup=question_markup(seed, ans, L))
        except Exception:  # noqa: BLE001
            await c.message.answer(question_text(pos, L, seed), parse_mode="HTML", reply_markup=question_markup(seed, ans, L))

    @r.callback_query(F.data.regexp(r"^pb:\d[1-5]{0,%d}$" % (N - 1)))
    async def back(c: CallbackQuery):
        await c.answer()
        L = lang(c.from_user.id)
        seed, ans = int(c.data[3]), c.data[4:]
        try:
            await c.message.edit_text(question_text(len(ans), L, seed), parse_mode="HTML", reply_markup=question_markup(seed, ans, L))
        except Exception:  # noqa: BLE001
            await c.message.answer(question_text(len(ans), L, seed), parse_mode="HTML", reply_markup=question_markup(seed, ans, L))
    return r
