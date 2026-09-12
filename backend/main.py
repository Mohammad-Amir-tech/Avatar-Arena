import base64
import uuid
from pathlib import Path
from pydantic import BaseModel
import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from dotenv import load_dotenv
import edge_tts

load_dotenv()

app = FastAPI()

import sqlite3

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_avatars (
            id TEXT PRIMARY KEY,
            name TEXT,
            personality TEXT,
            language TEXT,
            photo_base64 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


# ⭐ Har language ke liye voices (edge-tts se)
VOICES = {
    "en":       {"pro": "en-US-GuyNeural",     "con": "en-US-JennyNeural",   "judge": "en-GB-RyanNeural"},
    "hi":       {"pro": "hi-IN-MadhurNeural",  "con": "hi-IN-SwaraNeural",   "judge": "hi-IN-MadhurNeural"},
    "ur":       {"pro": "ur-PK-AsadNeural",    "con": "ur-PK-UzmaNeural",    "judge": "ur-PK-AsadNeural"},
    "bn":       {"pro": "bn-IN-BashkarNeural", "con": "bn-IN-TanishaaNeural","judge": "bn-IN-BashkarNeural"},
    "ta":       {"pro": "ta-IN-ValluvarNeural","con": "ta-IN-PallaviNeural", "judge": "ta-IN-ValluvarNeural"},
    "te":       {"pro": "te-IN-MohanNeural",   "con": "te-IN-ShrutiNeural",  "judge": "te-IN-MohanNeural"},
    "mr":       {"pro": "mr-IN-ManoharNeural", "con": "mr-IN-AarohiNeural",  "judge": "mr-IN-ManoharNeural"},
    "gu":       {"pro": "gu-IN-NiranjanNeural","con": "gu-IN-DhwaniNeural",  "judge": "gu-IN-NiranjanNeural"},
    "kn":       {"pro": "kn-IN-GaganNeural",   "con": "kn-IN-SapnaNeural",   "judge": "kn-IN-GaganNeural"},
    "ml":       {"pro": "ml-IN-MidhunNeural",  "con": "ml-IN-SobhanaNeural", "judge": "ml-IN-MidhunNeural"},
    "pa":       {"pro": "hi-IN-MadhurNeural",  "con": "hi-IN-SwaraNeural",   "judge": "hi-IN-MadhurNeural"},
    "hinglish": {"pro": "en-IN-PrabhatNeural", "con": "en-IN-NeerjaNeural",  "judge": "en-IN-PrabhatNeural"},
    "es":       {"pro": "es-ES-AlvaroNeural",  "con": "es-ES-ElviraNeural",  "judge": "es-ES-AlvaroNeural"},
    "fr":       {"pro": "fr-FR-HenriNeural",   "con": "fr-FR-DeniseNeural",  "judge": "fr-FR-HenriNeural"},
    "de":       {"pro": "de-DE-ConradNeural",  "con": "de-DE-KatjaNeural",   "judge": "de-DE-ConradNeural"},
    "ja":       {"pro": "ja-JP-KeitaNeural",   "con": "ja-JP-NanamiNeural",  "judge": "ja-JP-KeitaNeural"},
    "ko":       {"pro": "ko-KR-InJoonNeural",  "con": "ko-KR-SunHiNeural",   "judge": "ko-KR-InJoonNeural"},
    "zh":       {"pro": "zh-CN-YunxiNeural",   "con": "zh-CN-XiaoxiaoNeural","judge": "zh-CN-YunxiNeural"},
    "ar":       {"pro": "ar-SA-HamedNeural",   "con": "ar-SA-ZariyahNeural", "judge": "ar-SA-HamedNeural"},
    "ru":       {"pro": "ru-RU-DmitryNeural",  "con": "ru-RU-SvetlanaNeural","judge": "ru-RU-DmitryNeural"},
}


# ⭐ AI ko kaunsi language mein likhna hai
LANG_INSTRUCTIONS = {
    "en":       "Respond ONLY in English.",
    "hi":       "कृपया केवल हिंदी में उत्तर दें (देवनागरी लिपि में)। Respond ONLY in Hindi.",
    "ur":       "براہ کرم صرف اردو میں جواب دیں۔ Respond ONLY in Urdu.",
    "bn":       "শুধুমাত্র বাংলায় উত্তর দিন। Respond ONLY in Bengali.",
    "ta":       "தமிழில் மட்டுமே பதிலளிக்கவும்। Respond ONLY in Tamil.",
    "te":       "తెలుగులో మాత్రమే సమాధానం ఇవ్వండి। Respond ONLY in Telugu.",
    "mr":       "कृपया फक्त मराठीत उत्तर द्या। Respond ONLY in Marathi.",
    "gu":       "કૃપા કરીને ફક્ત ગુજરાતીમાં જવાબ આપો। Respond ONLY in Gujarati.",
    "kn":       "ದಯವಿಟ್ಟು ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ। Respond ONLY in Kannada.",
    "ml":       "ദയവായി മലയാളത്തിൽ മാത്രം ഉത്തരം നൽകുക। Respond ONLY in Malayalam.",
    "pa":       "ਕਿਰਪਾ ਕਰਕੇ ਸਿਰਫ਼ ਪੰਜਾਬੀ ਵਿੱਚ ਜਵਾਬ ਦਿਓ। Respond ONLY in Punjabi (Gurmukhi script).",
    "hinglish": "Respond ONLY in Hinglish — a natural mix of Hindi and English in Roman script. Example: 'AI education ko transform kar raha hai lekin teachers ka role bhi important hai.'",
    "es":       "Responde SOLO en español.",
    "fr":       "Répondez UNIQUEMENT en français.",
    "de":       "Antworte NUR auf Deutsch.",
    "ja":       "日本語のみで答えてください。",
    "ko":       "한국어로만 답변하세요.",
    "zh":       "请只用中文回答。",
    "ar":       "الرجاء الرد باللغة العربية فقط.",
    "ru":       "Отвечайте ТОЛЬКО на русском языке.",
}


AGENTS = {
    "pro": {
        "name": "Alex",
        "role": "Pro",
        "system": "You are Alex, an optimistic debater. You argue IN FAVOR of the topic. Keep responses 2-3 sentences, punchy and clear. Use evidence when possible.",
    },
    "con": {
        "name": "Maya",
        "role": "Con",
        "system": "You are Maya, a skeptical debater. You argue AGAINST the topic. Keep responses 2-3 sentences, sharp and critical. Point out flaws and risks.",
    },
    "judge": {
        "name": "Judge",
        "role": "Judge",
        "system": "You are a neutral judge. After hearing both sides, deliver a balanced verdict in 3-4 sentences. Weigh evidence, logic, and rhetoric.",
    },
}


async def agent_response(agent_key, topic, history, language):
    agent = AGENTS[agent_key]
    lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["en"])
    system_content = agent["system"] + " " + lang_instruction

    messages = [{"role": "system", "content": system_content}]
    for h in history:
        messages.append({"role": "user", "content": f"{h['agent']}: {h['text']}"})
    messages.append({"role": "user", "content": f"Topic: {topic}. Now respond as {agent['name']}."})

    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=400,
            timeout=20.0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Groq failed: {e}")
        return "AI temporarily unavailable. Please retry."



