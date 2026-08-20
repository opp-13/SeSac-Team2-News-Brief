import os
 
import requests
 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
 
GOOGLE_TRANSLATE_API_KEY = os.environ.get("GOOGLE_TRANSLATE_API_KEY")
GOOGLE_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
 
 
_PROMPT_TEMPLATES = {
    "kor": (
        "다음 뉴스 기사를 3문장 이내로 핵심만 간결하게 한국어로 요약해줘. "
        "요약문 외의 다른 말은 붙이지 마.\n\n"
        "제목: {title}\n\n본문: {text}"
    ),
    "eng": (
        "Summarize the following news article in English, in 3 sentences or fewer, "
        "covering only the key points. Do not add anything besides the summary.\n\n"
        "Title: {title}\n\nBody: {text}"
    ),
}
 
 
def _summarize_with_groq(title: str, text: str, lang: str):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY 환경변수가 설정되어 있지 않습니다.")
 
    prompt = _PROMPT_TEMPLATES[lang].format(title=title, text=text)
 
    resp = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 300,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
 
 
def _translate_with_google(text: str, target: str = "ko"):
    if not GOOGLE_TRANSLATE_API_KEY:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY 환경변수가 설정되어 있지 않습니다.")
 
    resp = requests.post(
        GOOGLE_TRANSLATE_URL,
        params={"key": GOOGLE_TRANSLATE_API_KEY},
        json={"q": text, "target": target, "format": "text"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["translations"][0]["translatedText"]
 
 
def summarize_item(item, lang: str):

    if lang not in ("kor", "eng"):
        raise ValueError(f"lang은 'kor' 또는 'eng'여야 합니다: {lang!r}")
 
    source_text = getattr(item, "body", None) or getattr(item, "description", None) or item.title
 
    try:
        summary = _summarize_with_groq(item.title, source_text, lang)
    except Exception as e:
        item.summary = f"(요약 실패: {e})"
        item.summary_ko = None
        return
 
    item.summary = summary
 
    if lang == "kor":
        item.summary_ko = None  
    else:  
        try:
            item.summary_ko = _translate_with_google(summary, target="ko")
        except Exception as e:
            item.summary_ko = f"(번역 실패: {e})"
 
 
PROVIDER_LANG = {
    "naver": "kor",
    "freenews": "eng",
}
 
 
def summarize_stage(items: list, lang: str = None):
    for item in items:
        item_lang = lang or PROVIDER_LANG.get(item.provider, "kor")
        summarize_item(item, item_lang)
    return items
 