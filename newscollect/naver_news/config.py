"""API credential configuration for NAVER API HUB."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class NaverAPIConfig:
    client_id: str
    client_secret: str
    base_url: str = "https://naverapihub.apigw.ntruss.com"

    @classmethod
    def from_env(cls) -> "NaverAPIConfig":
        load_dotenv()

        client_id = os.environ.get("NCP_CLIENT_ID")
        client_secret = os.environ.get("NCP_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("NCP_CLIENT_ID / NCP_CLIENT_SECRET 환경변수를 설정해야 합니다.")

        return cls(client_id=client_id, client_secret=client_secret)
