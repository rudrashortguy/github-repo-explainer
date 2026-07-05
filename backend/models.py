import re

from pydantic import BaseModel, field_validator


class ExplainRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def valid_github_url(cls, v: str) -> str:
        if not re.match(r"^https?://(www\.)?github\.com/[\w.-]+/[\w.-]+/?$", v):
            raise ValueError("Must be a valid https://github.com/owner/repo URL")
        return v.rstrip("/")


class RepoReport(BaseModel):
    architecture_mermaid: str
    folder_explanations: dict[str, str]
    api_endpoints_guessed: list[str]
    readme_summary: str
    contribution_guide: str
    tech_stack_badges: list[str]
