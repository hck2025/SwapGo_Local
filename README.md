# SwapGo

SwapGo는 다음 세 개의 주요 구성 요소로 나뉩니다:

- `swapgo-frontend` - Next.js 기반 웹 애플리케이션
- `swapgo-backend` - FastAPI 기반 Python 백엔드 서버
- `swapgo-engine` - AI 봇 및 모델 추론 서버

> `.gitignore`에 명시된 빌드 아티팩트, 환경 파일, 가상환경, 캐시 디렉토리 등은 버전 관리 대상이 아닙니다.

## 권장 순서

의존성 및 환경종속성 세팅 완료 후 swapgo-launcher.pyw로 실행

## 프로젝트 구조

```text
swapgo/
├── swapgo-frontend/
├── swapgo-backend/
├── swapgo-engine/
├── swapgo-instructions/
├── swapgo-launcher.bat
└── swapgo-launcher.pyw
```

## 공통 요구사항

- Windows 기준으로 작성되었지만, 각 영역은 일반적인 Node.js/Python 개발 환경으로도 동작합니다.
- 각 Python 서비스는 독립적인 가상환경(`venv`)을 만들고 활성화해서 사용하는 것이 권장됩니다.

## swapgo-frontend

`swapgo-frontend`는 Next.js 애플리케이션입니다.

- 의존성 정의: `swapgo-frontend/package.json`
- 주요 스크립트:
  - `npm run dev` - 개발 서버
  - `npm run build` - 프로덕션 빌드
  - `npm run start` - 빌드된 앱 실행
  - `npm run lint` - ESLint 검사

### 설치 및 실행

```bash
cd swapgo-frontend
npm install
npm run dev
```

> `node_modules`, `.next`, `out`, `build` 등은 `.gitignore`로 제외됩니다.

## swapgo-backend

`swapgo-backend`는 FastAPI 기반 Python 백엔드입니다.

- 의존성 정의: `swapgo-backend/pyproject.toml`
- 개발 의존성: `dev` optional dependencies
- 권장 실행: Python 가상환경을 생성하여 실행

### 설치 및 실행

```bash
cd swapgo-backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

### 개발 서버 실행

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> `venv`, `.env`, `__pycache__` 등은 `.gitignore`에 의해 관리되지 않습니다.

## swapgo-engine

`swapgo-engine`는 AI 봇/추론 서버로, `requirements.txt` 기반 Python 패키지 설치를 사용합니다.

- 의존성 정의: `swapgo-engine/requirements.txt`
- 학습 관련 의존성: `swapgo-engine/train/requirements_train.txt`
- 실행 진입점: `swapgo-engine/main.py`

### 설치 및 실행

```bash
cd swapgo-engine
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 9000
```

> `venv`, `__pycache__`, `*.pyc` 등은 `.gitignore`에 의해 제외됩니다.

## 추가 참고

- `swapgo-backend`는 FastAPI + SQLite 기반이며, 인증 없는 익스플로러 API 및 WebSocket 채널을 포함합니다.
- `swapgo-engine`은 SwapGo 백엔드와 연동하여 캔들 데이터를 수집하고 ONNX 기반 예측/거래 봇을 실행합니다.
- 프론트엔드는 백엔드/엔진 API를 호출하는 대시보드 역할을 합니다.

## 권장 순서

1. `swapgo-backend` 가상환경 설치 및 서버 실행
2. `swapgo-engine` 가상환경 설치 및 서버 실행
3. `swapgo-frontend` 의존성 설치 및 개발 서버 실행

필요 시 각 하위 프로젝트의 README를 참고하여 세부 설정을 확인하세요.
