# Authors: Andrew Wang, Alicia Ramirez, Vedant Sharan, Ava Siclait
# Congressional District: FL-27
# Project name: FishFarmer.AI

# -- import statements -- #
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import List, Optional
import bcrypt
from google import genai

load_dotenv()  # load .env
GENIE_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GENIE_KEY)  # use client, not GenerativeModel

app = FastAPI()

# --- file paths ---
preferencesFile = os.path.join(os.getcwd(), "preferences.json")
userData = os.path.join(os.getcwd(), "users.json")
frontendDir = os.path.join(os.path.dirname(__file__), "frontend")

# --- preferences ---
def loadPreferences():
    if os.path.exists(preferencesFile):
        with open(preferencesFile, "r") as f:
            return json.load(f)
    return {"sfx": True, "volume": 50, "includeRationale": True, "geographicRegion": "north-america"}

def savePreferences(prefs):
    with open(preferencesFile, "w") as f:
        json.dump(prefs, f, indent=4)

# --- users ---
def loadUser():
    if os.path.exists(userData):
        with open(userData, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def saveUser(users):
    with open(userData, "w") as f:
        json.dump(users, f, indent=4)

# --- models ---
class userNewPreferences(BaseModel):
    sfx: bool = True
    volume: int = 50
    includeRationale: bool = True
    geographicRegion: str = "north-america"

class userCredentials(BaseModel):
    username: str
    password: str

class userRegistration(userCredentials):
    email: str

class loginResponse(BaseModel):
    status: str
    message: str
    username: str

class FarmingData(BaseModel):
    phValue: Optional[float] = None
    salinity: Optional[float] = None
    algae: Optional[float] = None
    dissolvedOxygen: Optional[float] = None
    bacterialLoad: Optional[float] = None
    environmentalCondition: Optional[str] = None

class chatMessage(BaseModel):
    role: str
    content: str

class chatRequest(BaseModel):
    messages: List[chatMessage] = []
    farmingData: Optional[FarmingData] = None

class response(BaseModel):
    response: str

# --- static ---
app.mount("/static", StaticFiles(directory=frontendDir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- routes for HTML pages ---
@app.get("/", response_class=HTMLResponse)
async def homeScreen():
    with open(os.path.join(frontendDir, "1Home.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())
@app.get("/1Home.html", response_class=HTMLResponse)
async def homeScreen():
    with open(os.path.join(frontendDir, "1Home.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/2Chat.html", response_class=HTMLResponse)
async def chatScreen():
    with open(os.path.join(frontendDir, "2Chat.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/3Options.html", response_class=HTMLResponse)
async def optionsScreen():
    with open(os.path.join(frontendDir, "3Options.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/4Account.html", response_class=HTMLResponse)
async def accountScreen():
    with open(os.path.join(frontendDir, "4Account.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/5Saves.html", response_class=HTMLResponse)
async def saveScreen():
    with open(os.path.join(frontendDir, "5Saves.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/6Response.html", response_class=HTMLResponse)
async def responseScreen():
    with open(os.path.join(frontendDir, "6Response.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ... repeat similar GET routes for other HTML pages ...

# --- Gemini AI ---
@app.post("/geminiCall", response_model=response)
async def geminiCall(data: chatRequest):
    try:
        # build prompt from farmingData
        prompt = ""
        if data.farmingData:
            fd = data.farmingData
            prefs = loadPreferences()
            addRationale = "Also, analyze each condition with rationale." if prefs.get("includeRationale", True) else "Analyze briefly, no rationale."
            region = prefs.get("geographicRegion", "north-america")
            prompt = f"""
            Fish pond water conditions:
            pH: {fd.phValue}, Dissolved oxygen: {fd.dissolvedOxygen} mg/L,
            Salinity: {fd.salinity} ppt, Algae: {fd.algae} cells/L,
            Bacterial load: {fd.bacterialLoad} CFU/mL,
            Environmental conditions: {fd.environmentalCondition}.
            Tailor your response for {region}. {addRationale}. 
            Lastly, don't format your response. Just have normal text, and try to make sentences as short and concise as possible.
            """

        # combine chat history + prompt
        chat_texts = [f"{m.role}: {m.content}" for m in data.messages] if data.messages else []
        if prompt:
            chat_texts.append(f"User: {prompt}")
        full_content = "\n".join(chat_texts) or "Hello, analyze these conditions."

        # call Gemini API
        response_obj = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_content
        )

        result_text = getattr(response_obj, "text", "No response generated.")
        return {"response": result_text}

    except Exception as e:
        print("Gemini error:", e)
        return JSONResponse(content={"error": f"Gemini request failed: {e}"}, status_code=500)

# --- analyze endpoint ---
@app.post("/analyzeData")
async def analyzeData(data: FarmingData):
    wrapped = chatRequest(messages=[], farmingData=data)
    return await geminiCall(wrapped)

# --- auth endpoints ---
@app.post("/register")
async def registerUser(user: userRegistration):
    users = loadUser()
    for u in users:
        if u['username'] == user.username:
            raise HTTPException(status_code=400, detail="Username already taken")
        if u['email'] == user.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    users.append({"username": user.username, "email": user.email, "password": hashed})
    saveUser(users)
    return {"status": "success", "message": "Welcome to FishFarmer.AI!"}

@app.post("/login", response_model=loginResponse)
async def loginUser(credentials: userCredentials):
    users = loadUser()
    userRec = next((u for u in users if u['username'] == credentials.username or u['email'] == credentials.username), None)
    if not userRec:
        raise HTTPException(status_code=401, detail="User not found")
    if bcrypt.checkpw(credentials.password.encode(), userRec['password'].encode()):
        return loginResponse(status="success", message=f"Welcome back, {credentials.username}!", username=userRec['username'])
    else:
        raise HTTPException(status_code=401, detail="Incorrect password")

# --- preferences ---
@app.get("/options")
async def get_options():
    return JSONResponse(loadPreferences())

@app.post("/options")
async def save_options(prefs: userNewPreferences):
    savePreferences(prefs.model_dump())
    return {"status": "success", "message": "Preferences saved"}
