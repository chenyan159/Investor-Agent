import asyncio
import os
import re
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class WorkflowState(TypedDict, total=False):
    prompt_template: str
    item: str
    final_prompt: str
    output: str
    extracted_companies: list[str]
    extracted_tickers: list[str]


def build_model(model_name: str):
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, temperature=0)

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=model_name, temperature=0)


def extract_entities(text: str) -> tuple[list[str], list[str]]:
    tickers = sorted(set(re.findall(r"\b[A-Z]{1,5}\b", text)))
    companies = sorted(set(re.findall(r"\b[A-Z][A-Za-z&,.\- ]{2,40}(?:Inc|Corp|Corporation|Ltd|Limited|Group|Holdings)\b", text)))
    return companies[:50], tickers[:100]


def create_graph(model_name: str, extract_company_ticker: bool):
    model = build_model(model_name)

    def format_prompt(state: WorkflowState) -> WorkflowState:
        item = state.get("item", "")
        prompt = state["prompt_template"].replace("{{item}}", item)
        return {"final_prompt": prompt}

    def run_model(state: WorkflowState) -> WorkflowState:
        msg = model.invoke(state["final_prompt"])
        output = getattr(msg, "content", str(msg))
        return {"output": output}

    def maybe_extract(state: WorkflowState) -> WorkflowState:
        if not extract_company_ticker:
            return {"extracted_companies": [], "extracted_tickers": []}
        companies, tickers = extract_entities(state.get("output", ""))
        return {"extracted_companies": companies, "extracted_tickers": tickers}

    graph = StateGraph(WorkflowState)
    graph.add_node("format_prompt", format_prompt)
    graph.add_node("run_model", run_model)
    graph.add_node("extract", maybe_extract)
    graph.set_entry_point("format_prompt")
    graph.add_edge("format_prompt", "run_model")
    graph.add_edge("run_model", "extract")
    graph.add_edge("extract", END)
    return graph.compile()


async def run_batch(
    prompt_template: str,
    items: list[str],
    model_name: str,
    extract_company_ticker: bool,
) -> list[dict[str, Any]]:
    graph = create_graph(model_name, extract_company_ticker)
    run_items = items if items else [""]

    async def run_one(item: str):
        res = await graph.ainvoke({"prompt_template": prompt_template, "item": item})
        return {
            "item": item,
            "final_prompt": res.get("final_prompt", ""),
            "output": res.get("output", ""),
            "extracted_companies": res.get("extracted_companies", []),
            "extracted_tickers": res.get("extracted_tickers", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    return await asyncio.gather(*(run_one(i) for i in run_items))
