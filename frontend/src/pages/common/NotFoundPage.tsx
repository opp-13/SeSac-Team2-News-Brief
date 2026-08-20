import { useNavigate } from 'react-router-dom'
import { colors, typeScale, radius } from '../../constants/theme'

// docs/figma-export/pages/NotFoundPage.tsx 이식. navigate prop → useNavigate(),
// #155E75 → colors.accent, borderRadius 8 → radius.control. fontSize 18은
// typeScale.h2와 정확히 일치해 교체. 나머지(64/14)는 7개 역할 어디에도 안 맞아 그대로 둠.
export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center h-96 gap-4 text-center px-4">
      <p className="text-slate-400 font-medium" style={{ fontSize: 64, lineHeight: 1 }}>
        404
      </p>
      <p className="text-slate-700 font-semibold" style={{ fontSize: typeScale.h2.fontSize }}>
        페이지를 찾을 수 없습니다
      </p>
      <p className="text-slate-500" style={{ fontSize: 14 }}>
        주소를 확인하거나 홈으로 돌아가세요
      </p>
      <button
        onClick={() => navigate('/')}
        className="h-10 px-4 rounded-lg text-white text-[14px] font-medium"
        style={{ background: colors.accent, borderRadius: radius.control }}
      >
        홈으로 돌아가기
      </button>
    </div>
  )
}
