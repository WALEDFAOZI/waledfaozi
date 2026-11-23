"""نصوص الواجهة بالعربية والإنجليزية."""
from __future__ import annotations

import random

from .config import CATEGORY_LABELS, CATEGORY_LABELS_EN

T: dict[str, dict[str, str]] = {
"ar": {
 "welcome": "أهلًا بك في <b>بوت اختبار الأوتاكو</b> 🎌\n\nاختبر معرفتك بالأنمي: أكثر من <b>1400 سؤال</b> من الأسهل للأصعب، وألعاب، وتحدٍّ يومي، ومواجهات ومسابقات في المجموعات والقنوات.\nتحصل على <b>تقييم من 10 ولقب ومستوى وإنجازات</b>!\n\nاختر طريقة اللعب:",
 "challenge_banner": "\n\n⚔️ <b>{name}</b> تحداك! حصل على <b>{score}/10</b> ويلقّب <b>{title}</b>.\nتقبل التحدي بنفس الأسئلة؟",
 "btn_full": "🎯 الاختبار الكامل", "btn_quick": "⚡ اختبار سريع",
 "btn_cat": "📂 حسب التصنيف", "btn_sudden": "☠️ الموت المفاجئ", "btn_games": "🎮 ألعاب أخرى",
 "btn_top": "🌍 التقييم العام", "btn_lang": "🌐 English", "btn_accept": "✅ أقبل التحدي", "btn_back": "◀️ رجوع",
 "btn_stale": "هذا الزر قديم 🕒 اكتب /start (أو /admin) لقائمة جديدة", "btn_week": "📅 تقييم الأسبوع", "btn_stats": "📈 إحصائياتي", "btn_images": "🖼 شخصيات بالصور", "btn_suggest": "💡 اقترح سؤالًا",
 "sg_prompt": "💡 <b>اقترح سؤالًا للبوت!</b>\nأرسل <b>5 أسطر</b> في رسالة واحدة:\n1) السؤال\n2) الجواب الصحيح\n3-5) ثلاثة خيارات خاطئة\n\nمثال:\nمن هو مؤلف One Piece؟\nإييتشيرو أودا\nماساشي كيشيموتو\nأكيرا تورياما\nتيتي كوبو\n\nللإلغاء: /cancel",
 "sg_ok": "شكرًا! وصل اقتراحك للمراجعة 🙏 وإذا قُبل ستصلك رسالة.", "sg_cancel": "تم الإلغاء ✅",
 "sg_format": "لازم 5 أسطر بالضبط: السؤال، الجواب الصحيح، ثم 3 خيارات خاطئة. أعد المحاولة أو /cancel",
 "sg_len": "السؤال بين 10 و200 حرف، وكل خيار حتى 60 حرفًا. أعد المحاولة أو /cancel",
 "sg_dupopt": "الخيارات الأربعة لازم تكون مختلفة. أعد المحاولة أو /cancel",
 "sg_exists": "هذا السؤال موجود عندنا بالفعل 👍 جرّب سؤالًا آخر.",
 "sg_limit": "وصلت الحد اليومي للاقتراحات ({n}). جرّب غدًا 🙏",
 "sg_pending": "عندك {n} اقتراحات قيد المراجعة. انتظر حتى تُراجع ثم اقترح غيرها 🙏",
 "sg_accepted": "✅ تم قبول سؤالك وأضيف إلى البنك! شكرًا لمساهمتك 🙏\n«{q}»",
 "sec_quiz": "—— 🎯 الاختبارات ——", "sec_games": "—— 🎮 الألعاب ——", "sec_more": "—— 🏆 المزيد ——",
 "cat_menu": "📂 اختر التصنيف (10 أسئلة من الأسهل للأصعب):", "no_cats": "لا توجد تصنيفات كافية حاليًا.",
 "sub_required": "🔒 للمشاركة لازم تشترك أولًا في قناتنا {ch}\nاشترك ثم اضغط «تحققت».",
 "btn_subscribe": "📢 اشترك في القناة", "btn_checked": "✅ تحققت",
 "sub_no": "ما لقيتك مشترك بعد 🙁 اشترك ثم جرّب مرة ثانية", "sub_err": "تعذّر التحقق: البوت ليس أدمن في القناة",
 "sub_ok": "✅ تمام، أهلًا بك!",
 "sub_unverifiable": "⚠️ تعذّر التحقق من الاشتراك حاليًا. نبّه صاحب البوت: لازم يكون البوت مشرفًا (أدمن) في القناة.",
 "resume_prompt": "عندك اختبار غير مكتمل (وصلت للسؤال {n}/{t}).", "btn_resume": "▶️ كمّل", "btn_new": "🆕 ابدأ من جديد",
 "cooldown": "⏳ لازم تنتظر {m} دقيقة قبل اختبار كامل جديد.\nجرّب الوضع السريع ⚡ أو الألعاب 🎮 في الأثناء، أو راجع /stats و/top",
 "bank_short": "عذرًا، بنك الأسئلة لا يكفي لهذا الوضع حاليًا. جرّب لاحقًا.",
 "q_head": "🎌 <b>السؤال {n}/{t}</b>  ·  المستوى {lvl}/10", "timer": "⏱ {s}ث",
 "btn_stop": "⛔ إنهاء", "btn_next": "التالي ▶️", "timeout": "⏰ <b>انتهى الوقت!</b>\nالجواب الصحيح: <b>{ans}</b>",
 "toast_ok": "✅ صح!", "toast_bad": "❌ غلط — الجواب: {ans}", "toast_time": "⏰ انتهى الوقت", "toast_stale": "هذا السؤال لم يعد نشطًا",
 "stopped": "تم إيقاف الاختبار. ارجع متى ما حبيت! 🎌",
 "stop_confirm": "🛑 <b>تبي تلغي الاختبار؟</b>\nلن تُحتسب نتيجته.", "stop_yes": "🛑 نعم، ألغِ", "stop_no": "↩️ لا، أكمل",
 "cancel_done": "✅ تم الإلغاء: {what}", "cancel_nothing": "ما عندك شيء جارٍ لإلغائه 🙂 اكتب /start للقائمة",
 "w_quiz": "الاختبار", "w_game": "اللعبة", "w_input": "الإدخال المعلّق",
 "g_stop": "⛔ إنهاء اللعبة", "g_stopped": "تم إنهاء اللعبة. ارجع متى ما حبيت! 🎮",
 "btn_profile": "👤 ملفي", "btn_share_profile": "📤 شارك ملفي",
 "prof_head": "👤 <b>ملف {name}</b>", "prof_best": "⭐ أفضل تقييم: <b>{best}/10</b> — {title}",
 "prof_rank": "🌍 ترتيبك العام: <b>#{rank}</b>", "prof_week": "📅 ترتيبك هذا الأسبوع: <b>#{rank}</b>",
 "prof_tests": "🎯 الاختبارات الكاملة: {n}", "prof_acc": "✅ دقتك الكلية: {pct}% ({ok}/{n})",
 "prof_sudden": "☠️ أفضل «موت مفاجئ»: {n}", "prof_cat": "💪 أقوى تصنيفاتك:",
 "prof_share": "ملفي في بوت اختبار الأوتاكو: {score}/10 — {title}! تقدر تغلبني؟",
 "fin_head": "🏁 <b>انتهى التقييم يا {name}!</b>", "res_score": "⭐ التقييم: <b>{score} / 10</b>", "res_title": "🏷 اللقب: <b>{title}</b>",
 "res_correct": "✅ الإجابات الصحيحة: {c}/{t}", "res_pct": "📊 أفضل من {p}% من اللاعبين", "res_cat": "<b>حسب التصنيف:</b>",
 "res_suspect": "⚠️ إجاباتك كانت سريعة جدًا؛ لن تُحتسب النتيجة في المتصدرين.",
 "res_nolb": "ℹ️ نتيجة هذا الوضع لا تدخل المتصدرين (الاختبار الكامل فقط).",
 "sudden_res": "☠️ <b>الموت المفاجئ</b>\nصمدت <b>{n}</b> سؤالًا متتاليًا وانتهت رحلتك عند المستوى {lvl}.\n🏅 رقمك القياسي: <b>{best}</b>",
 "sudden_perfect": "👑 ما أخطأت ولا مرة! أنهيت كل الأسئلة بلا خطأ.",
 "vs_head": "🆚 <b>النتيجة مقابل {name}</b>", "vs_line": "أنت: <b>{me}</b>  ·  {name}: <b>{them}</b>",
 "vs_win": "🔥 فزت بالتحدي!", "vs_lose": "😅 خسرت هالمرة… جرّب مرة ثانية", "vs_draw": "🤝 تعادل!",
 "vs_dm": "⚔️ <b>{name}</b> قبل تحداك!\nأنت: <b>{them}</b>  ·  {name}: <b>{me}</b>\n{verdict}",
 "vs_dm_win": "🔥 فزت!", "vs_dm_lose": "😅 خسرت هذه الجولة", "vs_dm_draw": "🤝 تعادل!",
 "btn_again": "🔁 اختبار جديد", "btn_menu": "🏠 القائمة", "btn_share": "📤 تحدَّ صديقك", "btn_report": "🚩 أبلغ عن سؤال",
 "share_text": "حصلت على {score}/10 وصرت «{title}» في بوت اختبار الأوتاكو! تقدر تغلبني بنفس الأسئلة؟",
 "ch_gone": "هذا التحدي لم يعد متاحًا.", "ch_self": "هذا تحديك أنت 😄 شاركه مع أصدقائك!",
 "ch_done": "سبق وخضت هذا التحدي ✅ نتيجتك: <b>{score}/10</b>",
 "lb_all": "🌍 <b>التقييم العام — أفضل 10 أوتاكو</b>\nحسب أفضل تقييم لكل لاعب في الاختبار الكامل", "lb_week": "📅 <b>متصدرو الأسبوع</b>\nيتصفر كل أحد 00:00 (توقيت مكة)",
 "lb_sudden": "☠️ <b>متصدرو الموت المفاجئ</b>", "lb_empty": "ما فيه متصدرين بعد، كن الأول! 🏆", "lb_you": "\n\nترتيبك: <b>#{rank}</b>",
 "tab_all": "🌍 العام", "tab_week": "📅 الأسبوع", "tab_sd": "☠️ الموت المفاجئ",
 "stats": "📈 <b>إحصائياتك</b>\nأفضل تقييم: <b>{best}/10</b> ({title})\nالترتيب: #{rank}\nعدد الاختبارات الكاملة: {n}\nأفضل «موت مفاجئ»: {sd}\nآخر النتائج: {recent}",
 "no_tests": "ما أخذت أي اختبار كامل بعد. اضغط /start 🎌",
 "rp_pick": "🚩 اختر السؤال الذي تريد الإبلاغ عنه (الأسئلة التي أخطأت فيها):", "rp_none": "ما فيه أسئلة أخطأت فيها في هذا الاختبار 👌",
 "rp_reason": "ما المشكلة في هذا السؤال؟",
 "rr_0": "الجواب الصحيح غير صحيح", "rr_1": "السؤال غامض أو فيه أكثر من جواب", "rr_2": "المعلومة قديمة", "rr_3": "خطأ إملائي", "rr_4": "الصورة غير صحيحة",
 "rp_ok": "شكرًا! وصل بلاغك للمراجعة 🙏", "rp_dup": "أبلغت عن هذا السؤال من قبل.",
 "rp_limit": "وصلت الحد اليومي للبلاغات ({n}). جرّب غدًا.", "rp_closed": "هذه الجلسة لم تعد متاحة.",
 "lang_set": "تم ✅ اللغة: العربية", "help": "/start — القائمة\n/retry — اختبار جديد\n/stats — إحصائياتك\n/top — المتصدرون\n/weekly — تقييم الأسبوع\n/profile — ملفي\n/games — الألعاب\n/suggest — اقترح سؤالًا\n/stop — إلغاء أي اختبار/لعبة\n/lang — اللغة",
 "en_note": "ℹ️ بعض الأسئلة غير متوفرة بالإنجليزية بعد.",
 # الألعاب
 "g_menu": "🎮 <b>ألعاب أخرى</b>\nاختر لعبة:\n\n🎌 <b>كت</b>: اكتب «كت» في أي محادثة، وتصلك سؤال عن الأنمي. كل كلمة «كت» سؤال جديد من بنك 1000 سؤال.", "g_tf": "✅❌ صح أم غلط", "g_song": "🎵 خمّن الأنمي من الأغنية", "g_ord": "📅 رتّب حسب سنة العرض",
 "g_tf_q": "✅❌ <b>صح أم غلط؟</b>  ({n}/{t})\n\n{s}", "g_true": "✅ صح", "g_false": "❌ غلط",
 "g_song_q": "🎵 <b>({n}/{t})</b> من أي أنمي هذه الأغنية/المقدمة؟\n\n🎶 <b>{s}</b>",
 "g_ord_q": "📅 <b>({n}/{t})</b> رتّب هذه الأعمال من الأقدم إلى الأحدث بالضغط عليها بالترتيب:\n\n{picked}",
 "g_reset": "↩️ إعادة الترتيب", "g_ok": "✅ صح!", "g_bad": "❌ غلط", "g_ord_ok": "✅ ترتيب صحيح!",
 "g_ord_bad": "❌ الترتيب الصحيح: {order}", "g_end": "🏁 <b>{title}</b>\nنتيجتك: <b>{score}/{total}</b>\n🏅 أفضل نتيجة لك: <b>{best}</b>",
 "g_char": "🕵️ خمّن الشخصية من وصفها", "g_quote": "💬 خمّن الأنمي من اقتباس",
 "g_char_q": "🕵️ <b>({n}/{t})</b> من هذه الشخصية؟\n\n{s}", "g_quote_q": "💬 <b>({n}/{t})</b> من أي أنمي هذا الاقتباس؟\n\n«{s}»",
 "g_again": "🔁 العب مرة ثانية", "g_stale": "هذه الجولة انتهت",
},
"en": {
 "welcome": "Welcome to the <b>Otaku Quiz Bot</b> 🎌\n\nTest your anime knowledge: <b>1400+ questions</b> from easy to hard, games, a daily challenge, duels and contests in groups and channels.\nYou get a <b>score out of 10, a title, a level and achievements</b>!\n\nPick a mode:",
 "challenge_banner": "\n\n⚔️ <b>{name}</b> challenged you! They scored <b>{score}/10</b> and are <b>{title}</b>.\nAccept the challenge with the same questions?",
 "btn_full": "🎯 Full test", "btn_quick": "⚡ Quick test",
 "btn_cat": "📂 By category", "btn_sudden": "☠️ Sudden death", "btn_games": "🎮 Other games",
 "btn_top": "🌍 Overall rating", "btn_lang": "🌐 العربية", "btn_accept": "✅ Accept challenge", "btn_back": "◀️ Back",
 "btn_stale": "This button is outdated 🕒 Send /start (or /admin) for a fresh menu", "btn_week": "📅 Weekly rating", "btn_stats": "📈 My stats", "btn_images": "🖼 Character pics", "btn_suggest": "💡 Suggest a question",
 "sg_prompt": "💡 <b>Suggest a question for the bot!</b>\nSend <b>5 lines</b> in one message:\n1) The question\n2) The correct answer\n3-5) Three wrong options\n\nExample:\nWho wrote One Piece?\nEiichiro Oda\nMasashi Kishimoto\nAkira Toriyama\nTite Kubo\n\nTo cancel: /cancel",
 "sg_ok": "Thanks! Your suggestion was sent for review 🙏 You'll get a message if it's accepted.", "sg_cancel": "Cancelled ✅",
 "sg_format": "I need exactly 5 lines: the question, the correct answer, then 3 wrong options. Try again or /cancel",
 "sg_len": "The question must be 10–200 characters and each option up to 60. Try again or /cancel",
 "sg_dupopt": "All four options must be different. Try again or /cancel",
 "sg_exists": "We already have that question 👍 Try another one.",
 "sg_limit": "You reached the daily suggestion limit ({n}). Try tomorrow 🙏",
 "sg_pending": "You have {n} suggestions waiting for review. Wait for them, then suggest more 🙏",
 "sg_accepted": "✅ Your question was accepted and added to the bank! Thanks for contributing 🙏\n“{q}”",
 "sec_quiz": "—— 🎯 Tests ——", "sec_games": "—— 🎮 Games ——", "sec_more": "—— 🏆 More ——",
 "cat_menu": "📂 Pick a category (10 questions, easy → hard):", "no_cats": "Not enough categories yet.",
 "sub_required": "🔒 To play you must first join our channel {ch}\nJoin, then tap “I joined”.",
 "btn_subscribe": "📢 Join the channel", "btn_checked": "✅ I joined",
 "sub_no": "I can't see you in the channel yet 🙁 Join and try again", "sub_err": "Can't verify: the bot is not an admin of the channel",
 "sub_ok": "✅ Welcome aboard!",
 "sub_unverifiable": "⚠️ Can't verify your subscription right now. Tell the bot owner: the bot must be an admin of the channel.",
 "resume_prompt": "You have an unfinished test (question {n}/{t}).", "btn_resume": "▶️ Resume", "btn_new": "🆕 Start over",
 "cooldown": "⏳ Please wait {m} min before another full test.\nTry ⚡ Quick mode or 🎮 games meanwhile, or check /stats and /top",
 "bank_short": "Sorry, not enough questions for this mode yet. Try later.",
 "q_head": "🎌 <b>Question {n}/{t}</b>  ·  Level {lvl}/10", "timer": "⏱ {s}s",
 "btn_stop": "⛔ Stop", "btn_next": "Next ▶️", "timeout": "⏰ <b>Time's up!</b>\nCorrect answer: <b>{ans}</b>",
 "toast_ok": "✅ Correct!", "toast_bad": "❌ Wrong — answer: {ans}", "toast_time": "⏰ Time's up", "toast_stale": "This question is no longer active",
 "stopped": "Test stopped. Come back anytime! 🎌",
 "stop_confirm": "🛑 <b>Cancel this test?</b>\nIts result won't count.", "stop_yes": "🛑 Yes, cancel", "stop_no": "↩️ No, continue",
 "cancel_done": "✅ Cancelled: {what}", "cancel_nothing": "Nothing in progress to cancel 🙂 Send /start for the menu",
 "w_quiz": "the test", "w_game": "the game", "w_input": "the pending input",
 "g_stop": "⛔ End game", "g_stopped": "Game ended. Come back anytime! 🎮",
 "btn_profile": "👤 My profile", "btn_share_profile": "📤 Share my profile",
 "prof_head": "👤 <b>{name}'s profile</b>", "prof_best": "⭐ Best score: <b>{best}/10</b> — {title}",
 "prof_rank": "🌍 Overall rank: <b>#{rank}</b>", "prof_week": "📅 Rank this week: <b>#{rank}</b>",
 "prof_tests": "🎯 Full tests taken: {n}", "prof_acc": "✅ Overall accuracy: {pct}% ({ok}/{n})",
 "prof_sudden": "☠️ Best “sudden death”: {n}", "prof_cat": "💪 Your strongest categories:",
 "prof_share": "My Otaku Quiz profile: {score}/10 — {title}! Can you beat me?",
 "fin_head": "🏁 <b>Test complete, {name}!</b>", "res_score": "⭐ Score: <b>{score} / 10</b>", "res_title": "🏷 Title: <b>{title}</b>",
 "res_correct": "✅ Correct answers: {c}/{t}", "res_pct": "📊 Better than {p}% of players", "res_cat": "<b>By category:</b>",
 "res_suspect": "⚠️ Your answers were suspiciously fast; this result won't count on the leaderboard.",
 "res_nolb": "ℹ️ This mode doesn't count for the leaderboard (full test only).",
 "sudden_res": "☠️ <b>Sudden death</b>\nYou survived <b>{n}</b> questions in a row and fell at level {lvl}.\n🏅 Your record: <b>{best}</b>",
 "sudden_perfect": "👑 Flawless! You cleared every question without a mistake.",
 "vs_head": "🆚 <b>Result vs {name}</b>", "vs_line": "You: <b>{me}</b>  ·  {name}: <b>{them}</b>",
 "vs_win": "🔥 You won the challenge!", "vs_lose": "😅 You lost this time… try again", "vs_draw": "🤝 It's a draw!",
 "vs_dm": "⚔️ <b>{name}</b> accepted your challenge!\nYou: <b>{them}</b>  ·  {name}: <b>{me}</b>\n{verdict}",
 "vs_dm_win": "🔥 You won!", "vs_dm_lose": "😅 You lost this round", "vs_dm_draw": "🤝 Draw!",
 "btn_again": "🔁 New test", "btn_menu": "🏠 Menu", "btn_share": "📤 Challenge a friend", "btn_report": "🚩 Report a question",
 "share_text": "I scored {score}/10 and became “{title}” in the Otaku Quiz Bot! Can you beat me on the same questions?",
 "ch_gone": "This challenge is no longer available.", "ch_self": "That's your own challenge 😄 Share it with friends!",
 "ch_done": "You already took this challenge ✅ Your score: <b>{score}/10</b>",
 "lb_all": "🌍 <b>Overall rating — Top 10 Otaku</b>\nBy each player's best full-test score", "lb_week": "📅 <b>Weekly leaderboard</b>\nResets every Sunday 00:00 (Mecca time)",
 "lb_sudden": "☠️ <b>Sudden-death leaderboard</b>", "lb_empty": "No one on the board yet — be the first! 🏆", "lb_you": "\n\nYour rank: <b>#{rank}</b>",
 "tab_all": "🌍 Overall", "tab_week": "📅 Week", "tab_sd": "☠️ Sudden death",
 "stats": "📈 <b>Your stats</b>\nBest score: <b>{best}/10</b> ({title})\nRank: #{rank}\nFull tests taken: {n}\nBest “sudden death”: {sd}\nRecent results: {recent}",
 "no_tests": "You haven't taken a full test yet. Tap /start 🎌",
 "rp_pick": "🚩 Pick the question you want to report (ones you got wrong):", "rp_none": "You got no questions wrong in this test 👌",
 "rp_reason": "What's wrong with this question?",
 "rr_0": "The correct answer is wrong", "rr_1": "Ambiguous / more than one answer", "rr_2": "Outdated info", "rr_3": "Typo", "rr_4": "The image is wrong",
 "rp_ok": "Thanks! Your report was sent for review 🙏", "rp_dup": "You already reported this question.",
 "rp_limit": "You reached the daily report limit ({n}). Try tomorrow.", "rp_closed": "This session is no longer available.",
 "lang_set": "Done ✅ Language: English", "help": "/start — menu\n/retry — new test\n/stats — your stats\n/top — leaderboard\n/weekly — weekly rating\n/profile — my profile\n/games — games\n/suggest — suggest a question\n/stop — cancel any test/game\n/lang — language",
 "en_note": "ℹ️ Some questions aren't available in English yet.",
 "g_menu": "🎮 <b>Other games</b>\nPick a game:\n\n🎌 <b>Kt</b>: type «كت» in any chat and get an anime question. Each «كت» gives a new question from a bank of 1000.", "g_tf": "✅❌ True or false", "g_song": "🎵 Guess the anime from the song", "g_ord": "📅 Order by release year",
 "g_tf_q": "✅❌ <b>True or false?</b>  ({n}/{t})\n\n{s}", "g_true": "✅ True", "g_false": "❌ False",
 "g_song_q": "🎵 <b>({n}/{t})</b> Which anime is this song from?\n\n🎶 <b>{s}</b>",
 "g_ord_q": "📅 <b>({n}/{t})</b> Order these from oldest to newest by tapping them in order:\n\n{picked}",
 "g_reset": "↩️ Reset", "g_ok": "✅ Correct!", "g_bad": "❌ Wrong", "g_ord_ok": "✅ Correct order!",
 "g_ord_bad": "❌ Correct order: {order}", "g_end": "🏁 <b>{title}</b>\nYour score: <b>{score}/{total}</b>\n🏅 Your best: <b>{best}</b>",
 "g_char": "🕵️ Guess the character", "g_quote": "💬 Guess the anime from a quote",
 "g_char_q": "🕵️ <b>({n}/{t})</b> Who is this character?\n\n{s}", "g_quote_q": "💬 <b>({n}/{t})</b> Which anime is this quote from?\n\n“{s}”",
 "g_again": "🔁 Play again", "g_stale": "This round is over",
},
}


