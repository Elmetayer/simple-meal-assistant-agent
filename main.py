import os
from fastapi import FastAPI, Form
from notion_client import Client
import anthropic
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

# Initialisation des clients
notion = Client(auth=os.getenv("NOTION_TOKEN"))
# Utilisation du SDK Anthropic
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DB_HISTORY_ID = os.getenv("DATABASE_ID_HISTORY")

def get_notion_context():
    """Récupère l'historique des repas dans Notion avec la syntaxe correcte."""
    try:
        # Correction de la syntaxe pour les versions récentes du SDK
        response = notion.databases.query(
            **{
                "database_id": DB_HISTORY_ID,
                "page_size": 10,
                "sorts": [{"property": "Date", "direction": "descending"}]
            }
        )
        
        meals = []
        for row in response.get("results", []):
            # Sécurité supplémentaire pour accéder aux propriétés
            properties = row.get("properties", {})
            name_prop = properties.get("Nom", {}).get("title", [])
            if name_prop:
                meals.append(name_prop[0]["plain_text"])
                
        return ", ".join(meals) if meals else "Aucun historique trouvé."
    except Exception as e:
        print(f"Erreur détaillée Notion: {str(e)}")
        return f"Erreur technique lors de la récupération."

@app.post("/whatsapp")
async def whatsapp_reply(Body: str = Form(...)):
    user_msg = Body.lower()
    
    # 1. Extraction du contexte
    past_meals = get_notion_context()
    
    # 2. Génération avec Claude 3.5 Sonnet
    # Le 'system prompt' est passé en paramètre séparé chez Anthropic
    system_msg = f"""
    Tu es un assistant familial expert en planification de repas. 
    Historique des 10 derniers repas : {past_meals}.
    Instructions : Propose des idées variées, évite les répétitions. 
    Réponds de manière chaleureuse et concise pour WhatsApp.
    """
    
    message = claude_client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        system=system_msg,
        messages=[
            {"role": "user", "content": user_msg}
        ]
    )
    
    ai_response = message.content[0].text

    # 3. Retour vers WhatsApp via Twilio
    resp = MessagingResponse()
    resp.message(ai_response)
    return str(resp)
