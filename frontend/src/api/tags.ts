import { apiFetch } from './client'

// 백엔드 GET /api/v1/tags 응답 (backend/app/modules/feed/schemas/tag.py TagResponse).
export interface Tag {
  id: number
  name: string
  /** tags.tag_type — 'CATEGORY' | 'KEYWORD'. 게스트 필터 칩은 CATEGORY만 쓴다. */
  tagType: string
}

export const TAG_TYPE_CATEGORY = 'CATEGORY'

/** 게스트 필터 칩에 쓸 카테고리 이름 목록. */
export function categoryNames(tags: Tag[]): string[] {
  return tags.filter((tag) => tag.tagType === TAG_TYPE_CATEGORY).map((tag) => tag.name)
}

/** 선택 가능한 전체 태그. 설정 화면·회원가입 온보딩·게스트 카테고리 칩이 공유한다. */
export function fetchTags(): Promise<Tag[]> {
  return apiFetch<Tag[]>('/tags')
}

/**
 * 태그 **이름** 목록을 id 목록으로 바꾼다.
 *
 * 프런트는 태그를 이름으로 다루는데(필터 칩, userTags, 설정 화면) 백엔드
 * `PUT /me/tags`는 `{tagIds:[...]}`를 받는다. 그 간극을 이 레이어에서 메운다 —
 * 컴포넌트가 id를 알아야 할 이유가 없다.
 *
 * 서버에 없는 이름은 조용히 버린다. 저장 자체를 실패시키면 태그 목록이 갱신된 뒤
 * 예전 이름을 들고 있던 사용자가 아무것도 저장할 수 없게 된다.
 */
export function toTagIds(names: string[], tags: Tag[]): number[] {
  const byName = new Map(tags.map((tag) => [tag.name, tag.id]))
  return names.map((name) => byName.get(name)).filter((id): id is number => id !== undefined)
}
