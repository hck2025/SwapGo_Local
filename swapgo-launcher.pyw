"""SwapGo 런처 — 백엔드(FastAPI), AI 엔진(FastAPI), 프론트엔드(Next.js) 서버를
GUI로 켜고 끄는 도구.

요구사항:
- Python 3.10+ (tkinter 포함, Windows 기본)
- swapgo_backend/.venv  — 의존성 설치 완료
- swapgo_engine/.venv   — 의존성 설치 완료
- swapgo_frontend/node_modules — npm install 완료

더블클릭으로 실행 가능한 .pyw 파일이라 콘솔창 없이 GUI 만 뜬다.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import ttk
from typing import Optional


# ── 경로 설정 ─────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent
BACKEND_DIR  = ROOT / "swapgo-backend"
ENGINE_DIR   = ROOT / "swapgo-engine"
FRONTEND_DIR = ROOT / "swapgo-frontend"

BACKEND_PORT  = 8000
ENGINE_PORT   = 9000
FRONTEND_PORT = 3000


# ── 프로세스 실행 명령 ────────────────────────────────────────

def _venv_python(project_dir: Path) -> str:
    """OS에 맞는 가상환경 Python 경로 반환."""
    win = project_dir / ".venv" / "Scripts" / "python.exe"
    unix = project_dir / ".venv" / "bin" / "python"
    return str(win) if win.exists() else str(unix)


def _backend_cmd() -> list[str]:
    return [_venv_python(BACKEND_DIR), "run.py", "--no-reload", "--port", str(BACKEND_PORT)]


def _engine_cmd() -> list[str]:
    """AI 엔진 서버 — uvicorn main:app 으로 실행."""
    return [
        _venv_python(ENGINE_DIR),
        "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", str(ENGINE_PORT),
    ]


def _frontend_cmd() -> list[str]:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    return [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT)]


# ── HTTP 헬스 체크 ────────────────────────────────────────────

def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
        return False


# ── 서버 상태 모델 ────────────────────────────────────────────

@dataclass
class ServerState:
    name: str
    cwd: Path
    cmd_factory: callable          # type: ignore
    port: int
    health_url: str
    log_color: str
    proc: Optional[subprocess.Popen] = None
    log_queue: queue.Queue = field(default_factory=queue.Queue)
    pump_thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> str | None:
        if self.running:
            return "이미 실행 중이에요."
        if not self.cwd.exists():
            return f"경로를 찾을 수 없어요: {self.cwd}"
        try:
            # 자식 프로세스가 UTF-8 로 출력하도록 강제한다.
            # Windows 기본 콘솔 인코딩(cp949)에서는 백엔드/엔진의 이모지 로그(✅·❌ 등)가
            # UnicodeEncodeError 를 일으켜 서버가 부팅 도중 죽는다. PYTHONUNBUFFERED 는
            # 로그가 버퍼에 갇히지 않고 런처 로그창에 즉시 흐르게 한다.
            child_env = os.environ.copy()
            child_env["PYTHONIOENCODING"] = "utf-8"
            child_env["PYTHONUNBUFFERED"] = "1"
            kwargs: dict = dict(
                cwd=str(self.cwd),
                env=child_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if os.name == "nt":
                kwargs["creationflags"] = (
                    subprocess.CREATE_NO_WINDOW
                    | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                )
            self.proc = subprocess.Popen(self.cmd_factory(), **kwargs)
        except FileNotFoundError as e:
            return f"실행 파일을 찾지 못했어요: {e}"
        except Exception as e:  # noqa: BLE001
            return f"시작 실패: {e}"
        self._start_pump()
        return None

    def _start_pump(self) -> None:
        def pump():
            assert self.proc is not None and self.proc.stdout is not None
            for line in iter(self.proc.stdout.readline, ""):
                self.log_queue.put(line.rstrip("\n"))
            self.log_queue.put(f"[{self.name}] 프로세스가 종료되었어요.")

        self.pump_thread = threading.Thread(target=pump, daemon=True)
        self.pump_thread.start()

    def stop(self) -> str | None:
        if not self.running:
            return "이미 멈춰 있어요."
        proc = self.proc
        assert proc is not None
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    text=True,
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception as e:  # noqa: BLE001
            return f"중지 중 오류: {e}"
        return None


# ── GUI 앱 ────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SwapGo 런처")
        self.geometry("1060x580")
        self.minsize(860, 460)
        self.configure(bg="#f8fafc")

        # ── 서버 인스턴스 ─────────────────────────────────────
        self.backend = ServerState(
            name="backend",
            cwd=BACKEND_DIR,
            cmd_factory=_backend_cmd,
            port=BACKEND_PORT,
            health_url=f"http://localhost:{BACKEND_PORT}/health",
            log_color="#86efac",   # 연두
        )
        self.engine = ServerState(
            name="engine",
            cwd=ENGINE_DIR,
            cmd_factory=_engine_cmd,
            port=ENGINE_PORT,
            health_url=f"http://localhost:{ENGINE_PORT}/health",
            log_color="#c4b5fd",   # 연보라
        )
        self.frontend = ServerState(
            name="frontend",
            cwd=FRONTEND_DIR,
            cmd_factory=_frontend_cmd,
            port=FRONTEND_PORT,
            health_url=f"http://localhost:{FRONTEND_PORT}",
            log_color="#93c5fd",   # 연파랑
        )

        self._build_ui()
        self._tick()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI 구성 ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabelframe", background="#f8fafc")
        style.configure(
            "TLabelframe.Label",
            background="#f8fafc",
            font=("Segoe UI", 10, "bold"),
        )

        wrap = tk.Frame(self, bg="#f8fafc")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        # 헤더
        tk.Label(
            wrap,
            text="스왑고 SwapGo 런처",
            font=("Segoe UI", 14, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
        ).pack(anchor="w")
        tk.Label(
            wrap,
            text=(
                "백엔드(FastAPI · :8000)   AI 엔진(FastAPI · :9000)   "
                "프론트엔드(Next.js · :3000)"
            ),
            font=("Segoe UI", 9),
            bg="#f8fafc",
            fg="#64748b",
        ).pack(anchor="w", pady=(0, 8))

        # ── 카드 3열 ─────────────────────────────────────────
        cards = tk.Frame(wrap, bg="#f8fafc")
        cards.pack(fill="x")

        self.backend_card = self._build_card(
            cards,
            title="백엔드 (FastAPI)",
            subtitle="API / 스왑 / 지갑 / 풀",
            port=BACKEND_PORT,
            buttons=[
                ("시작",    lambda: self._start(self.backend)),
                ("중지",    lambda: self._stop(self.backend)),
                ("API 문서", lambda: webbrowser.open(
                    f"http://localhost:{BACKEND_PORT}/docs")),
                ("Health",  lambda: webbrowser.open(
                    f"http://localhost:{BACKEND_PORT}/health")),
            ],
        )
        self.backend_card.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.engine_card = self._build_card(
            cards,
            title="AI 엔진 (FastAPI)",
            subtitle="GRU 예측 / 신호 ingest / 가상거래",
            port=ENGINE_PORT,
            buttons=[
                ("시작",      lambda: self._start(self.engine)),
                ("중지",      lambda: self._stop(self.engine)),
                ("API 문서",  lambda: webbrowser.open(
                    f"http://localhost:{ENGINE_PORT}/docs")),
                ("거래 스트림", lambda: webbrowser.open(
                    f"http://localhost:{ENGINE_PORT}/stream/trades")),
            ],
        )
        self.engine_card.grid(row=0, column=1, sticky="ew", padx=5)

        self.frontend_card = self._build_card(
            cards,
            title="프론트엔드 (Next.js)",
            subtitle="거래 / 마켓 / 포트폴리오 UI",
            port=FRONTEND_PORT,
            buttons=[
                ("시작",      lambda: self._start(self.frontend)),
                ("중지",      lambda: self._stop(self.frontend)),
                ("웹 열기",   lambda: webbrowser.open(
                    f"http://localhost:{FRONTEND_PORT}")),
                ("AI 대시보드", lambda: webbrowser.open(
                    f"http://localhost:{FRONTEND_PORT}/ai")),
            ],
        )
        self.frontend_card.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)
        cards.grid_columnconfigure(2, weight=1)

        # ── 일괄 동작 버튼 ────────────────────────────────────
        bulk = tk.Frame(wrap, bg="#f8fafc")
        bulk.pack(fill="x", pady=(8, 4))

        self._mk_btn(
            bulk, "전체 시작", self._start_all, primary=True
        ).pack(side="left")
        self._mk_btn(
            bulk, "전체 중지", self._stop_all
        ).pack(side="left", padx=(6, 0))
        self._mk_btn(
            bulk, "엔진만 재시작", self._restart_engine
        ).pack(side="left", padx=(6, 0))
        # 백엔드는 부팅 시 자동으로 시드된다(run.py). 수동 시드/관리 엔드포인트는
        # POST + x-admin-token 헤더가 필요해 브라우저 GET 으로 못 열기에, 직접 실행
        # 가능한 Swagger 문서(/docs)를 연다. (예전 'DB 시드' 버튼은 /admin/seed 를 GET
        # 으로 열어 405 가 났다.)
        self._mk_btn(
            bulk,
            "관리 (API 문서)",
            lambda: webbrowser.open(
                f"http://localhost:{BACKEND_PORT}/docs"
            ),
        ).pack(side="right")

        # ── 로그 영역 ─────────────────────────────────────────
        log_frame = ttk.LabelFrame(wrap, text="로그")
        log_frame.pack(fill="both", expand=True, pady=(8, 0))

        self.log = tk.Text(
            log_frame,
            wrap="word",
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            font=("Consolas", 9),
            relief="flat",
            padx=8,
            pady=6,
        )
        self.log.pack(fill="both", expand=True, side="left")
        self.log.tag_configure("backend",  foreground="#86efac")   # 연두
        self.log.tag_configure("engine",   foreground="#c4b5fd")   # 연보라
        self.log.tag_configure("frontend", foreground="#93c5fd")   # 연파랑
        self.log.tag_configure("system",   foreground="#fcd34d")   # 노랑

        sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log["yscrollcommand"] = sb.set

        # ── 상태바 ────────────────────────────────────────────
        self.status = tk.Label(
            wrap,
            text="대기 중",
            anchor="w",
            bg="#f8fafc",
            fg="#64748b",
            font=("Segoe UI", 9),
        )
        self.status.pack(fill="x", pady=(6, 0))

        # 초기 경로 로그
        self._log("system", "런처 준비됨.")
        self._log("system", f"백엔드  경로: {BACKEND_DIR}")
        self._log("system", f"AI 엔진 경로: {ENGINE_DIR}")
        self._log("system", f"프론트  경로: {FRONTEND_DIR}")
        for d, label in (
            (BACKEND_DIR,  "swapgo_backend"),
            (ENGINE_DIR,   "swapgo_engine"),
            (FRONTEND_DIR, "swapgo_frontend"),
        ):
            if not d.exists():
                self._log("system", f"⚠️  {label} 디렉토리를 찾지 못했어요: {d}")

    def _build_card(
        self,
        parent: tk.Widget,
        *,
        title: str,
        subtitle: str,
        port: int,
        buttons: list[tuple[str, callable]],  # type: ignore
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg="white",
            highlightbackground="#e2e8f0",
            highlightthickness=1,
        )
        inner = tk.Frame(card, bg="white")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        head = tk.Frame(inner, bg="white")
        head.pack(fill="x")
        tk.Label(
            head, text=title, font=("Segoe UI", 11, "bold"), bg="white"
        ).pack(side="left")
        dot = tk.Label(head, text="●", fg="#94a3b8", bg="white", font=("Segoe UI", 12))
        dot.pack(side="right")
        card.dot = dot  # type: ignore[attr-defined]

        tk.Label(
            inner, text=subtitle, fg="#64748b", bg="white", font=("Segoe UI", 9)
        ).pack(anchor="w")
        card.status_label = tk.Label(  # type: ignore[attr-defined]
            inner,
            text=f"포트 {port} · 중지됨",
            fg="#64748b",
            bg="white",
            font=("Segoe UI", 9),
        )
        card.status_label.pack(anchor="w", pady=(2, 8))  # type: ignore[attr-defined]

        btn_row = tk.Frame(inner, bg="white")
        btn_row.pack(fill="x")
        for i, (label, cmd) in enumerate(buttons):
            primary = label == "시작"
            self._mk_btn(btn_row, label, cmd, primary=primary).grid(
                row=0, column=i, padx=(0, 4), sticky="ew"
            )
        for i in range(len(buttons)):
            btn_row.grid_columnconfigure(i, weight=1)

        return card

    def _mk_btn(
        self,
        parent: tk.Widget,
        text: str,
        cmd,
        *,
        primary: bool = False,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg="#2563eb" if primary else "#f1f5f9",
            fg="white" if primary else "#0f172a",
            activebackground="#1d4ed8" if primary else "#e2e8f0",
            activeforeground="white" if primary else "#0f172a",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold" if primary else "normal"),
            padx=10,
            pady=5,
            borderwidth=0,
        )

    # ── 동작 ──────────────────────────────────────────────────

    def _start(self, srv: ServerState) -> None:
        err = srv.start()
        if err:
            self._log("system", f"[{srv.name}] {err}")
        else:
            self._log("system", f"[{srv.name}] 시작 명령 발행됨 (port {srv.port})")

    def _stop(self, srv: ServerState) -> None:
        err = srv.stop()
        if err:
            self._log("system", f"[{srv.name}] {err}")
        else:
            self._log("system", f"[{srv.name}] 중지 명령 발행됨")

    def _start_all(self) -> None:
        """시작 순서: 백엔드(0) → AI 엔진(1.2s) → 프론트엔드(2.4s)
        AI 엔진은 백엔드 SwapGo API 에 의존하므로 백엔드가 먼저 기동해야 합니다."""
        self._start(self.backend)
        self.after(1200, lambda: self._start(self.engine))
        self.after(2400, lambda: self._start(self.frontend))

    def _stop_all(self) -> None:
        """종료 순서: 프론트엔드 → AI 엔진 → 백엔드."""
        self._stop(self.frontend)
        self.after(400, lambda: self._stop(self.engine))
        self.after(800, lambda: self._stop(self.backend))

    def _restart_engine(self) -> None:
        """AI 엔진만 재시작 (모델 교체 후 핫리로드 용도)."""
        self._log("system", "[engine] 재시작 중...")
        self._stop(self.engine)
        self.after(1500, lambda: self._start(self.engine))

    # ── 1초 폴링 ──────────────────────────────────────────────

    def _tick(self) -> None:
        for srv, card in (
            (self.backend,  self.backend_card),
            (self.engine,   self.engine_card),
            (self.frontend, self.frontend_card),
        ):
            self._drain_logs(srv)
            self._refresh_card(srv, card)
        self._refresh_statusbar()
        self.after(1000, self._tick)

    def _drain_logs(self, srv: ServerState) -> None:
        drained = 0
        while drained < 200:
            try:
                line = srv.log_queue.get_nowait()
            except queue.Empty:
                break
            self._log(srv.name, line)
            drained += 1

    def _refresh_card(self, srv: ServerState, card: tk.Frame) -> None:
        running = srv.running
        healthy = _http_ok(srv.health_url) if running else False
        if running and healthy:
            color = "#10b981"
            text  = f"포트 {srv.port} · 정상 (PID {srv.proc.pid if srv.proc else '-'})"
        elif running:
            color = "#f59e0b"
            text  = f"포트 {srv.port} · 시작 중 (PID {srv.proc.pid if srv.proc else '-'})"
        else:
            color = "#94a3b8"
            text  = f"포트 {srv.port} · 중지됨"
        card.dot.configure(fg=color)             # type: ignore[attr-defined]
        card.status_label.configure(text=text)   # type: ignore[attr-defined]

    def _refresh_statusbar(self) -> None:
        def icon(srv: ServerState) -> str:
            if srv.running and _http_ok(srv.health_url):
                return "🟢"
            return "🟡" if srv.running else "⚪"

        b = icon(self.backend)
        e = icon(self.engine)
        f = icon(self.frontend)
        self.status.configure(
            text=(
                f"백엔드 {b} :8000   "
                f"AI 엔진 {e} :9000   "
                f"프론트엔드 {f} :3000"
            )
        )

    # ── 로그 ──────────────────────────────────────────────────

    def _log(self, tag: str, line: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {line}\n", tag)
        try:
            if self.log.yview()[1] > 0.95:
                self.log.see("end")
        except tk.TclError:
            pass

    # ── 창 닫기 ───────────────────────────────────────────────

    def _on_close(self) -> None:
        any_running = (
            self.backend.running
            or self.engine.running
            or self.frontend.running
        )
        if any_running:
            self._stop_all()
            self.after(900, self.destroy)
        else:
            self.destroy()


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