def t(lang: str, key: str, **kw) -> str:
    s = T.get(lang, T["ar"]).get(key)
    if s is None:
        s = T["ar"][key]
    if isinstance(s, (list, tuple)):          # مجموعة جمل: نختار واحدة عشوائيًا فلا يتكرر الرد نفسه
        s = random.choice(s)
    return s.format(**kw) if kw else s


def cat_label(lang: str, cat: str) -> str:
    table = CATEGORY_LABELS_EN if lang == "en" else CATEGORY_LABELS
    return table.get(cat, cat)


# ═════════ نبرة بشرية وروح أوتاكو ═════════
# تتجاوز النصوص الجامدة أعلاه بجمل أدفأ وأقرب للكلام العادي، ومجموعات جمل (قوائم) تتبدّل عشوائيًا.
# نحافظ على نفس المتغيرات {name} {ans} ... وعلى الكلمات المفتاحية التي تعتمد عليها الاختبارات.
T["ar"].update({
 "mode_quick": "اختبار سريع",
 "welcome": "يا هلا والله {name}! 🎌\n\nهذا <b>بوت اختبار الأوتاكو</b>: تحسب نفسك تعرف الأنمي؟ خلنا نشوف! أكثر من 1400 سؤال تبدأ سهلة وتشتد معك، وألعاب وتحديات، وفي الآخر تاخذ تقييم من 10 ولقب ومستوى تفتخر فيهم.\nوالسؤال الصعب يوزن أكثر، فلا تستخف فيه 😏\n\nوش تبي تلعب؟",
 "challenge_banner": "\n\n⚔️ <b>{name}</b> يتحداك! جاب <b>{score}/10</b> ولقبه «{title}».\nتجرؤ تواجهه بنفس الأسئلة؟",
 "toast_ok": ["✅ صح عليك!", "✅ كفو!", "✅ ناكاما! 💪", "✅ هذا هو!", "✅ ضربة معلم 🔥", "✅ ما شاء الله"],
 "toast_bad": ["❌ لا… الجواب: {ans}", "❌ قربت! الجواب: {ans}", "❌ أوه لا، الجواب: {ans}", "❌ مو هذا، الجواب: {ans}"],
 "toast_time": ["⏰ فات الوقت!", "⏰ الوقت خلص!"],
 "timeout": "⏰ <b>انتهى الوقت!</b>\nكان الجواب: <b>{ans}</b>",
 "fin_head": "🏁 خلصت يا {name}!",
 "cooldown": "تعبت؟ 😄 ارتاح {m} دقيقة وارجع للاختبار الكامل.\nوفي الأثناء جرّب الوضع السريع ⚡ أو الألعاب 🎮",
 "sub_required": "قبل ما نبدأ… اشترك في قناتنا {ch} 🙏\nاشترك ثم اضغط «تحققت».",
 "sub_ok": "✅ تمام، حيّاك الله!",
 "stopped": "طيب، وقفنا هنا. ارجع متى ما حبيت 🎌",
 "stop_confirm": "🛑 <b>تبي تلغي الاختبار؟</b>\nنتيجة هالجولة ما راح تنحسب.",
 "g_stopped": "وقفنا اللعبة. ارجع متى ما حبيت 🎮",
 "no_tests": "ما أخذت أي اختبار كامل بعد 🙂 اكتب /start وجرّب أول واحد.",
 "lb_empty": "ما فيه أحد بالقائمة بعد… كن أول واحد يكتب اسمه! 🏆",
 "sg_ok": "وصل اقتراحك 🙏 بنراجعه، وإذا انقبل بتوصلك رسالة منا.",
 "sg_limit": "وصلت الحد اليومي للاقتراحات ({n}). كمّل بكرة 🙏",
 "sg_exists": "هالسؤال موجود عندنا من قبل 👍 جرّب غيره.",
 "sg_accepted": "✅ تم قبول سؤالك وصار في البنك! ممتن لك 🙏\n«{q}»",
 "vs_win": "🔥 فزت بالتحدي! الهوكاغي يبارك لك", "vs_lose": "😅 خسرت هالجولة… الثأر في المرة الجاية!",
 "ch_gone": "هذا التحدي ما عاد موجود 😅", "ch_self": "هذا تحديك أنت 😄 أرسله لأصحابك!",
 "res_line_king": ["ما شاء الله… حتى ريوك يطلب منك نصيحة 🍎", "هذا مو أوتاكو، هذا موسوعة تمشي على قدمين 👑", "اكتب اسمك في الدفتر… بس لا تقتل أحد 😂"],
 "res_line_sensei": ["سينسي! طلابك يحتاجون دروسك 🥋", "مستوى يخلي الهوكاغي يفكر يتقاعد", "شوي وتلبس التاج… جرّب مرة ثانية 💪"],
 "res_line_seasoned": ["أوتاكو متمرس! بس فيه أسئلة تكسر الظهر 😅", "قريب من القمة، لا توقف الحين!", "معلوماتك تمام، ناقصك لمسة بس"],
 "res_line_otaku": ["أوتاكو صاعد! قدامك ماراثون أنمي طويل 📺", "مو بطّال أبدًا، كمّل!", "الأساس موجود، والباقي بالمشاهدة 😉"],
 "res_line_casual": ["مشاهد لطيف، بس الأنمي أوسع من كذا 😄", "فيه مجال تتحسن، وأنت قدها", "ما عليك، حتى الأبطال يبدؤون من تحت"],
 "res_line_noob": ["لا تزعل، حتى لوفي بدأ من الصفر 🍼", "شغّل Death Note وارجع لنا 😂", "الجولة الجاية أحسن، وعد!"],
 "sd_line_low": ["سقطت بدري… الدفتر ما رحمك ☠️", "جرّب مرة ثانية، الشجاع ما يستسلم"],
 "sd_line_mid": ["مو بطّال! بس الأسئلة الصعبة تنتظرك 😈", "قدرت تصمد، كمّل للأعلى"],
 "sd_line_high": ["وحش! ما أحد يوقفك 🔥", "هذا مستوى أبطال الشونن حقيقي"],
})
T["en"].update({
 "mode_quick": "Quick test",
 "welcome": "Hey {name}, welcome aboard! 🎌\n\nThink you know your anime? Let's find out! Four-choice questions that start easy and get nasty, and at the end you get a score out of 10 and a title worth bragging about.\nHard questions are worth more, so don't skip the boss fights 😏\n\nWhat are we playing?",
 "challenge_banner": "\n\n⚔️ <b>{name}</b> challenges you! They scored <b>{score}/10</b> and hold the title “{title}”.\nDare to face them on the same questions?",
 "toast_ok": ["✅ Nice!", "✅ That's the one!", "✅ Nakama approved 💪", "✅ Boom!", "✅ Master move 🔥", "✅ Sugoi!"],
 "toast_bad": ["❌ Nope… answer: {ans}", "❌ So close! Answer: {ans}", "❌ Oh no, answer: {ans}", "❌ Not that one, answer: {ans}"],
 "toast_time": ["⏰ Too slow!", "⏰ Time's up!"],
 "timeout": "⏰ <b>Time's up!</b>\nThe answer was: <b>{ans}</b>",
 "fin_head": "🏁 All done, {name}!",
 "cooldown": "Tired already? 😄 Rest for {m} min before another full test.\nTry ⚡ Quick mode or 🎮 games meanwhile.",
 "sub_required": "Before we start… join our channel {ch} 🙏\nJoin, then tap “I joined”.",
 "sub_ok": "✅ Perfect, welcome aboard!",
 "stopped": "Alright, we stopped here. Come back anytime 🎌",
 "stop_confirm": "🛑 <b>Cancel this test?</b>\nThis round's result won't count.",
 "g_stopped": "Game stopped. Come back anytime 🎮",
 "no_tests": "You haven't taken a full test yet 🙂 Send /start and try your first one.",
 "lb_empty": "Nobody on the board yet… be the first to write your name! 🏆",
 "sg_ok": "Got your suggestion 🙏 We'll review it, and you'll hear from us if it's accepted.",
 "sg_exists": "We already have that one 👍 Try another!",
 "sg_accepted": "✅ Your question was accepted and is now in the bank! Thank you 🙏\n“{q}”",
 "vs_win": "🔥 You won the challenge! The Hokage approves", "vs_lose": "😅 You lost this round… revenge next time!",
 "ch_gone": "That challenge isn't around anymore 😅", "ch_self": "That's your own challenge 😄 Send it to your friends!",
 "res_line_king": ["Even Ryuk would ask you for advice 🍎", "That's not an otaku, that's a walking encyclopedia 👑", "Write your name in the notebook… but don't hurt anyone 😂"],
 "res_line_sensei": ["Sensei! Your students need your lessons 🥋", "The Hokage is thinking about retiring", "A little more and you wear the crown… go again 💪"],
 "res_line_seasoned": ["Seasoned otaku! A few questions still break backs 😅", "So close to the top, don't stop now!", "Solid knowledge, just a touch more"],
 "res_line_otaku": ["Rising otaku! A long anime marathon ahead 📺", "Not bad at all, keep going!", "The foundation is there, the rest is watch time 😉"],
 "res_line_casual": ["Nice casual viewer, but anime is bigger than this 😄", "Room to grow, and you've got it in you", "Don't worry, every hero starts at the bottom"],
 "res_line_noob": ["Don't sulk, even Luffy started from zero 🍼", "Go watch Death Note and come back 😂", "Next round will be better, promise!"],
 "sd_line_low": ["Fell early… the notebook showed no mercy ☠️", "Try again, the brave never give up"],
 "sd_line_mid": ["Not bad! The hard ones are waiting for you 😈", "You held on, now climb higher"],
 "sd_line_high": ["Beast mode! Nobody can stop you 🔥", "Real shonen protagonist energy"],
})


# ═════════ الدول والموقع ═════════
T["ar"].update({
 "btn_country": "🏳️ بلدي والدول",
 "cn_not_set": "🏳️ <b>من أي بلد أنت؟</b>\nاختر بلدك وشوف ترتيبك بين لاعبي دولتك وترتيب الدول 🌍",
 "cn_pick": "اختر بلدك:",
 "cn_ask_first": "🏳️ سؤال سريع: من أي بلد أنت؟\nنرتّب اللاعبين حسب الدولة ونعمل تنافس بين البلدان 🌍 (تقدر تتخطى)",
 "cn_btn_skip": "لاحقًا",
 "cn_btn_rank": "🌐 ترتيب الدول", "cn_btn_change": "✏️ غيّر بلدي",
 "cn_current": "🏳️ بلدك: <b>{c}</b>", "cn_your_rank": "ترتيبك في بلدك: <b>#{rank}</b>",
 "cn_saved": "تمام ✅ صرت من {c}", "cn_top_title": "🏆 <b>متصدرو {c}</b>",
 "cn_no_players": "ما فيه لاعبين من بلدك بالقائمة بعد… كن أول واحد! 🏁",
 "cn_rank_title": "🌐 <b>ترتيب الدول</b>\nمتوسط أفضل {top} لاعبين من كل بلد، وتظهر الدولة عند {min} لاعبين على الأقل.",
 "cn_no_countries": "لسا ما فيه دولة وصلت للحد الأدنى من اللاعبين. ادعُ أصحابك من بلدك! 🚀",
 "cn_country_pos": "ترتيب {c}: <b>#{pos}</b> بين الدول",
 "prof_country": "🏳️ بلدك: {c}", "prof_country_rank": "🏳️ بلدك: {c} · ترتيبك فيه <b>#{rank}</b>",
})
T["en"].update({
 "btn_country": "🏳️ My country & rankings",
 "cn_not_set": "🏳️ <b>Which country are you from?</b>\nPick yours to see your rank among your countrymen and the countries ranking 🌍",
 "cn_pick": "Pick your country:",
 "cn_ask_first": "🏳️ Quick question: which country are you from?\nWe rank players by country and run a friendly rivalry between nations 🌍 (you can skip)",
 "cn_btn_skip": "Later",
 "cn_btn_rank": "🌐 Countries ranking", "cn_btn_change": "✏️ Change country",
 "cn_current": "🏳️ Your country: <b>{c}</b>", "cn_your_rank": "Your rank in your country: <b>#{rank}</b>",
 "cn_saved": "Done ✅ You're from {c}", "cn_top_title": "🏆 <b>Top players of {c}</b>",
 "cn_no_players": "Nobody from your country on the board yet… be the first! 🏁",
 "cn_rank_title": "🌐 <b>Countries ranking</b>\nAverage of each country's top {top} players; a country appears with at least {min} players.",
 "cn_no_countries": "No country has enough players yet. Invite your friends from your country! 🚀",
 "cn_country_pos": "{c} is ranked <b>#{pos}</b> among countries",
 "prof_country": "🏳️ Your country: {c}", "prof_country_rank": "🏳️ Your country: {c} · your rank there <b>#{rank}</b>",
})

T["ar"]["cn_btn_top"] = "🏆 متصدرو بلدي"
T["en"]["cn_btn_top"] = "🏆 My country's top"


# ═════════ الإبلاغ عن كل سؤال ═════════
T["ar"]["btn_report_q"] = "🚩 أبلغ"
T["en"]["btn_report_q"] = "🚩 Report"
T["ar"]["rp_pick"] = "🚩 اختر السؤال اللي فيه خطأ (✅ أجبته صح، ❌ أخطأت، ⏭ تخطّيته):"
T["en"]["rp_pick"] = "🚩 Pick the question with a mistake (✅ got it, ❌ missed, ⏭ skipped):"
T["ar"]["rp_ok"] = "شكرًا! وصل بلاغك للمراجعة 🙏"

# ── اقترح لي أنمي ──
GENRE_NAMES = {
    "action": ("أكشن", "Action"), "adventure": ("مغامرة", "Adventure"), "fantasy": ("خيال", "Fantasy"),
    "comedy": ("كوميديا", "Comedy"), "romance": ("رومانسي", "Romance"), "drama": ("دراما", "Drama"),
    "sports": ("رياضة", "Sports"), "mystery": ("غموض", "Mystery"), "thriller": ("إثارة", "Thriller"),
    "scifi": ("خيال علمي", "Sci-Fi"), "supernatural": ("خارق للطبيعة", "Supernatural"), "music": ("موسيقى", "Music"),
    "slice": ("شريحة من الحياة", "Slice of Life"), "psychological": ("نفسي", "Psychological"),
    "school": ("مدرسي", "School"), "family": ("عائلي", "Family"), "historical": ("تاريخي", "Historical"),
}
T["ar"].update({
    "btn_anime": "🎬 اقترح لي أنمي",
    "an_menu": "🎬 <b>اقترح لي أنمي</b>\nاختر ما يناسبك، أو اترك الأمر للحظ 🎲\n<i>قائمة منتقاة بعناية وبدون محتوى مبتذل.</i>",
    "an_surprise": "🎲 فاجئني", "an_family": "👨‍👩‍👧 مناسب للجميع", "an_genre": "🎭 حسب النوع", "an_len": "⏱ حسب الطول",
    "an_pick_genre": "🎭 اختر النوع:", "an_pick_len": "⏱ اختر الطول:",
    "an_len_film": "🎞 فيلم", "an_len_short": "⚡ قصير (حتى 26 حلقة)", "an_len_medium": "📺 متوسط (27–100)", "an_len_long": "🌊 طويل جدًا",
    "an_next": "🔄 اقتراح آخر", "an_back": "⬅️ القائمة",
    "an_empty": "ما لقيت شيئًا بهذه الشروط 😅 جرّب شرطًا آخر.",
    "an_rate_all": "🟢 مناسب للجميع", "an_rate_teen": "🟡 +13", "an_rate_mature": "🟠 +16",
    "an_f_genre": "🎭 النوع", "an_f_rate": "🔞 التصنيف", "an_f_info": "📊 المعلومات", "an_f_note": "⚠️ ملاحظة",
    "an_film": "🎬 فيلم · {m} دقيقة", "an_series": "📺 {s} · {e}",
    "an_seasons": "{n} موسم", "an_eps": "{n} حلقة", "an_ongoing": "مستمر",
    "an_foot": "ℹ️ المعلومات تقريبية. إن لقيت خطأ اضغط 🚩",
    "an_rp_ok": "شكرًا! سنراجع هذا العمل 🙏",
})
T["en"].update({
    "btn_anime": "🎬 Suggest anime",
    "an_menu": "🎬 <b>Suggest me an anime</b>\nPick what suits you, or leave it to luck 🎲\n<i>A carefully curated list with no crude content.</i>",
    "an_surprise": "🎲 Surprise me", "an_family": "👨‍👩‍👧 All ages", "an_genre": "🎭 By genre", "an_len": "⏱ By length",
    "an_pick_genre": "🎭 Pick a genre:", "an_pick_len": "⏱ Pick a length:",
    "an_len_film": "🎞 Movie", "an_len_short": "⚡ Short (up to 26 eps)", "an_len_medium": "📺 Medium (27–100)", "an_len_long": "🌊 Very long",
    "an_next": "🔄 Another one", "an_back": "⬅️ Menu",
    "an_empty": "Nothing matches that 😅 Try another filter.",
    "an_rate_all": "🟢 All ages", "an_rate_teen": "🟡 13+", "an_rate_mature": "🟠 16+",
    "an_f_genre": "🎭 Genre", "an_f_rate": "🔞 Rating", "an_f_info": "📊 Info", "an_f_note": "⚠️ Note",
    "an_film": "🎬 Movie · {m} min", "an_series": "📺 {s} · {e}",
    "an_seasons": "{n} season(s)", "an_eps": "{n} episodes", "an_ongoing": "ongoing",
    "an_foot": "ℹ️ Info is approximate. Spot a mistake? Tap 🚩",
    "an_rp_ok": "Thanks! We'll review this title 🙏",
})

T["ar"]["btn_channel"] = "💬 قناتنا"
T["en"]["btn_channel"] = "💬 Our channel"

T["ar"].update({
    "btn_invite": "👥 ادعُ أصدقاءك",
    "iv_head": "👥 <b>ادعُ أصدقاءك</b>\nتُحسب الدعوة بعد أن يكمل صديقك أول اختبار كامل ويشترك بالقناة، وتأخذ ألقابًا خاصة.",
    "iv_count": "📨 دعواتك المكتملة: {n}", "iv_badge": "🏅 لقبك: {b}", "iv_nobadge": "🏅 لا لقب بعد، أول دعوة تعطيك لقبًا!",
    "iv_next": "🎯 باقي {k} للقب {b}", "iv_btn": "📤 شارك الرابط",
    "iv_share": "تعال جرّب اختبار الأوتاكو، شف كم تجيب من 10 🔥",
    "iv_joined": "🎉 صديقك أكمل أول اختبار واشترك! دعواتك المكتملة: {n}", "iv_badge_up": "🏅 ترقّيت للقب: {b}",
})
T["en"].update({
    "btn_invite": "👥 Invite friends",
    "iv_head": "👥 <b>Invite friends</b>\nAn invite counts once your friend finishes a full test and joins the channel. Earn special badges.",
    "iv_count": "📨 Completed invites: {n}", "iv_badge": "🏅 Your badge: {b}", "iv_nobadge": "🏅 No badge yet, your first invite earns one!",
    "iv_next": "🎯 {k} more for {b}", "iv_btn": "📤 Share link",
    "iv_share": "Come try the Otaku Quiz, see what you score out of 10 🔥",
    "iv_joined": "🎉 Your friend finished a first test and joined! Completed invites: {n}", "iv_badge_up": "🏅 New badge: {b}",
})

T["ar"]["btn_games_menu"] = "🎮 الألعاب"
T["en"]["btn_games_menu"] = "🎮 Games"
T["ar"]["btn_more"] = "⚙️ المزيد"
T["en"]["btn_more"] = "⚙️ More"
T["ar"]["more_menu"] = "⚙️ المزيد: إحصائياتي، الاقتراحات، اللغة."
T["en"]["more_menu"] = "⚙️ More: my stats, suggestions, language."

T["ar"]["pf_visit"] = "\n\n👤 شارك معك <b>{name}</b> ملفه: أفضل تقييم <b>{score}</b>/10 — {title}\nتقدر تتفوّق عليه؟ 😏"
T["en"]["pf_visit"] = "\n\n👤 <b>{name}</b> shared their profile: best score <b>{score}</b>/10 — {title}\nThink you can beat it?? 😏"
T["ar"]["btn_try_too"] = "🎯 جرّب أنت"
T["en"]["btn_try_too"] = "🎯 Try it too"

T["ar"]["sub_left"] = "⚠️ لازم تكون مشتركًا في القناة عشان تكمل. اشترك ثم اضغط «تحققت»."
T["en"]["sub_left"] = "⚠️ You must be subscribed to the channel to continue. Join, then tap “I joined”."

