# Meta API 계약

> **상태: DRAFT — 담당 미정.** 이 엔드포인트는 collector/ai/feed/auth 같은 특정 도메인
> 모듈에 속하지 않는 배포 검증용 엔드포인트다. `backend/app/main.py` 또는 `core/`
> (루트 CLAUDE.md §3 공용 영역)에 구현하는 걸 제안하며, 실제 구현 담당과 착수 시점은
> 팀 합의가 필요하다. CI/CD 자동 배포 후 "지금 떠 있는 게 어느 버전·어느 인스턴스인지"
> 확인하려는 목적으로 프론트(D)가 요청해 작성한 초안이다.

공통 규약(루트 CLAUDE.md §6)을 따른다: `BASE = /api/v1`, 응답은
`{ success: true, data }` | `{ success: false, error }`.

---

## GET /meta/deploy-info

### 인증

세션 여부와 무관하게 응답한다(로그인 불필요) — 배포 검증용이라 로그인 장벽이 있으면 안 된다.

### 응답 200

```json
{
  "success": true,
  "data": {
    "apiVersion": "1.4.2",
    "serverIp": "10.0.3.21",
    "serverName": "ip-10-0-3-21",
    "clientIp": "203.0.113.7",
    "xForwardedFor": "203.0.113.7, 10.0.1.5"
  }
}
```

### 필드 설명 · 구현 힌트

| 필드 | 설명 | 구현 힌트 |
|---|---|---|
| `apiVersion` | 배포된 API 빌드 버전 | CI가 빌드 시 환경변수로 주입(git 태그/SHA)하거나 `__version__` 값을 읽어 응답 |
| `serverIp` | 이 요청을 처리한 인스턴스의 내부 IP | 컨테이너/인스턴스 환경변수(`HOSTNAME`, k8s `POD_IP`) 또는 `socket.gethostbyname(socket.gethostname())` |
| `serverName` | 인스턴스 hostname | 위와 동일 계열 |
| `clientIp` | FastAPI `request.client.host` | nginx 리버스 프록시(루트 CLAUDE.md §2) 뒤에 있으면 이 값은 프록시 IP가 된다. 실제 클라이언트 IP는 `xForwardedFor`의 첫 번째 값을 신뢰해야 한다(단, nginx가 XFF를 올바르게 설정해준다는 전제) |
| `xForwardedFor` | 요청 헤더 `X-Forwarded-For` 원본값 | 값이 없으면 `null` |

### ⚠️ 보안 참고 — 팀 확인 필요

내부 서버 IP·hostname을 응답에 그대로 담는다. 프론트는 "모든 사용자에게 항상 표시"로
요청받아 반영했지만, 이 값을 인증 없이 아무나 조회 가능한 API로 공개해도 되는지는
별도 결정이 필요하다. 필요하면 프로덕션에서는 이 엔드포인트를 막거나 관리자 인증을
요구하는 방안도 검토한다.

### 에러 응답

서버 자체 조회 실패 시:

```json
{ "success": false, "error": { "code": "DEPLOY_INFO_UNAVAILABLE", "message": "..." } }
```
