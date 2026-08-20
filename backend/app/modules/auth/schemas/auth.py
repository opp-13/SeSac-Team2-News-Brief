"""auth 요청/응답 스키마 (임시 필드명).

[PROVISIONAL] 필드명·null 규칙은 D의 `docs/api-contracts/auth.md`가 기준이다.
계약이 확정되면 이 파일의 필드명을 계약에 맞춘다(계약을 코드에 맞추지 않는다).
"""

from datetime import datetime

from pydantic import EmailStr, Field

from app.modules.auth.schemas.base import ApiModel


class SignupRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nickname: str = Field(min_length=1, max_length=50)
    # [OPEN] 지원 언어 목록 미결(B·C 협의). 검증은 설정값으로 외부화한다.
    preferred_language: str = "ko"


class LoginRequest(ApiModel):
    email: EmailStr
    password: str


class UserResponse(ApiModel):  # [PROV-A11]
    id: int
    email: EmailStr
    nickname: str
    preferred_language: str
    created_at: datetime


class LoginResponse(ApiModel):  # [PROV-A12]
    user: UserResponse
    # [PROV-A13] 세션 ID 전달 방식(쿠키 only vs 바디 동시 반환) D와 합의 필요.
    session_id: str


class PasswordChangeRequest(ApiModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)
