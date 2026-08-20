"""배포 검증용 메타 정보 (공용 영역).

프런트 헤더의 `API {버전}` 표시와 하단 고정 정보줄이 이 응답을 쓴다
(`frontend/src/api/meta.ts`, `docs/api-contracts/meta.md`). CI/CD로 배포한 뒤
**어느 서버 인스턴스가 응답했는지**, **리버스 프록시가 클라이언트 IP를 제대로
넘기는지(XFF)** 를 화면에서 바로 확인하려는 용도다.

[소유권 미정] CLAUDE.md §3 표에 없는 엔드포인트다. 인프라 성격이라 공용에 두었으나
담당자는 팀에서 정해야 한다.

인증을 걸지 않았다 — 배포 직후 로그인 없이 확인하는 것이 목적이다. 대신 호스트명·사설
IP 외에 내부 정보를 노출하지 않는다.
"""

import socket

from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter(tags=["meta"])


def _server_ip() -> str:
    """컨테이너/사설망에서의 자기 IP. 외부로 패킷을 보내지 않고 라우팅 테이블만 조회한다."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # connect()만 호출하면 UDP는 실제 통신이 일어나지 않는다.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "unknown"
    finally:
        sock.close()


@router.get("/meta/deploy-info")
def deploy_info(request: Request) -> dict:
    settings = get_settings()
    return {
        "apiVersion": settings.api_version,
        "serverIp": _server_ip(),
        "serverName": socket.gethostname(),
        # 프록시 뒤에 있으면 request.client.host는 프록시 IP가 된다. 실제 클라이언트는
        # XFF의 첫 번째 값이므로 둘 다 그대로 내려보내고 판단은 화면에서 한다.
        "clientIp": request.client.host if request.client else "unknown",
        "xForwardedFor": request.headers.get("x-forwarded-for"),
    }