import sqlite3

def get_custom_avatar(avatar_id):
    """Fetch custom avatar from DB by ID."""
    if not avatar_id:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            "SELECT id, name, personality, language, photo_base64 FROM custom_avatars WHERE id = ?",
            (avatar_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "name": row[1], "personality": row[2], 
                    "language": row[3], "photo": row[4]}
    except Exception as e:
        print(f"[ERROR] get_custom_avatar: {e}")
    return None
    


async def debate_stream(topic, language="en", custom_avatar_id=None, custom_side="pro"):
    print(f"[INFO] Language: {language}, Custom: {custom_avatar_id} on {custom_side}")
    yield f"data: {json.dumps({'type': 'language', 'language': language})}\n\n"

    # ⭐ Custom avatar fetch karo
    custom = get_custom_avatar(custom_avatar_id)
    custom_agent = None
    if custom:
        # Personality ke hisaab se system prompt banao
        personality_prompts = {
            "optimist": "You are an optimistic debater. You argue IN FAVOR of the topic with enthusiasm and evidence.",
            "skeptic": "You are a skeptical debater. You argue AGAINST the topic with sharp critical thinking and risks.",
            "neutral": "You are a balanced analyst. You weigh both sides fairly.",
        }
        custom_agent = {
            "name": custom["name"],
            "role": custom_side.capitalize() if custom_side != "judge" else "Judge",
            "system": personality_prompts.get(custom["personality"], personality_prompts["optimist"]),
            "photo": custom["photo"],
            "is_custom": True,
        }
        # ⭐ Frontend ko custom avatar info bhejo
        yield f"data: {json.dumps({'type': 'custom_avatar', 'side': custom_side, 'avatar': {'name': custom['name'], 'photo': custom['photo'], 'id': custom['id']}})}\n\n"

    history = []
    turns = ["pro", "con", "pro", "con", "judge"]

    for agent_key in turns:
        # ⭐ Agar custom avatar is side pe hai to usko use karo
        if custom_agent and custom_side == agent_key:
            actual_agent = custom_agent
            yield f"data: {json.dumps({'type': 'turn_start', 'agent': agent_key})}\n\n"
            text = await custom_agent_response(custom_agent, topic, history, language)
            history.append({"agent": custom_agent["name"], "text": text})
            yield f"data: {json.dumps({'type': 'text', 'agent': agent_key, 'text': text, 'language': language, 'name': custom_agent['name']})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'turn_start', 'agent': agent_key})}\n\n"
            text = await agent_response(agent_key, topic, history, language)
            history.append({"agent": AGENTS[agent_key]["name"], "text": text})
            yield f"data: {json.dumps({'type': 'text', 'agent': agent_key, 'text': text, 'language': language})}\n\n"
        await asyncio.sleep(0.3)

    yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def custom_agent_response(agent, topic, history, language):
    """Response from a custom user-created avatar."""
    lang_instruction = LANG_INSTRUCTIONS.get(language, LANG_INSTRUCTIONS["en"])
    system_content = agent["system"] + " " + lang_instruction

    messages = [{"role": "system", "content": system_content}]
    for h in history:
        messages.append({"role": "user", "content": f"{h['agent']}: {h['text']}"})
    messages.append({"role": "user", "content": f"Topic: {topic}. Now respond as {agent['name']}."})

    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=400,
            timeout=20.0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Custom avatar failed: {e}")
        return "AI temporarily unavailable."