T["ar"].update({
    "btn_daily": "📅 التحدي اليومي", "dy_open": "📅 افتح التحدي",
    "dy_menu": "📅 <b>التحدي اليومي</b>\n🔥 سلسلتك: <b>{streak}</b> يوم · الأفضل: {best}\n\n❓ سؤال اليوم: {q}\n🎯 تحدي اليوم (5 أسئلة): {d}\n\nنفس الأسئلة لكل اللاعبين، وتتجدد منتصف الليل (توقيت مكة).",
    "dy_done": "✅ خلّصته", "dy_todo": "⏳ متاح",
    "dy_btn_q": "❓ سؤال اليوم", "dy_btn_d": "🎯 تحدي اليوم", "dy_btn_lb": "🏆 متصدرو اليوم",
    "dy_rm_on": "🔔 التذكير: يعمل (اضغط للإيقاف)", "dy_rm_off": "🔕 التذكير: متوقف (اضغط للتفعيل)",
    "dy_rm_set_on": "🔔 تمام! أذكّرك مرة واحدة بالمساء إن ما لعبت.", "dy_rm_set_off": "🔕 أوقفت التذكير.",
    "dy_remind_off": "🔕 أوقف التذكير",
    "dy_remind_streak": "🔥 سلسلتك {n} يوم في خطر! لسّا ما لعبت تحدي اليوم، لحقها قبل منتصف الليل.",
    "dy_remind_new": "📅 تحدي اليوم جاهز، 5 أسئلة بس! تعال شوف كم تجيب.",
    "dy_played": "📅 لعبت هذا اليوم. ارجع بكرة لتحدٍّ جديد 😉",
    "dy_res_q": "❓ <b>سؤال اليوم</b>\n{r}\n📊 {p}% من اللاعبين جاوبوه صح اليوم ({n} لاعب)",
    "dy_res_q_solo": "❓ <b>سؤال اليوم</b>\n{r}",
    "dy_right": "✅ إجابتك صحيحة!", "dy_wrong": "❌ إجابتك غلط، بس السلسلة محفوظة!",
    "dy_res_d": "🎯 <b>تحدي اليوم</b>\nنتيجتك: <b>{c}/{n}</b> · ⏱ {s} ث\n🏅 ترتيبك اليوم: {rank}",
    "dy_streak_now": "🔥 السلسلة: {n} يوم", "dy_streak_ms": "🎉 إنجاز! {n} يوم متواصل!",
    "dy_board": "🏆 <b>متصدرو تحدي اليوم</b>\n\n{rows}", "dy_board_empty": "ما فيه نتائج لسا. كن الأول! 💪",
    "du_btn": "⚔️ تحدَّ صديقًا", "du_wait": "⚔️ انتهيت: <b>{c}/{n}</b>\nأرسل الرابط لصديقك ليلعب نفس الأسئلة، وأبلغك بالنتيجة.",
    "du_share_btn": "📤 أرسل لصديق", "du_share_text": "⚔️ تحدّاك في 7 أسئلة أنمي، تقدر تغلبني؟",
    "du_invite": "\n\n⚔️ <b>{name}</b> يتحداك في 7 أسئلة! نتيجته تظهر بعد ما تخلّص.",
    "du_accept": "⚔️ أقبل التحدي", "du_unavail": "هذا التحدي لم يعد متاحًا (انتهى أو أخذه شخص آخر).",
    "du_result": "⚔️ <b>نتيجة المواجهة</b>\n{a}: <b>{sa}/{n}</b>\n{b}: <b>{sb}/{n}</b>\n\n{v}",
    "du_win": "🏆 فاز {w}!", "du_draw": "🤝 تعادل!",
})
T["en"].update({
    "btn_daily": "📅 Daily challenge", "dy_open": "📅 Open challenge",
    "dy_menu": "📅 <b>Daily challenge</b>\n🔥 Your streak: <b>{streak}</b> days · Best: {best}\n\n❓ Question of the day: {q}\n🎯 Daily challenge (5 questions): {d}\n\nSame questions for everyone, resets at midnight (Mecca time).",
    "dy_done": "✅ done", "dy_todo": "⏳ available",
    "dy_btn_q": "❓ Question of the day", "dy_btn_d": "🎯 Daily challenge", "dy_btn_lb": "🏆 Today's top",
    "dy_rm_on": "🔔 Reminder: on (tap to turn off)", "dy_rm_off": "🔕 Reminder: off (tap to turn on)",
    "dy_rm_set_on": "🔔 Done! One evening reminder if you haven't played.", "dy_rm_set_off": "🔕 Reminder turned off.",
    "dy_remind_off": "🔕 Turn off reminders",
    "dy_remind_streak": "🔥 Your {n}-day streak is at risk! You haven't played today's challenge, hurry before midnight.",
    "dy_remind_new": "📅 Today's challenge is ready, just 5 questions! See what you score.",
    "dy_played": "📅 You've played today. Come back tomorrow for a new one 😉",
    "dy_res_q": "❓ <b>Question of the day</b>\n{r}\n📊 {p}% of players got it right today ({n} players)",
    "dy_res_q_solo": "❓ <b>Question of the day</b>\n{r}",
    "dy_right": "✅ Correct!", "dy_wrong": "❌ Wrong, but your streak is safe!",
    "dy_res_d": "🎯 <b>Daily challenge</b>\nYour score: <b>{c}/{n}</b> · ⏱ {s}s\n🏅 Today's rank: {rank}",
    "dy_streak_now": "🔥 Streak: {n} days", "dy_streak_ms": "🎉 Milestone! {n} days in a row!",
    "dy_board": "🏆 <b>Today's top players</b>\n\n{rows}", "dy_board_empty": "No results yet. Be the first! 💪",
    "du_btn": "⚔️ Challenge a friend", "du_wait": "⚔️ Done: <b>{c}/{n}</b>\nSend the link to a friend so they play the same questions, and I'll tell you the result.",
    "du_share_btn": "📤 Send to a friend", "du_share_text": "⚔️ I challenge you to 7 anime questions, can you beat me?",
    "du_invite": "\n\n⚔️ <b>{name}</b> challenges you to 7 questions! Their score is revealed after you finish.",
    "du_accept": "⚔️ Accept the challenge", "du_unavail": "This challenge is no longer available (finished or taken).",
    "du_result": "⚔️ <b>Duel result</b>\n{a}: <b>{sa}/{n}</b>\n{b}: <b>{sb}/{n}</b>\n\n{v}",
    "du_win": "🏆 {w} wins!", "du_draw": "🤝 It's a draw!",
})

T["ar"]["btn_rank"] = "🏆 الترتيب"
T["en"]["btn_rank"] = "🏆 Rankings"

T["ar"].update({"lt_quiz": "🎯 الاختبار", "lt_sd": "☠️ الموت", "lt_games": "🎮 الألعاب", "lt_daily": "📅 اليومي",
                "lt_daily_head": "📅 <b>متصدرو تحدي اليوم</b>", "lt_game_head": "🎮 <b>متصدرو لعبة: {g}</b>"})
T["en"].update({"lt_quiz": "🎯 Test", "lt_sd": "☠️ Sudden", "lt_games": "🎮 Games", "lt_daily": "📅 Daily",
                "lt_daily_head": "📅 <b>Today's daily challenge top</b>", "lt_game_head": "🎮 <b>Top players: {g}</b>"})

T["ar"].update({
    "lbm_text": "🏆 <b>الترتيب</b>\nاختر القسم اللي تبي تشوفه:\n\n🎯 <b>الاختبار</b> — أعلى تقييم من 10 (عام وأسبوعي)\n☠️ <b>الموت المفاجئ</b> — أطول سلسلة إجابات صحيحة\n🎮 <b>الألعاب</b> — أعلى نتيجة في كل لعبة\n📅 <b>اليومي</b> — متصدرو تحدي اليوم",
    "lbm_quiz": "🎯 ترتيب الاختبار", "lbm_sd": "☠️ ترتيب الموت المفاجئ", "lbm_games": "🎮 ترتيب الألعاب", "lbm_daily": "📅 متصدرو اليوم",
    "lb_back": "⬅️ أقسام الترتيب", "lb_you_none": "\n\nما دخلت الترتيب بعد، العب وكن منهم! 💪",
    "lg_tf": "✅❌ صح/غلط", "lg_song": "🎵 الأغنية", "lg_ord": "📅 الترتيب", "lg_char": "🕵️ الشخصية", "lg_quote": "💬 الاقتباس",
    "tab_all": "🌍 العام", "tab_week": "📅 الأسبوعي",
})
T["en"].update({
    "lbm_text": "🏆 <b>Rankings</b>\nPick a section:\n\n🎯 <b>Test</b> — best score out of 10 (overall & weekly)\n☠️ <b>Sudden death</b> — longest correct streak\n🎮 <b>Games</b> — best score in each game\n📅 <b>Daily</b> — today's challenge leaders",
    "lbm_quiz": "🎯 Test ranking", "lbm_sd": "☠️ Sudden-death ranking", "lbm_games": "🎮 Games ranking", "lbm_daily": "📅 Today's leaders",
    "lb_back": "⬅️ Ranking sections", "lb_you_none": "\n\nYou're not on the board yet, play and join in! 💪",
    "lg_tf": "✅❌ True/False", "lg_song": "🎵 Song", "lg_ord": "📅 Order", "lg_char": "🕵️ Character", "lg_quote": "💬 Quote",
    "tab_all": "🌍 Overall", "tab_week": "📅 Weekly",
})

T["ar"].update({
    "gpk_quiz": "🎯 أسئلة عامة", "gpk_sudden": "☠️ الموت المفاجئ", "gpk_tf": "✅❌ صح أو غلط",
    "gpk_song": "🎵 خمّن الأغنية", "gpk_char": "🕵️ من الشخصية؟", "gpk_quote": "💬 من قال؟",
    "gpk_ord": "📅 أيّها أقدم؟", "gpk_images": "🖼 أسئلة صور", "gpm_xo": "❌⭕ إكس أو", "gpm_rps": "✊ حجرة ورقة مقص", "gpm_c4": "🔴🟡 أربعة في صف", "gpm_top": "🏆 الترتيب",
    "gp_menu": "🎮 <b>لعبة جماعية</b>\nاختر نوع اللعبة (لصاحب الأمر أو أدمن المجموعة):",
    "gp_lobby": "🎮 <b>{kind}</b>\n👤 المضيف: {host}\n\n⏳ تبدأ بعد <b>{left}</b> ثانية — اضغط «انضم»!\n👥 المنضمون ({n}): {names}\n<i>يلزم {min} لاعبين على الأقل.</i>",
    "gp_join": "✋ انضم", "gp_start_now": "▶️ ابدأ الآن", "gp_cancel": "❌ إلغاء",
    "gp_started": "🚀 بدأت اللعبة! اللاعبون ({n}): {names}",
    "gp_round": "❓ <b>سؤال {n}/{t}</b> · ⏱ {s} ث", "gp_answered": "أجاب {a} من {n}",
    "gp_reveal": "✅ <b>سؤال {n}/{t}</b> — الجواب: <b>{a}</b>", "gp_nobody": "😅 ما أحد جاوب صح", "gp_and_more": "…و{n} آخرين صح",
    "gp_out": "خرجوا",
    "gp_final": "🏁 <b>انتهت اللعبة!</b>\n{w}\n\n{rows}\n\n<i>لعبة جديدة: /play</i>",
    "gp_winner": "الفائز: {w}", "gp_nowinner": "ما فيه فائز هالمرة 🤷",
    "gp_too_few": "❌ ما اكتمل العدد (يلزم {min} لاعبين على الأقل). جرّب مرة ثانية بـ /play", "gp_no_rounds": "⚠️ ما قدرت أجهّز أسئلة لهذه اللعبة الآن.",
    "gp_stopped": "⛔ تم إيقاف اللعبة.", "gp_busy": "⏳ فيه لعبة شغالة الآن في المجموعة. (للإيقاف: /gstop)",
    "gp_cooldown": "⏱ انتظر {s} ثانية قبل لعبة جديدة.", "gp_disabled": "ألعاب المجموعات متوقفة حاليًا.",
    "gp_host_only": "هذا الزر لصاحب الأمر أو أدمن المجموعة فقط.", "gp_gone": "هذه اللعبة انتهت أو غير موجودة.",
    "gp_already": "أنت منضم ✅", "gp_full": "اكتمل العدد الأقصى للاعبين.", "gp_joined": "انضممت ✅ استعد!",
    "gp_late": "انتهى وقت هذا السؤال ⌛", "gp_not_in": "ما انضممت لهذه اللعبة، انضم في اللعبة القادمة 😉",
    "gp_you_out": "خرجت من اللعبة 💀", "gp_changed_no": "سجّلت إجابتك من قبل ✅", "gp_got": "✅ تسجّلت إجابتك",
    "gp_song_q": "🎵 أي أنمي هذه الأغنية؟ <b>{s}</b>", "gp_char_q": "🕵️ من هي الشخصية؟ {s}", "gp_quote_q": "💬 من قال هذا الاقتباس؟ {s}",
    "gp_ord_q": "📅 أيّ هذه الأعمال عُرض أولًا؟",
    "gp_top": "🏆 <b>متصدرو المجموعة</b>\n\n📅 <b>هذا الأسبوع</b>\n{week}\n\n🌍 <b>كل الأوقات</b>\n{all}",
    "gp_lang_set": "🌐 لغة ألعاب المجموعة: العربية.",
    "gp_help": "🎌 <b>اختبار الأوتاكو</b>\nللعب مع الأصدقاء هنا اكتب /play أو أحد الأوامر: /quiz /sudden /tf /char /quote /order /images\n/gtop متصدرو المجموعة · /gstop إيقاف اللعبة · /glang تغيير اللغة (للأدمن)\nولاختبارك الشخصي افتح البوت بالخاص.",
    "gp_open_private": "💬 افتح البوت بالخاص",
})
T["en"].update({
    "gpk_quiz": "🎯 General quiz (10)", "gpk_sudden": "☠️ Sudden death (last one standing)", "gpk_tf": "✅❌ True or false",
    "gpk_song": "🎵 Guess the anime from the song", "gpk_char": "🕵️ Who's the character?", "gpk_quote": "💬 Who said it?",
    "gpk_ord": "📅 Which came first?", "gpk_images": "🖼 Image questions",
    "gp_menu": "🎮 <b>Group game</b>\nPick a game type (command sender or group admins only):",
    "gp_lobby": "🎮 <b>{kind}</b>\n👤 Host: {host}\n\n⏳ Starts in <b>{left}</b>s — tap “Join”!\n👥 Players ({n}): {names}\n<i>At least {min} players needed.</i>",
    "gp_join": "✋ Join", "gp_start_now": "▶️ Start now", "gp_cancel": "❌ Cancel",
    "gp_started": "🚀 Game on! Players ({n}): {names}",
    "gp_round": "❓ <b>Question {n}/{t}</b> · ⏱ {s}s", "gp_answered": "{a} of {n} answered",
    "gp_reveal": "✅ <b>Question {n}/{t}</b> — Answer: <b>{a}</b>", "gp_nobody": "😅 Nobody got it right", "gp_and_more": "…and {n} more got it",
    "gp_out": "Out",
    "gp_final": "🏁 <b>Game over!</b>\n{w}\n\n{rows}\n\n<i>New game: /play</i>",
    "gp_winner": "Winner: {w}", "gp_nowinner": "No winner this time 🤷",
    "gp_too_few": "❌ Not enough players (need at least {min}). Try again with /play", "gp_no_rounds": "⚠️ Couldn't prepare questions right now.",
    "gp_stopped": "⛔ Game stopped.", "gp_busy": "⏳ A game is already running here. (Stop it: /gstop)",
    "gp_cooldown": "⏱ Wait {s}s before a new game.", "gp_disabled": "Group games are currently off.",
    "gp_host_only": "Only the command sender or a group admin can use this.", "gp_gone": "That game is over or doesn't exist.",
    "gp_already": "You're in ✅", "gp_full": "The game is full.", "gp_joined": "Joined ✅ get ready!",
    "gp_late": "Time's up for this question ⌛", "gp_not_in": "You didn't join this game, join the next one 😉",
    "gp_you_out": "You're out 💀", "gp_changed_no": "Your answer is already in ✅", "gp_got": "✅ Answer recorded",
    "gp_song_q": "🎵 Which anime is this song from? <b>{s}</b>", "gp_char_q": "🕵️ Who's the character? {s}", "gp_quote_q": "💬 Who said this quote? {s}",
    "gp_ord_q": "📅 Which of these aired first?",
    "gp_top": "🏆 <b>Group leaderboard</b>\n\n📅 <b>This week</b>\n{week}\n\n🌍 <b>All time</b>\n{all}",
    "gp_lang_set": "🌐 Group games language: English.",
    "gp_help": "🎌 <b>Otaku Quiz</b>\nTo play with friends here use /play or: /quiz /sudden /tf /char /quote /order /images\n/gtop group leaderboard · /gstop stop the game · /glang switch language (admins)\nFor your personal test open the bot in private.",
    "gp_open_private": "💬 Open the bot in private",
})

T["ar"].update({
    "lbm_text": "🏆 <b>الترتيب</b>\nاختر المدة:\n\n🌍 <b>العام</b> — أفضل نتيجة لكل لاعب على الإطلاق\n📅 <b>الأسبوعي</b> — يتصفّر كل أحد 00:00 (توقيت مكة)\n☀️ <b>اليوم</b> — يتصفّر كل منتصف ليل",
    "lbp_a": "🌍 العام", "lbp_w": "📅 الأسبوعي", "lbp_d": "☀️ اليوم",
    "lbp_s_a": "🌍 العام", "lbp_s_w": "📅 الأسبوعي", "lbp_s_d": "☀️ اليوم",
    "lbt_head_a": "🌍 <b>الترتيب العام</b>\nاختر النوع:", "lbt_head_w": "📅 <b>الترتيب الأسبوعي</b>\nاختر النوع:", "lbt_head_d": "☀️ <b>ترتيب اليوم</b>\nاختر النوع:",
    "lbt_dc": "⚡ تحدي اليوم", "lbt_q": "🎯 الاختبار", "lbt_s": "☠️ الموت المفاجئ", "lbt_tf": "✅❌ صح أم غلط", "lbt_song": "🎵 الأغنية",
    "lbt_ord": "📅 رتّب بالسنة", "lbt_char": "🕵️ الشخصية", "lbt_quote": "💬 الاقتباس",
    "lb_title": "🏆 <b>{p} · {k}</b>", "lb_back_types": "⬅️ الأنواع", "lb_back_period": "🏆 المدة",
})
T["en"].update({
    "lbm_text": "🏆 <b>Rankings</b>\nPick a period:\n\n🌍 <b>Overall</b> — each player's best ever\n📅 <b>Weekly</b> — resets every Sunday 00:00 (Mecca time)\n☀️ <b>Today</b> — resets every midnight",
    "lbp_a": "🌍 Overall (all time)", "lbp_w": "📅 Weekly", "lbp_d": "☀️ Today",
    "lbp_s_a": "🌍 Overall", "lbp_s_w": "📅 Weekly", "lbp_s_d": "☀️ Today",
    "lbt_head_a": "🌍 <b>Overall ranking</b>\nPick a type:", "lbt_head_w": "📅 <b>Weekly ranking</b>\nPick a type:", "lbt_head_d": "☀️ <b>Today's ranking</b>\nPick a type:",
    "lbt_dc": "⚡ Daily challenge", "lbt_q": "🎯 Test", "lbt_s": "☠️ Sudden death", "lbt_tf": "✅❌ True/False", "lbt_song": "🎵 Song",
    "lbt_ord": "📅 Order by year", "lbt_char": "🕵️ Character", "lbt_quote": "💬 Quote",
    "lb_title": "🏆 <b>{p} · {k}</b>", "lb_back_types": "⬅️ Types", "lb_back_period": "🏆 Period",
})

T["ar"].update({
    "btn_group": "👥 تحدٍّ في مجموعة",
    "gpm_text": "👥 <b>تحدٍّ في مجموعة</b>\n1️⃣ اضغط الزر واختر المجموعة (يُضاف البوت إليها)\n2️⃣ أعطه صلاحية إرسال الرسائل\n3️⃣ اكتب <b>/play</b> في المجموعة وتبدأ اللعبة بعد 30 ثانية!\n\n<i>إذا كان البوت موجودًا في المجموعة، اكتب /play مباشرة.</i>",
    "gpm_btn": "➕ اختر المجموعة", "gp_top_btn": "🏆 ترتيب المجموعة",
    "gp_top": "🏆 <b>متصدرو المجموعة</b>\n<i>🏆 انتصارات · 🎮 ألعاب · ⭐ نقاط</i>\n\n📅 <b>هذا الأسبوع</b>\n{week}\n\n🌍 <b>كل الأوقات</b>\n{all}",
    "gp_top_plain": "🏆 متصدرو المجموعة (🏆 انتصارات · 🎮 ألعاب · ⭐ نقاط)\n{all}",
})
T["en"].update({
    "btn_group": "👥 Group challenge",
    "gpm_text": "👥 <b>Challenge in a group</b>\n1️⃣ Tap the button and pick the group (the bot gets added)\n2️⃣ Give it permission to send messages\n3️⃣ Type <b>/play</b> in the group and the game starts in 30 seconds!\n\n<i>If the bot is already in the group, just type /play.</i>",
    "gpm_btn": "➕ Pick a group", "gp_top_btn": "🏆 Group ranking",
    "gp_top": "🏆 <b>Group leaderboard</b>\n<i>🏆 wins · 🎮 games · ⭐ points</i>\n\n📅 <b>This week</b>\n{week}\n\n🌍 <b>All time</b>\n{all}",
    "gp_top_plain": "🏆 Group leaderboard (🏆 wins · 🎮 games · ⭐ points)\n{all}",
})

T["ar"].update({
    "btn_channel_game": "📢 تحدٍّ في قناة",
    "ch_intro": "📢 <b>تحدٍّ في قناة</b>\n1️⃣ اضغط «اختر القناة» وأضف البوت أدمن (نشر + تعديل + حذف رسائل)\n2️⃣ سيصلك هنا اختيار نوع المسابقة\n3️⃣ بعدها تبدأ مشاركة 3 دقائق، ثم أسئلة (30 ثانية لكل سؤال)، وتظهر النتيجة بالأفضل 10.\n\n<i>القناة مضافة سابقًا؟ اكتب /play في القناة (سأحذف منشورك وأرسل لك القائمة هنا)، أو اختر من قنواتك أدناه.</i>",
    "ch_add_btn": "➕ اختر القناة", "ch_linked": "📢 القناة: <b>{title}</b>\nاختر نوع المسابقة:",
    "ch_rights_warn": "⚠️ البوت يحتاج صلاحية <b>نشر الرسائل وتعديلها</b> في القناة حتى تعمل المسابقة.",
    "ch_publish_fail": "ما قدرت أنشر في القناة. تأكد أن البوت أدمن فيها بصلاحية نشر وتعديل الرسائل.",
    "ch_started_toast": "🚀 نُشرت غرفة المشاركة في القناة!",
    "ch_started": "✅ نُشرت المسابقة في القناة. المشاركة مفتوحة 3 دقائق.\nتحكّم من هنا:",
    "gp_lobby_ch": "🎮 <b>مسابقة: {kind}</b>\n\n⏳ تبدأ بعد <b>{left}</b> ثانية — اضغط «شارك»!\n👥 المشاركون: <b>{n}</b>\n<i>سؤال كل 30 ثانية، والأسرع يكسب نقاطًا أكثر.</i>",
})
T["en"].update({
    "btn_channel_game": "📢 Channel challenge",
    "ch_intro": "📢 <b>Challenge in a channel</b>\n1️⃣ Tap “Pick channel” and add the bot as admin (post + edit + delete messages)\n2️⃣ You'll get the contest type menu here\n3️⃣ Then 3 minutes to join, then questions (30s each), and the top 10 are shown at the end.\n\n<i>Bot already in your channel? Type /play there (I'll delete your post and send the menu here), or pick from your channels below.</i>",
    "ch_add_btn": "➕ Pick a channel", "ch_linked": "📢 Channel: <b>{title}</b>\nPick the contest type:",
    "ch_rights_warn": "⚠️ The bot needs permission to <b>post and edit messages</b> in the channel.",
    "ch_publish_fail": "I couldn't post in the channel. Make sure the bot is an admin with post & edit rights.",
    "ch_started_toast": "🚀 The join post is live in the channel!",
    "ch_started": "✅ The contest is posted in the channel. Joining is open for 3 minutes.\nControl it here:",
    "gp_lobby_ch": "🎮 <b>Contest: {kind}</b>\n\n⏳ Starts in <b>{left}</b>s — tap “Join”!\n👥 Players: <b>{n}</b>\n<i>A question every 30s; faster answers earn more points.</i>",
})
for L in ("ar", "en"):
    T[L]["gp_final"] = T[L]["gp_final"].replace("{w}\n\n{rows}", "{w}\n👥 {n}\n\n{rows}")

