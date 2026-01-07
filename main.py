from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import os
from dotenv import load_dotenv
from groq import Groq

app = FastAPI()

load_dotenv()

# Configuramos el cliente de Gemini UNA SOLA VEZ al inicio
# Usamos un nombre claro para que no se confunda con otros clientes
api_key = os.getenv("GROQ_API_KEY")
client_ia = Groq(api_key=api_key)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get('/', response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get('/analizar/{username}')
async def analyze(username: str):
    headers = {"Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/users/{username}/repos"
    
    # Llamamos a este 'http_client' para no pisar al de Gemini
    async with httpx.AsyncClient() as http_client:
        respuesta = await http_client.get(url, headers=headers)
    
    if respuesta.status_code != 200:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en GitHub")
    
    datos = respuesta.json()
    if not datos or isinstance(datos, dict):
        return {"usuario": username, "mensaje": "Sin repositorios"}
    
    # Procesamiento de datos de GitHub
    total_estrellas = sum(repo.get("stargazers_count", 0) for repo in datos)
    lenguajes = {}
    for repo in datos:
        leng = repo.get("language")
        if leng:
            lenguajes[leng] = lenguajes.get(leng, 0) + 1

    nivel = "Principiante" if total_estrellas == 0 else "Estrella"
    
    
    try:
        # Mejoramos el prompt para que sea más directo y técnico
        prompt_mentor = (
            f"Actúa como un Mentor Tech Senior. Analiza este perfil: {username}. "
            f"Tecnologías usadas: {list(lenguajes.keys())}. Estrellas: {total_estrellas}. "
            "Da un consejo técnico motivador de máximo 2 líneas. Sé directo, no saludes."
        )

        completion = client_ia.chat.completions.create (
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt_mentor}]
        )
        consejo_ia = completion.choices[0].message.content
    except Exception as e:
        print(f"Error detectado: {e}")
        consejo_ia = "Tu stack tecnológico es sólido. ¡Seguí puliendo esos repositorios!"
    
    return {
        "usuario": username,
        "repositorios_publicos": len(datos),    
        "estrellas_totales": total_estrellas,
        "tecnologias": lenguajes,
        "nivel_desarrollador": nivel,
        "consejo": consejo_ia
    }