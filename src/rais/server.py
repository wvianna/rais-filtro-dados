"""Servidor web (API JSON + frontend estático) usando apenas a stdlib.

Exposição:
  GET  /                    -> web/index.html
  GET  /styles.css|app.js   -> estáticos
  GET  /api/health          -> status do serviço
  GET  /api/files           -> arquivos de dados disponíveis
  GET  /api/layouts?tipo=   -> taxonomias (escolaridade|subclasse|municipio)
  GET  /api/schema?file=    -> esquema/colunas do arquivo selecionado
  GET  /api/index?file=     -> status do índice do arquivo
  POST /api/index           -> {file}  constrói o índice (streaming)
  POST /api/analyze         -> {file, municipio, subclasse, use_index}

Todas as respostas em JSON (UTF-8) com CORS habilitado.
"""

from __future__ import annotations

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from . import __version__, analyzer, config, domains, files, index, schema


def build_app(
    data_dir: Optional[str] = None,
    layout_dir: Optional[str] = None,
    web_dir: Optional[str] = None,
    index_dir: Optional[str] = None,
) -> "RaisServer":
    return RaisServer(data_dir=data_dir, layout_dir=layout_dir, web_dir=web_dir, index_dir=index_dir)


class RaisServer:
    """Empacota as dependências e o manipulador HTTP em um único servidor."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        layout_dir: Optional[str] = None,
        web_dir: Optional[str] = None,
        index_dir: Optional[str] = None,
    ) -> None:
        self.data_dir = data_dir or config.DEFAULT_DATA_DIR
        self.layout_dir = layout_dir or config.DEFAULT_LAYOUT_DIR
        self.web_dir = web_dir or config.DEFAULT_WEB_DIR
        self.index_dir = index_dir or config.DEFAULT_INDEX_DIR
        self.domains = domains.Domains(self.layout_dir)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ API
    def api_health(self) -> Dict:
        return {"status": "ok", "servico": "rais-filtro-dados", "versao": __version__}

    def api_files(self) -> Dict:
        return {"arquivos": [f.as_dict() for f in files.list_data_files(self.data_dir)]}

    def api_layouts(self, tipo: str, busca: Optional[str] = None, limit: int = 500) -> Dict:
        busca = (busca or "").strip().lower()
        if tipo == "escolaridade":
            itens = [{"codigo": n.codigo, "rotulo": n.rotulo} for n in self.domains.escolaridade]
        elif tipo == "subclasse":
            itens = [{"codigo": c, "rotulo": d} for c, d in self.domains.subclasses.items()]
        elif tipo == "municipio":
            itens = [{"codigo": c, "rotulo": d} for c, d in self.domains.municipios.items()]
        else:
            return {"tipo": tipo, "itens": []}
        if busca:
            itens = [
                i for i in itens
                if busca in i["codigo"].lower() or busca in i["rotulo"].lower()
            ]
        itens.sort(key=lambda i: i["codigo"])
        return {"tipo": tipo, "total": len(itens), "itens": itens[:limit]}

    def api_schema(self, file_name: str) -> Dict:
        df = files.find_file(file_name, self.data_dir)
        if df is None:
            return {"error": "arquivo não encontrado", "file": file_name}
        sch = schema.detect_schema(df.path)
        return {"file": df.as_dict(), "schema": sch.as_dict()}

    def api_index_status(self, file_name: str) -> Dict:
        df = files.find_file(file_name, self.data_dir)
        if df is None:
            return {"error": "arquivo não encontrado", "file": file_name}
        stats = index.index_stats(df.path, self.index_dir)
        return {"file": df.as_dict(), "index": stats or {"exists": False}}

    def api_index_build(self, file_name: str) -> Dict:
        df = files.find_file(file_name, self.data_dir)
        if df is None:
            return {"error": "arquivo não encontrado", "file": file_name}
        try:
            return index.build_index(df.path, index_dir=self.index_dir)
        except Exception as exc:  # noqa: BLE001 - erro vira JSON
            return {"error": str(exc), "file": file_name}

    def api_analyze(self, payload: Dict) -> Dict:
        file_name = payload.get("file") or payload.get("arquivo")
        if not file_name:
            return {"error": "campo 'file' obrigatório"}
        df = files.find_file(file_name, self.data_dir)
        if df is None:
            return {"error": "arquivo não encontrado", "file": file_name}
        try:
            res = analyzer.analyze(
                df.path,
                municipio=payload.get("municipio") or None,
                subclasse=payload.get("subclasse") or None,
                use_index=bool(payload.get("use_index", False)),
                index_dir=self.index_dir,
                domains_obj=self.domains,
            )
            data = res.as_dict()
            data["file"] = df.as_dict()
            return data
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc), "file": file_name}


class RaisHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP que delega para o RaisServer do servidor."""

    server: "RaisHTTPServer"

    # ------------------------------------------------------------- helpers
    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, data) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _read_json(self) -> Dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _serve_static(self, rel: str) -> None:
        app = self.server.app
        base = os.path.realpath(app.web_dir)
        target = os.path.realpath(os.path.join(base, rel.lstrip("/")))
        if not target.startswith(base + os.sep) and target != base:
            self._send_json(403, {"error": "caminho proibido"})
            return
        if not os.path.isfile(target):
            self._send_json(404, {"error": "não encontrado", "path": rel})
            return
        ctype, _ = mimetypes.guess_type(target)
        ctype = ctype or "application/octet-stream"
        with open(target, "rb") as fh:
            self._send(200, fh.read(), ctype)

    # --------------------------------------------------------------- rotas
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        app = self.server.app

        try:
            if path in ("/", "/index.html"):
                self._serve_static("index.html")
            elif path in ("/styles.css", "/app.js"):
                self._serve_static(path.lstrip("/"))
            elif path == "/api/health":
                self._send_json(200, app.api_health())
            elif path == "/api/files":
                self._send_json(200, app.api_files())
            elif path == "/api/layouts":
                tipo = (query.get("tipo") or [""])[0]
                busca = (query.get("busca") or [None])[0]
                limit = int((query.get("limit") or ["500"])[0])
                self._send_json(200, app.api_layouts(tipo, busca, limit))
            elif path == "/api/schema":
                fname = (query.get("file") or [""])[0]
                self._send_json(200, app.api_schema(fname))
            elif path == "/api/index":
                fname = (query.get("file") or [""])[0]
                self._send_json(200, app.api_index_status(fname))
            else:
                self._send_json(404, {"error": "rota não encontrada", "path": path})
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        app = self.server.app
        payload = self._read_json()
        try:
            if path == "/api/analyze":
                self._send_json(200, app.api_analyze(payload))
            elif path == "/api/index":
                self._send_json(200, app.api_index_build(payload))
            else:
                self._send_json(404, {"error": "rota não encontrada", "path": path})
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": str(exc)})

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        # Log compacto no formato padrão.
        super().log_message(fmt, *args)


class RaisHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer com referência ao app configurado."""

    daemon_threads = True

    def __init__(self, addr, app: RaisServer) -> None:
        self.app = app
        super().__init__(addr, RaisHandler)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    **kwargs,
) -> RaisHTTPServer:
    app = build_app(**kwargs)
    return RaisHTTPServer((host, port), app)