@app.get("/api/debate")
async def debate(topic: str, language: str = "en", custom_avatar: str = None, custom_side: str = "pro"):
    return StreamingResponse(
        debate_stream(topic, language, custom_avatar, custom_side),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/tts")
async def tts_endpoint(request: Request):
    data = await request.json()
    text = data.get("text", "")
    agent_key = data.get("agent", "pro")
    language = data.get("language", "en")

    voice = VOICES.get(language, VOICES["en"]).get(agent_key, VOICES["en"][agent_key])
    print(f"[TTS] {agent_key} | {language} | {voice}")

    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        print(f"[ERROR] TTS: {e}")
        return Response(content=b"", media_type="audio/mpeg", status_code=500)

class AvatarCreate(BaseModel):
    name: str
    personality: str  # "optimist" / "skeptic" / "neutral"
    language: str
    photo_base64: str  # data:image/jpeg;base64,...

@app.post("/api/avatar/create")
async def create_avatar(avatar: AvatarCreate):
    avatar_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO custom_avatars (id, name, personality, language, photo_base64) VALUES (?, ?, ?, ?, ?)",
        (avatar_id, avatar.name, avatar.personality, avatar.language, avatar.photo_base64)
    )
    conn.commit()
    conn.close()
    return {"id": avatar_id, "status": "created"}

@app.get("/api/avatar/list")
async def list_avatars():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT id, name, personality, language, photo_base64 FROM custom_avatars")
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "personality": r[2], "language": r[3], "photo": r[4]}
        for r in rows
    ]

@app.delete("/api/avatar/{avatar_id}")
async def delete_avatar(avatar_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("DELETE FROM custom_avatars WHERE id = ?", (avatar_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        return {"status": "deleted", "id": avatar_id}
    return {"status": "not_found", "id": avatar_id}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
