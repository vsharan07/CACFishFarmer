# Authors: Andrew Wang, Alicia Ramirez, Vedant Sharan, Ava Sinclait
# Congressional District: FL-27
# Project name: FishFarmer
# might make ts open source, will make a github repos 
# 

# import statements
from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import openai

load_dotenv() # loads files from .env
openai.api_key = os.getenv("apiKey") # gets api key

app = FastAPI() 

from fastapi.staticfiles import StaticFiles

# frontend directory 
frontendDir = os.path.join(os.path.dirname(__file__), "frontend")

app.mount("/static", StaticFiles(directory=frontendDir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/", response_class=HTMLResponse)
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

class farmingData(BaseModel): # Data class
    phValue: float 
    salinity: float 
    algae: float
    dissolvedOxygen: float  
    waterQuality: float # Bacterial load
    environmentalCondition: str # Depends on geographic location, also may change so that users do image inputs instead
    
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
    Analyze these conditions. When finished, provide analysis + rationale for any possible improvements that could made to water conditions.
    """
    try:
        response = openai.chat.completions.create( 
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return {"Response": response.choices[0].message.content}
    except Exception as e:
        return {"Error": {str(e)}}

@app.post("/analyzeData")
def analyzeData(data: farmingData):
    return {"response": callOpenAI(data)}







