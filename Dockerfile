FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/data/otaku.db

# خط يدعم العربية + مكتبات تشكيل النص لبطاقة النتيجة
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core libraqm0 libfribidi0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# pytest غير لازم في الصورة
RUN grep -v '^pytest' requirements.txt > /tmp/req.txt && pip install --no-cache-dir -r /tmp/req.txt

COPY otaku_bot ./otaku_bot
COPY data ./data
COPY assets ./assets

RUN useradd -m bot && mkdir /data && chown bot /data
USER bot
VOLUME /data

# فحص بنك الأسئلة عند البناء؛ التوكن يُمرَّر وقت التشغيل ولا يدخل الصورة
RUN python -m otaku_bot --check

CMD ["python", "-m", "otaku_bot"]
