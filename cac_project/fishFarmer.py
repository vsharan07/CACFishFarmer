# Authors: Andrew Wang, Alicia Ramirez, Vedant Sharan, Ava Siclait
# Congressional District: FL-27
# Project name: FishFarmer.AI

# -- import statements -- #
import json
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse 
from fastapi import Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import google.generativeai as genai
import bcrypt
from typing import List, Optional
load_dotenv() # loads files from .env
genai.configure(api_key = os.getenv("GEMINI_API_KEY")) 
app = FastAPI() 

preferencesFile = os.path.join(os.getcwd(), "preferences.json") # user preference data
userData = os.path.join(os.getcwd(), "users.json") # user login data, users.json is empty initially; it keeps growing as more accounts are made.

# -- preference stuff -- # 
def loadPreferences():
    if os.path.exists(preferencesFile):
        with open(preferencesFile, "r") as f:
            return json.load(f)
    return {
        "sfx": True,
        "volume": 50,
        "includeRationale": True,
        "geographicRegion": "north-america"
    }

def savePreferences(prefs):
    print("Saving preferences:", prefs)
    with open(preferencesFile, "w") as f:
        json.dump(prefs, f, indent=4)

defaultPreferences = loadPreferences()

class userNewPreferences(BaseModel):
    sfx: bool = True
    volume: int = 50
    includeRationale: bool = True
    geographicRegion: str = "north-america"

# -- user account stuff -- #
def loadUser():
    # actually loads user data from users.json
    if os.path.exists(userData):
        with open(userData, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                # File exists but is empty or invalid JSON, return empty list
                return []
    return []

def saveUser(users):
    # saves the current list of users to users.json
    with open(userData, "w") as f:
        json.dump(users, f, indent=4)

# -- user auth stuff -- #
class userCredentials(BaseModel):
    # base model for login or registration 
    username: str
    password: str

class userRegistration(userCredentials):
    # a model but for email
    email: str

class loginResponse(BaseModel):
    # used when a login is successful
    status: str
    message: str
    username: str       
        
# -- chat stuff -- #
class farmingData(BaseModel): # Data class
    phValue: float # ranges from 0 - 14 (can go above 14, but would be completely unrealistic)
    salinity: float # ppt
    algae: float # cfu/Liter
    dissolvedOxygen: float # mg/L
    bacterialLoad: float # CFU/mL
    environmentalCondition: str # depends on geographic location, could also include additional environmental factors put on your tank, like aerators, filters, etc.
    
class chatMessage(BaseModel):
    role: str # user or model
    content: str

class chatRequest(BaseModel):
    messages: List[chatMessage] = []
    farmingData: Optional["farmingData"] = None 

class response(BaseModel):
    response: str        
    
# frontend directory 
frontendDir = os.path.join(os.path.dirname(__file__), "frontend")

app.mount("/static", StaticFiles(directory=frontendDir), name="static") # app mounts to frontend static files
app.mount("/music", StaticFiles(directory=os.path.join(frontendDir, "music")), name="music") # app also mounts to music files, wouldn't work on uvicorn servers before

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# -- fastapi routes, corresponds to html pages -- #
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
async def saveScreen():
    with open(os.path.join(frontendDir, "6Response.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read())
    

# -- this is where the user's inputs go -- #
@app.post("/geminiCall", response_model=response)
async def geminiCall(data: chatRequest):
    try:
        # build the base prompt if farming data exists
        basePrompt = ""
        if data.farmingData:
            payload = data.farmingData.model_dump()
            currentPrefs = loadPreferences()
            includeRationale = currentPrefs.get("includeRationale")
            promptRegion = currentPrefs.get("geographicRegion")

            addRationale = (
                "Also, analyze each of these conditions, and provide a detailed rationale."
                if includeRationale
                else "Analyze each of these conditions briefly, no rationale."
            )

            basePrompt = f"""
            The following are fish pond water conditions:
            pH: {payload['phValue']}, Dissolved oxygen: {payload['dissolvedOxygen']} mg/L,
            Salinity: {payload['salinity']} ppt, Algae: {payload['algae']} cells/L,
            Bacterial load: {payload['bacterialLoad']} CFU/mL, 
            Environmental conditions: {payload['environmentalCondition']}.
            Tailor your response for {promptRegion}. {addRationale}
            """

        # include previous conversation
        model = genai.GenerativeModel("gemini-2.5-flash")
        chat_history = data.messages or []

        # combine the base prompt with chat history
        full_context = [{"role": m.role, "parts": [m.content]} for m in chat_history]
        if basePrompt:
            full_context.append({"role": "user", "parts": [basePrompt]})

        result = model.generate_content(full_context)
        text = getattr(result, "text", "No response generated.")
        return {"response": text}

    except Exception as e:
        return JSONResponse(content={"error": f"Gemini request failed: {e}"}, status_code=500)

@app.post("/analyzeData") 
async def analyzeData(data: farmingData):
    wrapped = chatRequest(messages=[], farmingData=data)
    return await geminiCall(wrapped)

# -- user authentication endpoints -- # 
@app.post("/register")
async def registerUser(user: userRegistration):
    users = loadUser()
    # this part checks if username/email already exists
    for u in users: 
        if u['username'] == user.username:
            raise HTTPException (status_code = 400, detail = "Username already taken :(")
        if u['email'] == user.email:
            raise HTTPException (status_code = 400, detail = "Email already registered :(")
    restrictedPassword = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') # for security ofc
    # creates new user record
    newUser = {
        "username": user.username,
        "email": user.email,
        "password": restrictedPassword
    }
    users.append(newUser)
    saveUser(users)
    
    return {"status": "success", "message": "Welcome to FishFarmer.AI!"}

@app.post("/login", response_model = loginResponse)
async def loginUser(credentials: userCredentials):
    users = loadUser()
    userRecord = None
    for u in users:
        if u['username'] == credentials.username or u['email'] == credentials.username:
            userRecord = u
            break
    if not userRecord:
        raise HTTPException(status_code=401, detail="User not found! Check your username/email.")
    
    if bcrypt.checkpw(credentials.password.encode('utf-8'), userRecord['password'].encode('utf-8')):
        return loginResponse(
            status="success",
            message=f"Welcome back, {credentials.username}!",
            username=userRecord['username']
        )
    else:
        raise HTTPException(status_code=401, detail="Incorrect password, try again!") 

@app.get("/options")
async def get_options():
    return JSONResponse(content=loadPreferences())

@app.post("/options")
async def save_options(prefs: userNewPreferences):
    newPrefs = prefs.model_dump()
    savePreferences(newPrefs)
    return {"status": "success", "message": "Preferences saved!"}
