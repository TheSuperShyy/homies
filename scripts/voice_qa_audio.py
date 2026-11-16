# -*- coding: utf-8 -*-
"""Render a voice_qa run's transcripts to audio, the way a real call would sound.

    python scripts/voice_qa_audio.py RUN_DIR OUT_DIR     # spends a little Cartesia

Made 7 Oct for the owner's "give me 3 samples each voice agent": Claude-played
transcripts cannot show pronunciation, and audio can.


Michael's lines: Homies' Cartesia account (the only one that owns the live
voices), the live voice of that agent, sonic-3.5, volume 2 (incoming: speed 0.8
and the happy tag Vapi prepends), the masculine pronunciation dictionary, and
our own voice_guard replacements applied first, as Vapi applies them before the
text reaches Cartesia. The waiting line Vapi speaks while a tool runs is included.
The caller's lines: our own Cartesia key, a Hebrew library voice, no dictionary.
Writes one MP3 per call plus index.html with the transcript, into OUT."""
import html, io, json, os, re, subprocess, sys, urllib.request, urllib.error, wave
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)
sys.stdout.reconfigure(encoding="utf-8")
import voice_guard as G
import cartesia_tts as T

RUN, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
HOMIES = T.load_key("CARTESIA_YARIV_API_KEY")
OURS = T.load_key("CARTESIA_API_KEY")
DICT_M = re.search(r"^CARTESIA_DICT_INBOUND=(.*)$", io.open(".env", encoding="utf-8").read(), re.M).group(1).strip()
# 16 Nov: a call to a woman carries the feminine dictionary live (the Call button since 8 Oct, the dialer
# since PR #13), so her test call is voiced with it too; a man's and an unknown name's keep the masculine one.
DICT_F = re.search(r"^CARTESIA_DICT_FEMININE=(.*)$", io.open(".env", encoding="utf-8").read(), re.M).group(1).strip()
# Mirrors scripts/vapi_set_voice.py's AGENT_VOICE. Since 7 Oct evening both agents
# speak with the 31 Aug clone; until then the incoming line was clone A
# (4486a4a7…, speed 0.8, the happy tag), dropped for sounding "like a karaoke mic".
VOICE = {"inbound": {"id": "ba765d50-19c6-4b3e-bc15-9de3b45f82f7", "speed": None, "tag": ""},
         "debt":    {"id": "ba765d50-19c6-4b3e-bc15-9de3b45f82f7", "speed": None, "tag": ""}}
CALLER_VOICE = "84b969ad-19c7-428d-b742-48d387f7f138"   # Gil, "Friendly Host", a library voice
# A card may name its own caller voice (`caller_voice`): 8 Oct, a woman on the line is
# Yael, "Casual Presence" (1daba551-...), a female Hebrew library voice on our key.
# 15 Nov: VOICE_QA_RATE=24000 halves each line's download, for a line that keeps
# dropping Cartesia's replies part-way; 44.1 kHz stays the default.
RATE = int(os.environ.get("VOICE_QA_RATE", "44100"))
REPS = G.replacements()
chars = {"homies": 0, "ours": 0}


def guard(chunk):
    """Vapi's formatPlan on one chunk: exact rules replace all, regex rules the first match."""
    for r in REPS:
        if r["type"] == "exact":
            chunk = chunk.replace(r["key"], r["value"])
        else:
            flags = re.I if any(o.get("type") == "ignore-case" for o in (r.get("options") or [])) else 0
            chunk = re.sub(r["regex"], r["value"].replace("\\", "\\\\"), chunk, count=1, flags=flags)
    return chunk


def tts(key, voice_id, text, speed=None, dict_id=None):
    body = {"model_id": "sonic-3.5", "transcript": text, "voice": {"mode": "id", "id": voice_id},
            "language": "he", "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": RATE},
            "generation_config": {"volume": 2.0}}
    if speed:
        body["generation_config"]["speed"] = speed
    if dict_id:
        body["pronunciation_dict_id"] = dict_id
    req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"X-API-Key": key, "Cartesia-Version": "2026-03-01", "Content-Type": "application/json"})
    # 15 Nov: Cartesia timed out mid-run once; a slow line is retried, not fatal.
    import http.client
    for attempt in range(4):
        try:
            raw = urllib.request.urlopen(req, timeout=120).read()
            break
        except urllib.error.HTTPError as e:
            sys.exit("Cartesia %s: %s" % (e.code, e.read()[:300]))
        except (TimeoutError, urllib.error.URLError, http.client.IncompleteRead, ConnectionError) as e:
            if attempt == 3:
                raise
            # A dropped line or lost DNS needs a moment; back off 10, 20, then 30 s.
            print("Cartesia slow (%s), retrying" % e, flush=True)
            import time
            time.sleep(10 * (attempt + 1))
    with wave.open(io.BytesIO(raw)) as w:
        return w.readframes(w.getnframes())


def michael(agent, text, gender="m"):
    v = VOICE[agent]
    # Vapi cuts a turn into chunks at sentence ends and runs the guard on each one.
    chunks = [c for c in re.split(r"(?<=[.?!])\s+", text.strip()) if c]
    spoken = " ".join((v["tag"] + guard(c)) for c in chunks)
    chars["homies"] += len(spoken)
    return tts(HOMIES, v["id"], spoken, v["speed"], DICT_F if gender == "f" else DICT_M), spoken


