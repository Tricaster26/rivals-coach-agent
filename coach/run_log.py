import json
from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage


class RunLog:
    def __init__(self, runs_dir: Path, match_id: str):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.folder = runs_dir / f"{timestamp}-{match_id}"
        self.usage_rows: list[dict] = []

    def save_json(self, file_name: str, data: object) -> None:
        text = json.dumps(data, indent=2, ensure_ascii=False)
        self.save_text(file_name, text)

    def save_text(self, file_name: str, text: str) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / file_name).write_text(text, encoding="utf-8")

    def save_llm_step(self, step_name: str, system_prompt: str, user_message: str, response: AIMessage) -> None:
        self.save_text(f"{step_name}.prompt.md", f"# System\n\n{system_prompt}\n\n# User\n\n{user_message}\n")
        self.save_text(f"{step_name}.output.md", str(response.content))

        reasoning = response.additional_kwargs.get("reasoning_content")
        if reasoning:
            self.save_text(f"{step_name}.reasoning.md", reasoning)

        usage = response.usage_metadata or {}
        self.usage_rows.append(
            {
                "step": step_name,
                "inputTokens": usage.get("input_tokens"),
                "outputTokens": usage.get("output_tokens"),
                "totalTokens": usage.get("total_tokens"),
            }
        )
        self.save_json("usage.json", self.usage_rows)
