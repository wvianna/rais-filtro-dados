"""Testes do leitor streaming."""

import unittest

from rais import reader, schema

from support import PARTIAL


class TestStreamingReader(unittest.TestCase):
    def test_contagem_linhas(self):
        self.assertEqual(reader.count_rows(PARTIAL), 299)

    def test_iter_rows(self):
        n = 0
        first = None
        for i, row in reader.iter_rows(PARTIAL):
            if first is None:
                first = (i, row)
            n += 1
        self.assertEqual(n, 299)
        # primeira linha de dados é índice 0
        self.assertEqual(first[0], 0)

    def test_iter_rows_with_offsets(self):
        offsets = []
        n = 0
        for _i, off, _row in reader.iter_rows_with_offsets(PARTIAL):
            offsets.append(off)
            n += 1
        self.assertEqual(n, 299)
        # offsets devem ser estritamente crescentes
        self.assertEqual(offsets, sorted(offsets))
        self.assertGreater(len(set(offsets)), 250)

    def test_read_rows_at_offsets_consistencia(self):
        sch = schema.detect_schema(PARTIAL)
        todos = list(reader.iter_rows_with_offsets(PARTIAL, delimiter=sch.delimiter, expected_columns=sch.columns))
        amostra_offsets = [off for _i, off, _r in todos[:5]]
        relidas = list(reader.read_rows_at_offsets(PARTIAL, amostra_offsets, delimiter=sch.delimiter))
        originais = [r for _i, _off, r in todos[:5]]
        self.assertEqual(relidas, originais)


if __name__ == "__main__":
    unittest.main()