T["ar"]["gp_join_ch"] = "✋ شارك"
T["en"]["gp_join_ch"] = "✋ Participate"
T["ar"]["gp_joined_ch"] = "✅ تم تسجيل مشاركتك! انتظر بداية الأسئلة"
T["en"]["gp_joined_ch"] = "✅ You're in! Wait for the questions to start"

T["ar"].update({
    "ch_test_btn": "🔧 تجربة النشر", "ch_test_ok": "✅ البوت ينشر ويحذف في القناة بشكل سليم.",
    "ch_test_ok_nodel": "⚠️ البوت ينشر لكن لا يستطيع الحذف: فعّل له صلاحية «حذف الرسائل».",
    "ch_open_pm": "📩 لإكمال المسابقة افتح البوت بالخاص أولًا: @{me} ثم أعد كتابة /play",
})
T["en"].update({
    "ch_test_btn": "🔧 Test posting", "ch_test_ok": "✅ The bot can post and delete in the channel.",
    "ch_test_ok_nodel": "⚠️ The bot can post but not delete: enable the “Delete messages” right.",
    "ch_open_pm": "📩 To continue, open the bot in private first: @{me}, then type /play again",
})

T["ar"]["gp_nobody_joined"] = "😴 ما شارك أحد هذه المرة. جرّب مرة ثانية!"
T["en"]["gp_nobody_joined"] = "😴 Nobody joined this time. Try again!"

T["ar"]["btn_sub_bot_channel"] = "💬 قناتنا"
T["en"]["btn_sub_bot_channel"] = "💬 Our channel"
T["ar"]["gp_must_sub"] = "⚠️ لازم تشترك في قناتنا @{ch} عشان تشارك. اشترك ثم اضغط «شارك» مرة ثانية."
T["en"]["gp_must_sub"] = "⚠️ You must subscribe to our channel @{ch} to take part. Subscribe, then tap “Participate” again."

T["ar"].update({
    "btn_suggest": "💬 اقتراحات",
    "fb_menu": "💬 <b>الاقتراحات والملاحظات</b>\nرأيك يهمنا! اختر نوع رسالتك:",
    "fbk_feat": "🛠 اقتراح لتطوير البوت", "fbk_q": "❓ اقتراح سؤال", "fbk_anime": "🎬 اقتراح أنمي للقائمة",
    "fbk_bug": "🐞 مشكلة أو خطأ", "fbk_note": "💭 ملاحظة أو شكر",
    "fbp_feat": "🛠 <b>اقتراح لتطوير البوت</b>\nاكتب فكرتك في رسالة واحدة (ميزة جديدة، تحسين، لعبة…).\n<i>من 10 إلى 1000 حرف.</i>",
    "fbp_anime": "🎬 <b>اقتراح أنمي للقائمة</b>\nاكتب اسم الأنمي وسبب ترشيحه في رسالة واحدة.\n<i>القائمة للأعمال النظيفة فقط.</i>",
    "fbp_bug": "🐞 <b>مشكلة أو خطأ</b>\nاشرح ماذا حصل وأين (القائمة، اللعبة، السؤال…) وسأوصله للإدارة.",
    "fbp_note": "💭 <b>ملاحظة أو شكر</b>\nاكتب ما تريد قوله للإدارة.",
    "fb_cancel": "⬅️ رجوع", "fb_len": "اكتب من 10 إلى 1000 حرف من فضلك.",
    "fb_limit": "وصلت للحد اليومي ({n} رسائل). جرّب بكرة 🙏", "fb_pending": "عندك رسائل كثيرة لم تُراجع بعد. انتظر ردنا أولًا 🙏",
    "fb_dup": "أرسلت نفس الرسالة من قبل 😉", "fb_ok": "شكرًا! وصلت رسالتك للإدارة 💙",
    "fb_reply": "💬 <b>رد من الإدارة</b>\n\n{text}",
})
T["en"].update({
    "btn_suggest": "💬 Suggestions",
    "fb_menu": "💬 <b>Suggestions & feedback</b>\nWe value your opinion! Pick a type:",
    "fbk_feat": "🛠 Suggest a bot improvement", "fbk_q": "❓ Suggest a question", "fbk_anime": "🎬 Suggest an anime for the list",
    "fbk_bug": "🐞 Problem or bug", "fbk_note": "💭 Note or thanks",
    "fbp_feat": "🛠 <b>Bot improvement</b>\nWrite your idea in one message (new feature, improvement, game…).\n<i>10 to 1000 characters.</i>",
    "fbp_anime": "🎬 <b>Suggest an anime</b>\nWrite the anime's name and why you recommend it, in one message.\n<i>The list is for clean titles only.</i>",
    "fbp_bug": "🐞 <b>Problem or bug</b>\nExplain what happened and where (menu, game, question…) and I'll pass it on.",
    "fbp_note": "💭 <b>Note or thanks</b>\nWrite what you'd like to tell the team.",
    "fb_cancel": "⬅️ Back", "fb_len": "Please write 10 to 1000 characters.",
    "fb_limit": "Daily limit reached ({n} messages). Try tomorrow 🙏", "fb_pending": "You have many unreviewed messages. Please wait for our reply 🙏",
    "fb_dup": "You've sent this already 😉", "fb_ok": "Thanks! Your message reached the team 💙",
    "fb_reply": "💬 <b>Reply from the team</b>\n\n{text}",
})

T["ar"].update({
    "pg_level": "⭐ المستوى <b>{lv}</b> — {rank}\n{bar} {xp}/{nxt} XP",
    "pg_levelup": "🆙 ارتقيت إلى المستوى <b>{lv}</b> — {rank}!",
    "pg_ach_new": "🏅 إنجاز جديد: {icon} <b>{name}</b> (+25 XP)",
    "pg_ach_head": "🏅 <b>إنجازاتي</b> ({n}/{total})", "pg_xp_gain": "⭐ +{xp} XP",
    "btn_achs": "🏅 إنجازاتي",
})
T["en"].update({
    "pg_level": "⭐ Level <b>{lv}</b> — {rank}\n{bar} {xp}/{nxt} XP",
    "pg_levelup": "🆙 You reached level <b>{lv}</b> — {rank}!",
    "pg_ach_new": "🏅 New achievement: {icon} <b>{name}</b> (+25 XP)",
    "pg_ach_head": "🏅 <b>My achievements</b> ({n}/{total})", "pg_xp_gain": "⭐ +{xp} XP",
    "btn_achs": "🏅 My achievements",
})

T["ar"].update({
    "dy_freezes": "🧊 تجميد السلسلة: {n} (يحمي سلسلتك إن فاتك يوم)",
    "dy_freeze_used": "🧊 استُهلك تجميد لإنقاذ سلسلتك!", "dy_freeze_gain": "🧊 كسبت تجميدًا جديدًا (عندك {n})!",
    "du_rematch": "🔁 ثأر", "du_rematch_invite": "🔁 <b>{name}</b> يطلب ثأرًا منك! 7 أسئلة جديدة، تقبل؟",
})
T["en"].update({
    "dy_freezes": "🧊 Streak freezes: {n} (protects your streak if you miss a day)",
    "dy_freeze_used": "🧊 A freeze was used to save your streak!", "dy_freeze_gain": "🧊 You earned a new freeze (you have {n})!",
    "du_rematch": "🔁 Rematch", "du_rematch_invite": "🔁 <b>{name}</b> wants a rematch! 7 new questions, accept?",
})

T["ar"].update({
    "tm_none": "🛡 <b>العشائر</b>\nانضم لعشيرة أو أنشئ عشيرتك! تتنافس العشائر بمجموع خبرة أعضائها كل أسبوع، ويراها الجميع في الترتيب.\n<i>الحد الأقصى 30 عضوًا للعشيرة.</i>",
    "tm_create": "➕ أنشئ عشيرة", "tm_join_list": "🔍 انضم لعشيرة", "tm_rank_btn": "🏆 ترتيب العشائر", "tm_leave": "🚪 غادر العشيرة",
    "tm_invite": "📤 ادعُ لعشيرتك", "tm_invite_text": "انضم لعشيرتي «{name}» في بوت اختبار الأوتاكو ⚔️",
    "tm_view": "🛡 <b>{name}</b>\n👥 الأعضاء: {n}/{mx} · القائد: {leader}\n⭐ خبرة العشيرة هذا الأسبوع: <b>{wxp}</b> · ترتيبها: <b>#{rank}</b>\n\n<b>أفضل الأعضاء هذا الأسبوع</b>\n{rows}",
    "tm_ask_name": "اكتب اسم عشيرتك (من {a} إلى {b} حرفًا، بدون روابط):", "tm_name_len": "الاسم من {a} إلى {b} حرفًا من فضلك.",
    "tm_name_bad": "الاسم غير مناسب، جرّب اسمًا آخر.", "tm_taken": "هذا الاسم مستخدم، اختر اسمًا آخر.",
    "tm_created": "🎉 تم إنشاء عشيرة <b>{name}</b>! ادعُ أصدقاءك بالزر التالي.", "tm_cant": "لا يمكنك إنشاء عشيرة الآن (أنت في عشيرة أصلًا).",
    "tm_admin_no": "الأدمن لا ينضم للعشائر (حفاظًا على الخصوصية).", "tm_none_yet": "ما فيه عشائر متاحة بعد. كن أول من ينشئ عشيرة!",
    "tm_pick": "🔍 اختر عشيرة للانضمام:", "tm_joined": "🎉 انضممت للعشيرة!",
    "tm_join_gone": "هذه العشيرة غير متاحة.", "tm_join_admin": "الأدمن لا ينضم للعشائر.", "tm_join_already": "أنت فيها أصلًا ✅",
    "tm_join_in_other": "أنت في عشيرة أخرى، غادرها أولًا.", "tm_join_full": "العشيرة ممتلئة (30 عضوًا).",
    "tm_leave_ask": "متأكد من مغادرة العشيرة؟", "tm_leave_yes": "نعم، غادر", "tm_left": "غادرت العشيرة.",
    "tm_start_invite": "\n\n🛡 دُعيت للانضمام لعشيرة <b>{name}</b> ({n}/{mx}).",
    "btn_teams": "🛡 عشيرتي", "lbm_teams": "🛡 ترتيب العشائر", "lbt_team_head": "🛡 <b>ترتيب العشائر · {p}</b>\n<i>مجموع خبرة الأعضاء</i>",
})
T["en"].update({
    "tm_none": "🛡 <b>Clans</b>\nJoin a clan or create your own! Clans compete by their members' total XP every week, visible to everyone in the rankings.\n<i>Max 30 members per clan.</i>",
    "tm_create": "➕ Create a clan", "tm_join_list": "🔍 Join a clan", "tm_rank_btn": "🏆 Clan ranking", "tm_leave": "🚪 Leave clan",
    "tm_invite": "📤 Invite to your clan", "tm_invite_text": "Join my clan “{name}” in the Otaku Quiz bot ⚔️",
    "tm_view": "🛡 <b>{name}</b>\n👥 Members: {n}/{mx} · Leader: {leader}\n⭐ Clan XP this week: <b>{wxp}</b> · Rank: <b>#{rank}</b>\n\n<b>Top members this week</b>\n{rows}",
    "tm_ask_name": "Write your clan's name ({a} to {b} characters, no links):", "tm_name_len": "The name must be {a} to {b} characters.",
    "tm_name_bad": "That name isn't allowed, try another.", "tm_taken": "That name is taken, pick another.",
    "tm_created": "🎉 Clan <b>{name}</b> created! Invite your friends with the next button.", "tm_cant": "You can't create a clan now (you're already in one).",
    "tm_admin_no": "Admins don't join clans (privacy).", "tm_none_yet": "No clans available yet. Be the first to create one!",
    "tm_pick": "🔍 Pick a clan to join:", "tm_joined": "🎉 You joined the clan!",
    "tm_join_gone": "That clan isn't available.", "tm_join_admin": "Admins don't join clans.", "tm_join_already": "You're already in it ✅",
    "tm_join_in_other": "You're in another clan, leave it first.", "tm_join_full": "The clan is full (30 members).",
    "tm_leave_ask": "Sure you want to leave the clan?", "tm_leave_yes": "Yes, leave", "tm_left": "You left the clan.",
    "tm_start_invite": "\n\n🛡 You're invited to join the clan <b>{name}</b> ({n}/{mx}).",
    "btn_teams": "🛡 My clan", "lbm_teams": "🛡 Clan ranking", "lbt_team_head": "🛡 <b>Clan ranking · {p}</b>\n<i>Total member XP</i>",
})

T["ar"]["pg_ach_count"] = "🏅 الإنجازات: {n}/{total}"
T["en"]["pg_ach_count"] = "🏅 Achievements: {n}/{total}"

T["ar"].update({
    "du_share_first": "⚔️ <b>تحدٍّ جديد: 7 أسئلة</b>\nأرسل الرابط لصديقك الآن، يقدر يقبل التحدي ويلعب نفس الأسئلة في أي وقت (قبلك أو بعدك). ثم اضغط «ابدأ» لتلعب أنت.",
    "du_go": "▶️ ابدأ أسئلتي", "du_rematch_sent": "✅ أرسلت له التحدي مباشرة أيضًا.",
    "du_wait_host": "⏳ انتهيت: <b>{c}/{n}</b>\nننتظر المضيف يخلّص أسئلته، وأرسل لك النتيجة فور انتهائه.",
})
T["en"].update({
    "du_share_first": "⚔️ <b>New duel: 7 questions</b>\nSend the link to your friend now; they can accept and play the same questions any time (before or after you). Then tap “Start” to play yours.",
    "du_go": "▶️ Start my questions", "du_rematch_sent": "✅ I also sent them the challenge directly.",
    "du_wait_host": "⏳ Done: <b>{c}/{n}</b>\nWaiting for the host to finish; I'll send you the result as soon as they do.",
})

T["ar"]["gp_final"] = "🏁 <b>انتهت اللعبة!</b>\n{w}\n👥 {n}\n\n{rows}"
T["en"]["gp_final"] = "🏁 <b>Game over!</b>\n{w}\n👥 {n}\n\n{rows}"
T["ar"].update({
    "gp_try_btn": "🔥 جرّب اختبار الأوتاكو وشوف مستواك الحقيقي!",
    "gp_leave": "↩️ إلغاء مشاركتي", "gp_left": "تم إلغاء مشاركتك ✅ تقدر تشارك ثانية قبل ما تبدأ الأسئلة",
    "gp_leave_late": "بدأت الأسئلة، ما تقدر تنسحب الآن", "gp_not_joined": "أنت غير مشارك أصلًا",
    "gp_cancel": "⛔ إلغاء اللعبة",
})
T["en"].update({
    "gp_try_btn": "🔥 Try the Otaku Quiz and see your real level!",
    "gp_leave": "↩️ Cancel my participation", "gp_left": "Your participation was cancelled ✅ You can join again before the questions start",
    "gp_leave_late": "The questions have started, you can't leave now", "gp_not_joined": "You haven't joined",
    "gp_cancel": "⛔ Cancel game",
})

T["ar"].update({
    "lb_hide_btn": "👁 إخفاء اسمي من الترتيب", "lb_show_btn": "👁 إظهار اسمي في الترتيب",
    "lb_hidden_note": "👻 أنت مخفي من الترتيب الآن. تقدر تظهر اسمك من الزر أسفل.",
    "lb_hide_on": "تم إخفاء اسمك من كل الترتيبات 👻", "lb_hide_off": "تم إظهار اسمك في الترتيب 👁",
    "lb_rank_of": "📍 ترتيبك: <b>#{rank}</b>", "lb_rank_none_q": "📍 ما دخلت الترتيب بعد، العب وكن منهم!",
    "tie_hint": "⚖️ عندك تقييم مساوٍ لبعض اللاعبين. تحدَّاهم لتحديد الأفضل (تُغلق المهلة بعد 5 ساعات):",
    "tie_btn": "⚔️ تحدَّ {name} ({score})",
    "tie_no": "لا يمكن هذا التحدي.", "tie_not": "التقييم لم يعد متساويًا.", "tie_hidden": "أحد الطرفين مخفي من الترتيب.",
    "tie_cooldown": "تحدّيت هذا اللاعب قبل قليل. جرّب بعد 24 ساعة.",
    "tie_invite": "⚖️ <b>{name}</b> عنده نفس تقييمك بالضبط! يتحداك لتحديد الأفضل بينكما.\n\n⏳ عندك <b>5 ساعات</b> تلعب فيها، وإن ما لعبت يُحسب الفوز لمن وصل لهذا التقييم أولًا.",
    "tie_timeout_win": "🏆 انتهت مهلة التحدي (5 ساعات) ولم يلعب {name}. وبما أنك وصلت لهذا التقييم أولًا، فأنت الأفضل وترتيبك أعلى منه الآن!",
    "tie_timeout_lose": "⏰ انتهت مهلة التحدي (5 ساعات) ولم تلعب، فاحتُسب الفوز لـ{name} لأنه وصل لهذا التقييم أولًا.",
    "tie_timeout_lose_played": "⏰ انتهت مهلة التحدي (5 ساعات) ولم يلعب الطرف الآخر، واحتُسب الفوز لـ{name} لأنه وصل لهذا التقييم أولًا.",
    "tie_share": "⚖️ تحدّيتك على أفضل تقييم! هل تقدر تثبت أنك الأفضل؟",
})
T["en"].update({
    "lb_hide_btn": "👁 Hide my name from rankings", "lb_show_btn": "👁 Show my name in rankings",
    "lb_hidden_note": "👻 You're hidden from the rankings. Show your name with the button below.",
    "lb_hide_on": "Your name is hidden from all rankings 👻", "lb_hide_off": "Your name is shown in rankings 👁",
    "lb_rank_of": "📍 Your rank: <b>#{rank}</b>", "lb_rank_none_q": "📍 You're not on the board yet, play and join in!",
    "tie_hint": "⚖️ Some players have the exact same score as you. Challenge them to find the best (the window closes after 5 hours):",
    "tie_btn": "⚔️ Challenge {name} ({score})",
    "tie_no": "This challenge isn't possible.", "tie_not": "Your scores are no longer tied.", "tie_hidden": "One of you is hidden from the rankings.",
    "tie_cooldown": "You challenged this player recently. Try again in 24 hours.",
    "tie_invite": "⚖️ <b>{name}</b> has the exact same score as you! They challenge you to decide who's the best.\n\n⏳ You have <b>5 hours</b> to play; if you don't, the win goes to whoever reached this score first.",
    "tie_timeout_win": "🏆 The 5-hour window closed and {name} didn't play. You reached this score first, so you're the best and rank above them now!",
    "tie_timeout_lose": "⏰ The 5-hour window closed and you didn't play, so the win went to {name} who reached this score first.",
    "tie_timeout_lose_played": "⏰ The 5-hour window closed and the other side didn't play; the win went to {name} who reached this score first.",
    "tie_share": "⚖️ I challenged you on our top score! Can you prove you're the best?",
})

T["ar"].update({"gp_top_week": "📅 <b>متصدرو المجموعة · هذا الأسبوع</b>", "gp_top_all": "🌍 <b>متصدرو المجموعة · كل الأوقات</b>"})
T["en"].update({"gp_top_week": "📅 <b>Group top · This week</b>", "gp_top_all": "🌍 <b>Group top · All time</b>"})

T["ar"].update({
    "btn_persona": "🧬 نمط الشخصية", "ps_go": "ابدأ الاختبار",
    "ps_intro": "🧬 <b>اختبار نمط الشخصية</b>\n{n} سؤالًا قصيرًا. جاوب بدون تفكير طويل، وقيّم كل عبارة من 1 (لا تنطبق عليّ) إلى 5 (تنطبق عليّ تمامًا).\nالنتيجة تُظهر لك قربك من كل جانب، وشخصيات أنمي من نفس النمط.",
    "ps_q": "🧬 <b>سؤال {n}/{total}</b>\n{q}\n\n<i>1 = لا تنطبق عليّ · 5 = تنطبق عليّ تمامًا</i>",
    "ps_back": "↩️ السؤال السابق", "ps_again": "🔄 أعد الاختبار",
    "ps_res_head": "🧬 <b>نمط شخصيتك: {code}</b>",
    "ps_closer": "↳ أقرب إلى <b>{side}</b> ({pct}%)",
    "ps_anime_head": "🎭 <b>شخصيات أنمي من نمط {code}</b> (أشهر 10):",
    "ps_anime_soon": "🎭 قائمة شخصيات هذا النمط قيد الإعداد.",
})
T["en"].update({
    "btn_persona": "🧬 Personality type", "ps_go": "Start the test",
    "ps_intro": "🧬 <b>Personality type test</b>\n{n} short statements. Answer quickly, rate each from 1 (doesn't describe me) to 5 (describes me perfectly).\nYou'll see how close you are to each side, and anime characters of the same type.",
    "ps_q": "🧬 <b>Question {n}/{total}</b>\n{q}\n\n<i>1 = not me · 5 = very much me</i>",
    "ps_back": "↩️ Previous question", "ps_again": "🔄 Retake the test",
    "ps_res_head": "🧬 <b>Your type: {code}</b>",
    "ps_closer": "↳ Closer to <b>{side}</b> ({pct}%)",
    "ps_anime_head": "🎭 <b>Anime characters of type {code}</b> (top 10):",
    "ps_anime_soon": "🎭 The character list for this type is coming soon.",
})

