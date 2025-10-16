# Authors: Andrew Wang, Alicia Ramirez, Vedant Sharan, Ava Sinclait
# Congressional District: FL-27
# Project name: FishFarmer

# import statements
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse 
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from openai import OpenAI
load_dotenv() # loads files from .env
client = OpenAI(api_key=os.getenv("OpenAI_API_Key"))
app = FastAPI() 

defaultPreferences = {
    "sfx": True,
    "volume": True,
    "includeRationale": True,
    "geographicRegion": "north-america"
} # user prefernces automatically set upon web launch

# frontend directory 
frontendDir = os.path.join(os.path.dirname(__file__), "frontend")

app.mount("/static", StaticFiles(directory=frontendDir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
#fastapi routes, corresponds to frontend html pages
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

class farmingData(BaseModel): # Data class
    phValue: float 
    salinity: float 
    algae: float
    dissolvedOxygen: float  
    waterQuality: float # Bacterial load
    environmentalCondition: str # Depends on geographic location
    
class response(BaseModel):
    response: str    

@app.post("/callOpenAI", response_model=response) 
def callOpenAI(data: farmingData):
    prompt = f"""
    The following are fish pond water conditions:
    pH: {data.phValue}, 
    Oxygen: {data.dissolvedOxygen}, 
    Salinity: {data.salinity},
    Algae: {data.algae}, 
    Bacterial load: {data.waterQuality},
    Environmental conditions: {data.environmentalCondition}.
    Analyze these conditions. When finished, provide analysis + rationale for any possible improvements that could made to conditions.
    """
    try:
        response = client.chat.completions.create( 
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyzeData")
def analyzeData(data: farmingData):
    if not (0 <= data.phValue <= 14):
        raise HTTPException(status_code=400, detail= "pH must be between 0 - 14")
    return {"response": callOpenAI(data)}

class userNewPreferences(BaseModel):
    sfx: bool = True
    volume: int = 50
    includeRationale: bool = True
    geographicRegion: str = "north-america"

@app.get("/options")
async def get_options():
    return JSONResponse(content=defaultPreferences)

@app.post("/options")
async def save_options(prefs: userNewPreferences):
    defaultPreferences.update(prefs.model_dumpt()) 
    return {"status": "success", "message": "Preferences saved!"}
