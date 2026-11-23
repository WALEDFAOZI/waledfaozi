"""بوت تليجرام لاختبار الأوتاكو."""
import os
import socket
import time

# يتغير مع كل نسخة؛ يظهر في /myid لتعرف أي نسخة هي التي ترد عليك
VERSION = "2026-11-23-dq"
# هوية هذه العملية بالذات: اسم الجهاز + رقم العملية. لو ردّ عليك /myid بهويتين مختلفتين فعندك نسختان شغالتان
INSTANCE = f"{socket.gethostname()[:14]}-{os.getpid()}"
STARTED = time.time()
