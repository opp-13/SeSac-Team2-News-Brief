"""auth 모듈 API 경로 상수 (임시값).

[PROVISIONAL] 이 파일의 모든 값은 D의 `docs/api-contracts/auth.md`가 확정되기 전까지 쓰는
임시 이름이다. 확정 후에는 **이 파일만 고치면** 라우터/테스트가 모두 따라간다.
경로 문자열을 라우터에 직접 쓰지 말 것.
"""

API_PREFIX = "/api/v1"  # [PROV-A00]

AUTH_PREFIX = f"{API_PREFIX}/auth"

SIGNUP = "/signup"          # [PROV-A01] POST
LOGIN = "/login"            # [PROV-A02] POST
LOGOUT = "/logout"          # [PROV-A03] POST
ME = "/me"                  # [PROV-A04] GET
ME_PASSWORD = "/me/password"  # [PROV-A05] PATCH

SESSION_COOKIE_NAME = "nb_session"  # [PROV-A06] D와 쿠키명/전송방식 합의 필요
