"""هروب HTML (نسخة مستقلة لتجنّب الاستيراد الدائري)."""
import html


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)
