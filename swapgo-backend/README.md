# SwapGo Backend

Python AMM DEX (CPMM, Uniswap V2 식 `x*y=k`) 기반 모의투자·학습 플랫폼 백엔드.

- 임시 지갑(secp256k1) + 챌린지-서명 로그인 (EIP-191, MetaMask 호환)
- 체인형 해시 원장 + 머클루트 스냅샷 + 인증 없는 공개 익스플로러
- 슬리피지 임계값 분류(safe/warning/danger) + 한국어 친절 에러 + 용어사전 API
- AI 봇 통합용 ingest API + WebSocket 실시간 채널
- FastAPI + SQLite(WAL) + SQLAlchemy 2

## 빠른 시작

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
cp .env.example .env

# 개발 서버
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 시드 (자산/풀/용어사전/봇)
curl -X POST http://localhost:8000/admin/seed -H "x-admin-token: admin-bootstrap-change-me"
```

## 핵심 흐름 (curl)

```bash
# 회원가입 (개인키/니모닉 1회 표시)
curl -X POST localhost:8000/auth/signup -H "Content-Type: application/json" -d '{"display_name":"alice"}'

# 챌린지 + 로그인 (서명은 클라이언트에서 EIP-191 personal_sign)
curl -X POST localhost:8000/auth/challenge -d '{"address":"0x..."}'
curl -X POST localhost:8000/auth/login -d '{"address":"0x...","signature":"0x...","nonce":"..."}'

# 모의 입금
curl -X POST localhost:8000/wallet/deposit/mock -H "Authorization: Bearer $T" -d '{"symbol":"USDT","amount":"100000"}'

# 견적 + 실행
curl -X POST localhost:8000/swap/quote -d '{"pool_id":1,"side":"quote_to_base","amount_in_human":"100"}'
curl -X POST localhost:8000/swap/execute -H "Authorization: Bearer $T" -d '{...}'

# 공개 익스플로러 (인증 불필요 — 다른 지갑/익명 누구나 검증 가능)
curl localhost:8000/explorer/tx/1
curl 'localhost:8000/explorer/verify?from=1'
```

## 테스트

```bash
.venv/Scripts/python.exe -m pytest -q
```