T["ar"]["mf_title"] = '🎌 <b>「 المافيا 」</b>\n<i>لعبة الظلال والخيانة</i>'
T["ar"]['mf_host'] = '🎩 المضيف: {h}'
T["ar"]['mf_killers'] = 'القتلة'
T["ar"]['mf_killers_btn'] = '🔪 القتلة: {k}'
T["ar"]['mf_players'] = '👥 المنضمون ({n}): {names}'
T["ar"]['mf_left'] = '⏳ تبدأ بعد {s} ثانية، ويلزم {min} لاعبين على الأقل'
T["ar"]["mf_howto"] = '📖 <b>كيف تلعب المافيا؟</b>\n🎯 <b>الهدف:</b> المواطنون يكشفون القتلة ويطردونهم، والقتلة يقتلون حتى يتساووا مع الباقين.\n1️⃣ انضم بزر «انضم». عند البدء تصلك رسالة خاصة فيها دورك (سرّي).\n2️⃣ <b>الليل:</b> القتلة يختارون ضحية، والطبيب يحمي، والمحقق يكشف فريقًا. كل ذلك من الخاص بالأزرار.\n3️⃣ <b>الصباح:</b> يُعلن من قُتل، أو أن الضحية كانت محمية.\n4️⃣ <b>النهار:</b> ناقشوا في المجموعة، ثم كل حي يصوّت لطرد من يشتبه به، أو يضغط «تخطّي».\n⚖️ يُطرد صاحب <b>الأصوات الأكثر</b>، وإن تعادل الأعلى لا يُطرد أحد.\n⏳ إذا مرت 3 جولات بدون قتل ولا طرد، يختار النظام لاعبًا عشوائيًا يخرج.\n🏆 المواطنون يفوزون بطرد كل القتلة، والقتلة يفوزون إذا تساووا مع الباقين.'
T["ar"]['mf_join'] = '✋ انضم'
T["ar"]['mf_leave'] = '🚪 انسحب'
T["ar"]['mf_start'] = '▶️ ابدأ'
T["ar"]['mf_cancel'] = '⛔ إلغاء'
T["ar"]["mf_skip"] = '⏭ تخطّي (ما عندي شك)'
T["ar"]['mf_r_citizen'] = 'مواطن'
T["ar"]['mf_r_killer'] = 'القاتل'
T["ar"]['mf_r_detective'] = 'المحقق'
T["ar"]['mf_r_doctor'] = 'الطبيب'
T["ar"]['mf_r_joker'] = 'المجنون'
T["ar"]['mf_desc_citizen'] = 'أنت مواطن عادي، لا قدرة لك ليلًا. في النهار ناقش وصوّت لطرد من تشك أنه من المافيا. هدفك كشف القتلة.'
T["ar"]['mf_desc_killer'] = 'أنت من المافيا 🔪. كل ليلة يختار القتلة ضحية من الأزرار هنا، والأكثر أصواتًا يُقتل. لا تكشف نفسك في النهار.'
T["ar"]['mf_desc_detective'] = '🔍 كل ليلة اختر لاعبًا لتعرف فريقه (مافيا أو مواطنون). النتيجة تصلك فورًا. لا تكشف نفسك للقتلة.'
T["ar"]['mf_desc_doctor'] = '🩺 كل ليلة اختر لاعبًا لتحميه من القتل، ويمكنك حماية نفسك.'
T["ar"]['mf_desc_joker'] = '🃏 هدفك وحدك: أن يطردك الناس بالتصويت. لا قدرة لك ليلًا. إن طُردت تفوز وحدك.'
T["ar"]['mf_team_town'] = '👥 المواطنون'
T["ar"]['mf_team_mafia'] = '🔪 المافيا'
T["ar"]['mf_team_solo'] = '🃏 لاعب منفرد'
T["ar"]['mf_too_few'] = '❌ لم يكتمل العدد ({min} لاعبين على الأقل). جرّب مرة أخرى بـ /mafia'
T["ar"]['mf_config_err'] = '❌ الإعدادات غير مقبولة: {e}'
T["ar"]['mf_role_dm'] = '{icon} <b>دورك: {role}</b>\n\n{desc}\n\nفريقك: {team}\n\n<i>الأدوار سرّية حتى نهاية اللعبة، لا تكشفها.</i>'
T["ar"]['mf_dm_fail'] = '❌ ما قدرت أرسل الأدوار لبعض اللاعبين ({names}). يجب أن يفتحوا البوت بالخاص أولًا، ثم تعيدوا اللعب.'
T["ar"]['mf_n_killer'] = '🔪 اختر ضحية الليلة (زملاؤك يختارون معك، والأكثر أصواتًا يُقتل):'
T["ar"]['mf_n_doctor'] = '🩺 اختر من تحميه الليلة:'
T["ar"]['mf_n_detective'] = '🔍 اختر من تكشف فريقه:'
T["ar"]["mf_night_live"] = '🌙 <b>「 الليلة {r} · ظلام القرية 」</b>\n━━━━━━━━━━━━━━━━\n⏳ {s} ثانية\n👥 الأحياء ({n}):\n{names}\n━━━━━━━━━━━━━━━━\n<i>القتلة يتهامسون في الظلام… والطبيب يترقب، والمحقق يبحث عن الحقيقة. الباقون ينتظرون الفجر.</i>'
T["ar"]["mf_day_live"] = '☀️ <b>「 النهار {r} · حكم الجماعة 」</b>\n━━━━━━━━━━━━━━━━\n⏳ {s} ثانية\n👥 الأحياء:\n{names}\n━━━━━━━━━━━━━━━━\n⚖️ <i>من تشك فيه؟ اضغط اسمه… أو «تخطّي» إن كنت ما تزال تتردد. يُطرد الأكثر أصواتًا، والتعادل على الأعلى = لا طرد.</i>'
T["ar"]["mf_morning_dead"] = '💀 <b>「 سقط {name} في الظلام… 」</b>\nضربة القاتل لم تُرحم، والقرية تستيقظ على الفاجعة.'
T["ar"]["mf_morning_saved"] = '🛡 <b>「 ضربة القاتل ارتدت… 」</b>\nالطبيب سبق السكين في اللحظة الأخيرة، ونجا الضحية من الموت.'
T["ar"]["mf_morning_quiet"] = '🌅 <b>「 فجر هادئ… أو هذا ما يبدو 」</b>\nلم يسقط أحد الليلة، لكن الخوف يتسلل بين الجميع.'
T["ar"]["mf_executed"] = '⚖️ <b>「 حُكم عليه بالتصويت 」</b>\n<b>{name}</b> سقط في ساحة الحكم، ودوره يبقى سرًّا حتى النهاية.'
T["ar"]["mf_no_exec"] = '⚖️ <b>「 لم يُحسم الحكم 」</b>\nالأصوات تفرّقت، ولم يُطرد أحد اليوم.'
T["ar"]['mf_detect_res'] = '🔍 النتيجة: <b>{name}</b> من فريق {team}.'
T["ar"]["mf_end_town"] = '🎉 <b>「 انتهت الحكاية… فاز المواطنون 」</b>\nتم القضاء على كل القتلة، ونجت القرية.'
T["ar"]["mf_end_mafia"] = '🔪 <b>「 انتهت الحكاية… فازت المافيا 」</b>\nتساوى القتلة مع الباقين، وسقطت القرية في الظلام.'
T["ar"]['mf_end_solo'] = '🃏 فاز المجنون وحده!'
T["ar"]["mf_end_draw"] = '🤝 <b>「 انتهت الحكاية بالتعادل 」</b>\nوصلت اللعبة للحد الأقصى من الجولات دون حسم.'
T["ar"]['mf_end'] = '🏁 <b>انتهت اللعبة!</b>\n{head}\n\n<b>الأدوار:</b>\n{reveal}\n\n<i>الجولات: {rounds}</i>'
T["ar"]["mf_stopped"] = '⛔ <b>「 توقفت الحكاية قبل نهايتها 」</b>\nأُلغيت اللعبة.'
T["ar"]['mf_quit_live'] = '🚪 {name} غادر اللعبة وخرج منها.'
T["ar"]['mf_busy'] = '⏳ فيه لعبة شغالة في هذه المجموعة الآن.'
T["ar"]['mf_cool'] = '⏱ انتظر قليلًا قبل لعبة مافيا جديدة.'
T["ar"]['mf_gone'] = 'هذه اللعبة انتهت أو غير موجودة.'
T["ar"]['mf_already'] = 'أنت منضم بالفعل ✅'
T["ar"]['mf_full'] = 'اكتمل العدد الأقصى للاعبين.'
T["ar"]['mf_joined_toast'] = 'انضممت ✅ ستصلك رسالة خاصة بدورك عند البدء.'
T["ar"]['mf_left_toast'] = 'تم إلغاء انضمامك.'
T["ar"]['mf_not_in'] = 'أنت لست منضمًا.'
T["ar"]['mf_quit_toast'] = 'خرجت من اللعبة.'
T["ar"]['mf_host_only'] = 'هذا الزر للمضيف أو أدمن المجموعة.'
T["ar"]['mf_info_toast'] = 'الليلة: القتلة والطبيب والمحقق يتصرفون بالخاص بالأزرار. انتظر النتيجة في الصباح.'
T["ar"]['mf_late'] = 'انتهى وقت هذا الإجراء ⌛'
T["ar"]['mf_not_alive'] = 'الميت لا يصوّت.'
T["ar"]['mf_bad_target'] = 'هذا الاختيار غير صالح.'
T["ar"]['mf_voted'] = 'تم تسجيل صوتك ✅ (تقدر تغيّره قبل انتهاء الوقت)'
T["ar"]['mf_not_yours'] = 'هذا الزر ليس لدورك.'
T["ar"]['mf_pick_saved'] = 'تم تسجيل اختيارك: {name}'
T["ar"]['mf_no_channels'] = 'ما عندك قنوات مرتبطة. أضف البوت أدمن في قناتك ثم حاول.'
T["ar"]['mf_pick_channel'] = '📢 اختر القناة لبدء لعبة المافيا فيها:'
T["ar"]['mf_channel_started'] = '✅ نُشرت لعبة المافيا في القناة. تحكّم منها بالأزرار هناك.'
T["en"]['mf_title'] = '🎌 <b>Mafia · Anime game</b>'
T["en"]['mf_host'] = '🎩 Host: {h}'
T["en"]['mf_killers'] = 'Killers'
T["en"]['mf_killers_btn'] = '🔪 Killers: {k}'
T["en"]['mf_players'] = '👥 Players ({n}): {names}'
T["en"]['mf_left'] = '⏳ Starts in {s}s, at least {min} players needed'
T["en"]["mf_howto"] = '📖 <b>How to play Mafia</b>\n🎯 <b>Goal:</b> Citizens find and eliminate the killers; killers win when they equal the rest.\n1️⃣ Join with «Join». At the start you get a private message with your secret role.\n2️⃣ <b>Night:</b> killers pick a victim; the doctor and guard protect; the detective checks a team. All privately, with buttons.\n3️⃣ <b>Morning:</b> the result is announced: who was killed, or that the target was protected.\n4️⃣ <b>Day:</b> discuss in the group, then every living player votes to eliminate a suspect, or taps «Skip».\n⚖️ The player with the <b>most votes</b> is eliminated; a tie for first means nobody is.\n⏳ If 3 rounds pass with no death or vote, the game picks a random player to leave.\n🏆 Citizens win by eliminating all killers; killers win when they equal the rest.'
T["en"]['mf_join'] = '✋ Join'
T["en"]['mf_leave'] = '🚪 Leave'
T["en"]['mf_start'] = '▶️ Start'
T["en"]['mf_cancel'] = '⛔ Cancel'
T["en"]["mf_skip"] = '⏭ Skip (no suspect)'
T["en"]['mf_r_citizen'] = 'Citizen'
T["en"]['mf_r_killer'] = 'Killer'
T["en"]['mf_r_detective'] = 'Detective'
T["en"]['mf_r_doctor'] = 'Doctor'
T["en"]['mf_r_joker'] = 'Joker'
T["en"]['mf_desc_citizen'] = "You're a citizen with no night power. In the day, discuss and vote to eliminate who you think is mafia."
T["en"]['mf_desc_killer'] = "You're mafia 🔪. Each night the killers pick a victim with these buttons; the most-voted dies. Don't reveal yourself by day."
T["en"]['mf_desc_detective'] = '🔍 Each night pick a player to learn their team (mafia or citizens). You get the result instantly.'
T["en"]['mf_desc_doctor'] = '🩺 Each night pick a player to protect from being killed; you may protect yourself.'
T["en"]['mf_desc_joker'] = "🃏 Your goal alone: be voted out by the people. You have no night power. If you're voted out, you win alone."
T["en"]['mf_team_town'] = '👥 Citizens'
T["en"]['mf_team_mafia'] = '🔪 Mafia'
T["en"]['mf_team_solo'] = '🃏 Lone player'
T["en"]['mf_too_few'] = '❌ Not enough players (at least {min}). Try again with /mafia'
T["en"]['mf_config_err'] = '❌ Invalid settings: {e}'
T["en"]['mf_role_dm'] = "{icon} <b>Your role: {role}</b>\n\n{desc}\n\nYour team: {team}\n\n<i>Roles stay secret until the end, don't reveal yours.</i>"
T["en"]['mf_dm_fail'] = "❌ I couldn't send roles to some players ({names}). They must open the bot privately first, then restart the game."
T["en"]['mf_n_killer'] = "🔪 Pick tonight's victim (your fellow killers choose too; the most-voted dies):"
T["en"]['mf_n_doctor'] = '🩺 Pick who to protect tonight:'
T["en"]['mf_n_detective'] = '🔍 Pick whose team to check:'
T["en"]["mf_night_live"] = '🌙 <b>Night {r}</b>\n⏳ {s}s\n👥 Alive ({n}): {names}\n\n<i>Killers, doctor and detective act in private. Everyone else waits for morning.</i>'
T["en"]["mf_day_live"] = '☀️ <b>Day {r}</b>\n⏳ {s}s\n👥 Alive: {names}\n\n🗳 Tap the name of your suspect, or «Skip» if you have none. The player with the most votes is eliminated; a tie for first means nobody is.'
T["en"]['mf_morning_dead'] = '🔪 <b>{name}</b> was killed by the mafia 💀'
T["en"]['mf_morning_saved'] = '🛡 The mafia tried to kill someone tonight, but the target was protected!'
T["en"]['mf_morning_quiet'] = '☀️ A quiet night… nobody died.'
T["en"]['mf_executed'] = '⚖️ <b>{name}</b> was voted out. (Their role stays secret until the end)'
T["en"]['mf_no_exec'] = '⚖️ No majority, nobody was eliminated today.'
T["en"]['mf_detect_res'] = '🔍 Result: <b>{name}</b> is on the {team} side.'
T["en"]['mf_end_town'] = '🎉 Citizens win! All killers are gone.'
T["en"]['mf_end_mafia'] = '🔪 The mafia wins! They equal the citizens.'
T["en"]['mf_end_solo'] = '🃏 The Joker wins alone!'
T["en"]['mf_end_draw'] = '🤝 Draw (the round limit was reached).'
T["en"]['mf_end'] = '🏁 <b>Game over!</b>\n{head}\n\n<b>Roles:</b>\n{reveal}\n\n<i>Rounds: {rounds}</i>'
T["en"]['mf_stopped'] = '⛔ The game was cancelled.'
T["en"]['mf_quit_live'] = '🚪 {name} left the game.'
T["en"]['mf_busy'] = '⏳ A game is already running in this group.'
T["en"]['mf_cool'] = '⏱ Wait a moment before a new mafia game.'
T["en"]['mf_gone'] = "This game ended or doesn't exist."
T["en"]['mf_already'] = "You're already in ✅"
T["en"]['mf_full'] = 'The game is full.'
T["en"]['mf_joined_toast'] = "Joined ✅ you'll get a private message with your role at start."
T["en"]['mf_left_toast'] = 'Your join was cancelled.'
T["en"]['mf_not_in'] = "You haven't joined."
T["en"]['mf_quit_toast'] = 'You left the game.'
T["en"]['mf_host_only'] = 'Only the host or a group admin can use this.'
T["en"]['mf_info_toast'] = 'At night killers, doctor and detective act privately with buttons. Wait for the result in the morning.'
T["en"]['mf_late'] = "This action's time is up ⌛"
T["en"]['mf_not_alive'] = "The dead can't vote."
T["en"]['mf_bad_target'] = "That choice isn't valid."
T["en"]['mf_voted'] = 'Vote recorded ✅ (you can change it before time runs out)'
T["en"]['mf_not_yours'] = "This button isn't for your role."
T["en"]['mf_pick_saved'] = 'Choice recorded: {name}'
T["en"]['mf_no_channels'] = 'You have no linked channels. Add the bot as admin in your channel first.'
T["en"]['mf_pick_channel'] = '📢 Pick the channel to start a mafia game in:'
T["en"]['mf_channel_started'] = '✅ The mafia game is posted in the channel. Control it with the buttons there.'

T["ar"]["btn_mafia_channel"] = "🔪 مافيا في قناة"
T["en"]["btn_mafia_channel"] = "🔪 Mafia in a channel"

T["ar"]['sp_title'] = '🎭 <b>برا السالفة · أنمي</b>'
T["ar"]['sp_host'] = '🎩 المضيف: {h}'
T["ar"]['sp_players'] = '👥 المنضمون ({n}): {names}'
T["ar"]['sp_left'] = 'تم إلغاء انضمامك'
T["ar"]['sp_howto'] = '📖 <b>كيف تلعب؟</b>\nالجميع يعرف شخصية أنمي واحدة… إلا لاعب واحد هو <b>برا السالفة</b> ما يعرفها.\n🔁 10 جولات: المضيف يضغط «التالي»، ويختار البوت من يسأل ومن يجيب (في المجموعة).\n🗳 بعدها تصوّتون في الخاص على من برا السالفة، ولو لم تكتشفوه يكمل اللعب.\n🎯 برا السالفة إن انكشف يخمّن الشخصية من قائمة.'
T["ar"]['sp_join'] = '✋ انضم'
T["ar"]['sp_leave'] = '🚪 انسحب'
T["ar"]['sp_start'] = '▶️ ابدأ'
T["ar"]['sp_cancel'] = '⛔ إلغاء'
T["ar"]['sp_too_few'] = '❌ لم يكتمل العدد ({min} لاعبين على الأقل).'
T["ar"]['sp_joined'] = 'انضممت ✅'
T["ar"]['sp_already'] = 'أنت منضم بالفعل ✅'
T["ar"]['sp_full'] = 'اكتمل العدد الأقصى.'
T["ar"]['sp_gone'] = 'هذه اللعبة انتهت أو غير موجودة.'
T["ar"]['sp_host_only'] = 'هذا الزر للمضيف أو أدمن المجموعة.'
T["ar"]['sp_busy'] = '⏳ فيه لعبة برا السالفة شغالة في المجموعة.'
T["ar"]['sp_cool'] = '⏱ انتظر قليلًا قبل لعبة جديدة.'
T["ar"]['sp_roles_done'] = '🎬 <b>تم توزيع الأدوار</b> ({n} لاعبين). تحقّقوا من رسائلكم الخاصة.'
T["ar"]['sp_in_dm'] = '🎭 <b>شخصية السالفة هي:</b> {char}\n\nالجميع يعرفها ما عدا شخص واحد حاول تكتشف مين الشخص الي ما يعرف الشخصية منكم عن طريق انك تساله اسئلة بدون ما تقرب له بزيادة.'
T["ar"]['sp_out_dm'] = '🕵️ <b>أنت برا السالفة!</b>\nما تعرف الشخصية. استمع للأسئلة والأجوبة وحاول تكتشفها، ولا تكشف نفسك.'
T["ar"]['sp_dm_fail'] = '❌ ما قدرت أرسل الأدوار لبعض اللاعبين ({names}). يجب أن يفتحوا البوت بالخاص أولًا.'
T["ar"]['sp_next_btn'] = '▶️ التالي'
T["ar"]['sp_next_live'] = '🔄 <b>الجولة {r}/{total}</b> · {label}\n\nالمضيف يضغط «التالي» لبدء الجولة (وإن ما ضغط تبدأ تلقائيًا بعد دقيقة).'
T["ar"]['sp_round_label'] = 'سؤال وجواب'
T["ar"]['sp_extra_label'] = 'جولة إضافية {e}'
T["ar"]['sp_ask_live'] = '❓ <b>الجولة {r}</b>\n\n<b>{a}</b>\n⬇️ يسأل\n<b>{b}</b>\n\nاكتب سؤالك في المجموعة الآن.'
T["ar"]['sp_answer_live'] = '<b>{a}</b>\n⬇️ اسأل\n<b>{b}</b>'
T["ar"]['sp_no_question'] = '⏭ {a} ما سأل بوقته، نكمل.'
T["ar"]['sp_no_answer'] = '⏭ {b} ما جاوب بوقته، نكمل.'
T["ar"]['sp_no_name'] = '🚫 {a}: لا تكتب اسم الشخصية في المجموعة، حذفت رسالتك.'
T["ar"]['sp_no_delete'] = '⚠️ الرسالة تحتوي اسم الشخصية، لكن ما أقدر أحذفها. اكتب بدون اسم الشخصية.'
T["ar"]['sp_choose_live'] = '🗳 <b>انتهت الجولات</b> ({n} لاعبين، إضافية {extra}/{max})\nاختاروا: تصويت أم جولة إضافية؟ (لازم أكثر من نصف اللاعبين على التصويت).'
T["ar"]['sp_vote_btn'] = '🗳 تصويت'
T["ar"]['sp_more_btn'] = '➕ أكمل أسئلة'
T["ar"]['sp_chosen'] = 'تم تسجيل اختيارك ✅'
T["ar"]['sp_vote_dm'] = '🗳 <b>صوّت على برا السالفة:</b> اختر اللاعب الذي تظن أنه ما يعرف الشخصية.'
T["ar"]['sp_revote_live'] = '⚖️ تعادل التصويت. إعادة تصويت بين المتعادلين في الخاص.'
T["ar"]['sp_bad_vote'] = 'هذا التصويت غير صالح.'
T["ar"]['sp_voted'] = 'صوتك على {name} ✅'
T["ar"]['sp_caught'] = '🕵️ <b>تم كشف برا السالفة:</b> {name}!\nيخمّن الآن الشخصية من القائمة ({s} ثانية).'
T["ar"]['sp_guess_live'] = '🎯 <b>{name}</b> يختار الشخصية التي يظنها هي السالفة ({s} ثانية):'
T["ar"]['sp_guess_saved'] = 'تم استلام تخمينك ✅'
T["ar"]['sp_not_outsider'] = 'فقط برا السالفة المكشوف يخمّن.'
T["ar"]['sp_guessed'] = '🎯 تخمينه: {g}'
T["ar"]['sp_end_out_win'] = '🏆 فاز <b>برا السالفة</b>!'
T["ar"]['sp_end_team_win'] = '🎉 فاز <b>المواطنون</b> (داخل السالفة)!'
T["ar"]['sp_end'] = '🏁 <b>انتهت برا السالفة!</b>\n{head}\n\nالشخصية كانت: <b>{char}</b>\nبرا السالفة: <b>{out}</b>\n\nنقاط الترتيب: الفائز 100، والبقية 0 (الأدمن لا يُحسب).'
T["ar"]['sp_stopped'] = '⛔ أُلغيت اللعبة.'
T["en"]['sp_title'] = '🎭 <b>Outside the Story · Anime</b>'
T["en"]['sp_host'] = '🎩 Host: {h}'
T["en"]['sp_players'] = '👥 Players ({n}): {names}'
T["en"]['sp_left'] = 'Your join was cancelled'
T["en"]['sp_howto'] = "📖 <b>How to play</b>\nEveryone knows one anime character… except one player: <b>outside the story</b>, who doesn't.\n🔁 10 rounds: the host presses “Next”, the bot picks who asks and who answers (in the group).\n🗳 Then you vote in private on who's outside; if nobody is caught, the game goes on.\n🎯 If caught, the outsider guesses the character from a list."
T["en"]['sp_join'] = '✋ Join'
T["en"]['sp_leave'] = '🚪 Leave'
T["en"]['sp_start'] = '▶️ Start'
T["en"]['sp_cancel'] = '⛔ Cancel'
T["en"]['sp_too_few'] = '❌ Not enough players (at least {min}).'
T["en"]['sp_joined'] = 'Joined ✅'
T["en"]['sp_already'] = "You're already in ✅"
T["en"]['sp_full'] = 'The game is full.'
T["en"]['sp_gone'] = "This game ended or doesn't exist."
T["en"]['sp_host_only'] = 'Only the host or a group admin can use this.'
T["en"]['sp_busy'] = '⏳ A game is already running in this group.'
T["en"]['sp_cool'] = '⏱ Wait a moment before a new game.'
T["en"]['sp_roles_done'] = '🎬 <b>Roles are distributed</b> ({n} players). Check your private messages.'
T["en"]['sp_in_dm'] = '🎭 <b>The story character is:</b> {char}\n\nEveryone knows it except one person. Try to find out who doesn\'t know the character by asking questions without getting too close to them.'
T["en"]['sp_out_dm'] = "🕵️ <b>You're outside the story!</b>\nYou don't know the character. Listen to the questions and answers, figure it out, and don't reveal yourself."
T["en"]['sp_dm_fail'] = "❌ I couldn't send roles to some players ({names}). They must open the bot privately first."
T["en"]['sp_next_btn'] = '▶️ Next'
T["en"]['sp_next_live'] = '🔄 <b>Round {r}/{total}</b> · {label}\n\nThe host presses “Next” to start the round (it starts by itself after a minute otherwise).'
T["en"]['sp_round_label'] = 'question & answer'
T["en"]['sp_extra_label'] = 'extra round {e}'
T["en"]['sp_ask_live'] = '❓ <b>Round {r}</b>\n\n<b>{a}</b>\n⬇️ asks\n<b>{b}</b>\n\nWrite your question in the group now.'
T["en"]['sp_answer_live'] = '<b>{a}</b>\n⬇️ ask\n<b>{b}</b>'
T["en"]['sp_no_question'] = "⏭ {a} didn't ask in time, moving on."
T["en"]['sp_no_answer'] = "⏭ {b} didn't answer in time, moving on."
T["en"]['sp_no_name'] = "🚫 {a}: don't type the character's name in the group, your message was deleted."
T["en"]['sp_no_delete'] = "⚠️ That message contains the character's name and I can't delete it. Write without the name."
T["en"]['sp_choose_live'] = '🗳 <b>Rounds are over</b> ({n} players, extra {extra}/{max})\nVote now or keep asking? Voting needs more than half of the players.'
T["en"]['sp_vote_btn'] = '🗳 Vote'
T["en"]['sp_more_btn'] = '➕ Keep asking'
T["en"]['sp_chosen'] = 'Choice recorded ✅'
T["en"]['sp_vote_dm'] = "🗳 <b>Vote for the one outside the story:</b> pick the player you think doesn't know the character."
T["en"]['sp_revote_live'] = '⚖️ Tie. A re-vote among the tied players is in private.'
T["en"]['sp_bad_vote'] = "That vote isn't valid."
T["en"]['sp_voted'] = 'Your vote for {name} ✅'
T["en"]['sp_caught'] = '🕵️ <b>Outsider caught:</b> {name}!\nThey now guess the character from the list ({s}s).'
T["en"]['sp_guess_live'] = '🎯 <b>{name}</b> picks the character they think it is ({s}s):'
T["en"]['sp_guess_saved'] = 'Guess received ✅'
T["en"]['sp_not_outsider'] = 'Only the caught outsider can guess.'
T["en"]['sp_guessed'] = '🎯 Their guess: {g}'
T["en"]['sp_end_out_win'] = '🏆 <b>The outsider</b> wins!'
T["en"]['sp_end_team_win'] = '🎉 <b>The insiders</b> win!'
T["en"]['sp_end'] = '🏁 <b>Outside the Story is over!</b>\n{head}\n\nThe character was: <b>{char}</b>\nOutsider: <b>{out}</b>\n\nRanking points: winner 100, others 0 (admins excluded).'
T["en"]['sp_stopped'] = '⛔ The game was cancelled.'

