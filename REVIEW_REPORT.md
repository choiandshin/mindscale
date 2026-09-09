# MindScale 게시 전 검토 — 2026-09-09

`REVIEW_BRIEF.md`의 우선순위와 유지보수 제약을 기준으로 검토했습니다.
원본은 `~/GitHub/mindscale-site.zip`이며, 작업 시작 시 `mindscale` 폴더와 Git 저장소는 없었습니다.

## 주요 발견과 조치

| 우선순위 | 발견 | 조치 / 상태 |
|---|---|---|
| 높음 | Crossref에서 받은 제목·저자·저널 정보가 HTML로 그대로 삽입될 수 있음 | 가져올 때 외부 문자열을 이스케이프하고, 렌더러는 기존 `<me>`, `<em>`, `<strong>`만 허용. 링크는 HTTP(S)만 허용. 악성 마크업 회귀 테스트 통과 |
| 높음 | JSON을 직접 덮어써 저장 중 실패하면 기존 논문 목록이 손상될 수 있음 | 같은 폴더의 임시 파일에 완전히 쓰고 flush/fsync 후 원자적으로 교체. 교체 실패 시 원본 보존 테스트 통과. HTML 렌더러도 동일하게 보호 |
| 높음 | 두 Crossref 요청이 모두 실패해도 종료 코드 0과 “No new publications found” 출력 | 일시적인 오류에 최대 3회 재시도. 한 요청이라도 끝내 실패하거나 응답 형식이 잘못되면 종료 코드 1, 데이터 변경 없음. 워크플로에서 실패가 드러남 |
| 중간 | 모바일에서 JavaScript가 꺼지면 모든 메뉴 링크가 숨겨짐 | 기본 HTML 메뉴를 표시하고 스크립트 초기화 후에만 접기. `aria-controls`, Escape 닫기·버튼으로 초점 복귀 추가 |
| 중간 | 작은 보조 글자의 대비가 부족함 | `--ink-faint`를 조정: 흰 배경 대비 3.85:1 → 5.86:1, 연한 청록 배경 5.10:1. 링크 hover 색도 조정 |
| 중간 | 논문 필터는 기존 `aria-pressed`가 있었으나 변경된 결과 수를 알리지 않음 | live status로 개수와 선택 필터 안내. JavaScript가 없으면 작동하지 않는 필터 버튼은 감추고 44개 논문 전체 유지 |
| 중간 | Crossref 누락/비정상 필드에서 예외 발생, DOI·이름·한글 제목 비교가 불완전 | 필드 타입 검사, DOI URL/접두어/대소문자 정규화, 하이픈·붙여 쓴 이름 대응, Unicode 제목 비교. 비한국어 original-title만으로 한국어 분류하지 않음 |
| 중간 | 액션 태그가 변경 가능하고 작업 제한·검증이 없음 | 공식 안정 릴리스 커밋 해시 고정, 기본 읽기 권한과 갱신 job의 쓰기 권한 분리, 10분 제한·중복 실행 직렬화. PR 변경 파일을 JSON/논문 HTML로 한정. 사전 테스트와 HTML 검증 추가 |
| 낮음 | 연구 페이지 등의 제목 단계와 footer h4가 불필요하게 건너뜀 | 문구는 유지하고 제목 단계를 정리 |
| 낮음 | 상대 OG 이미지 주소, canonical·구조화 데이터 부재 | `choiandshin.github.io/mindscale/` 기준 절대 URL, 페이지별 canonical/OG URL, Person JSON-LD, 렌더러가 만드는 ScholarlyArticle JSON-LD 추가 |
| 낮음 | 로고의 크기 정보 부족, 아래쪽 사진의 즉시 로딩 | 실제 이미지 크기를 지정하고 하단 이미지 지연 로딩, 첫 사진 우선 로딩. Safari용 backdrop-filter 접두어와 동작 줄이기 설정 대응 |
| 낮음 | 공유 레이아웃 마커가 중복되거나 역순일 때 안전하지 않음 | 모든 페이지의 마커를 쓰기 전에 검사. 논문 렌더러도 마커 개수·순서를 검사 |

## 검증 결과

변경 전:

- HTTP 서버에서 7개 페이지 모두 200 응답.
- `python3 tools/sync_layout.py --check`: All 7 pages already in sync.
- `python3 tools/build_publications.py`: already up to date (44 entries).
- 실제 네트워크 `python3 tools/fetch_new_publications.py --dry-run`: 후보 6건, 파일 변경 없음.
- 제한된 네트워크에서 원래 갱신기의 실패 은폐 문제도 재현됨.

변경 후:

- 동일한 레이아웃 검사 및 논문 렌더러 재실행 통과, 44개 항목 유지.
- `data/publications.json`은 원본과 바이트 단위로 동일.
- HTML 시작/닫힘, 중복 ID, 주요 landmark, 이미지 alt/크기, 내부 파일/앵커, JSON-LD 검사 통과.
- Python 오프라인 회귀 테스트 10개 통과: 비정상 API 레코드, 부분 실패, 이름/DOI/한글 비교,
  외부 마크업, 재시도 횟수, 저장 실패 시 원본 보존 등.
