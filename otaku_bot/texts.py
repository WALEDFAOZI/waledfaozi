"""نصوص الواجهة بالعربية والإنجليزية."""
from __future__ import annotations

import random

from .config import CATEGORY_LABELS, CATEGORY_LABELS_EN

T: dict[str, dict[str, str]] = {
"ar": {
 "welcome": "أهلًا بك في <b>بوت اختبار الأوتاكو</b> 🎌\n\nاختبر معرفتك بالأنمي: أكثر من <b>1400 سؤال</b> من الأسهل للأصعب، وألعاب، وتحدٍّ يومي، ومواجهات ومسابقات في المجموعات والقنوات.\nتحصل على <b>تقييم من 10 ولقب ومستوى وإنجازات</b>!\n\nاختر طريقة اللعب:",
 "challenge_banner": "\n\n⚔️ <b>{name}</b> تحداك! حصل على <b>{score}/10</b> ويلقّب <b>{title}</b>.\nتقبل التحدي بنفس الأسئلة؟",
 "btn_full": "🎯 الاختبار الكامل (50 سؤال)", "btn_quick": "⚡ اختبار سريع (10 أسئلة)",
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
 "g_menu": "🎮 <b>ألعاب أخرى</b>\nاختر لعبة:", "g_tf": "✅❌ صح أم غلط", "g_song": "🎵 خمّن الأنمي من الأغنية", "g_ord": "📅 رتّب حسب سنة العرض",
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
 "btn_full": "🎯 Full test (50 questions)", "btn_quick": "⚡ Quick test (10 questions)",
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
 "g_menu": "🎮 <b>Other games</b>\nPick a game:", "g_tf": "✅❌ True or false", "g_song": "🎵 Guess the anime from the song", "g_ord": "📅 Order by release year",
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
    "btn_anime": "🎬 Suggest me an anime",
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

T["ar"]["btn_channel"] = "💬 تعال للقناة وتفاعل مع الأوتاكو"
T["en"]["btn_channel"] = "💬 Join the channel & chat with fellow otakus"

T["ar"].update({
    "btn_invite": "👥 ادعُ أصدقاءك",
    "iv_head": "👥 <b>ادعُ أصدقاءك</b>\nتُحسب الدعوة بعد أن يكمل صديقك أول اختبار كامل ويشترك بالقناة، وتأخذ ألقابًا خاصة.",
    "iv_count": "📨 دعواتك المكتملة: {n}", "iv_badge": "🏅 لقبك: {b}", "iv_nobadge": "🏅 لا لقب بعد، أول دعوة تعطيك لقبًا!",
    "iv_next": "🎯 باقي {k} للقب {b}", "iv_btn": "📤 شارك رابط الدعوة",
    "iv_share": "تعال جرّب اختبار الأوتاكو، شف كم تجيب من 10 🔥",
    "iv_joined": "🎉 صديقك أكمل أول اختبار واشترك! دعواتك المكتملة: {n}", "iv_badge_up": "🏅 ترقّيت للقب: {b}",
})
T["en"].update({
    "btn_invite": "👥 Invite friends",
    "iv_head": "👥 <b>Invite friends</b>\nAn invite counts once your friend finishes a full test and joins the channel. Earn special badges.",
    "iv_count": "📨 Completed invites: {n}", "iv_badge": "🏅 Your badge: {b}", "iv_nobadge": "🏅 No badge yet, your first invite earns one!",
    "iv_next": "🎯 {k} more for {b}", "iv_btn": "📤 Share invite link",
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
T["en"]["pf_visit"] = "\n\n👤 <b>{name}</b> shared their profile: best score <b>{score}</b>/10 — {title}\nThink you can beat it? 😏"
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
    "du_share_btn": "📤 أرسل التحدي لصديق", "du_share_text": "⚔️ تحدّاك في 7 أسئلة أنمي، تقدر تغلبني؟",
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
    "du_share_btn": "📤 Send challenge to a friend", "du_share_text": "⚔️ I challenge you to 7 anime questions, can you beat me?",
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
    "gpk_quiz": "🎯 أسئلة عامة (10)", "gpk_sudden": "☠️ الموت المفاجئ (الأخير يفوز)", "gpk_tf": "✅❌ صح أم غلط",
    "gpk_song": "🎵 خمّن الأنمي من الأغنية", "gpk_char": "🕵️ من هي الشخصية؟", "gpk_quote": "💬 من قال الاقتباس؟",
    "gpk_ord": "📅 أيّها أقدم؟", "gpk_images": "🖼 أسئلة صور",
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
    "gp_help": "🎌 <b>اختبار الأوتاكو</b>\nللعب مع الأصدقاء هنا اكتب /play أو أحد الأوامر: /quiz /sudden /tf /song /char /quote /order /images\n/gtop متصدرو المجموعة · /gstop إيقاف اللعبة · /glang تغيير اللغة (للأدمن)\nولاختبارك الشخصي افتح البوت بالخاص.",
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
    "gp_help": "🎌 <b>Otaku Quiz</b>\nTo play with friends here use /play or: /quiz /sudden /tf /song /char /quote /order /images\n/gtop group leaderboard · /gstop stop the game · /glang switch language (admins)\nFor your personal test open the bot in private.",
    "gp_open_private": "💬 Open the bot in private",
})

T["ar"].update({
    "lbm_text": "🏆 <b>الترتيب</b>\nاختر المدة:\n\n🌍 <b>العام</b> — أفضل نتيجة لكل لاعب على الإطلاق\n📅 <b>الأسبوعي</b> — يتصفّر كل أحد 00:00 (توقيت مكة)\n☀️ <b>اليوم</b> — يتصفّر كل منتصف ليل",
    "lbp_a": "🌍 العام (كل الأوقات)", "lbp_w": "📅 الأسبوعي", "lbp_d": "☀️ اليوم",
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
    "btn_group": "👥 Challenge in a group",
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
    "btn_channel_game": "📢 Challenge in a channel",
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
    "ch_test_btn": "🔧 اختبار النشر في القناة", "ch_test_ok": "✅ البوت ينشر ويحذف في القناة بشكل سليم.",
    "ch_test_ok_nodel": "⚠️ البوت ينشر لكن لا يستطيع الحذف: فعّل له صلاحية «حذف الرسائل».",
    "ch_open_pm": "📩 لإكمال المسابقة افتح البوت بالخاص أولًا: @{me} ثم أعد كتابة /play",
})
T["en"].update({
    "ch_test_btn": "🔧 Test posting in the channel", "ch_test_ok": "✅ The bot can post and delete in the channel.",
    "ch_test_ok_nodel": "⚠️ The bot can post but not delete: enable the “Delete messages” right.",
    "ch_open_pm": "📩 To continue, open the bot in private first: @{me}, then type /play again",
})

T["ar"]["gp_nobody_joined"] = "😴 ما شارك أحد هذه المرة. جرّب مرة ثانية!"
T["en"]["gp_nobody_joined"] = "😴 Nobody joined this time. Try again!"

T["ar"]["btn_sub_bot_channel"] = "📢 اشترك في قناة البوت"
T["en"]["btn_sub_bot_channel"] = "📢 Subscribe to the bot's channel"
T["ar"]["gp_must_sub"] = "⚠️ لازم تشترك في قناتنا @{ch} عشان تشارك. اشترك ثم اضغط «شارك» مرة ثانية."
T["en"]["gp_must_sub"] = "⚠️ You must subscribe to our channel @{ch} to take part. Subscribe, then tap “Participate” again."

T["ar"].update({
    "btn_suggest": "💬 الاقتراحات والملاحظات",
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
    "btn_suggest": "💬 Suggestions & feedback",
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