T["ar"]['sw_btn'] = '🎭 تبادل الشخصيات'
T["ar"]['sw_guess_btn'] = '🎯 خمّنت شخصيتي'
T["ar"]['sw_quit_btn'] = '🏳 استسلم'
T["ar"]['sw_invite_text'] = '🎭 <b>تبادل الشخصيات</b>\nأرسل الرابط لصديقك. أول ما يقبل تتوزع الشخصيات: كل واحد يعرف شخصية صاحبه ولا يعرف شخصيته.\nاسألوا بعض بأي طريقة تبون، وأول من يخمّن شخصيته يفوز.'
T["ar"]['sw_share_btn'] = '📤 أرسل لصديق'
T["ar"]['sw_share_text'] = 'تعال نلعب تبادل الشخصيات 🎭 أنا أعرف شخصيتك وأنت تعرف شخصيتي… من يخمّن أولًا؟'
T["ar"]['sw_accept_ask'] = '🎭 <b>{name}</b> يتحداك بتبادل الشخصيات. تقبل؟'
T["ar"]['sw_accept_btn'] = '✅ اقبل التحدي'
T["ar"]['sw_start'] = '🎭 <b>بدأ التحدي!</b>\nشخصيتك: <i>لا تعرفها</i>\nشخصية صاحبك: <b>{other}</b>\n\nاسأل صاحبك عن شخصيتك (وهو يعرف شخصيتك ويجاوب بصدق). أول من يخمّن شخصيته يفوز.'
T["ar"]['sw_guess_ask'] = '🎯 اكتب اسم الشخصية اللي تظن أنها شخصيتك (بالعربي أو الإنجليزي):'
T["ar"]['sw_wrong'] = '❌ ليست هي. كمّل تسأل!'
T["ar"]['sw_cooldown'] = '⏱ انتظر {s} ثانية بين كل تخمين وآخر.'
T["ar"]['sw_busy'] = 'أنت في تحدٍّ شخصيات آخر الآن.'
T["ar"]['sw_gone'] = 'هذا التحدي انتهى أو غير موجود.'
T["ar"]['sw_win'] = '🏆 <b>فزت!</b>'
T["ar"]['sw_lose'] = '😅 <b>خسرت هذه المرة</b>'
T["ar"]['sw_end'] = '{head}\nشخصيتك كانت: <b>{own}</b>\nشخصية صاحبك: <b>{other}</b>'
T["en"]['sw_btn'] = '🎭 Swap characters'
T["en"]['sw_guess_btn'] = '🎯 I guessed my character'
T["en"]['sw_quit_btn'] = '🏳 Give up'
T["en"]['sw_invite_text'] = "🎭 <b>Swap characters</b>\nSend the link to your friend. Once they accept, each of you gets the other's character without knowing your own.\nAsk each other however you like; the first to guess their own character wins."
T["en"]['sw_share_btn'] = '📤 Send to a friend'
T["en"]['sw_share_text'] = "Let's play Swap Characters 🎭 I know yours and you know mine… who guesses first?"
T["en"]['sw_accept_ask'] = '🎭 <b>{name}</b> challenges you to Swap Characters. Accept?'
T["en"]['sw_accept_btn'] = '✅ Accept'
T["en"]['sw_start'] = "🎭 <b>The challenge begins!</b>\nYour character: <i>unknown to you</i>\nYour friend's character: <b>{other}</b>\n\nAsk your friend about yours (they know it and answer honestly). First to guess their own wins."
T["en"]['sw_guess_ask'] = '🎯 Type the character you think is yours (Arabic or English):'
T["en"]['sw_wrong'] = '❌ Not it. Keep asking!'
T["en"]['sw_cooldown'] = '⏱ Wait {s} seconds between guesses.'
T["en"]['sw_busy'] = "You're already in another character swap."
T["en"]['sw_gone'] = "This challenge ended or doesn't exist."
T["en"]['sw_win'] = '🏆 <b>You won!</b>'
T["en"]['sw_lose'] = '😅 <b>You lost this time</b>'
T["en"]['sw_end'] = "{head}\nYour character was: <b>{own}</b>\nYour friend's character: <b>{other}</b>"

T["ar"]['btn_online'] = '🌐 لعب أونلاين'
T["ar"]['on_menu'] = '🌐 <b>لعب أونلاين</b>\nاختر اللعبة، وأوّل لاعب يلاقيك في الطابور تتنافسون على نفس الأسئلة. الأفضل يفوز، وتظهر النتيجة لكم الاثنين.'
T["ar"]['on_kind_quiz'] = '🎯 أسئلة أنمي'
T["ar"]['on_kind_tf'] = '✅❌ صح أم غلط'
T["ar"]['on_busy'] = 'أنت في مباراة أو في الطابور.'
T["ar"]['on_waiting'] = '⏳ تنتظر منافسًا في <b>{kind}</b>. أول لاعب يدخل نفس اللعبة يلاقيك تلقائيًا (ينتهي الانتظار بعد {s} ثانية).'
T["ar"]['on_cancel'] = '❌ إلغاء الانتظار'
T["ar"]['on_cancelled'] = 'تم إلغاء الانتظار.'
T["ar"]['on_timeout'] = '⏱ ما لقينا منافسًا هالمرة. جرّب مرة ثانية.'
T["ar"]['on_started'] = '⚔️ <b>بدأت المباراة</b> ({kind})! نفس الأسئلة للطرفين. كل سؤال له {secs} ثانية.'
T["ar"]['on_round'] = '<b>السؤال {n}/{total}</b> · ⏱ {secs}s\nالنتيجة: أنت {a} — المنافس {b}\n\n{q}\n\n{opts}'
T["ar"]['on_reveal_ok'] = '✅ إجابتك صحيحة!\nالجواب: <b>{right}</b>'
T["ar"]['on_reveal_bad'] = '❌ إجابتك غلط أو ما جاوبت.\nالجواب: <b>{right}</b>'
T["ar"]['on_forfeit'] = '🏳 انسحب'
T["ar"]['on_late'] = 'انتهى وقت هذا السؤال ⌛'
T["ar"]['on_already'] = 'جاوبت على هذا السؤال ✅'
T["ar"]['on_saved'] = 'تم تسجيل إجابتك ✅'
T["ar"]['on_win'] = '🏆 <b>فزت!</b>'
T["ar"]['on_lose'] = '😅 <b>خسرت</b>'
T["ar"]['on_draw'] = '🤝 <b>تعادل!</b>'
T["ar"]['on_result'] = '🏁 <b>انتهت المباراة</b>\n{head}\n\nأنت: <b>{me}</b> · المنافس ({name}): <b>{op}</b> من {n}'
T["en"]['btn_online'] = '🌐 Play online'
T["en"]['on_menu'] = '🌐 <b>Play online</b>\nPick a game. The first player who joins the queue after you is your opponent, on the same questions. The best wins, and both see the result.'
T["en"]['on_kind_quiz'] = '🎯 Anime questions'
T["en"]['on_kind_tf'] = '✅❌ True or false'
T["en"]['on_busy'] = "You're already in a match or in the queue."
T["en"]['on_waiting'] = '⏳ Waiting for an opponent in <b>{kind}</b>. The next player who picks the same game is matched with you automatically (waiting ends after {s}s).'
T["en"]['on_cancel'] = '❌ Cancel waiting'
T["en"]['on_cancelled'] = 'Waiting cancelled.'
T["en"]['on_timeout'] = '⏱ No opponent found this time. Try again.'
T["en"]['on_started'] = '⚔️ <b>Match started</b> ({kind})! Same questions for both. {secs}s per question.'
T["en"]['on_round'] = '<b>Question {n}/{total}</b> · ⏱ {secs}s\nScore: you {a} — opponent {b}\n\n{q}\n\n{opts}'
T["en"]['on_reveal_ok'] = '✅ Correct!\nAnswer: <b>{right}</b>'
T["en"]['on_reveal_bad'] = '❌ Wrong or no answer.\nAnswer: <b>{right}</b>'
T["en"]['on_forfeit'] = '🏳 Forfeit'
T["en"]['on_late'] = "Time's up for this question ⌛"
T["en"]['on_already'] = 'Already answered ✅'
T["en"]['on_saved'] = 'Answer recorded ✅'
T["en"]['on_win'] = '🏆 <b>You won!</b>'
T["en"]['on_lose'] = '😅 <b>You lost</b>'
T["en"]['on_draw'] = '🤝 <b>Draw!</b>'
T["en"]['on_result'] = '🏁 <b>Match over</b>\n{head}\n\nYou: <b>{me}</b> · Opponent ({name}): <b>{op}</b> of {n}'

T["ar"]['mf_cfg_title'] = '⚙️ <b>إعدادات لعبة المافيا</b>'
T["ar"]['mf_cfg_hint'] = 'ضبط عدد القتلة والأدوار الخاصة، ثم ابدأ. (الإعدادات تظهر لك فقط)'
T["ar"]['mf_host_dm_missing'] = '⚠️ ما قدرت أرسل لك إعدادات اللعبة. افتح البوت بالخاص أولًا: @{me} ثم أعد /mafia.'
T["ar"]['mf_joined_dm'] = '✅ انضممت للعبة المافيا! انتظر بدء اللعبة، وستصلك رسالة دورك هنا.'
T["ar"]['mf_starting'] = '▶️ تبدأ اللعبة الآن.'
T["en"]['mf_cfg_title'] = '⚙️ <b>Mafia game settings</b>'
T["en"]['mf_cfg_hint'] = 'Set the number of killers and special roles, then start. (Settings are only shown to you)'
T["en"]['mf_host_dm_missing'] = "⚠️ I couldn't send you the game settings. Open the bot privately first: @{me}, then /mafia again."
T["en"]['mf_joined_dm'] = '✅ You joined the mafia game! Wait for the start; your role will arrive here.'
T["en"]['mf_starting'] = '▶️ The game starts now.'

T["ar"]["prof_recent"] = "🕘 آخر نتائجك: {recent}"
T["en"]["prof_recent"] = "🕘 Recent scores: {recent}"

T["ar"]["gpk_mafia"] = "🔪 المافيا"
T["en"]["gpk_mafia"] = "🔪 Mafia (anime game)"
T["ar"]["gpk_spy"] = "🎭 برا السالفة"
T["en"]["gpk_spy"] = "🎭 Outside the Story"

T["ar"].update({"du_pick_game": "⚔️ <b>تحدَّ صديقًا</b>\nاختر اللعبة:", "du_game_quiz": "🎯 أسئلة أنمي (7 أسئلة)",
                "on_opp_card": "🆚 <b>منافسك</b>\n🏅 ترتيبه العام: <b>#{rank}</b>\n⭐ أفضل تقييم: <b>{best}</b>/10 · 📝 اختبارات كاملة: {tests}\n☠️ أطول موت مفاجئ: {sd} · 🎮 ألعابه: {games}\n<i>الاسم مخفي حتى نهاية المباراة.</i>"})
T["en"].update({"du_pick_game": "⚔️ <b>Challenge a friend</b>\nPick the game:", "du_game_quiz": "🎯 Anime questions (7)",
                "on_opp_card": "🆚 <b>Your opponent</b>\n🏅 Overall rank: <b>#{rank}</b>\n⭐ Best score: <b>{best}</b>/10 · 📝 Full tests: {tests}\n☠️ Longest sudden-death streak: {sd} · 🎮 Games played: {games}\n<i>Name hidden until the match ends.</i>"})

T["ar"].update({"on_kind_sudden": "☠️ الموت المفاجئ", "on_kind_images": "🖼 شخصيات بالصور",
                "on_queue_n": "  🟢 ({n} ينتظر)"})
T["en"].update({"on_kind_sudden": "☠️ Sudden death", "on_kind_images": "🖼 Character pictures",
                "on_queue_n": "  🟢 ({n} waiting)"})

T["ar"]["on_opp_card"] = "🆚 <b>منافسك: {name}</b>\n🏅 ترتيبه العام: <b>#{rank}</b>\n⭐ أفضل تقييم: <b>{best}</b>/10 · 📝 اختبارات كاملة: {tests}\n☠️ أطول موت مفاجئ: {sd} · 🎮 ألعابه: {games}"
T["en"]["on_opp_card"] = "🆚 <b>Your opponent: {name}</b>\n🏅 Overall rank: <b>#{rank}</b>\n⭐ Best score: <b>{best}</b>/10 · 📝 Full tests: {tests}\n☠️ Longest sudden-death streak: {sd} · 🎮 Games played: {games}"

T["ar"]["btn_back_group"] = "↩️ العودة للمجموعة"
T["en"]["btn_back_group"] = "↩️ Back to the group"
T["ar"]["btn_back_channel"] = "↩️ العودة للقناة"
T["en"]["btn_back_channel"] = "↩️ Back to the channel"
T["ar"]["btn_open_private"] = "💬 افتح الخاص"
T["en"]["btn_open_private"] = "💬 Open private chat"
T["ar"]["sp_vote_dm_live"] = "🗳 التصويت بدأ في الخاص. افتح البوت واختر من تظن أنه المتطفل."
T["en"]["sp_vote_dm_live"] = "🗳 Voting has started in private. Open the bot and pick who you think is the outsider."

T["ar"]["leave_nudge"] = "👋 لاحظنا أنك غادرت {ch}\nارجع لها عشان ما يفوتك الجديد من الأنمي والتحديات 🎌"
T["en"]["leave_nudge"] = "👋 We noticed you left {ch}\nCome back so you don't miss new anime and challenges 🎌"

T["ar"]["inl_challenge_title"] = "⚔️ تحدّي الأوتاكو"
T["en"]["inl_challenge_title"] = "⚔️ Otaku challenge"
T["ar"]["inl_challenge"] = "⚔️ {name} يتحداك في اختبار الأوتاكو!\nشف كم تجيب من 10 🔥"
T["en"]["inl_challenge"] = "⚔️ {name} challenges you in the Otaku quiz!\nSee how many of 10 you get 🔥"
T["ar"]["inl_go"] = "🎯 ابدأ التحدي"
T["en"]["inl_go"] = "🎯 Start the challenge"
T["ar"]["inl_result_title"] = "🏆 نتيجتي: {score}/10"
T["en"]["inl_result_title"] = "🏆 My score: {score}/10"
T["ar"]["inl_result"] = "🏆 {name} حصل على <b>{score}/10</b> — {title}\nتقدر تتفوق عليه؟ 👇"
T["en"]["inl_result"] = "🏆 {name} scored <b>{score}/10</b> — {title}\nCan you beat that? 👇"
T["ar"]["inv_join_bonus"] = "🎁 مكافأة الانضمام بالدعوة: +{xp} خبرة"
T["en"]["inv_join_bonus"] = "🎁 Invite bonus: +{xp} XP"

T["ar"]["mf_auto_btn"] = "🎲 تلقائي حسب العدد"
T["en"]["mf_auto_btn"] = "🎲 Auto by player count"
T["ar"]["mf_tm_lobby"] = "⏳ الانتظار: {s}ث"
T["en"]["mf_tm_lobby"] = "⏳ Lobby: {s}s"
T["ar"]["mf_tm_night"] = "🌙 الليل: {s}ث"
T["en"]["mf_tm_night"] = "🌙 Night: {s}s"
T["ar"]["mf_tm_day"] = "☀️ النهار: {s}ث"
T["en"]["mf_tm_day"] = "☀️ Day: {s}s"

T["ar"]["mf_vote_status"] = "🗳 <b>{name}</b> صوّت.\n📊 صوّتوا: {done} من {total} · باقي: {left}"
T["en"]["mf_vote_status"] = "🗳 <b>{name}</b> voted.\n📊 Voted: {done} of {total} · Left: {left}"
T["ar"]["mf_quiet_death"] = "⚰️ مرت 3 جولات بدون قتل ولا طرد، فاختار القدر <b>{name}</b> ليخرج من اللعبة 💀"
T["en"]["mf_quiet_death"] = "⚰️ Three rounds passed with no death or vote, so fate chose <b>{name}</b> to leave the game 💀"

T["ar"]["mf_self_votes"] = '⏳ <b>「 من بقي صامتًا 」</b>\n{names}\n<i>صوت كل واحد منهم اعتُبر على نفسه، فلا يُطرد أحد بسببه.</i>'
T["en"]["mf_self_votes"] = "⏳ Did not vote: {names}\n↩️ Each of their votes counts for themselves, so it eliminates nobody."
T["ar"]["mf_vote_dm"] = "🗳 بدأ التصويت الصباحي في اللعبة.\nاضغط الزر وصوّت قبل انتهاء الوقت. من لا يصوّت يُحسب صوته على نفسه ↩️"
T["en"]["mf_vote_dm"] = "🗳 Morning voting has started.\nTap the button and vote before time runs out. If you don't vote, your vote counts for yourself ↩️"
T["ar"]["btn_go_vote"] = "🗳 صوّت الآن"
T["en"]["btn_go_vote"] = "🗳 Vote now"
T["ar"]["mf_vote_note"] = "ℹ️ من لا يصوّت يُحسب صوته على نفسه."
T["en"]["mf_vote_note"] = "ℹ️ If you don't vote, your vote counts for yourself."

T["ar"]["mf_vote_results"] = '📊 <b>「 حصيلة الأصوات 」</b>\n━━━━━━━━━━━━━━━━\n{lines}'
T["en"]["mf_vote_results"] = "📊 <b>Vote results</b> (voters are not named):\n{lines}"
T["ar"]["mf_vote_skip"] = "• ⏭ تخطّي: {n}"
T["en"]["mf_vote_skip"] = "• ⏭ Skip: {n}"

T["ar"]["mf_place_pick"] = "📍 <b>أين يكون النقاش؟</b>\nاختر مكان النقاش للمافيا:"
T["en"]["mf_place_pick"] = "📍 <b>Where should the discussion happen?</b>\nChoose where the mafia discussion takes place:"
T["ar"]["mf_place_channel"] = "💬 في القناة نفسها"
T["en"]["mf_place_channel"] = "💬 In the channel itself"
T["ar"]["mf_place_post"] = "🔗 في تعليقات منشور"
T["en"]["mf_place_post"] = "🔗 In a post's comments"
T["ar"]["mf_post_ask"] = ("🔗 <b>أرسل رابط المنشور من قناتك</b>\n"
    "مثال: <code>https://t.me/اسم_القناة/123</code>\n"
    "النقاش يكون في تعليقات هذا المنشور، والبوت يرد داخل التعليقات.\n"
    "⚠️ لازم يكون البوت أدمنًا في مجموعة التعليقات المرتبطة بالقناة، وأن يكون المنشور نُشر بعد إضافته.")
T["en"]["mf_post_ask"] = ("🔗 <b>Send the link of a post from your channel</b>\n"
    "Example: <code>https://t.me/channel_name/123</code>\n"
    "The discussion happens in that post's comments, and the bot replies inside them.\n"
    "⚠️ The bot must be an admin in the channel's linked comments group, and the post must be published after it was added.")
T["ar"]["mf_post_bad"] = "❌ هذا ما يبدو رابط منشور في قناتك. أرسل الرابط بالشكل: <code>https://t.me/اسم_القناة/123</code>"
T["en"]["mf_post_bad"] = "❌ This doesn't look like a post link from your channel. Send it like: <code>https://t.me/channel_name/123</code>"
T["ar"]["mf_post_nocopy"] = "❌ ما قدرت أجد المنشور في تعليقات القناة. تأكد أن البوت أدمن في مجموعة التعليقات، وأن المنشور نُشر بعد إضافته."
T["en"]["mf_post_nocopy"] = "❌ I couldn't find that post in the channel's comments. Make sure the bot is an admin in the comments group, and the post was published after it was added."
T["ar"]["mf_post_started"] = "🎮 لعبة المافيا بدأت في تعليقات المنشور 👇\n{link}\nانضم من هناك واللعب يكون داخل التعليقات."
T["en"]["mf_post_started"] = "🎮 Mafia started in the post's comments 👇\n{link}\nJoin from there; the game happens inside the comments."
T["ar"]["mf_post_started_ch"] = "🎮 لعبة مافيا جديدة في تعليقات هذا المنشور. ادخل التعليقات وانضم!"
T["en"]["mf_post_started_ch"] = "🎮 A new Mafia game is running in this post's comments. Open the comments and join!"
T["ar"]["mf_post_go"] = "💬 افتح التعليقات"
T["en"]["mf_post_go"] = "💬 Open the comments"

