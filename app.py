import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request
from twilio.rest import Client
import openai
import requests
from io import BytesIO
import time

app = Flask(__name__)

TWILIO_SID    = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE  = os.environ.get("TWILIO_PHONE_NUMBER")
WHATSAPP_DEST = os.environ.get("WHATSAPP_DESTINATION")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY")

client_twilio = Client(TWILIO_SID, TWILIO_TOKEN)
client_openai = openai.OpenAI(api_key=OPENAI_KEY)

@app.route("/start_recording", methods=["POST"])
def start_recording():
    body = request.form.get("body", "")
    call_sid = request.form.get("CallSid") or (body.split("CallSid=")[-1].split("&")[0] if "CallSid=" in body else None)
    client_twilio.calls(call_sid).recordings.create()
    return "", 200

@app.route("/transcrire", methods=["POST"])
def transcrire():
    call_status   = request.form.get("CallStatus", "")
    body = request.form.get("body", "")
    call_sid = request.form.get("CallSid") or (body.split("CallSid=")[-1].split("&")[0] if "CallSid=" in body else "")
    telephone = request.form.get("From") or (body.split("From=")[-1].split("&")[0] if "From=" in body else "Inconnu")

    print(f"CallStatus reçu: {call_status}")
    print(f"Tous les paramètres: {request.form}")
    if call_status and call_status != "completed":
        return "", 200

    # Attendre que l'enregistrement soit prêt
    time.sleep(15)

    # Récupérer l'enregistrement
    recordings = client_twilio.recordings.list(call_sid=call_sid, limit=1)
    if not recordings:
        return "", 200

    recording = recordings[0]
    recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Recordings/{recording.sid}.mp3"

    audio_bytes = requests.get(
        recording_url,
        auth=(TWILIO_SID, TWILIO_TOKEN)
    ).content

    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = client_openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="fr"
    )
    texte_brut = transcript.text.strip()

    try:
        client_twilio.recordings(recording.sid).delete()
    except Exception:
        pass

    prompt = f"""Tu es un assistant pour une infirmière libérale.
Voici la transcription complète d'un appel téléphonique :

- Téléphone : {telephone}
- Transcription : {texte_brut}

Rédige un message WhatsApp professionnel, clair et bien structuré pour l'infirmière.
Extrais et présente : nom/prénom, motif, coordonnées, disponibilités.
Corrige les fautes. Message sobre et professionnel, sans emojis."""

    reponse = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    message_final = reponse.choices[0].message.content

    client_twilio.messages.create(
        from_=f"whatsapp:+14155238886",
        to=WHATSAPP_DEST,
        body=message_final
    )

    return "", 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)