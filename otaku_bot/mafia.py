"""منطق لعبة المافيا (بطابع أنمي): توزيع الأدوار، الليل، التصويت، وشروط الفوز.

هذا الجزء نقي (بلا تليجرام) لتسهيل اختباره؛ الرسائل الخاصة والأزرار تأتي فوقه لاحقًا.
القواعد:
• المضيف يحدد عدد القتلة (≥1). المواطنون العاديون (غير القتلة والأدوار الخاصة) ≥ 3.
• الأدوار الخاصة (محقق، طبيب، حارس، مجنون) فريدة: لا يحملها لاعبان. القاتل وحده يتكرر.
• البداية: القتلة أقل من غيرهم، حتى لا يفوز القتلة من أول لحظة.
• الليل: القتلة يختارون ضحية واحدة. الطبيب والحارس يحميان، والمحقق يكشف فريقًا.
• النهار: تصويت بالأغلبية المطلقة لطرد لاعب. التعادل = لا طرد.
• الفوز: المواطنون إن لم يبق قاتل. القتلة إن تساووا مع غيرهم أو تفوّقوا. المجنون يفوز وحده إذا طُرد بالتصويت.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

TOWN = "town"
MAFIA = "mafia"
SOLO = "solo"

# الدور: (المفتاح, الاسم العربي, الفريق)
ROLES = {
    "citizen": ("مواطن", TOWN),
    "killer": ("القاتل", MAFIA),
    "detective": ("المحقق", TOWN),
    "doctor": ("الطبيب", TOWN),
    "guard": ("الحارس", TOWN),
    "joker": ("المجنون", SOLO),
}
SPECIAL = ("detective", "doctor", "guard", "joker")   # فريدة: لا يتكرر أي منها
MIN_CITIZENS = 3
MIN_PLAYERS = 5
MAX_PLAYERS = 15


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    killers: int
    specials: list[str] = field(default_factory=list)

    def validate(self, n_players: int) -> None:
        if not MIN_PLAYERS <= n_players <= MAX_PLAYERS:
            raise ConfigError(f"عدد اللاعبين لازم يكون بين {MIN_PLAYERS} و{MAX_PLAYERS}")
        if self.killers < 1:
            raise ConfigError("لازم قاتل واحد على الأقل")
        for r in self.specials:
            if r not in SPECIAL:
                raise ConfigError(f"دور غير معروف: {r}")
        if len(set(self.specials)) != len(self.specials):
            raise ConfigError("ما ينفع يكون في اثنين عندهم نفس الدور الخاص")
        citizens = n_players - self.killers - len(self.specials)
        if citizens < MIN_CITIZENS:
            raise ConfigError(f"لازم يكون في {MIN_CITIZENS} مواطنين على الأقل (الآن {max(citizens, 0)})")
        if self.killers >= n_players - self.killers:
            raise ConfigError("عدد القتلة لازم يكون أقل من بقية اللاعبين، وإلا يفوز القتلة من البداية")


def auto_config(n_players: int) -> tuple[int, list[str]]:
    """إعداد تلقائي حسب عدد اللاعبين: عدد القتلة والأدوار الخاصة، ويمرّ دائمًا من التحقق."""
    n = max(MIN_PLAYERS, min(MAX_PLAYERS, n_players))
    killers = 1 if n <= 6 else 2 if n <= 8 else 3 if n <= 11 else 4
    specials = ["detective"] if n >= 6 else []
    if n >= 7:
        specials.append("doctor")
    if n >= 9:
        specials.append("guard")
    if n >= 12:
        specials.append("joker")
    Config(killers=killers, specials=specials).validate(n)
    return killers, specials


def assign(player_ids: list[int], cfg: Config, rng: random.Random) -> dict[int, str]:
    """يوزّع الأدوار عشوائيًا. يرجع {uid: role_key}."""
    cfg.validate(len(player_ids))
    ids = list(player_ids)
    rng.shuffle(ids)
    roles: dict[int, str] = {}
    for uid in ids[: cfg.killers]:
        roles[uid] = "killer"
    rest = ids[cfg.killers:]
    for uid, role in zip(rest, cfg.specials):
        roles[uid] = role
    for uid in rest[len(cfg.specials):]:
        roles[uid] = "citizen"
    return roles


@dataclass
class Night:
    """أفعال الليل: كل قيمة هي uid الهدف، أو None إن لم يتصرف صاحب الدور."""
    kill: int | None = None           # ما اتفق عليه القتلة (الأغلبية أو الأول)
    protect: dict[str, int] = field(default_factory=dict)   # {"doctor": uid, "guard": uid}
    check: int | None = None          # المحقق يكشف فريق هذا الهدف


@dataclass
class Result:
    victim: int | None                 # من مات في الليل (None = لا أحد)
    saved: bool = False                # هل أنقذه الطبيب أو الحارس
    detective: tuple[int, str] | None = None   # (الهدف، الفريق) لو كشف المحقق


def resolve_night(roles: dict[int, str], alive: set[int], night: Night) -> Result:
    kill = night.kill if night.kill in alive else None
    protected = {night.protect.get(r) for r in ("doctor", "guard")} - {None}
    victim = None
    saved = False
    if kill is not None:
        if kill in protected:
            saved = True
        else:
            victim = kill
    det = None
    if night.check in alive and roles.get(night.check) is not None:
        det = (night.check, ROLES[roles[night.check]][1])
    return Result(victim=victim, saved=saved, detective=det)


def vote(alive: set[int], ballots: dict[int, int]) -> int | None:
    """ballots = {voter: target}. يطرد الهدف إن حصل على أغلبية مطلقة من الأحياء. وإلا لا طرد."""
    counts: dict[int, int] = {}
    for voter, target in ballots.items():
        if voter in alive and target in alive and target != voter:
            counts[target] = counts.get(target, 0) + 1
    if not counts:
        return None
    target, votes = max(counts.items(), key=lambda kv: kv[1])
    if votes * 2 > len(alive):
        return target
    return None


def winner(roles: dict[int, str], alive: set[int], last_voted: str | None = None) -> str | None:
    """يرجع الفريق الفائز أو None لاستمرار اللعبة.
    last_voted: مفتاح دور الطرد الأخير (إن كان المجنون فيفوز وحده)."""
    if last_voted == "joker":
        return SOLO
    killers = [u for u in alive if roles.get(u) == "killer"]
    others = [u for u in alive if roles.get(u) != "killer" and roles.get(u) != "joker"]
    if not killers:
        return TOWN
    if len(killers) >= len(others):
        return MAFIA
    return None
