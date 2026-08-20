interface Props {
  navigate: (path: string) => void
}

export function NotFoundPage({ navigate }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-96 gap-4 text-center px-4">
      <p className="text-slate-400 font-medium" style={{ fontSize: 64, lineHeight: 1 }}>404</p>
      <p className="text-slate-700 font-semibold" style={{ fontSize: 18 }}>페이지를 찾을 수 없습니다</p>
      <p className="text-slate-500" style={{ fontSize: 14 }}>주소를 확인하거나 홈으로 돌아가세요</p>
      <button
        onClick={() => navigate('/')}
        className="h-10 px-4 rounded-lg text-white text-[14px] font-medium"
        style={{ background: '#155E75', borderRadius: 8 }}
      >
        홈으로 돌아가기
      </button>
    </div>
  )
}
