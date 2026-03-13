import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request
from twilio.rest import Client
import openai
import requests
from io import BytesIO

app = Flask(__name__)

TWILIO_SID    = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE  = os.environ.get("TWILIO_PHONE_NUMBER")
WHATSAPP_DEST = os.environ.get("WHATSAPP_DESTINATION")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY")

client_twilio = Client(TWILIO_SID, TWILIO_TOKEN)
client_openai = openai.OpenAI(api_key=OPENAI_KEY)

@app.route("/transcrire", methods=["POST"])
def transcrire():
    # 1. Récupérer les infos envoyées par Twilio
    recording_url = request.form.get("RecordingUrl", "") + ".mp3"
    recording_sid = request.form.get("RecordingSid", "")
    telephone     = request.form.get("From", "Inconnu")
    flux          = request.form.get("flux", "Inconnu")

    # 2. Télécharger l'audio
    audio_bytes = requests.get(
        recording_url,
        auth=(TWILIO_SID, TWILIO_TOKEN)
    ).content

    # 3. Transcrire avec Whisper
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = client_openai.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="fr"
    )
    texte_brut = transcript.text.strip()

    # 4. Supprimer l'audio chez Twilio (RGPD)
    try:
        client_twilio.recordings(recording_sid).delete()
    except Exception:
        pass

    # 5. GPT reformule en message professionnel
    prompt = f"""Tu es un assistant pour une infirmière libérale.
Voici un message vocal brut laissé par un appelant :

- Type d'appel : {flux}
- Telephone : {telephone}
- Message : {texte_brut}

Rédige un message WhatsApp professionnel, clair et bien formaté pour l'infirmière.
Corrige les fautes et reformule si nécessaire.
Le message doit être sobre et professionnel, sans emojis."""

    reponse = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    message_final = reponse.choices[0].message.content

    # 6. Envoyer le WhatsApp
    client_twilio.messages.create(
        from_=f"whatsapp:{TWILIO_PHONE}",
        to=WHATSAPP_DEST,
        body=message_final
    )

    return "", 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)