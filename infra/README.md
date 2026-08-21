# infra

Terraform으로 관리하는 AWS 인프라. `network`(VPC/서브넷/보안그룹) → `compute`(EC2/ALB/NLB/Route53) →
`deploy`(GitHub Actions OIDC + CodeDeploy) 순서로 의존하는 3개 모듈을, 환경별 루트 모듈
(`env/<name>/`)이 조합해서 씁니다.

## 디렉토리 구조

```
infra/
├── init/bootstrap/     # Terraform state용 S3 버킷 생성 (1회성, 팀에 하나만 있으면 됨)
├── modules/
│   ├── network/        # VPC, 서브넷, 보안그룹, team2.local 관련 없음(그건 compute 쪽)
│   ├── compute/        # EC2(frontend/backend/db/redis/bastion), ALB, 내부 NLB,
│   │                   # CodeDeploy agent용 인스턴스 롤, team2.local Route53 private zone
│   └── deploy/         # GitHub OIDC provider/role, S3 아티팩트 버킷, CodeDeploy app/배포그룹
└── env/
    └── dev/            # 현재 유일한 환경. 위 세 모듈을 조합
```

## 기본 사용법 (기존 `env/dev` 적용)

```bash
cd infra/env/dev
terraform init
terraform plan
terraform apply
```

자격증명은 Terraform이 별도로 선택해주지 않습니다 — **현재 활성화된 AWS CLI 자격증명(`aws configure`,
`AWS_PROFILE`, 환경변수 등)을 그대로 씁니다.** `variables.tf`에 `aws_profile`/`oidc_role_arn`/
`web_identity_token_file` 변수가 선언은 되어 있지만 `main.tf`의 `provider "aws"` 블록에 아직
연결되어 있지 않습니다 — 나중에 Terraform 자체를 CI에서 돌릴 때 쓰려고 미리 선언만 해둔 것이고,
지금 채워도 아무 효과가 없습니다.

`terraform.tfvars`는 실제 값이 든 파일이라 커밋되어 있지만(팀 전체가 같은 계정을 공유하는 동안은
이렇게 운영), 계정/값이 바뀌면 아래 "다른 환경 만들기"를 참고하세요.

## 다른 환경(다른 사람 계정 등)으로 배포하기

`env/dev`는 이름 그대로 하나의 환경입니다. 새 환경(다른 팀원, 다른 AWS 계정, 또는 같은 계정 안의
별도 zone)을 추가하려면:

### 1. 새 env 디렉토리 만들기

```bash
cp -r infra/env/dev infra/env/<name>   # 예: infra/env/alice
```

### 2. `version.tf`의 backend key 바꾸기

모든 환경이 **같은 S3 버킷**(`terraform-s3-sesac-team2`)을 쓰되, state 파일 경로(`key`)만
환경별로 분리합니다. `infra/env/<name>/version.tf`:

```hcl
backend "s3" {
  bucket       = "terraform-s3-sesac-team2"
  key          = "env/<name>/terraform.tfstate"   # <- 이 줄만 바꾸면 됨
  region       = "ap-northeast-2"
  encrypt      = true
  use_lockfile = true
}
```

버킷 자체가 없는 완전히 새 계정이면 `infra/init/bootstrap`을 먼저 그 계정에서 한 번 적용해서
버킷부터 만드세요 (`infra/init/bootstrap/README.md` 참고).

### 3. `terraform.tfvars` 값 채우기

- **같은 AWS 계정 안에서 구분만 하는 경우**: `zone`을 다른 값으로 바꾸세요 (예: `"alice"`).
  이 값이 `name_prefix`로 모든 리소스 이름(S3 버킷, IAM 롤, EC2 Name 태그 등)에 들어가서,
  같은 값을 쓰면 리소스 이름이 충돌합니다.
- **완전히 다른 AWS 계정인 경우**: `zone`은 같아도 되고(계정 경계 자체가 격리 역할을 함),
  `bastion_ssh_cidr`/`key_pair_name`/`vpc_cidr`/`acm_certificate_domain` 등 계정별로
  실제 존재하는 값으로 교체하세요.

### 4. apply

그 계정에 대한 AWS 자격증명을 활성화한 상태로:

```bash
cd infra/env/<name>
terraform init
terraform apply
```

### 5. GitHub OIDC provider 중복 주의

`module.deploy`가 만드는 `aws_iam_openid_connect_provider`(`token.actions.githubusercontent.com`)는
**계정당 하나만 존재할 수 있습니다.** 그 계정에 GitHub Actions용 OIDC provider가 이미 있으면
(다른 프로젝트에서 만들어뒀거나 등) `terraform apply`가 `EntityAlreadyExists`로 실패합니다.
먼저 확인하세요:

```bash
aws iam list-open-id-connect-providers
```

이미 있으면, apply 전에 기존 것을 state로 import:

```bash
terraform import 'module.deploy[0].aws_iam_openid_connect_provider.github' \
  arn:aws:iam::<계정ID>:oidc-provider/token.actions.githubusercontent.com
```

### 6. GitHub 쪽 설정

`.github/workflows/deploy.yml`은 `matrix.environment`로 GitHub Environment별 시크릿/변수를
읽습니다. 새 환경 추가 시:

1. repo Settings → Environments → 새 environment 생성 (env 이름, 위에서 정한 `<name>`과
   맞출 필요는 없지만 맞춰두면 헷갈리지 않음)
2. 그 environment에 Variables `DEPLOY_ROLE_ARN`, `CODEDEPLOY_ARTIFACTS_BUCKET` (`terraform
   output`으로 뽑은 값), Secrets `DATABASE_URL`, `REDIS_URL` 등록
3. `deploy.yml`의 `matrix: environment: [john]` 목록에 그 environment 이름 한 줄 추가
   (job 자체는 복붙 안 해도 됨 — matrix가 같은 job을 환경마다 반복 실행함)

## 선택적 기능 플래그 (`terraform.tfvars`)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `create_bastion` | `false` | 퍼블릭 서브넷에 SSH bastion 생성 |
| `create_deploy` | `true` | CodeDeploy 파이프라인(OIDC/S3/앱) + compute 쪽 에이전트 인스턴스 롤 생성 |
| `enable_private_dns` | `false` | `team2.local` private hosted zone (`db`/`redis`/`api` 레코드) 생성 |
| `enable_https` | `false` | 퍼블릭 ALB에 HTTPS 리스너 추가 (기존 발급된 ACM 인증서 필요) |

## 알려진 제약 / 미해결

- `aws_profile`/`oidc_role_arn`/`web_identity_token_file` 변수는 선언만 되어 있고 미배선 (위 참고)
- `docs/db/schema.sql`(DB 스키마)과 `infra/modules/compute/scripts/install_mysql.sh`가 매번
  최신 스키마를 git clone해서 받아 쓰도록 되어 있음 — DB 계정(`frodo`) 생성/GRANT는
  `install_mysql.sh`가 스키마와 별개로 담당
