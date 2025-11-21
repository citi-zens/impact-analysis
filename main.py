import asyncio
import json
from fastapi import FastAPI, Request, Depends, WebSocket, BackgroundTasks, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Repository, AnalysisReport
from service.utils.repo_utils import clone_repo, list_source_files
from service.ingest_repo import initiate_graph
from service.llm.hybridRetriever import analyze_impact
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
import os

load_dotenv()

LOCAL_PATH=os.getenv("LOCAL_REPO_PATH")

# Init DB
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Simulation Logic ---
async def simulate_pipeline(repo_id: int):
    """Simulates cloning, linting, and dependency checking."""
    steps = ["Cloning Repository...", "Embedding Codebase...", "Onboarding Complete"]
    # 1. Create a NEW session manually
    db = SessionLocal()
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    print("Simulating pipeline for repo:", LOCAL_PATH+repo.name,repo.url)
    msg = json.dumps({"repo_id": repo_id, "status": steps[0], "progress": True})
    await manager.broadcast(msg)
    # 2. Clone the repo
    clone_repo(repo.url,LOCAL_PATH+repo.name)
    msg = json.dumps({"repo_id": repo_id, "status": steps[1], "progress": False})

    #3. Embed Codebase
    initiate_graph(repo.name)
    msg = json.dumps({"repo_id": repo_id, "status": steps[2], "progress": False})
    await manager.broadcast(msg)


async def simulate_impact_analysis(repo_id: int, type_param: str,data: str):
    """Simulates calculating impact."""\
    # await manager.broadcast(json.dumps({"status": f"Analyzing {type_param}...", "repo_id": repo_id}))
    analyze_impact_result = analyze_impact(is_fr=(type_param=='FR'),data="Sample data for analysis",top_k=20)
    result = analyze_impact_result
    # result = {
    #     "files_changed": ["api/auth.py", "core/config.py"],
    #     "risk_level": "High",
    #     "affected_services": ["UserAuth", "Billing"],
    #     "status": "Report Ready"
    # }
    await manager.broadcast(json.dumps({"repo_id": repo_id, "report": result, "type":"readme"}))
    print("Impact analysis completed for repo:", repo_id,result)

# --- Routes ---

@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    repos = db.query(Repository).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "repos": repos})

@app.post("/onboard")
async def onboard_repo(background_tasks: BackgroundTasks, url: str = Form(...), db: Session = Depends(get_db)):
    # 1. Create Repo Entry
    repo_name = url.split("/")[-1].replace(".git", "")
    hasrepo=db.query(Repository).filter(Repository.name == repo_name).first()
    if hasrepo:
        return {"message": "Repo already exists", "repo_id": hasrepo.id}
    else:
        new_repo = Repository(name=repo_name, url=url, status="Onboarding")
        db.add(new_repo)
        db.commit()
        db.refresh(new_repo)
        
        # 2. Trigger Pipeline in Background
        background_tasks.add_task(simulate_pipeline, new_repo.id)
        
        return {"message": "Onboarding started", "repo_id": new_repo.id}

@app.get("/repo/{repo_id}")
def repo_detail(request: Request, repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    return templates.TemplateResponse("repo_detail.html", {"request": request, "repo": repo})

# @app.post("/analyze/{repo_id}")
# async def analyze_trigger(,repo_id: int, type_: str = Form(...)):
#     print("Triggering analysis for repo:", repo_id, type_)
#     # background_tasks.add_task(simulate_impact_analysis, repo_id, type_)
#     return {"message": "Analysis started"}



# Define the structure of the incoming JSON body
class AnalysisRequest(BaseModel):
    type: str # 'FR' or 'PR'
    fr_data: Optional[str] = None # Functional Requirements text
    pr_id: Optional[str] = None # Pull Request ID

@app.post("/analyze/{repo_id}")
async def analyze_repo(background_tasks: BackgroundTasks, repo_id: str, request: AnalysisRequest):
    # Retrieve repository details (e.g., connection details, API key) based on repo_id
    # repo = get_repo_details(repo_id) 

    if request.type == "FR":
        # 1. Functional Requirements Analysis
        if not request.fr_data:
            raise HTTPException(status_code=400, detail="Missing FR data for FR analysis.")
        
        # Call your core analysis service with the provided FR text
        # analyze_impact(repo_id, type="FR", data=request.fr_data)
        background_tasks.add_task(simulate_impact_analysis, repo_id, request.type,request.fr_data)
        # Start the WebSocket process (assuming your service handles it)
        print(f"Starting FR analysis for repo {repo_id} with data: {request.fr_data[:50]}...")
        return {"message": "FR analysis initiated."}

    elif request.type == "PR":
        # 2. Pull Request Analysis
        if not request.pr_id:
            raise HTTPException(status_code=400, detail="Missing PR ID for PR analysis.")

        # For PR, the backend is responsible for:
        # a. Calling the Git provider API (e.g., GitHub, GitLab) using repo_id and request.pr_id.
        # b. Fetching the branch name and the actual diff/files changed data.
        # c. analyze_impact(repo_id, type="PR", data=request.pr_id) # The service will fetch content

        print(f"Starting PR analysis for repo {repo_id}, PR #{request.pr_id}. Backend will fetch PR content.")
        return {"message": "PR analysis initiated."}

    else:
        raise HTTPException(status_code=400, detail="Invalid analysis type.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)