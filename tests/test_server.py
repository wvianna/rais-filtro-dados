"""Testes do servidor HTTP (API JSON)."""

import json
import threading
import unittest
import urllib.request

from rais import sample
from rais.server import create_server

from support import TempSampleDir


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TempSampleDir()
        cls.server = create_server(host="127.0.0.1", port=0, data_dir=cls.tmp.tmp)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.__exit__(None, None, None)

    def _get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path, payload):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_health(self):
        d = self._get("/api/health")
        self.assertEqual(d["status"], "ok")

    def test_files(self):
        d = self._get("/api/files")
        nomes = [f["name"] for f in d["arquivos"]]
        self.assertIn("amostra_com_identificador.csv", nomes)

    def test_layouts(self):
        d = self._get("/api/layouts?tipo=municipio&busca=campos")
        self.assertTrue(any(i["codigo"] == "330100" for i in d["itens"]))

    def test_schema(self):
        d = self._get("/api/schema?file=amostra_com_identificador.csv")
        self.assertEqual(d["schema"]["columns"], 63)
        self.assertIn("identificador_estabelecimento", d["schema"]["present"])

    def test_analyze(self):
        d = self._post("/api/analyze", {
            "file": "amostra_com_identificador.csv",
            "municipio": sample.EXPECTED["municipio"],
            "subclasse": sample.EXPECTED["subclasse"],
        })
        self.assertNotIn("error", d)
        self.assertEqual(d["vinculos"], sample.EXPECTED["vinculos"])
        self.assertEqual(d["estabelecimentos"]["quantidade"], sample.EXPECTED["estabelecimentos"])

    def test_analyze_arquivo_inexistente(self):
        d = self._post("/api/analyze", {"file": "nao_existe.csv"})
        self.assertIn("error", d)

    def test_pagina_inicial(self):
        with urllib.request.urlopen(self.base + "/", timeout=15) as r:
            body = r.read().decode("utf-8")
            self.assertEqual(r.status, 200)
            self.assertIn("RAIS", body)


if __name__ == "__main__":
    unittest.main()