# 15 Nov: a caller's "I see / want / hope" is spelled the same for a man and a woman,
# and the library voice guesses (a woman's "אני רואה" came out leaning masculine).
# The test caller is a simulated person, so its own words are pointed by its gender
# before voicing; the transcript keeps the speech-to-text spelling.
SELF = {"רואה": ("רוֹאֶה", "רוֹאָה"), "רוצה": ("רוֹצֶה", "רוֹצָה"), "עושה": ("עוֹשֶׂה", "עוֹשָׂה"),
        "קונה": ("קוֹנֶה", "קוֹנָה"), "מקווה": ("מְקַוֶּה", "מְקַוָּה"), "שותה": ("שׁוֹתֶה", "שׁוֹתָה")}


def point_self(text, gender):
    i = 1 if gender == "f" else 0
    return re.sub(r"(?<=אני )(%s)(?![֐-׿])" % "|".join(SELF), lambda m: SELF[m.group(1)][i], text)


def caller(text, voice=CALLER_VOICE, gender="m"):
    text = point_self(text, gender)
    chars["ours"] += len(text)
    return tts(OURS, voice, text)


def silence(sec):
    return b"\x00\x00" * int(RATE * sec)


cards = {s["id"]: s for s in json.load(open(os.path.join(RUN, "deck.json"), encoding="utf-8"))["scenarios"]}
# 15 Nov: only the agents the run bundled (a debt-only deck has no live_inbound.json).
waits = {a: json.load(open(os.path.join(RUN, "live_%s.json" % a), encoding="utf-8"))["waiting_lines"]
         for a in ("inbound", "debt") if os.path.exists(os.path.join(RUN, "live_%s.json" % a))}
# 15 Nov: VOICE_QA_ONLY=id,id renders only those calls (the rest keep their MP3 and
# still appear in index.html), so one failed call is redone without paying for all.
ONLY = {x for x in os.environ.get("VOICE_QA_ONLY", "").split(",") if x}
pages = []
for fn in sorted(os.listdir(os.path.join(RUN, "transcripts"))):
    if not fn.endswith(".json"):
        continue
    sid = fn[:-5]
    agent = cards[sid]["agent"]
    tenant = (cards[sid].get("vars") or {}).get("gender", "m")
    render = not ONLY or sid in ONLY
    t = json.load(open(os.path.join(RUN, "transcripts", fn), encoding="utf-8"))
    audio, rows = [], []
    for turn in t["turns"]:
        for rnd in turn.get("rounds") or []:
            for call in rnd:
                w = waits[agent].get(call.get("tool"))
                if w and render:
                    pcm, _ = michael(agent, w, tenant)
                    audio += [pcm, silence(0.6)]
                rows.append(("tool", "%s %s" % (call.get("tool"), json.dumps(call.get("arguments") or {}, ensure_ascii=False)), ""))
        if "agent" in turn:
            if render:
                pcm, spoken = michael(agent, turn["agent"], tenant)
                audio += [pcm, silence(0.45)]
            rows.append(("Michael", turn["agent"], turn.get("en", "")))
        elif "caller" in turn:
            if render:
                audio += [caller(turn["caller"], cards[sid].get("caller_voice") or CALLER_VOICE,
                                 (cards[sid].get("vars") or {}).get("gender", "m")), silence(0.45)]
            rows.append(("Caller", turn["caller"], turn.get("en", "")))
    pages.append((sid, cards[sid]["title"], rows))
    if not render:
        continue
    wav_path = os.path.join(OUT, sid + ".wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(b"".join(audio))
    mp3 = os.path.join(OUT, sid + ".mp3")
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-i", wav_path, "-b:a", "128k", mp3], check=True)
    os.remove(wav_path)
    print("rendered", sid, "->", mp3, flush=True)

css = ("body{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;background:#fafafa;color:#222}"
       "h1{font-size:22px}h2{font-size:17px;margin-top:32px}audio{width:100%;margin:8px 0}"
       "table{border-collapse:collapse;width:100%}td{border-top:1px solid #ddd;padding:6px 8px;vertical-align:top}"
       "td.who{width:70px;font-weight:600}td.he{direction:rtl;text-align:right;font-size:16px}td.en{color:#555;font-size:14px}"
       "tr.tool td{color:#888;font-size:12px}")
out = ["<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
       "<title>Voice agent test 7 Oct</title><style>%s</style>" % css,
       "<h1>Voice agent test, 7 Oct: one scenario per agent, three samples each</h1>",
       "<p>Claude played both the agent's AI (from the live instructions) and the caller; the audio is Michael's live voice "
       "with the gender dictionary, the caller in another voice.</p>"]
for sid, title, rows in pages:
    out.append("<h2>%s <small>(%s)</small></h2><audio controls preload='none' src='%s.mp3'></audio><table>" % (html.escape(title), sid, sid))
    for who, he, en in rows:
        cls = " class='tool'" if who == "tool" else ""
        out.append("<tr%s><td class='who'>%s</td><td class='he'>%s</td><td class='en'>%s</td></tr>" % (cls, who, html.escape(he), html.escape(en)))
    out.append("</table>")
io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write("\n".join(out))
print("characters: Homies account %d, our account %d" % (chars["homies"], chars["ours"]))
