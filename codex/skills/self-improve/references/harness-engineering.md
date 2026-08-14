# Codex self-harness 지도

자기수정 loop는 `self-improve`가 진단·개입·승인을 맡고, 메타 문서 규율이 집필을 제한하며, 독립 검수가 결함을 찾고, Stop hook이 최종 검수 마킹 누락을 드러내는 구조다.

| 구성물 | 역할 |
|---|---|
| `codex/skills/self-improve` | Codex 사건의 진단과 로컬 개선 |
| `shared/skills/port-harness-change` | 확인된 의미만 다른 플랫폼으로 포팅 |
| `codex/skills/self-improve/references/meta-doc.md` | Codex 메타 문서의 소속·작성·검증 기준 |
| `codex/hooks/verify-meta-doc.py` | 마킹 이후 변경된 메타 문서를 Stop에서 탐지 |
| `codex/hooks/mark-verified.py` | 최종 검수된 파일의 mtime 기록 |
| `shared/principles.md` | 두 어댑터가 대조하는 플랫폼 중립 의미 |

검증 마커는 독립 검수가 실제로 수행됐음을 증명하지 않는다. 검수와 마킹의 책임은 `self-improve` 절차가 지고, hook은 누락을 계속 보이게 하는 게이트다.
