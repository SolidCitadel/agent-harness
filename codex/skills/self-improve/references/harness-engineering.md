# Codex self-harness 지도

자기수정 loop는 `self-improve`가 진단·개입·승인을 맡고, 메타 문서 규율이 집필을 제한하며, read-only `meta_doc_critic`이 작성자와 분리돼 결함을 찾는 구조다.

| 구성물 | 역할 |
|---|---|
| `codex/skills/self-improve` | Codex 사건의 진단과 로컬 개선 |
| `codex/agents/meta-doc-critic.toml` | 메타 편집의 read-only 독립 검수 |
| `shared/skills/port-harness-change` | 확인된 의미만 다른 플랫폼으로 포팅 |
| `codex/skills/self-improve/references/meta-doc.md` | Codex 메타 문서의 소속·작성·검증 기준 |
| `shared/principles.md` | 두 어댑터가 대조하는 플랫폼 중립 의미 |