T["ar"]["mf_post_ask"] = ("🔗 <b>أرسل رابط أي رسالة من داخل تعليقات المنشور</b>\n"
    "اضغط الرسالة في التعليقات ثم «نسخ الرابط».\n"
    "النقاش يكون داخل تعليقات ذلك المنشور، واللعب والتصويت يبقى في القناة.\n"
    "⚠️ لازم تكون مجموعة التعليقات مرتبطة بالقناة، وأن يكون البوت أدمنًا فيها.")
T["en"]["mf_post_ask"] = ("🔗 <b>Send a link to any message inside the post's comments</b>\n"
    "Open a message in the comments, then «Copy link».\n"
    "Discussion happens in that post's comments; playing and voting stay in the channel.\n"
    "⚠️ The comments group must be linked to the channel, and the bot must be an admin there.")
T["ar"]["mf_post_bad"] = "❌ هذا ما يبدو رابط تعليق داخل منشور في قناتك. أرسل رابطًا بالشكل: <code>https://t.me/اسم_القناة/123?comment=456</code>"
T["en"]["mf_post_bad"] = "❌ This doesn't look like a comment link from your channel's post. Send a link like: <code>https://t.me/channel_name/123?comment=456</code>"
T["ar"]["mf_post_started"] = "🎮 بدأت اللعبة في القناة، والنقاش في تعليقات المنشور 👇\n{link}"
T["en"]["mf_post_started"] = "🎮 The game started in the channel; discussion is in the post's comments 👇\n{link}"

T["ar"]["mf_discuss_line"] = "💬 <b>النقاش في تعليقات المنشور الموجود بالزر</b> 👇"
T["en"]["mf_discuss_line"] = "💬 <b>Discussion in the post's comments</b> 👇 (playing and voting stay here)"
T["ar"]["mf_discuss_btn"] = "💬 النقاش في التعليقات"
T["en"]["mf_discuss_btn"] = "💬 Discuss in comments"


T["ar"]["mf_news"] = "📰 <b>أخبار الليلة {ord}</b>\n\n{body}"
T["en"]["mf_news"] = "📰 <b>Night {ord} news</b>\n\n{body}"

T["ar"]["mf_r_mayor"] = "العمدة"
T["en"]["mf_r_mayor"] = "Mayor"
T["ar"]["mf_desc_mayor"] = "🎖 أنت العمدة، من المواطنين. لا قدرة لك ليلًا. في النهار يمكنك أن تكشف نفسك مرة واحدة فقط: بعدها يُحسب صوتك مرتين. إن مت قبل أن تكشف، يبقى دورك مجهولًا."
T["en"]["mf_desc_mayor"] = "🎖 You're the Mayor, a citizen. No night power. In the day you may reveal yourself once: after that your vote counts twice. If you die before revealing, your role stays unknown."
T["ar"]["mf_mayor_dm"] = "🎖 بدأ التصويت الصباحي. تقدر تكشف نفسك الآن (مرة واحدة فقط)، فيُحسب صوتك مرتين من تلك اللحظة."
T["en"]["mf_mayor_dm"] = "🎖 Morning voting has started. You can reveal yourself now (once only), and your vote counts twice from then on."
T["ar"]["mf_reveal_btn"] = "🎖 اكشف نفسي"
T["en"]["mf_reveal_btn"] = "🎖 Reveal myself"
T["ar"]["mf_mayor_revealed"] = '🎖 <b>「 الكشف! 」</b>\nالعمدة <b>{name}</b> يكشف عن نفسه أمام الجميع!\nمن الآن يُحسب صوته مرتين.'
T["en"]["mf_mayor_revealed"] = "🎖 <b>{name}</b> is the Mayor! Their vote counts twice from now on."
T["ar"]["mf_already_revealed"] = "العمدة كشف نفسه من قبل."
T["en"]["mf_already_revealed"] = "The mayor has already revealed."

T["ar"]["mf_vote_pending"] = '⏳ <b>「 ما زالوا يترددون… 」</b>\n{names}'
T["en"]["mf_vote_pending"] = "⏳ <b>Not voted yet:</b> {names}"
T["ar"]["mf_vote_all"] = '✅ <b>「 اكتمل الحكم 」</b> الكل صوّت.'
T["en"]["mf_vote_all"] = "✅ <b>Everyone voted</b>"

T["ar"]["mf_dm_removed"] = "⚠️ ما قدرت أرسل الدور لـ {names} (لم يفتحوا البوت بالخاص أو حظروه)، فتم استبعادهم وإعادة توزيع الأدوار."
T["en"]["mf_dm_removed"] = "⚠️ I couldn't send a role to {names} (they haven't opened the bot or blocked it). They were removed and roles were dealt again."
T["ar"]["mf_night_remind"] = '⏰ <b>「 الفجر يقترب… 」</b>\nتصرّف الآن من الأزرار قبل أن يفوت الوقت.'
T["en"]["mf_night_remind"] = "⏰ Reminder: night ends soon, act now with the buttons."
T["ar"]["mf_vote_remind"] = '⏰ <b>「 لم تُدلِ بصوتك بعد! 」</b>\nصوّت قبل أن يُغلق باب الحكم، ومن يصمت يُحسب صوته على نفسه.'
T["en"]["mf_vote_remind"] = "⏰ Reminder: you haven't voted yet! Vote before time runs out; if you don't, your vote counts for yourself."
T["ar"]["mf_gone_stop"] = "⚠️ توقفت لعبة المافيا لأن الرسالة الحيّة حُذفت. ابدأ لعبة جديدة."
T["en"]["mf_gone_stop"] = "⚠️ The mafia game stopped because its live message was deleted. Start a new game."

T["ar"]["mf_mayor_warn"] = '🎖 <b>「 تحذير… العمدة بيننا 」</b>\nالعمدة <b>{name}</b> كشف نفسه! تقدرون تقتلونه، لكن الطبيب قد يحميه. أو اكسبوه إلى صفكم… فصوته إذا صوّت عليكم يُحسب مرتين.'
T["en"]["mf_mayor_warn"] = "🎖 The Mayor <b>{name}</b> revealed! Be careful: you can kill them, but the doctor may protect them. Or win them over, since their vote counts twice against you."
T["ar"]["mf_joker_out"] = '🃏 <b>「 الضحكة الأخيرة… 」</b>\n<b>{name}</b> هو المجنون! قبل أن يُسحب إلى الظلام، يختار أحدكم ليرافقه. ({s} ثانية، وإن صمتّم اختار القدر.)'
T["en"]["mf_joker_out"] = "🃏 <b>{name}</b> was the Joker! Choose who they take with them ({s} seconds; if no one chooses, the bot does)."
T["ar"]["mf_joker_took"] = '🃏 <b>「 لن يخرج وحده… 」</b>\n<b>{joker}</b> سحب معه <b>{victim}</b> إلى الظلام!'
T["en"]["mf_joker_took"] = "🃏 <b>{joker}</b> took <b>{victim}</b> with them!"

T["ar"]["mf_desc_joker"] = "🃏 أنت المجنون، من المواطنين. لا قدرة لك ليلًا. إن طُردت بالتصويت يُكشف دورك، ويختار أحد الأحياء يسحبه معك خلال 60 ثانية، وإلا يختار البوت."
T["en"]["mf_desc_joker"] = "🃏 You're the Joker, on the citizens' side. No night power. If voted out, your role is revealed and someone alive is taken with you within 60 seconds, otherwise the bot picks."


T["ar"]["mf_roles_label"] = "الأدوار"
T["en"]["mf_roles_label"] = "Roles"
T["ar"]["mf_players_label"] = "المنضمون"
T["en"]["mf_players_label"] = "Players"
T["ar"]["mf_join_hint"] = "اضغط «انضم» للدخول،\nاضغط «❓ شرح اللعبة» لتعرف كل شيء."
T["en"]["mf_join_hint"] = "Tap «Join» to enter, and «❓ How to play» to learn everything."
T["ar"]["mf_help_btn"] = "❓ شرح اللعبة"
T["en"]["mf_help_btn"] = "❓ How to play"
T["ar"]["mf_help_long"] = (
"🎌 <b>المافيا · دليل اللعبة الكامل</b>\n━━━━━━━━━━━━━━━━\n"
"🎯 <b>الهدف</b>\n"
"• المواطنون (ومعهم العمدة والطبيب والمحقق والمجنون) يكشفون القتلة ويطردونهم بالتصويت.\n"
"• القتلة يتخلصون من المواطنين حتى يتساووا معهم، أو يتجاوزوهم.\n\n"
"🎭 <b>الأدوار</b>\n"
"🔪 <b>القاتل:</b> كل ليلة يختار ضحية مع بقية القتلة، والأكثر أصواتًا يُقتل.\n"
"🩺 <b>الطبيب:</b> كل ليلة يحمي لاعبًا (ويحق له حماية نفسه). إن كان الهدف محميًا، ينجو.\n"
"🔍 <b>المحقق:</b> كل ليلة يكشف فريق لاعب: مافيا أو مواطنون.\n"
"🎖 <b>العمدة:</b> من المواطنين. يكشف نفسه مرة واحدة في النهار، فيُحسب صوته مرتين من تلك اللحظة.\n"
"🃏 <b>المجنون:</b> من المواطنين. إن طُرد بالتصويت يُكشف دوره، ويختار أحدًا يسحبه معه خلال 60 ثانية.\n"
"👥 <b>المواطن:</b> لا قدرة له، قوته في التصويت وفي الكشف عن القتلة.\n\n"
"🌙 <b>الليل</b>\n"
"القتلة يختارون ضحية، والطبيب يحمي، والمحقق يكشف. كل ذلك من الخاص بالأزرار. وإن لم يختر القتلة أحدًا يختار البوت بالنيابة عنهم.\n\n"
"🌅 <b>الصباح</b>\n"
"يُعلن إن قُتل أحد، أو إن الضحية كانت محمية، أو إن ليلة هادئة مرت.\n\n"
"☀️ <b>النهار</b>\n"
"تناقشون في التعليقات أو القناة، ثم كل حي يصوّت لطرد من يشتبه به، أو «تخطّي». من لا يصوّت يُحسب صوته على نفسه ولا يطرد أحدًا.\n"
"⚖️ يُطرد صاحب <b>الأصوات الأكثر</b>. التعادل على الأعلى = لا طرد.\n\n"
"⏳ <b>الأوقات:</b> الانتظار 5 دقائق، والليل والنهار يعدّلهما المضيف من إعداداته.\n"
"⚠️ إذا مرت 3 جولات متتالية بلا قتل ولا طرد، يختار القدر لاعبًا عشوائيًا يخرج.\n"
"━━━━━━━━━━━━━━━━\n"
"<i>أسرار الأدوار تُكشف في النهاية فقط. لا تكشف دورك بنفسك!</i>")
T["en"]["mf_help_long"] = (
"🎌 <b>Mafia · Full guide</b>\n━━━━━━━━━━━━━━━━\n"
"🎯 <b>Goal</b>\n"
"• Citizens (with the Mayor, Doctor, Detective and Joker) find and vote out the killers.\n"
"• Killers eliminate citizens until they equal or outnumber them.\n\n"
"🎭 <b>Roles</b>\n"
"🔪 <b>Killer:</b> each night picks a victim with the other killers; the most-voted dies.\n"
"🩺 <b>Doctor:</b> each night protects one player (including self). A protected target survives.\n"
"🔍 <b>Detective:</b> each night checks a player's team: mafia or citizens.\n"
"🎖 <b>Mayor:</b> a citizen. Reveals once during the day; their vote then counts twice.\n"
"🃏 <b>Joker:</b> a citizen. If voted out, the role is revealed and takes one living player along within 60 seconds.\n"
"👥 <b>Citizen:</b> no power; strength in voting and finding killers.\n\n"
"🌙 <b>Night</b>: killers pick, doctor protects, detective checks; all with buttons in private. If no killer picks, the bot picks for them.\n\n"
"🌅 <b>Morning</b>: announces a death, a protected target, or a quiet night.\n\n"
"☀️ <b>Day</b>: discuss, then every living player votes to eliminate a suspect, or skips. Not voting counts as a vote for yourself (eliminates nobody).\n"
"⚖️ The player with the <b>most votes</b> is eliminated. A tie for first = no elimination.\n\n"
"⏳ <b>Timers</b>: 5 minutes to join; the host sets night and day times.\n"
"⚠️ If 3 rounds in a row have no death or vote, fate picks a random player to leave.\n"
"━━━━━━━━━━━━━━━━\n"
"<i>Roles stay secret until the end. Don't reveal yours!</i>")

# ── النقاش قبل التصويت + أوقات جديدة ──
T["ar"]["mf_discuss_live"] = '💬 <b>「 النهار {r} · وقت النقاش 」</b>\n━━━━━━━━━━━━━━━━\n⏳ {s} ثانية للنقاش\n👥 الأحياء:\n{names}\n━━━━━━━━━━━━━━━━\n<i>ناقشوا الآن في المجموعة أو التعليقات. بعد انتهاء الوقت تُفتح أزرار التصويت.</i>'
T["en"]["mf_discuss_live"] = '💬 <b>Day {r} · Discussion</b>\n━━━━━━━━━━━━━━━━\n⏳ {s}s to discuss\n👥 Alive:\n{names}\n━━━━━━━━━━━━━━━━\n<i>Talk it out now. Voting buttons open when the time is up.</i>'
T["ar"]["mf_discuss_dm"] = '💬 بدأ النهار، ووقت النقاش {s} ثانية.\nاضغط الزر وشارك في النقاش، وبعده يبدأ التصويت.'
T["en"]["mf_discuss_dm"] = '💬 Day has begun. You have {s}s to discuss.\nTap the button to join the discussion; voting starts afterwards.'
T["ar"]["btn_go_discuss"] = "💬 مكان النقاش"
T["en"]["btn_go_discuss"] = "💬 Discussion"
T["ar"]["mf_discuss_wait"] = "التصويت يفتح بعد انتهاء وقت النقاش."
T["en"]["mf_discuss_wait"] = "Voting opens after the discussion ends."
T["ar"]["mf_tm_night"] = "🔪 قتل المافيا: {s}ث"
T["en"]["mf_tm_night"] = "🔪 Mafia kill: {s}s"
T["ar"]["mf_tm_discuss"] = "💬 النقاش: {s}ث"
T["en"]["mf_tm_discuss"] = "💬 Discussion: {s}s"
T["ar"]["mf_tm_day"] = "🗳 التصويت: {s}ث"
T["en"]["mf_tm_day"] = "🗳 Voting: {s}s"

T["ar"]["mf_help_long"] = (
"🎌 <b>المافيا · دليل اللعبة الكامل</b>\n━━━━━━━━━━━━━━━━\n"
"🎯 <b>الهدف</b>\n"
"• المواطنون (ومعهم العمدة والطبيب والمحقق والمجنون) يكشفون القتلة ويطردونهم بالتصويت.\n"
"• القتلة يتخلصون من المواطنين حتى يتساووا معهم، أو يتجاوزوهم.\n\n"
"🎭 <b>الأدوار</b>\n"
"🔪 <b>القاتل:</b> كل ليلة يختار ضحية مع بقية القتلة، والأكثر أصواتًا يُقتل.\n"
"🩺 <b>الطبيب:</b> كل ليلة يحمي لاعبًا (ويحق له حماية نفسه). إن كان الهدف محميًا، ينجو.\n"
"🔍 <b>المحقق:</b> كل ليلة يكشف فريق لاعب: مافيا أو مواطنون.\n"
"🎖 <b>العمدة:</b> من المواطنين. يكشف نفسه مرة واحدة في النهار، فيُحسب صوته مرتين من تلك اللحظة.\n"
"🃏 <b>المجنون:</b> من المواطنين. إن طُرد بالتصويت يُكشف دوره، ويختار أحدًا يسحبه معه خلال 60 ثانية.\n"
"👥 <b>المواطن:</b> لا قدرة له، قوته في النقاش والتصويت.\n\n"
"🌙 <b>الليل</b>\n"
"القتلة يختارون ضحية، والطبيب يحمي، والمحقق يكشف. كل ذلك من الخاص بالأزرار. وإن لم يختر القتلة أحدًا يختار البوت بالنيابة عنهم.\n\n"
"🌅 <b>الصباح</b>\n"
"يُعلن إن قُتل أحد، أو إن الضحية كانت محمية، أو إن ليلة هادئة مرت.\n\n"
"☀️ <b>النهار</b>\n"
"1️⃣ <b>النقاش:</b> تتكلمون في المجموعة أو التعليقات، وتصلك رسالة خاصة فيها زر يودي لمكان النقاش.\n"
"2️⃣ <b>التصويت:</b> بعد انتهاء النقاش تُفتح الأزرار، فكل حي يطرد من يشتبه به أو يضغط «تخطّي».\n"
"من لا يصوّت يُحسب صوته على نفسه ولا يطرد أحدًا.\n"
"⚖️ يُطرد صاحب <b>الأصوات الأكثر</b>. التعادل على الأعلى = لا طرد.\n\n"
"⏳ <b>الأوقات الافتراضية:</b> الانتظار 5 دقائق، والنقاش 3 دقائق، والتصويت دقيقة، وقتل المافيا دقيقة. والمضيف يعدّلها من إعداداته.\n"
"⚠️ إذا مرت 3 جولات متتالية بلا قتل ولا طرد، يختار القدر لاعبًا عشوائيًا يخرج.\n"
"━━━━━━━━━━━━━━━━\n"
"<i>أسرار الأدوار تُكشف في النهاية فقط. لا تكشف دورك بنفسك!</i>")

T["en"]["mf_help_long"] = (
"🎌 <b>Mafia · Full guide</b>\n━━━━━━━━━━━━━━━━\n"
"🎯 <b>Goal</b>\n"
"• Citizens (with the Mayor, Doctor, Detective and Joker) find and vote out the killers.\n"
"• Killers eliminate citizens until they equal or outnumber them.\n\n"
"🎭 <b>Roles</b>\n"
"🔪 <b>Killer:</b> each night picks a victim with the other killers; the most-voted dies.\n"
"🩺 <b>Doctor:</b> each night protects one player (including self). A protected target survives.\n"
"🔍 <b>Detective:</b> each night checks a player's team: mafia or citizens.\n"
"🎖 <b>Mayor:</b> a citizen. Reveals once during the day; their vote then counts twice.\n"
"🃏 <b>Joker:</b> a citizen. If voted out, the role is revealed and takes one living player along within 60 seconds.\n"
"👥 <b>Citizen:</b> no power; strength in discussion and voting.\n\n"
"🌙 <b>Night</b>: killers pick, doctor protects, detective checks; all with buttons in private. If no killer picks, the bot picks for them.\n\n"
"🌅 <b>Morning</b>: announces a death, a protected target, or a quiet night.\n\n"
"☀️ <b>Day</b>\n"
"1️⃣ <b>Discussion:</b> talk in the group or comments; a private message with a button takes you there.\n"
"2️⃣ <b>Voting:</b> when discussion ends the buttons open; every living player votes to eliminate a suspect, or skips. Not voting counts as a vote for yourself.\n"
"⚖️ The player with the <b>most votes</b> is eliminated. A tie for first = no elimination.\n\n"
"⏳ <b>Default times:</b> join 5 min, discussion 3 min, voting 1 min, mafia kill 1 min. The host can change them.\n"
"⚠️ If 3 rounds in a row have no death or vote, fate picks a random player to leave.\n"
"━━━━━━━━━━━━━━━━\n"
"<i>Roles stay secret until the end. Don't reveal yours!</i>")

T["ar"]["btn_bot_game"] = "🎮 بوت اللعبة"
T["en"]["btn_bot_game"] = "🎮 Game bot"
T["ar"]["mf_not_player"] = "أنت لست مشاركًا في هذه اللعبة."
T["en"]["mf_not_player"] = "You are not a player in this game."

T["ar"]["mf_reveal_cfg"] = "👁 إظهار الدور عند الموت"
T["en"]["mf_reveal_cfg"] = "👁 Reveal role on death"
T["ar"]["mf_role_shown"] = "🎭 كان دوره: {role}"
T["en"]["mf_role_shown"] = "🎭 Their role was: {role}"

T["ar"]["mf_dm_removed"] = "⚠️ ما قدرت أرسل الدور لـ {names} (لم يفتحوا البوت بالخاص أو حظروه)، فتم استبعادهم.\n⏳ نفتح اللوبي {s} ثانية، ينضم غيرهم الآن."
T["en"]["mf_dm_removed"] = "⚠️ I couldn't send a role to {names} (they haven't opened the bot or blocked it), so they were removed.\n⏳ The lobby reopens for {s} seconds for others to join."

T["ar"]["mf_protect_repeat"] = "ما تقدر تحمي نفس الشخص ليلتين متتاليتين. اختر غيره."
T["en"]["mf_protect_repeat"] = "You can't protect the same person two nights in a row. Pick someone else."
T["ar"]["mf_ready_host"] = "✅ اكتمل الحد الأدنى ({n} لاعبين). تقدر تبدأ الآن، أو تنتظر انضمام غيرهم."
T["en"]["mf_ready_host"] = "✅ Minimum reached ({n} players). You can start now, or wait for more to join."

