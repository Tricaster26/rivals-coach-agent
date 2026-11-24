from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from coach.output.run_log import RunLog

JSON_RESPONSE_FORMAT = {"type": "json_object"}


def json_mode(llm: BaseChatModel) -> Runnable:
    return llm.bind(response_format=JSON_RESPONSE_FORMAT)


def ask(llm: BaseChatModel | Runnable, run_log: RunLog, step_name: str, system_prompt: str, user_message: str) -> str:
    print(f"  {step_name}...", flush=True)
    messages = [SystemMessage(system_prompt), HumanMessage(user_message)]
    response: AIMessage = llm.invoke(messages)
    run_log.save_llm_step(step_name, system_prompt, user_message, response)
    return str(response.content).strip()
