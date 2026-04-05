"""
react_agent.py — The core ReAct agent using LangGraph + Ollama.

This is the BRAIN of DataPilot. Here's how it works:

1. LangGraph creates a ReAct agent with our 8 tools
2. We give it a prompt: "Analyze this dataset"
3. The agent enters a loop:
   - THINK: "I should detect the problem type first"
   - ACT:   calls detect_problem tool
   - OBSERVE: reads the tool's output
   - THINK: "It's a classification problem. Now I should profile the data."
   - ACT:   calls profile_data tool
   - ...continues for all 8 tools...
   - FINAL ANSWER: summary of the entire analysis

LangGraph (replacing old LangChain AgentExecutor):
  LangChain v1.2+ moved agent orchestration to LangGraph.
  `create_react_agent` from langgraph.prebuilt creates a stateful graph
  that handles the Think → Act → Observe loop automatically.

  Key difference from old API:
  - Old: AgentExecutor + create_react_agent (from langchain.agents)
  - New: create_react_agent (from langgraph.prebuilt) — simpler, one function

Ollama's Role:
  - Runs a local LLM (Llama 3.1, Mistral, etc.) for FREE
  - No API key needed, no cloud costs
  - The LLM does the reasoning — deciding which tool to call and interpreting results

on_event Callback:
  We pass an async callback function that gets called whenever something
  interesting happens (tool starts, tool finishes, agent thinks).
  This callback pushes events to the SSE stream for real-time UI updates.
"""

import asyncio
from typing import Callable, Any

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE
from pipeline.state import PipelineState
from agent.prompts import SYSTEM_PROMPT
from tools.problem_detection import ProblemDetectionTool
from tools.data_profiling import DataProfilingTool
from tools.eda import EDATool
from tools.preprocessing import PreprocessingTool
from tools.feature_engineering import FeatureEngineeringTool
from tools.model_training import ModelTrainingTool
from tools.evaluation import EvaluationTool
from tools.explainability import ExplainabilityTool


def create_tools(state: PipelineState) -> list:
    """
    Create all 8 pipeline tools, each with access to the shared state.

    Each tool is instantiated with the same PipelineState object.
    When tool 3 (preprocessing) writes X_train to state,
    tool 4 (training) can read it — they share the same object.
    """
    return [
        ProblemDetectionTool(state=state),
        DataProfilingTool(state=state),
        EDATool(state=state),
        PreprocessingTool(state=state),
        FeatureEngineeringTool(state=state),
        ModelTrainingTool(state=state),
        EvaluationTool(state=state),
        ExplainabilityTool(state=state),
    ]


async def run_pipeline(state: PipelineState, on_event: Callable) -> PipelineState:
    """
    Run the full ML pipeline using the LangGraph ReAct agent.

    Args:
        state: PipelineState with raw_df already loaded
        on_event: async callback for streaming events to the UI

    Returns:
        Updated PipelineState with all results

    This function:
    1. Creates the Ollama LLM (free, local)
    2. Creates all 8 tools
    3. Builds a ReAct agent graph using LangGraph
    4. Runs the agent — it will call tools in order, reasoning at each step
    5. Streams events via callback for real-time UI updates
    """
    state.status = "running"
    await on_event({"type": "pipeline_start", "message": "Starting ML pipeline..."})

    try:
        # --- Step 1: Create the LLM ---
        # ChatOllama connects to your local Ollama server
        # No API key needed — Ollama is free!
        llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=LLM_TEMPERATURE,
        )

        # --- Step 2: Create tools ---
        tools = create_tools(state)

        # --- Step 3: Build the ReAct agent using LangGraph ---
        # create_react_agent from langgraph.prebuilt:
        #   - Takes an LLM and a list of tools
        #   - Returns a compiled graph that runs the ReAct loop
        #   - The graph handles: Think → Tool Call → Observe → Think → ...
        #   - Much simpler than the old AgentExecutor approach
        agent = create_react_agent(
            model=llm,
            tools=tools,
        )

        # --- Step 4: Prepare the input ---
        columns = list(state.raw_df.columns) if state.raw_df is not None else []
        shape = list(state.raw_df.shape) if state.raw_df is not None else [0, 0]

        # The input tells the agent what to do
        agent_input = (
            f"Analyze this dataset. It has {shape[0]} rows and {shape[1]} columns. "
            f"Columns: {columns}. "
            f"{'Target column: ' + state.target_column if state.target_column else 'Detect the target column automatically.'} "
            f"{'Task type: ' + state.task_type if state.task_type else 'Detect the task type automatically.'} "
            f"Run all 8 pipeline steps in order."
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=agent_input),
        ]

        # --- Step 5: Run the agent and stream events ---
        # agent.astream_events gives us a stream of every event:
        #   - tool calls, tool results, LLM tokens, etc.
        # We filter for the events we care about and push them to the UI.

        async for event in agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                await on_event({
                    "type": "tool_start",
                    "tool": tool_name,
                    "input": str(event.get("data", {}).get("input", ""))[:200],
                })

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = str(event.get("data", {}).get("output", ""))[:500]
                await on_event({
                    "type": "tool_end",
                    "tool": tool_name,
                    "output_preview": output,
                })

            elif kind == "on_chat_model_stream":
                # LLM is generating tokens — agent is "thinking"
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await on_event({
                        "type": "agent_thinking",
                        "content": str(chunk.content)[:200],
                    })

        # --- Step 6: Mark as complete ---
        state.status = "completed"
        await on_event({
            "type": "pipeline_complete",
            "summary": "Pipeline completed successfully. All 8 steps finished.",
        })

    except Exception as e:
        state.status = "error"
        await on_event({
            "type": "pipeline_error",
            "message": str(e),
        })
        raise

    return state
