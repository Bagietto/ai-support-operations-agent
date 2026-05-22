"""
Servico REST local de incidentes para demo do Agent Pack.

Executar:
  python services/incidents_api/server.py
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
INCIDENTS_PATH = BASE_DIR / "incidents.json"


def _carregar_incidentes() -> list:
    return json.loads(INCIDENTS_PATH.read_text(encoding="utf-8"))


def _normalizar(valor) -> str:
    return str(valor or "").strip().lower()


class IncidentsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/health", "/api/incidents/search"}:
            self._json(404, {"erro": "rota nao encontrada"})
            return

        if parsed.path == "/health":
            self._json(200, {"status": "ok", "service": "incidents-api"})
            return

        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        produto = _normalizar(params.get("produto") or params.get("product"))
        ambiente = _normalizar(params.get("ambiente") or params.get("environment"))
        categoria = _normalizar(params.get("categoria") or params.get("category"))

        encontrados = []
        for incidente in _carregar_incidentes():
            if produto and _normalizar(incidente.get("produto")) != produto:
                continue
            if ambiente and _normalizar(incidente.get("ambiente")) != ambiente:
                continue
            if categoria and _normalizar(incidente.get("categoria")) != categoria:
                continue
            encontrados.append(incidente)

        ativo = any(i.get("status") in {"investigating", "monitoring"} for i in encontrados)
        severidade = "nenhuma"
        if any(i.get("severidade") == "alta" for i in encontrados):
            severidade = "alta"
        elif any(i.get("severidade") == "media" for i in encontrados):
            severidade = "media"

        evidencias = []
        for incidente in encontrados:
            evidencias.extend(incidente.get("evidencias", []))

        self._json(
            200,
            {
                "incidentes_relacionados": encontrados,
                "incidente_ativo": ativo,
                "severidade_incidente": severidade,
                "evidencias_incidente": evidencias,
            },
        )

    def log_message(self, format, *args):
        return

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    servidor = ThreadingHTTPServer(("127.0.0.1", 8100), IncidentsHandler)
    print("incidents-api rodando em http://127.0.0.1:8100")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
