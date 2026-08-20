import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useEffect } from 'react'
import { MemoryRouter, Routes, Route, Outlet, useNavigate } from 'react-router-dom'

// AppRoutes.tsx의 실제 구조("/"와 "/articles/:id"가 같은 부모(Layout) 아래 형제 Route로
// 같은 컴포넌트를 가리킴)를 그대로 재현해, react-router가 이 둘 사이를 이동할 때
// 컴포넌트 인스턴스를 리마운트 없이 유지하는지 직접 검증한다 — 이론이 아니라 실측.
let mountCount = 0
let unmountCount = 0

function Layout() {
  return (
    <div>
      <Outlet />
    </div>
  )
}

function Probe() {
  const navigate = useNavigate()
  useEffect(() => {
    mountCount += 1
    return () => {
      unmountCount += 1
    }
  }, [])
  return (
    <div>
      <button onClick={() => navigate('/articles/1')}>open</button>
      <button onClick={() => navigate('/')}>close</button>
    </div>
  )
}

function TestRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Probe />} />
        <Route path="/articles/:id" element={<Probe />} />
      </Route>
    </Routes>
  )
}

describe('"/"와 "/articles/:id" 형제 Route가 같은 컴포넌트를 가리킬 때', () => {
  beforeEach(() => {
    mountCount = 0
    unmountCount = 0
  })

  it('둘 사이를 이동해도 컴포넌트 인스턴스가 리마운트되지 않는다', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <TestRoutes />
      </MemoryRouter>,
    )
    expect(mountCount).toBe(1)
    expect(unmountCount).toBe(0)

    fireEvent.click(screen.getByText('open'))
    expect(mountCount).toBe(1)
    expect(unmountCount).toBe(0)

    fireEvent.click(screen.getByText('close'))
    expect(mountCount).toBe(1)
    expect(unmountCount).toBe(0)
  })
})
