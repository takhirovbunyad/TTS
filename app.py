# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template_string, url_for, send_from_directory
import os, uuid
from datetime import datetime
from gtts import gTTS
import pyttsx3

APP_TITLE = "CHTTS"
app = Flask(__name__, static_folder="static")
AUDIO_DIR = os.path.join(app.static_folder, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

VOICE_OPTIONS = [
    {"id": "gtts:tr", "label": "IZZY VOICE"},
    {"id": "pyttsx3:uz", "label": "SDR VOICE"},
    {"id": "pyttsx3:ru_male", "label": "SDR VOICE MALE"},
]

DEFAULT_SPEED_WPM = 170  # pyttsx3 uchun rate

def unique_name(ext: str):
    return f"{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex}.{ext}"

def synth_gtts(text, lang, out_path):
    tts = gTTS(text=text, lang=lang)
    tts.save(out_path)
    return out_path

def synth_pyttsx3(text, out_path, rate=170, lang='uz'):
    """
    pyttsx3 bilan offline TTS
    lang='uz' -> Uzbek ovoz
    lang='ru_male' -> Russian Male ovoz
    """
    engine = pyttsx3.init()
    engine.setProperty('rate', rate)
    voices = engine.getProperty('voices')

    if lang == 'uz':
        # Uzbek ovoz
        for v in voices:
            if 'uz' in v.id.lower() or 'uzbek' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
    elif lang == 'ru_male':
        # Russian Male ovoz
        for v in voices:
            if ('ru' in v.id.lower() or 'russian' in v.name.lower()) and 'male' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        else:
            # Agar erkak ovoz topilmasa, default ruscha ovoz
            for v in voices:
                if 'ru' in v.id.lower() or 'russian' in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break

    engine.save_to_file(text, out_path)
    engine.runAndWait()
    engine.stop()
    return out_path


INDEX_HTML = """<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>
body{font-family:sans-serif;background:#f0f0f0;color:#111;margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100vh;}
.card{background:#fff;padding:20px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,.1);width:90%;max-width:600px;}
textarea{width:100%;height:140px;margin-bottom:12px;padding:10px;font-size:16px;border-radius:8px;border:1px solid #ccc;}
select,input[type=number]{width:48%;padding:8px;margin-bottom:12px;border-radius:6px;border:1px solid #ccc;}
.row{display:flex;justify-content:space-between;gap:4%;}
button{padding:10px 16px;border:none;border-radius:8px;background:#3b82f6;color:#fff;font-weight:600;cursor:pointer;}
button:disabled{opacity:.5;cursor:not-allowed;}
audio{width:100%;margin-top:12px;}
</style>
</head>
<body>
<div class="card">
<h2>{{ title }}</h2>
<textarea id="text">Salom chromaticus agar buni oqiyotgan bolsang shuni bilginki sen gaysan</textarea>
<div class="row">
<select id="voice">
{% for v in voices %}
<option value="{{ v.id }}">{{ v.label }}</option>
{% endfor %}
</select>
<input id="rate" type="number" value="170" min="80" max="300"/>
</div>
<button id="makeBtn">gapirtirish</button>
<span id="status"></span>
<div id="playerWrap" style="display:none">
<audio id="player" controls></audio>
<a id="downloadLink" href="#" download>skachat qilish</a>
</div>
<script>
const makeBtn=document.getElementById('makeBtn');
const textEl=document.getElementById('text');
const voiceEl=document.getElementById('voice');
const rateEl=document.getElementById('rate');
const statusEl=document.getElementById('status');
const playerWrap=document.getElementById('playerWrap');
const player=document.getElementById('player');
const downloadLink=document.getElementById('downloadLink');

makeBtn.addEventListener('click',async()=>{
    const payload={text:textEl.value.trim(),voice:voiceEl.value,rate:parseInt(rateEl.value||'170',10)};
    if(!payload.text){alert('Matn kiriting!');return;}
    makeBtn.disabled=true;statusEl.textContent='Yaratilyapti…';
    try{
        const res=await fetch('/synthesize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        const data=await res.json();
        if(!res.ok)throw new Error(data.error||'Xato');
        player.src=data.url;
        downloadLink.href=data.url; downloadLink.download=data.filename;
        playerWrap.style.display='block';
        statusEl.textContent='Tayyor';
    }catch(e){statusEl.textContent='Xato: '+e.message;}
    finally{makeBtn.disabled=false;}
});
</script>
</div>
</body>
</html>"""

@app.get("/")
def index():
    return render_template_string(INDEX_HTML, title=APP_TITLE, voices=VOICE_OPTIONS)

@app.post("/synthesize")
def synthesize():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    voice_id = data.get("voice") or "gtts:tr"
    rate = int(data.get("rate") or DEFAULT_SPEED_WPM)
    if not text: return jsonify({"error":"Matn bo'sh bo'lmasin"}),400
    provider, voice = voice_id.split(":",1)
    try:
        filename = unique_name("mp3")
        out_path = os.path.join(AUDIO_DIR, filename)
        if provider=="gtts":
            synth_gtts(text, voice, out_path)
        elif provider=="pyttsx3":
            synth_pyttsx3(text, out_path, rate, lang=voice)
        else:
            return jsonify({"error":"Noma'lum provider"}),400
        url=url_for('static',filename=f"audio/{filename}")
        return jsonify({"url":url,"filename":filename,"meta":provider})
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.get("/static/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename, as_attachment=False)

if __name__=="__main__":
    os.makedirs(AUDIO_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
