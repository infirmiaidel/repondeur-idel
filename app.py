import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request
from twilio.rest import Client
import openai
import time

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
    body = request.form.get("body", "")
    telephone = request.form.get("From") or (body.split("From=")[-1].split("&")[0] if "From=" in body else "Inconnu")
    transcription = request.form.get("Transcription", "")

    print(f"Telephone: {telephone}")
    print(f"Transcription: {transcription}")

    if not transcription:
        return "", 200

    prompt = f"""Tu es un assistant pour une infirmière libérale.
Voici la transcription d'un appel téléphonique :
- Téléphone : {telephone}
- Transcription : {transcription}

Rédige un message WhatsApp professionnel, clair et bien structuré pour l'infirmière.
Extrais et présente : nom/prénom, motif, coordonnées, disponibilités.
Corrige les fautes. Message sobre et professionnel, sans emojis."""

    reponse = client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    message_final = reponse.choices[0].message.content

    client_twilio.messages.create(
        from_="whatsapp:+14155238886",
        to=WHATSAPP_DEST,
        body=message_final
    )

    return "", 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)