- 수정 후 실제 Crossref dry-run도 후보 6건을 정상 보고. 신규 후보는 추가하지 않음.
- Chrome 및 WebKit 26.5: 각 7개 페이지 × 1440/390/320px × light/dark OS 설정 모두 통과.
  메뉴 ARIA·Escape, 7개 논문 필터의 실제 개수/선택 상태/live status, 이미지 로딩,
  가로 넘침, JavaScript 오류를 확인.
- 두 엔진에서 모바일 JavaScript 비활성 상태의 메뉴 및 전체 44개 논문 표시 통과.
- 데스크톱·모바일 스크린샷으로 기존 레이아웃 유지 확인.
- `git diff --check` 통과.

WebKit은 Safari와 같은 엔진을 사용하는 자동화 테스트이며 Safari 앱/VoiceOver 실기기 검사와 같지는 않습니다.
HTML 검사는 로컬 구조 검사이며 전체 W3C 적합성 인증이 아닙니다. 외부의 모든 논문 URL이나
연구 사실을 다시 검증한 것은 아닙니다. 사이트는 별도 다크 테마가 없으므로 두 OS 모드 모두
기존 밝은 팔레트를 유지합니다. Google Fonts는 이미 preconnect와 display=swap을 사용합니다.
이미지 포맷 변경이나 추가 빌드 도구는 도입하지 않았습니다.

## 남겨 둔 확인 사항

1. **cv.pdf**: 원래 알려진 미완료 항목. Contact의 CV 링크는 파일을 추가하기 전까지 404입니다.
2. **강의 설명**: 초안인 한 줄 설명을 소유자가 확인해야 합니다. 강의명과 본문은 수정하지 않았습니다.
3. **직급 이력의 표기**: README는 Associate Professor를 2026년 9월부터로 설명하지만,
   People의 Positions는 `2022–present / Associate Professor`로 표시합니다. 약력 사실을
   바꾸지 말라는 지침에 따라 그대로 두었으며, 기간과 직급 구분 확인을 권합니다.
4. **Crossref 후보 검토**: 이름만으로 동명이인을 확실히 구별할 수 없습니다. 실제 후보 중
   “Alginate as a Soil Conditioner: Properties, Mechanisms, and Agricultural Applications”
   (`10.1007/s12257-023-0206-1`)은 분야상 동명이인 가능성이 있어 특히 확인이 필요합니다.
   정오표 후보도 별도 논문으로 등재할지 판단해야 합니다. 자동으로 합치지 않습니다.
5. **조회 범위**: 기존 두 저자 검색의 상위 100건씩만 조회하는 설계를 유지했습니다.
   완전한 목록 수집이 필요하면 검증된 ORCID 등 식별자와 페이지 순회가 후속 과제입니다.
6. **출판 유형 추정**: 기존 Crossref 유형 매핑과 한국어 저널 목록은 발견 보조용입니다.
   `posted-content → review` 등은 실제 심사 상태를 보증하지 않으므로 PR에서 확인해야 합니다.
7. **주소 변경**: 계정 대표 홈페이지나 도메인을 선택하면 7개 head의 canonical/OG URL과
   People JSON-LD의 URL/이미지도 함께 변경해야 합니다.

## 유지보수와 배포

- 공통 header/footer는 `index.html`에서만 수정 후 `python3 tools/sync_layout.py` 실행.
- 논문은 JSON에서 수정 후 `python3 tools/build_publications.py` 실행.
  생성 영역의 내용과 논문 구조화 데이터는 렌더러가 함께 관리합니다.
- `.nojekyll`, 기존 논문 갱신 워크플로, 영어 본문과 `lang="ko"` 예외를 유지했습니다.
- 일반 사이트 파일은 GitHub Pages의 `main / (root)`에서 그대로 서비스합니다. 사이트 빌드 단계가 없습니다.
- 새 Check site 워크플로는 읽기 전용입니다. branch 배포 자체를 차단하지 않으므로 결과를 확인한 후 merge합니다.
- 주간 갱신은 제안 PR만 만들며 자동 merge하지 않습니다. 새 항목은 `needs_review: true`를 유지합니다.
- 원본 import 이후 화면/메타데이터, 갱신 안정성/검증, 문서의 변경을 별도 커밋으로 나눴습니다.
  `git log --oneline`, `git show <커밋>`으로 각 변경을 검토할 수 있습니다.

참고: [GitHub Pages 게시 소스 설정](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site),
[GitHub workflow trigger 제한](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow),
[ScholarlyArticle 스키마](https://schema.org/ScholarlyArticle).
JSON-LD 추가는 검색 서비스의 실제 수록이나 Google Scholar 노출을 보장하지 않습니다.
