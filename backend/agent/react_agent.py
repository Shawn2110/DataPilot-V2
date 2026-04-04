"""
react_agent.py — The core ReAct agent using LangChain + Ollama.

This is the BRAIN of DataPilot. Here's how it works:

1. LangChain creates a ReAct agent with our 8 tools
2. We give it a prompt: "Analyze this dataset"
3. The agent enters a loop:
   - THINK: "I should detect the problem type first"
   - ACT:   calls detect_problem tool
   - OBSERVE: reads the tool's output
   - THINK: "It's a classification problem with target 'Survived'. Now I should profile the data."
   - ACT:   calls profile_data tool
   - ...continues for all 8 tools...
   - FINAL ANSWER: summary of the entire analysis

ReAct Pattern (Reason + Act):
  The key insight is that the LLM REASONS before each action.
  It doesn't blindly call tools in order — it reads results and adapts.
  For example, if profiling reveals 80% missing values in a column,
  the agent might note this and adjust its preprocessing approach.

LangChain's Role:
  - Manages the tool-calling loop
  - Parses the LLM's output to extract tool calls
  - Executes tools and feeds results back to the LLM
  - Handles the ReAct format (Thought/Action/Observation)

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
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler

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


class StreamingCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that captures agent events for SSE streaming.

    LangChain fires callbacks at key moments:
      - on_tool_start: agent is about to call a tool
      - on_tool_end: tool finished executing
      - on_llm_start: LLM is generating a response
      - on_agent_action: agent decided on an action

    We capture these and push them to the event queue,
    which gets streamed to the VS Code extension via SSE.
    """

    def __init__(self, event_callback: Callable):
        super().__init__()
        self.event_callback = event_callback
        self._loop = None

    def _get_loop(self):
        """Get or create event loop for async callback."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    def _emit(self, event: dict):
        """Emit an event through the callback."""
        loop = self._get_loop()
        if loop and loop.is_running():
            asyncio.ensure_future(self.event_callback(event))
        else:
            # If no async loop, create one for this call
            try:
                asyncio.run(self.event_callback(event))
            except RuntimeError:
                pass  # Already in an async context

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """Called when a tool is about to be executed."""
        tool_name = serialized.get("name", "unknown")
        self._emit({
            "type": "tool_start",
            "tool": tool_name,
            "input": input_str[:200],  # Truncate long inputs
        })

    def on_tool_end(self, output: str, **kwargs):
        """Called when a tool finishes execution."""
        self._emit({
            "type": "tool_end",
            "output_preview": output[:500],  # First 500 chars of output
        })

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        """Called when the LLM starts generating."""
        self._emit({"type": "agent_thinking"})

    def on_agent_action(self, action, **kwargs):
        """Called when the agent decides on an action."""
        self._emit({
            "type": "agent_action",
            "tool": action.tool,
            "thought": action.log[:300] if hasattr(action, 'log') else "",
        })

    def on_agent_finish(self, finish, **kwargs):
        """Called when the agent produces its final answer."""
        self._emit({
            "type": "agent_finish",
            "output": finish.return_values.get("output", "")[:1000],
        })


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


# LangChain ReAct prompt template
# This wraps our system prompt with LangChain's required format
# {tools} and {tool_names} are injected by LangChain
# {agent_scratchpad} is where LangChain puts the Thought/Action/Observation history
REACT_PROMPT = PromptTemplate.from_template(
    """{system_prompt}

You have access to the following tools:

{tools}

Use the following format:

Thought: your reasoning about what to do next
Action: the tool name to use (one of [{tool_names}])
Action Input: the input to the tool (use empty string "" if no input needed)
Observation: the result of the tool call
... (this Thought/Action/Action Input/Observation can repeat)
Thought: I have completed all analysis steps
Final Answer: your comprehensive summary of the entire analysis

Begin! Analyze the dataset step by step.

{agent_scratchpad}"""
)


async def run_pipeline(state: PipelineState, on_event: Callable) -> PipelineState:
    """
    Run the full ML pipeline using the LangChain ReAct agent.

    Args:
        state: PipelineState with raw_df already loaded
        on_event: async callback for streaming events to the UI

    Returns:
        Updated PipelineState with all results

    This function:
    1. Creates the Ollama LLM (free, local)
    2. Creates all 8 tools
    3. Builds a ReAct agent
    4. Runs the agent — it will call tools in order, reasoning at each step
    5. Returns the updated state with all results
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

        # --- Step 3: Build the ReAct agent ---
        # create_react_agent: creates an agent that follows the ReAct pattern
        # It wraps the LLM with tool-calling logic
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=REACT_PROMPT.partial(system_prompt=SYSTEM_PROMPT),
        )

        # AgentExecutor runs the agent loop:
        #   Think → Act → Observe → Think → Act → ...
        # max_iterations prevents infinite loops
        # handle_parsing_errors retries if the LLM gives malformed output
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,  # Print Thought/Action/Observation to console (debugging)
            max_iterations=20,
            handle_parsing_errors=True,
            callbacks=[StreamingCallbackHandler(on_event)],
        )

        # --- Step 4: Run the agent ---
        columns = list(state.raw_df.columns) if state.raw_df is not None else []
        shape = list(state.raw_df.shape) if state.raw_df is not None else [0, 0]

        # This input tells the agent what dataset to analyze
        agent_input = (
            f"Analyze this dataset. It has {shape[0]} rows and {shape[1]} columns. "
            f"Columns: {columns}. "
            f"{'Target column: ' + state.target_column if state.target_column else 'Detect the target column automatically.'} "
            f"{'Task type: ' + state.task_type if state.task_type else 'Detect the task type automatically.'} "
            f"Run all 8 pipeline steps in order."
        )

        result = await asyncio.to_thread(
            executor.invoke,
            {"input": agent_input},
        )

        # --- Step 5: Mark as complete ---
        state.status = "completed"
        await on_event({
            "type": "pipeline_complete",
            "summary": result.get("output", "Pipeline completed successfully."),
        })

    except Exception as e:
        state.status = "error"
        await on_event({
            "type": "pipeline_error",
            "message": str(e),
        })
        raise

    return state
