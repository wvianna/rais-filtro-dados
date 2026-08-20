"""Testes do motor de análise (caso de uso de referência)."""

import unittest

from rais import analyzer, sample

from support import PARTIAL, TempSampleDir


class TestAnaliseAmostra(unittest.TestCase):
    """Valida a análise do caso de referência na amostra COM identificador."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = TempSampleDir()
        cls.res = analyzer.analyze(
            cls.tmp.sample_path,
            municipio=sample.EXPECTED["municipio"],
            subclasse=sample.EXPECTED["subclasse"],
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.__exit__(None, None, None)

    def test_vinculos(self):
        self.assertEqual(self.res.vinculos, sample.EXPECTED["vinculos"])  # 19

    def test_estabelecimentos(self):
        self.assertTrue(self.res.estabelecimentos["disponivel"])
        self.assertEqual(self.res.estabelecimentos["quantidade"], sample.EXPECTED["estabelecimentos"])  # 3

    def test_vinculos_por_estabelecimento(self):
        por = {e["identificador"]: e["vinculos"] for e in self.res.estabelecimentos["por_estabelecimento"]}
        self.assertEqual(por["01000000000100"], 10)
        self.assertEqual(por["02000000000200"], 5)
        self.assertEqual(por["03000000000300"], 3)

    def test_total_considerado(self):
        self.assertEqual(self.res.estabelecimentos["total_vinculos_considerados"], 18)

    def test_escolaridade_frequencias(self):
        freqs = {e.codigo: e.frequencia for e in self.res.escolaridade}
        self.assertEqual(freqs["1"], 1)
        self.assertEqual(freqs["2"], 3)
        self.assertEqual(freqs["11"], 2)
        self.assertEqual(sum(freqs.values()), 17)

    def test_ignorados_escolaridade(self):
        self.assertEqual(self.res.ignorados_escolaridade["frequencia"], 2)

    def test_percentuais_fecham_cem(self):
        total = sum(e.percentual for e in self.res.escolaridade) + self.res.ignorados_escolaridade["percentual"]
        self.assertAlmostEqual(total, 100.0, places=6)

    def test_modo_varredura(self):
        self.assertEqual(self.res.modo, "varredura_integral")
        self.assertEqual(self.res.total_linhas, 24)


class TestAnaliseArquivoParcial(unittest.TestCase):
    """Valida a análise no arquivo parcial real (sem coluna de identificação)."""

    def test_vinculos_filtro_real(self):
        res = analyzer.analyze(PARTIAL, municipio="310620", subclasse="8513900")
        self.assertEqual(res.vinculos, 41)
        self.assertEqual(res.total_linhas, 299)

    def test_estabelecimentos_indisponivel(self):
        res = analyzer.analyze(PARTIAL, municipio="310620", subclasse="8513900")
        self.assertFalse(res.estabelecimentos["disponivel"])
        self.assertIsNone(res.estabelecimentos["quantidade"])
        self.assertIn("identificação", res.estabelecimentos["motivo"].lower())
        # aviso registrado
        self.assertTrue(any("identificação" in a.lower() for a in res.avisos))

    def test_sem_resultados(self):
        res = analyzer.analyze(PARTIAL, municipio="999999", subclasse="9999999")
        self.assertEqual(res.vinculos, 0)
        self.assertEqual(res.escolaridade[0].frequencia, 0)

    def test_filtro_apenas_municipio(self):
        res = analyzer.analyze(PARTIAL, municipio="330455")
        self.assertGreater(res.vinculos, 0)
        self.assertEqual(res.filtros["subclasse"], None)


if __name__ == "__main__":
    unittest.main()
