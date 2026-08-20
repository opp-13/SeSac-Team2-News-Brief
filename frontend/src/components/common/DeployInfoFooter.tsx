import { useDeployInfo } from '../../hooks/useDeployInfo'
import { colors, typeScale } from '../../constants/theme'

const barStyle = {
  borderTop: `1px solid ${colors.border}`,
  background: colors.surface,
  color: colors.muted,
  fontSize: typeScale.micro.fontSize,
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  padding: '6px 8px',
}

// CI/CD 배포 검증용 — 어느 서버 인스턴스가 응답했는지, 리버스 프록시가 클라이언트 IP를
// 제대로 넘기는지(XFF) 확인하기 위한 하단 정보줄. app/App.tsx가 이 컴포넌트를 fixed
// 래퍼로 감싸 화면 하단에 고정하고, 실제 렌더 높이만큼 본문에 여백을 준다 — 그래서
// 여기서는 배경(투명하면 스크롤 중인 콘텐츠가 비쳐 보임)만 신경 쓰면 된다.
// docs/api-contracts/meta.md(DRAFT, 백엔드 미구현) 값이라 지금은 MSW 목업 응답을 보여준다.
export default function DeployInfoFooter() {
  const { data, isLoading, isError } = useDeployInfo()

  if (isLoading) {
    return (
      <footer className="text-center animate-pulse" style={barStyle}>
        배포 정보 확인 중…
      </footer>
    )
  }

  if (isError || !data) {
    return (
      <footer className="text-center" style={barStyle}>
        배포 정보를 불러오지 못했습니다
      </footer>
    )
  }

  return (
    <footer
      className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-center"
      style={barStyle}
    >
      <span>서버 IP {data.serverIp}</span>
      <span>서버명 {data.serverName}</span>
      <span>클라이언트 IP {data.clientIp}</span>
      <span>XFF {data.xForwardedFor ?? '없음'}</span>
    </footer>
  )
}
