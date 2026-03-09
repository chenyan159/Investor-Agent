from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.drive_store import DriveStorage
from app.workflow import run_batch

app = FastAPI(title="Investor Agent Drive App")
store = None


def get_store() -> DriveStorage:
    global store
    if store is None:
        store = DriveStorage()
    return store

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectRequest(BaseModel):
    project_name: str


class RunRequest(BaseModel):
    project_name: str
    prompt_template: str
    items: list[str] = Field(default_factory=list)
    model_name: str = "gemini-1.5-flash"
    extract_company_ticker: bool = True


class SaveConfigRequest(BaseModel):
    project_name: str
    config_name: str
    prompt_template: str
    items: list[str] = Field(default_factory=list)
    model_name: str
    extract_company_ticker: bool


@app.get("/api/projects")
def list_projects() -> dict[str, Any]:
    return {"projects": get_store().list_projects()}


@app.post("/api/projects")
def create_or_open_project(req: ProjectRequest) -> dict[str, Any]:
    project = get_store().ensure_project(req.project_name)
    return {"project": project}


@app.get("/api/projects/{project_name}/saved-configs")
def saved_configs(project_name: str) -> dict[str, Any]:
    project = get_store().ensure_project(project_name)
    configs = get_store().read_json(project["id"], "saved_configs.json", [])
    return {"configs": configs}


@app.post("/api/save-config")
def save_config(req: SaveConfigRequest) -> dict[str, Any]:
    project = get_store().ensure_project(req.project_name)
    configs = get_store().read_json(project["id"], "saved_configs.json", [])
    payload = req.model_dump()
    configs.append(payload)
    get_store().write_json(project["id"], "saved_configs.json", configs)
    return {"ok": True, "saved_count": len(configs)}


@app.post("/api/run")
async def run_prompts(req: RunRequest) -> dict[str, Any]:
    if not req.prompt_template.strip():
        raise HTTPException(status_code=400, detail="prompt_template is required")

    project = get_store().ensure_project(req.project_name)
    results = await run_batch(
        prompt_template=req.prompt_template,
        items=req.items,
        model_name=req.model_name,
        extract_company_ticker=req.extract_company_ticker,
    )

    record = {
        "project_name": req.project_name,
        "prompt_template": req.prompt_template,
        "items": req.items,
        "model_name": req.model_name,
        "extract_company_ticker": req.extract_company_ticker,
        "results": results,
    }
    get_store().append_jsonl(project["id"], "runs.jsonl", record)

    outputs_file = get_store().read_json(project["id"], "outputs.json", [])
    outputs_file.extend(results)
    get_store().write_json(project["id"], "outputs.json", outputs_file)

    return {"results": results}


@app.get("/")
def root() -> FileResponse:
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
