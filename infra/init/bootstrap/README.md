# bootstrap

Terraform state를 저장할 S3 버킷을 만드는 1회성 구성입니다. `init/network`를 포함한 다른 모든 모듈이 이 버킷을 backend로 사용하기 때문에, 그 모듈들보다 먼저 실행되어야 합니다.

## 특징

- 이 구성 자체는 **backend를 사용하지 않습니다** (로컬 state). 버킷이 생기기 전에는 원격 backend를 쓸 수 없는 최초 부트스트랩이기 때문입니다.
- 팀에서 한 번만(또는 버킷 설정을 바꿀 때만) 수동으로 실행하는 것을 전제로 합니다.
- 실행 후 생성되는 로컬 `terraform.tfstate`는 `.gitignore`에 의해 git에는 올라가지 않지만, 실행한 사람이 직접 안전하게 보관해야 합니다 (분실 시 버킷 관리가 어려워짐, 단 버킷 자체는 그대로 유지됨).

## 사용법

```bash
cd init/bootstrap
terraform init
terraform apply -var="bucket_name=<team-tfstate-bucket-name>"
```

생성된 버킷 이름을 `init/network/main.tf`의 `backend "s3" { bucket = "..." }`에 채워 넣은 뒤 `init/network`에서 `terraform init`을 실행하세요.

## 자동 생성 문서

아래는 pre-commit의 `terraform-docs` 훅이 커밋마다 자동으로 갱신합니다 (Requirements/Providers/Resources/Inputs/Outputs). 이 마커 밖의 내용은 손대지 않습니다.

<!-- BEGIN_TF_DOCS -->
<!-- END_TF_DOCS -->
