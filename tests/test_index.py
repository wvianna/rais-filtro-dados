"""Testes do índice persistente SQLite."""

import os
import unittest

from rais import analyzer, index, sample

from support import TempSampleDir


class TestIndice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TempSampleDir()
        cls.index_dir = os.path.join(cls.tmp.tmp, "idx")
        cls.path = cls.tmp.sample_path
        cls.meta = index.build_index(cls.path, index_dir=cls.index_dir)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.__exit__(None, None, None)

    def test_construcao(self):
        self.assertEqual(self.meta["indexed_rows"], 24)

    def test_status(self):
        stats = index.index_stats(self.path, index_dir=self.index_dir)
        self.assertIsNotNone(stats)
        self.assertEqual(stats["rows"], 24)
        self.assertGreater(stats["distinct_municipios"], 0)

    def test_lookup(self):
        offs = index.lookup_offsets(
            self.path,
            municipio=sample.EXPECTED["municipio"],
            subclasse=sample.EXPECTED["subclasse"],
            index_dir=self.index_dir,
        )
        self.assertEqual(len(offs), sample.EXPECTED["vinculos"])  # 19

    def test_analise_via_indice_equivale_varredura(self):
        completo = analyzer.analyze(
            self.path,
            municipio=sample.EXPECTED["municipio"],
            subclasse=sample.EXPECTED["subclasse"],
        )
        via_indice = analyzer.analyze(
            self.path,
            municipio=sample.EXPECTED["municipio"],
            subclasse=sample.EXPECTED["subclasse"],
            use_index=True,
            index_dir=self.index_dir,
        )
        self.assertEqual(via_indice.modo, "indice")
        self.assertEqual(via_indice.vinculos, completo.vinculos)
        self.assertEqual(via_indice.estabelecimentos["quantidade"], completo.estabelecimentos["quantidade"])
        self.assertEqual(via_indice.ignorados_escolaridade["frequencia"], completo.ignorados_escolaridade["frequencia"])

    def test_sem_indice_retorna_vazio(self):
        offs = index.lookup_offsets(
            self.path,
            municipio="330100",
            subclasse="2342702",
            index_dir=os.path.join(self.tmp.tmp, "idx_nao_existe"),
        )
        self.assertEqual(offs, [])


if __name__ == "__main__":
    unittest.main()
