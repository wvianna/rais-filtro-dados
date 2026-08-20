"""Testes das taxonomias/domínios de valor."""

import unittest

from rais import domains


class TestIgnorados(unittest.TestCase):
    def test_valores_ignorados(self):
        for v in ("-1", "{ñ class}", "{ñclass}", "{n class}", "", None, "  "):
            self.assertTrue(domains.is_ignored(v), v)

    def test_valores_validos(self):
        for v in ("1", "330100", "2342702", "CNPJ", "0"):
            self.assertFalse(domains.is_ignored(v), v)


class TestEscolaridade(unittest.TestCase):
    def setUp(self):
        self.niveis = domains.load_escolaridade()

    def test_quantidade(self):
        # 11 níveis + IGNORADO
        self.assertEqual(len(self.niveis), 12)

    def test_primeiro_ultimo(self):
        self.assertEqual(self.niveis[0].codigo, "1")
        self.assertEqual(self.niveis[0].rotulo, "ANALFABETO")
        self.assertEqual(self.niveis[-1].codigo, "-1")
        self.assertEqual(self.niveis[-1].rotulo, "IGNORADO")

    def test_rotulos(self):
        self.assertEqual(domains.rotulo_escolaridade("1", self.niveis), "ANALFABETO")
        self.assertEqual(domains.rotulo_escolaridade("7", self.niveis), "MEDIO COMPL")
        self.assertEqual(domains.rotulo_escolaridade("11", self.niveis), "DOUTORADO")

    def test_rotulo_ignorado(self):
        for v in ("-1", "", "99", "abc"):
            self.assertEqual(
                domains.rotulo_escolaridade(v, self.niveis),
                domains.ROTULO_ESCOLARIDADE,
                v,
            )


class TestSubclasse(unittest.TestCase):
    def setUp(self):
        self.subs = domains.load_subclasses()

    def test_referencia(self):
        desc = self.subs.get("2342702")
        self.assertIsNotNone(desc)
        self.assertTrue("Cer" in desc and "Barro" in desc, desc)

    def test_quantidade_razoavel(self):
        self.assertGreater(len(self.subs), 1000)


class TestMunicipio(unittest.TestCase):
    def setUp(self):
        self.muns = domains.load_municipios()

    def test_referencia(self):
        self.assertEqual(self.muns.get("330100"), "Rj-Campos dos Goytacazes")


if __name__ == "__main__":
    unittest.main()
