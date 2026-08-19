import { Link, useLocation } from 'react-router-dom'
import { colors, typeScale } from '../../constants/theme'

const TABS = [
  { path: '/admin/pipeline', label: '배치 실행 이력' },
  { path: '/admin/llm-usage', label: 'LLM 비용·사용량' },
  { path: '/admin/retention', label: '데이터 보관 정책' },
]

// design_plan.md/§5 NavRail 스펙은 "관리" 아이콘 하나만 명시하고, 관리자 화면 3개
// 사이의 이동 수단은 원본 프로토타입에도 없었다(사용자 확인 후 섹션 내 탭으로 결정).
// 활성 상태 강조색은 NavRail의 활성 아이템과 같은 accent를 그대로 재사용한다 — 새
// 색상 규칙을 만들지 않고 기존 "활성 = accent" 관례를 그대로 적용.
export default function AdminTabs() {
  const { pathname } = useLocation()

  return (
    <div className="border-b border-slate-200 bg-white">
      <div className="flex gap-1 px-4" style={{ paddingLeft: 80 }}>
        {TABS.map((tab) => {
          const isActive = pathname === tab.path
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className="px-3 py-3 transition-colors"
              style={{
                fontSize: typeScale.caption.fontSize,
                fontWeight: 500,
                color: isActive ? colors.accent : colors.muted,
                borderBottom: `2px solid ${isActive ? colors.accent : 'transparent'}`,
              }}
            >
              {tab.label}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
