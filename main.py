import os
from fastapi import FastAPI, Form, Request
from notion_client import Client
from openai import OpenAI
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

# Initialisation des clients
notion = Client(auth=os.getenv("NOTION_TOKEN"))
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_HISTORY_ID = os.getenv("DATABASE_ID_HISTORY")

def get_notion_context():
    """Récupère les 10 derniers dîners pour la fenêtre de contexte."""
    response = notion.databases.query(
        database_id=DB_HISTORY_ID,
        page_size=10,
        sorts=[{"property": "Date", "direction": "descending"}]
    )
    # Parsing simplifié des résultats (à adapter selon vos colonnes)
    meals = []
    for row in response["results"]:
        name = row["properties"]["Nom"]["title"][0]["plain_text"]
        meals.append(name)
    return ", ".join(meals)

@app.post("/whatsapp")
async def whatsapp_reply(Body: str = Form(...)):
    user_msg = Body.lower()
    
    # 1. Extraction du contexte de l'historique Notion
    past_meals = get_notion_context()
    
    # 2. Génération de la réponse avec l'IA
    system_prompt = f"""
    Tu es un assistant familial. Voici les derniers repas consommés : {past_meals}.
    Propose des idées variées en évitant les répétitions. 
    Sois concis, réponds sur un ton amical pour un groupe WhatsApp.
    """
    
    completion = ai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ]
    )
    ai_response = completion.choices[0].message.content

    # 3. Réponse formatée pour WhatsApp (TwiML)
    resp = MessagingResponse()
    resp.message(ai_response)
    return str(resp)
