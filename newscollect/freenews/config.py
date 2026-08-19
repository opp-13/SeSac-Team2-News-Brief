"""API credential configuration for Free News API (api.freenewsapi.io)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class FreeNewsConfig:
    api_key: str
    base_url: str = "https://api.freenewsapi.io/v1"

    @classmethod
    def from_env(cls) -> "FreeNewsConfig":
        load_dotenv()

        api_key = os.environ.get("FREENEWS_API_KEY")

        if not api_key:
            raise ValueError("FREENEWS_API_KEY 환경변수를 설정해야 합니다.")

        return cls(api_key=api_key)
