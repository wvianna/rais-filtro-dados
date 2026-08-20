"""Testes do esquema de colunas e detecção de separador."""

import unittest

from rais import config, schema

from support import PARTIAL


class TestNormalizacao(unittest.TestCase):
    def test_remove_acentos_caixa_separadores(self):
        self.assertEqual(schema.normalize_token("Município - Código"), "municipio codigo")
        self.assertEqual(schema.normalize_token("MUNICIPIO"), "municipio")
        self.assertEqual(schema.normalize_token("CNAE 2.0 Subclasse - Codigo"), "cnae 20 subclasse codigo")
        self.assertEqual(schema.normalize_token("Ind Vínculo Ativo 31/12 - Código"), "ind vinculo ativo 3112 codigo")

    def test_resolve_logical(self):
        self.assertEqual(schema.resolve_logical("Município - Código"), "municipio")
        self.assertEqual(schema.resolve_logical("MUNICIPIO"), "municipio")
        self.assertEqual(schema.resolve_logical("CNAE 2.0 Subclasse - Codigo"), "subclasse_cnae20")
        self.assertEqual(schema.resolve_logical("Escolaridade Após 2005 - Código"), "escolaridade")
        self.assertEqual(schema.resolve_logical("Identificad"), "identificador_estabelecimento")
        self.assertIsNone(schema.resolve_logical("coluna totalmente desconhecida"))


class TestDetecaoSeparador(unittest.TestCase):
    def test_delimitador_real_e_virgula(self):
        # O layout cita ";", mas os arquivos fornecidos usam ",".
        self.assertEqual(schema.detect_delimiter(PARTIAL), ",")


class TestDetectSchema(unittest.TestCase):
    def setUp(self):
        self.sch = schema.detect_schema(PARTIAL)

    def test_colunas(self):
        self.assertEqual(self.sch.columns, 62)
        self.assertEqual(self.sch.delimiter, ",")
        self.assertEqual(self.sch.encoding, config.DEFAULT_DATA_ENCODING)

    def test_campos_presentes(self):
        for field in ("municipio", "subclasse_cnae20", "escolaridade", "tipo_estabelecimento"):
            self.assertTrue(self.sch.present(field), field)

    def test_identificador_ausente(self):
        self.assertIn("identificador_estabelecimento", self.sch.missing)


if __name__ == "__main__":
    unittest.main()
