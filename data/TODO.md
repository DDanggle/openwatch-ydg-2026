# 수동 작업 TODO

현재 자동 매칭/분류가 안 된 항목들입니다.
CSV를 수정한 후 스크립트로 DB에 반영합니다.

---

## 1. 미매칭 의원 — 실거래가 수동 입력 (105명 / 158건)

아파트를 보유하고 있지만 자동 매칭이 안 된 항목입니다.
네이버 부동산(https://land.naver.com)에서 시세를 확인하여 채워주세요.

**파일:** `data/수동입력_미매칭.csv`

**채울 열:**
- `실거래추정_억` ← 네이버 부동산에서 확인한 시세 (억 단위, 예: 35.5)
- `아파트명_정정` ← 아파트명이 틀리면 여기에 (선택)
- `거래일` ← 참고한 거래 시점 (예: 2025.02)
- `출처_메모` ← "네이버부동산" 또는 URL

**반영 방법:**
```bash
cd backend
python3 scripts/import_manual_csv.py
python3 scripts/build_static_json.py  # 정적 JSON 재빌드
```

---

## 2. 정당 분류 (177명)

재산신고 엑셀에 정당 정보가 없어서 "국회"로 표시된 의원들입니다.
정당을 확인하여 채워주세요.

**파일:** `data/todo_정당분류.csv`

**채울 열:**
- `corrected_party` ← 정당명 (국민의힘, 더불어민주당, 조국혁신당, 개혁신당, 무소속 등)

**반영 방법:**
```bash
cd backend
python3 scripts/import_parties.py  # 아래 스크립트 사용
python3 scripts/build_static_json.py
```

---

## 3. 음수 괴리 검토 (19건)

신고가가 실거래 추정보다 높은 케이스입니다.
오매칭(다른 아파트와 비교됨)이거나, 실제로 공시가가 높은 특수 케이스입니다.

**파일:** `data/todo_음수괴리검토.csv`

**채울 열:**
- `action` ← 조치 (아래 중 택1)
  - `keep` — 데이터 맞음, 유지
  - `delete` — 오매칭, 삭제
  - `fix:XX.X` — 실거래가 수정 (억 단위, 예: fix:22.5)

**반영 방법:**
```bash
cd backend
python3 scripts/review_negatives.py  # 아래 스크립트 사용
python3 scripts/build_static_json.py
```

---

## 작업 완료 후

모든 CSV 수정이 끝나면:
```bash
cd backend
python3 scripts/build_static_json.py  # JSON 재빌드
cd ..
git add -A
git commit -m "수동 데이터 보정: 정당분류, 미매칭, 음수괴리"
git push  # Vercel 자동 배포
```