# ── مافيا أونلاين (otaku_bot/mafia_online.py) ──
T["ar"]["btn_mafia_online"] = "🔪 مافيا أونلاين"
T["en"]["btn_mafia_online"] = "🔪 Mafia online"
T["ar"]["mo_queued"] = "⏳ انضممت لطابور المافيا أونلاين ({n} الآن).\nتبدأ عند اكتمال 8 لاعبين، أو بعد {s} ثانية إن وُجد {min} على الأقل."
T["en"]["mo_queued"] = "⏳ You joined the Mafia online queue ({n} now).\nStarts at 8 players, or after {s}s if at least {min} are waiting."
T["ar"]["mo_timeout"] = "⌛ لم يكتمل العدد ({min} لاعبين على الأقل). جرّب مرة أخرى."
T["en"]["mo_timeout"] = "⌛ Not enough players ({min} needed). Try again."
T["ar"]["mo_already"] = "أنت في الطابور بالفعل."
T["en"]["mo_already"] = "You're already in the queue."
T["ar"]["mo_busy"] = "أنت في لعبة حاليًا، أنهِها أولًا."
T["en"]["mo_busy"] = "You're in a game right now. Finish it first."
T["ar"]["mo_cancel_btn"] = "❌ إلغاء الانتظار"
T["en"]["mo_cancel_btn"] = "❌ Cancel waiting"
T["ar"]["mo_cancelled"] = "تم إلغاء انتظارك."
T["en"]["mo_cancelled"] = "Your wait was cancelled."
T["ar"]["mo_started"] = "🔪 بدأت مافيا أونلاين مع {n} لاعبًا. أدوارك تصلك الآن في الخاص."
T["en"]["mo_started"] = "🔪 Online Mafia started with {n} players. Your role arrives now."
T["ar"]["mo_killer_mates"] = "🔪 زملاؤك القتلة: {names}"
T["en"]["mo_killer_mates"] = "🔪 Your fellow killers: {names}"
T["ar"]["mo_night"] = "🌙 <b>「 الليلة {r} 」</b>\nالقتلة والطبيب والمحقق يختارون الآن (⏳ {s} ثانية). الباقون ينتظرون الفجر."
T["en"]["mo_night"] = "🌙 <b>Night {r}</b>\nThe killers, doctor and detective choose now ({s}s). Everyone else waits for dawn."
T["ar"]["mo_night_wait"] = "🌙 أنت مواطن، انتظر الفجر."
T["en"]["mo_night_wait"] = "🌙 You're a citizen. Wait for dawn."
T["ar"]["mo_pick_killer"] = "🔪 اختر ضحية الليلة:"
T["en"]["mo_pick_killer"] = "🔪 Pick tonight's victim:"
T["ar"]["mo_pick_doctor"] = "🩺 اختر من تحميه الليلة (لا تقدر تحمي نفس الشخص ليلتين متتاليتين):"
T["en"]["mo_pick_doctor"] = "🩺 Pick who to protect tonight (not the same person two nights in a row):"
T["ar"]["mo_pick_detective"] = "🔍 اختر من تكشف فريقه:"
T["en"]["mo_pick_detective"] = "🔍 Pick whose team to check:"
T["ar"]["mo_late"] = "انتهى وقت هذه المرحلة."
T["en"]["mo_late"] = "This phase is over."
T["ar"]["mo_not_yours"] = "هذا الزر ليس لدورك."
T["en"]["mo_not_yours"] = "This button isn't for your role."
T["ar"]["mo_not_alive"] = "الميت لا يصوّت."
T["en"]["mo_not_alive"] = "The dead can't vote."
T["ar"]["mo_bad_target"] = "هذا الاختيار غير صالح."
T["en"]["mo_bad_target"] = "That choice isn't valid."
T["ar"]["mo_picked"] = "✅ تم اختيارك."
T["en"]["mo_picked"] = "✅ Choice saved."
T["ar"]["mo_detect_alert"] = "🔍 {name}: من فريق {team}"
T["en"]["mo_detect_alert"] = "🔍 {name}: on the {team} team"
T["ar"]["mo_talk"] = "☀️ <b>「 النهار {r} · النقاش 」</b>\nاكتبوا رسائلكم هنا، وتصل للجميع باسمك ({s} ثانية). ثم يبدأ التصويت.\n<i>الرسالة الواحدة كل 3 ثوانٍ، والحد 300 حرف.</i>"
T["en"]["mo_talk"] = "☀️ <b>Day {r} · Discussion</b>\nWrite your messages here; they reach everyone with your name ({s}s). Voting follows.\n<i>One message every 3 seconds, 300 characters max.</i>"
T["ar"]["mo_dead_talk"] = "أنت خارج اللعبة، تتابع فقط."
T["en"]["mo_dead_talk"] = "You're out of the game; you can only watch."
T["ar"]["mo_talk_rate"] = "⏳ انتظر ثلاث ثوانٍ قبل الرسالة التالية."
T["en"]["mo_talk_rate"] = "⏳ Wait three seconds before the next message."
T["ar"]["mo_talk_long"] = "الرسالة طويلة (الحد {n} حرف)."
T["en"]["mo_talk_long"] = "Message too long (max {n} characters)."
T["ar"]["mo_say"] = "👤 <b>{name}</b>: {text}"
T["en"]["mo_say"] = "👤 <b>{name}</b>: {text}"
T["ar"]["mo_vote_start"] = "🗳 <b>「 بدأ التصويت 」</b> ({s} ثانية). صوّت من الأزرار في الخاص."
T["en"]["mo_vote_start"] = "🗳 <b>Voting started</b> ({s}s). Vote with the buttons in private."
T["ar"]["mo_vote_pick"] = "🗳 من تشك فيه؟ من لا يصوّت يُحسب صوته على نفسه."
T["en"]["mo_vote_pick"] = "🗳 Who do you suspect? If you don't vote, your vote counts for yourself."
T["ar"]["mo_end_town"] = "🏆 <b>فاز المواطنون!</b> تم طرد كل القتلة."
T["en"]["mo_end_town"] = "🏆 <b>Citizens win!</b> Every killer is out."
T["ar"]["mo_end_mafia"] = "🏆 <b>فازت المافيا!</b> تساوى القتلة مع الباقين."
T["en"]["mo_end_mafia"] = "🏆 <b>Mafia wins!</b> The killers equal the rest."

T["ar"]["mo_reveal_btn"] = "🎖 اكشف نفسي (مرة واحدة)"
T["en"]["mo_reveal_btn"] = "🎖 Reveal myself (once)"
T["ar"]["mo_already_revealed"] = "كشفت نفسك من قبل."
T["en"]["mo_already_revealed"] = "You already revealed yourself."
T["ar"]["mo_mayor_revealed"] = "🎖 <b>كشف العمدة عن نفسه: {name}</b>\nصوته يُحسب مرتين من الآن."
T["en"]["mo_mayor_revealed"] = "🎖 <b>The Mayor revealed: {name}</b>\nTheir vote counts twice from now on."
T["ar"]["mo_joker_out"] = "🃏 <b>{name} كان المجنون!</b>\nاختاروا من يسحبه معه خلال {s} ثانية. أول من يضغط يحسم، وإلا يختار البوت."
T["en"]["mo_joker_out"] = "🃏 <b>{name} was the Joker!</b>\nChoose who to take with them within {s} seconds. The first press decides; otherwise the bot picks."
T["ar"]["mo_joker_pick"] = "🃏 اختر من تسحبه معك:"
T["en"]["mo_joker_pick"] = "🃏 Pick who to take with you:"
T["ar"]["mo_joker_took"] = "🃏 سحب المجنون {name} معه."
T["en"]["mo_joker_took"] = "🃏 The Joker took {name} with them."

T["ar"]["mo_help_btn"] = "❓ شرح المافيا"
T["en"]["mo_help_btn"] = "❓ Mafia guide"
T["ar"]["mo_help_long"] = (
"🎌 <b>مافيا أونلاين · الشرح</b>\n━━━━━━━━━━━━━━━━\n"
"🎯 <b>الهدف</b>\n"
"المواطنون يكشفون القتلة ويطردونهم بالتصويت. القتلة يقتلون حتى يتساووا مع الباقين.\n\n"
"🎟 <b>الدخول</b>\n"
"اضغط «مافيا أونلاين» وانتظر في الطابور. تبدأ الغرفة عند اكتمال 8 لاعبين (بعد 30 ثانية تنتظر من يلحق حتى 15)، أو بعد 3 دقائق إذا وُجد 5 على الأقل.\n\n"
"🎭 <b>الأدوار</b>\n"
"🔪 <b>القاتل:</b> كل ليلة يختار ضحية مع زملائه.\n"
"🔍 <b>المحقق:</b> كل ليلة يكشف فريق لاعب.\n"
"🩺 <b>الطبيب:</b> كل ليلة يحمي لاعبًا، لكن لا يحمي نفس الشخص ليلتين متتاليتين. (من 6 لاعبين)\n"
"🎖 <b>العمدة:</b> يكشف نفسه مرة واحدة في النهار، فيُحسب صوته مرتين. (من 8 لاعبين)\n"
"🃏 <b>المجنون:</b> من المواطنين. إذا طُرد يسحب معه لاعبًا خلال 60 ثانية. (من 12 لاعبًا)\n"
"👥 <b>المواطن:</b> قوته في النقاش والتصويت.\n\n"
"🌙 <b>الليل</b>\n"
"تصلك الأزرار في الخاص. إن لم يختر القتلة أحدًا يختار البوت.\n\n"
"☀️ <b>النهار</b>\n"
"1️⃣ <b>النقاش:</b> اكتب رسالتك هنا، وتصل للجميع باسمك. رسالة كل 3 ثوانٍ، والحد 300 حرف.\n"
"2️⃣ <b>التصويت:</b> تُفتح الأزرار في الخاص، وصوّت على من تشك فيه أو تخطّى. من لا يصوّت يُحسب صوته على نفسه.\n"
"⚖️ يُطرد صاحب <b>الأصوات الأكثر</b>، والتعادل على الأعلى = لا طرد.\n\n"
"⏳ <b>الأوقات:</b> الليل دقيقة، والنقاش 3 دقائق، والتصويت دقيقة.\n"
"━━━━━━━━━━━━━━━━\n"
"<i>الأدوار سرّية حتى نهاية اللعبة، لا تكشف دورك بنفسك!</i>")
T["en"]["mo_help_long"] = (
"🎌 <b>Mafia online · Guide</b>\n━━━━━━━━━━━━━━━━\n"
"🎯 <b>Goal</b>\n"
"Citizens find and vote out the killers. Killers kill until they equal the rest.\n\n"
"🎟 <b>Joining</b>\n"
"Tap «Mafia online» and wait in the queue. The room starts at 8 players (after a 30-second window for more up to 15), or after 3 minutes if at least 5 are waiting.\n\n"
"🎭 <b>Roles</b>\n"
"🔪 <b>Killer:</b> each night picks a victim with the other killers.\n"
"🔍 <b>Detective:</b> each night checks a player's team.\n"
"🩺 <b>Doctor:</b> each night protects a player, but never the same person two nights in a row. (from 6 players)\n"
"🎖 <b>Mayor:</b> reveals once during the day; their vote then counts twice. (from 8 players)\n"
"🃏 <b>Joker:</b> a citizen. If voted out, takes a player with them within 60 seconds. (from 12 players)\n"
"👥 <b>Citizen:</b> strength in discussion and voting.\n\n"
"🌙 <b>Night</b>: buttons arrive in private. If no killer picks, the bot picks.\n\n"
"☀️ <b>Day</b>\n"
"1️⃣ <b>Discussion:</b> write your message here; it reaches everyone with your name. One message every 3 seconds, 300 characters max.\n"
"2️⃣ <b>Voting:</b> buttons open in private. Vote for a suspect or skip. Not voting counts as a vote for yourself.\n"
"⚖️ The player with the <b>most votes</b> is eliminated; a tie for first = no elimination.\n\n"
"⏳ <b>Times:</b> night 1 minute, discussion 3 minutes, voting 1 minute.\n"
"━━━━━━━━━━━━━━━━\n"
"<i>Roles stay secret until the end. Don't reveal yours!</i>")

T["ar"]["btn_online_notify"] = "🔔 إشعار الأونلاين"
T["en"]["btn_online_notify"] = "🔔 Online alerts"
T["ar"]["on_notify_on"] = "🔔 تم تفعيل إشعارات الأونلاين. بيوصلك تنبيه عند فتح أي طابور."
T["en"]["on_notify_on"] = "🔔 Online alerts are on. You'll get a message when a queue opens."
T["ar"]["on_notify_off"] = "🔕 تم إيقاف إشعارات الأونلاين."
T["en"]["on_notify_off"] = "🔕 Online alerts are off."
T["ar"]["on_notify_open"] = "🎮 بدأ طابور <b>{game}</b> الآن، تحب تنضم؟"
T["en"]["on_notify_open"] = "🎮 A <b>{game}</b> queue just opened. Want to join?"
T["ar"]["on_notify_join"] = "✅ انضم الآن"
T["en"]["on_notify_join"] = "✅ Join now"

T["ar"]["ar_title_xo"] = "❌⭕ إكس أو"
T["en"]["ar_title_xo"] = "❌⭕ Tic-tac-toe"
T["ar"]["ar_title_rps"] = "✊✋✌️ حجرة ورقة مقص"
T["en"]["ar_title_rps"] = "✊✋✌️ Rock Paper Scissors"
T["ar"]["ar_title_c4"] = "🔴🟡 أربعة في صف"
T["en"]["ar_title_c4"] = "🔴🟡 Connect Four"
T["ar"]["ar_friend_btn"] = "👥 تحدّي صديق"
T["en"]["ar_friend_btn"] = "👥 Challenge a friend"
T["ar"]["ar_menu"] = "🎲 <b>ألعاب ثنائية</b>\nاختر اللعبة: 🌐 اللعب مع أي شخص من الطابور، أو 👥 تحدّي صديق برابط."
T["en"]["ar_menu"] = "🎲 <b>Two-player games</b>\nPick a game: play a random online opponent, or 👥 challenge a friend with a link."
T["ar"]["ar_vs"] = "ضد {name}"
T["en"]["ar_vs"] = "vs {name}"
T["ar"]["ar_your_turn"] = "🟢 دورك الآن"
T["en"]["ar_your_turn"] = "🟢 Your turn"
T["ar"]["ar_their_turn"] = "⏳ دور الخصم"
T["en"]["ar_their_turn"] = "⏳ Their turn"
T["ar"]["ar_score"] = "النتيجة: {s}"
T["en"]["ar_score"] = "Score: {s}"
T["ar"]["ar_rps_wait"] = "🤔 اختر حركتك (الأفضل من 3 جولات)"
T["en"]["ar_rps_wait"] = "🤔 Pick your move (best of 3)"
T["ar"]["ar_rps_done"] = "✅ اخترت، بانتظار الخصم"
T["en"]["ar_rps_done"] = "✅ Picked, waiting for the opponent"
T["ar"]["ar_round"] = "الجولة: {a} ضد {b} — فاز {w}"
T["en"]["ar_round"] = "Round: {a} vs {b} — {w} wins"
T["ar"]["ar_round_draw"] = "الجولة: {a} ضد {b} — تعادل"
T["en"]["ar_round_draw"] = "Round: {a} vs {b} — draw"
T["ar"]["ar_win"] = "🏆 فزت!"
T["en"]["ar_win"] = "🏆 You won!"
T["ar"]["ar_lose"] = "😅 خسرت هذه المرة."
T["en"]["ar_lose"] = "😅 You lost this time."
T["ar"]["ar_draw"] = "🤝 تعادل!"
T["en"]["ar_draw"] = "🤝 Draw!"
T["ar"]["ar_again"] = "🎲 ألعاب ثنائية"
T["en"]["ar_again"] = "🎲 Two-player games"
T["ar"]["ar_not_now"] = "ليس دورك، أو الحركة غير صالحة."
T["en"]["ar_not_now"] = "Not your turn, or the move isn't valid."
T["ar"]["ar_busy"] = "أنت في لعبة حاليًا، أنهِها أولًا."
T["en"]["ar_busy"] = "You're in a game right now. Finish it first."
T["ar"]["ar_queued"] = "⏳ انضممت للطابور، بيوصلك خصم قريبًا."
T["en"]["ar_queued"] = "⏳ You joined the queue; an opponent will show up soon."
T["ar"]["ar_cancel"] = "❌ إلغاء"
T["en"]["ar_cancel"] = "❌ Cancel"
T["ar"]["ar_cancelled"] = "تم إلغاء انتظارك."
T["en"]["ar_cancelled"] = "Your wait was cancelled."
T["ar"]["ar_invite"] = "👥 <b>تحدّي {game}</b>\nأرسل هذا الرابط لصديقك، أول من يفتحه يدخل المباراة معك:\n{link}"
T["en"]["ar_invite"] = "👥 <b>{game} challenge</b>\nSend this link to your friend; whoever opens it first joins you:\n{link}"
T["ar"]["ar_invite_gone"] = "هذا الرابط انتهى أو استُخدم."
T["en"]["ar_invite_gone"] = "This link has expired or was already used."
T["ar"]["ar_invite_self"] = "لا تقدر تتحدى نفسك 🙂 أرسل الرابط لصديقك."
T["en"]["ar_invite_self"] = "You can't challenge yourself 🙂 Send the link to a friend."

T["ar"]["ar_menu_btn"] = "🎲 ألعاب ثنائية"
T["en"]["ar_menu_btn"] = "🎲 Two-player games"

T["ar"]["ar_join_btn"] = "🙋 انضم للتحدي"
T["en"]["ar_join_btn"] = "🙋 Join the challenge"
T["ar"]["ar_waiting"] = "بانتظار لاعب ثانٍ… {names}"
T["en"]["ar_waiting"] = "Waiting for a second player… {names}"
T["ar"]["ar_chat_full"] = "المباراة بدأت أو انتهت."
T["en"]["ar_chat_full"] = "This match has started or ended."
T["ar"]["ar_chat_already"] = "أنت في المباراة بالفعل."
T["en"]["ar_chat_already"] = "You're already in this match."
T["ar"]["ar_chat_turn"] = "🟢 دور: {name}"
T["en"]["ar_chat_turn"] = "🟢 Turn: {name}"
T["ar"]["ar_chat_win"] = "🏆 فاز {name}!"
T["en"]["ar_chat_win"] = "🏆 {name} wins!"
T["ar"]["ar_chat_draw"] = "🤝 تعادل!"
T["en"]["ar_chat_draw"] = "🤝 Draw!"
T["ar"]["ar_rps_wait_chat"] = "🤔 بانتظار اختيار اللاعبين (سري حتى تكتمل الجولة)"
T["en"]["ar_rps_wait_chat"] = "🤔 Waiting for both picks (secret until the round ends)"

T["ar"]["ar_inline_text"] = "🎲 {name} يتحداك في <b>{game}</b>!\nاضغط الزر وادخل المباراة معه."
T["en"]["ar_inline_text"] = "🎲 {name} challenges you to <b>{game}</b>!\nTap the button to join the match."
T["ar"]["ar_inline_go"] = "🎮 اقبل التحدي"
T["en"]["ar_inline_go"] = "🎮 Accept the challenge"

T["ar"]["anon_name"] = "مجهول 🎭"
T["en"]["anon_name"] = "Anonymous 🎭"
T["en"]["pf_visit"] = T["en"]["pf_visit"].replace("Think you can beat it\n", "Think you can beat it?\n")

T["ar"]["gs_title"] = "🎮 <b>ألعابك</b>"
T["en"]["gs_title"] = "🎮 <b>Your games</b>"
T["ar"]["gs_row"] = "• {game}: {w} فوز · {l} خسارة · {d} تعادل"
T["en"]["gs_row"] = "• {game}: {w} won · {l} lost · {d} drawn"
T["ar"]["gs_mafia"] = "• {game}: {n} لعبة · {w} فوز"
T["en"]["gs_mafia"] = "• {game}: {n} games · {w} won"
T["ar"]["gs_mafia_group"] = "🔪 المافيا (مجموعات)"
T["en"]["gs_mafia_group"] = "🔪 Mafia (groups)"

T["ar"]["kt_title"] = "🎌 <b>كت</b> · سؤال عن الأنمي"
T["en"]["kt_title"] = "🎌 <b>Kt</b> · An anime question"
T["ar"]["kt_next"] = "🎲 سؤال آخر"
T["en"]["kt_next"] = "🎲 Another one"
T["ar"]["kt_empty"] = "ما في أسئلة حاليًا."
T["en"]["kt_empty"] = "No questions available right now."

T["ar"]["gp_top_title"] = "🏆 <b>متصدرو المجموعة</b>"
T["en"]["gp_top_title"] = "🏆 <b>Group leaderboard</b>"
T["ar"]["gp_top_title_plain"] = "🏆 متصدرو المجموعة"
T["en"]["gp_top_title_plain"] = "🏆 Group leaderboard"

T["ar"]["btn_two_player"] = "🎲 ألعاب ثنائية: إكس أو، حجرة ورقة مقص، أربعة في صف"
T["en"]["btn_two_player"] = "🎲 Two-player games: Tic-tac-toe, RPS, Connect Four"

T["ar"]["btn_discover"] = "🧬 اكتشف نمطك"
T["en"]["btn_discover"] = "🧬 Discover your type"

T["ar"]["mo_inline_go"] = "🔪 <b>مافيا أونلاين</b>\nاضغط الزر وادخل الطابور، وتبدأ اللعبة عند اكتمال اللاعبين."
T["en"]["mo_inline_go"] = "🔪 <b>Mafia online</b>\nTap the button to join the queue; the game starts once enough players arrive."
T["ar"]["inl_on_go"] = "🎮 <b>{game}</b>\nاضغط الزر وادخل الطابور."
T["en"]["inl_on_go"] = "🎮 <b>{game}</b>\nTap the button to join the queue."
T["ar"]["inl_game_text"] = "🎮 <b>{game}</b>\nاضغط الزر وابدأ الآن!"
T["en"]["inl_game_text"] = "🎮 <b>{game}</b>\nTap the button and start now!"
T["ar"]["inl_game_go"] = "🎮 ابدأ الآن"
T["en"]["inl_game_go"] = "🎮 Start now"
T["ar"]["inl_group_text"] = "👥 <b>{game}</b>\nأضف البوت لمجموعتك وابدأ اللعب مع أصدقائك."
T["en"]["inl_group_text"] = "👥 <b>{game}</b>\nAdd the bot to your group and play with your friends."
T["ar"]["inl_group_go"] = "➕ أضفني لمجموعتك"
T["en"]["inl_group_go"] = "➕ Add me to your group"
T["ar"]["kt_title_plain"] = "🎌 كت · سؤال عن الأنمي"
T["en"]["kt_title_plain"] = "🎌 Kt · An anime question"

T["ar"]["kt_title"] = "🎌 كت انمي"
T["en"]["kt_title"] = "🎌 Kt anime"

T["ar"]["ar_inline_start"] = "🎮 <b>{game}</b>\nاضغط «انضم للتحدي» وابدأ اللعب في هذه الرسالة."
T["en"]["ar_inline_start"] = "🎮 <b>{game}</b>\nTap «Join the challenge» and play right in this message."

T["ar"]["ar_pick_mode"] = "🎲 <b>{game}</b>\nكيف تبي تلعب؟"
T["en"]["ar_pick_mode"] = "🎲 <b>{game}</b>\nHow do you want to play?"
T["ar"]["ar_online_btn"] = "🌐 لعب أونلاين"
T["en"]["ar_online_btn"] = "🌐 Play online"

T["ar"]["ps_saved"] = "💾 تم حفظ نمطك في ملفك الشخصي."
T["en"]["ps_saved"] = "💾 Your type was saved to your profile."
T["ar"]["pf_persona"] = "🧬 <b>نمطك:</b> {code}"
T["en"]["pf_persona"] = "🧬 <b>Your type:</b> {code}"
T["ar"]["pf_persona_same"] = "👥 شخصيات من نفس نمطك:"
T["en"]["pf_persona_same"] = "👥 Characters with your type:"

T["ar"]["pf_games_none"] = "🎮 <b>ألعابك:</b> لم تلعب بعد"
T["en"]["pf_games_none"] = "🎮 <b>Your games:</b> not played yet"
T["ar"]["pf_persona_none"] = "🧬 <b>نمطك:</b> لم تكتشفه بعد، جرّب «اكتشف نمطك»"
T["en"]["pf_persona_none"] = "🧬 <b>Your type:</b> not discovered yet, try «Discover your type»"

T["en"]["gpm_xo"] = "❌⭕ Tic-tac-toe"
T["en"]["gpm_rps"] = "✊ Rock Paper Scissors"
T["en"]["gpm_c4"] = "🔴🟡 Connect Four"
T["en"]["gpm_top"] = "🏆 Ranking"

T["ar"]["sp_end_btn"] = "❌ إلغاء اللعبة"
T["en"]["sp_end_btn"] = "❌ Cancel game"

T["ar"]["sp_countdown"] = "⏳ تبدأ بعد {s} ثانية، ويلزم {min}–{max} لاعبين"
T["en"]["sp_countdown"] = "⏳ Starts in {s}s, needs {min}–{max} players"
