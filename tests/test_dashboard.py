"""
Integration tests for GET /api/dashboard – credit-card expense aggregation by invoice month.

Key behaviour under test (option 2):
  - Conta transactions are attributed to the month by transacoes.data.
  - Cartao transactions are attributed to the month by faturas.mes_referencia.

Reference scenario (mirrors the problem statement):
  - Purchase on 2026-02-28 with cartao that has dia_vencimento=10, dias_antes=10.
  - After recalculation the transaction lands in fatura with mes_referencia='2026-04'.
  - GET /api/dashboard?mes=2026-04 must include the purchase in despesas_realizadas.
  - GET /api/dashboard?mes=2026-02 must NOT include it (it belongs to April fatura).
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import app as flask_app  # noqa: E402


class TestDashboardCardByInvoiceMonth(unittest.TestCase):
    """Dashboard aggregates card expenses by faturas.mes_referencia."""

    def setUp(self):
        self.db_fd, db_path = tempfile.mkstemp(suffix='.db')
        flask_app.app.config['DATABASE'] = db_path
        flask_app.app.config['TESTING'] = True

        with flask_app.app.app_context():
            flask_app.init_db()

            # Card: vencimento=10, dias_antes=10
            # → fechamento of April 2026 = 10-10 = 28/02/2026 (exclusive)
            # → purchase on 28/02/2026 belongs to April fatura
            flask_app.execute_db(
                "INSERT INTO cartoes (nome, dia_vencimento, dias_antes_fechamento)"
                " VALUES ('Nubank', 10, 10)"
            )
            self.cartao_id = flask_app.query_db(
                "SELECT id FROM cartoes WHERE nome='Nubank'", one=True
            )['id']

            # Account (for conta-by-date transactions)
            flask_app.execute_db(
                "INSERT INTO contas (nome, saldo_inicial) VALUES ('Corrente', 1000)"
            )
            self.conta_id = flask_app.query_db(
                "SELECT id FROM contas WHERE nome='Corrente'", one=True
            )['id']

            # Category
            flask_app.execute_db(
                "INSERT INTO categorias (nome, tipo) VALUES ('Alimentacao', 'despesa')"
            )
            self.cat_id = flask_app.query_db(
                "SELECT id FROM categorias WHERE nome='Alimentacao'", one=True
            )['id']

            # Obtain (or create) the April 2026 fatura for this card.
            # obter_ou_criar_fatura(cartao_id, data_compra) – passing 28/02/2026 which is
            # the closing day (exclusive), so it belongs to April.
            self.abril_fatura_id = flask_app.obter_ou_criar_fatura(
                self.cartao_id, date(2026, 2, 28)
            )
            # Verify the fatura is indeed mes_referencia='2026-04'
            fatura = flask_app.query_db(
                "SELECT mes_referencia FROM faturas WHERE id=?",
                (self.abril_fatura_id,), one=True
            )
            assert fatura['mes_referencia'] == '2026-04', (
                f"Expected fatura mes_referencia='2026-04', got '{fatura['mes_referencia']}'"
            )

            # Card transaction: purchase on 28/02/2026, fatura = April 2026
            flask_app.execute_db(
                "INSERT INTO transacoes"
                " (tipo, valor, data, descricao, status, metodo_pagamento,"
                "  cartao_id, fatura_id, categoria_id)"
                " VALUES ('despesa', 150.0, '2026-02-28', 'Supermercado', 'realizado',"
                "         'cartao', ?, ?, ?)",
                (self.cartao_id, self.abril_fatura_id, self.cat_id)
            )

            # Conta transaction: expense on 05/04/2026 (same month, by date)
            flask_app.execute_db(
                "INSERT INTO transacoes"
                " (tipo, valor, data, descricao, status, metodo_pagamento,"
                "  conta_id, categoria_id)"
                " VALUES ('despesa', 80.0, '2026-04-05', 'Luz', 'realizado',"
                "         'conta', ?, ?)",
                (self.conta_id, self.cat_id)
            )

        self.client = flask_app.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(flask_app.app.config['DATABASE'])

    # ------------------------------------------------------------------
    # Core scenario: card purchase on 28/02 in April fatura
    # ------------------------------------------------------------------

    def test_abril_despesas_include_cartao_by_fatura(self):
        """April dashboard must include the card purchase (150) via fatura month."""
        resp = self.client.get('/api/dashboard?mes=2026-04')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        # 150 (card, fatura Apr) + 80 (conta, date Apr) = 230
        self.assertAlmostEqual(data['despesas_realizadas'], 230.0)

    def test_fevereiro_despesas_exclude_cartao_in_april_fatura(self):
        """February dashboard must NOT include the purchase – it belongs to April fatura."""
        resp = self.client.get('/api/dashboard?mes=2026-02')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        # No conta expense in Feb, and the card purchase belongs to April, not Feb
        self.assertAlmostEqual(data['despesas_realizadas'], 0.0)

    def test_abril_despesas_por_categoria_include_cartao(self):
        """Expenses by category for April must include the card purchase."""
        resp = self.client.get('/api/dashboard?mes=2026-04')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        cats = {c['nome']: c['total'] for c in data['despesas_por_categoria']}
        self.assertIn('Alimentacao', cats)
        self.assertAlmostEqual(cats['Alimentacao'], 230.0)

    def test_abril_barras_mensais_include_cartao(self):
        """Monthly bars for April must reflect the card purchase in April's bar."""
        resp = self.client.get('/api/dashboard?mes=2026-04')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        bars = {b['label']: b['despesas'] for b in data['barras_mensais']}
        self.assertIn('04/2026', bars)
        self.assertAlmostEqual(bars['04/2026'], 230.0)

    def test_abril_ultimas_transacoes_include_cartao(self):
        """Latest transactions for April must include the card purchase (option B)."""
        resp = self.client.get('/api/dashboard?mes=2026-04')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        descricoes = [t['descricao'] for t in data['ultimas_transacoes']]
        self.assertIn('Supermercado', descricoes)
        self.assertIn('Luz', descricoes)

    # ------------------------------------------------------------------
    # Conta-by-date is unaffected
    # ------------------------------------------------------------------

    def test_conta_transaction_in_correct_month(self):
        """Conta expense on 05/04/2026 appears in April but not in March."""
        resp_apr = self.client.get('/api/dashboard?mes=2026-04')
        resp_mar = self.client.get('/api/dashboard?mes=2026-03')
        data_apr = json.loads(resp_apr.data)
        data_mar = json.loads(resp_mar.data)
        # March should have 0 conta expenses (the 80 is in April)
        self.assertAlmostEqual(data_mar['despesas_realizadas'], 0.0)
        # April should include 80 from conta + 150 from card = 230
        self.assertAlmostEqual(data_apr['despesas_realizadas'], 230.0)


class TestDashboardCardNoFaturaFallback(unittest.TestCase):
    """Card transaction without fatura_id falls back to transacoes.data."""

    def setUp(self):
        self.db_fd, db_path = tempfile.mkstemp(suffix='.db')
        flask_app.app.config['DATABASE'] = db_path
        flask_app.app.config['TESTING'] = True

        with flask_app.app.app_context():
            flask_app.init_db()
            flask_app.execute_db(
                "INSERT INTO cartoes (nome, dia_vencimento, dias_antes_fechamento)"
                " VALUES ('Visa', 15, 7)"
            )
            self.cartao_id = flask_app.query_db(
                "SELECT id FROM cartoes WHERE nome='Visa'", one=True
            )['id']
            flask_app.execute_db(
                "INSERT INTO categorias (nome, tipo) VALUES ('Outros', 'despesa')"
            )
            cat_id = flask_app.query_db(
                "SELECT id FROM categorias WHERE nome='Outros'", one=True
            )['id']
            # Card transaction without fatura_id
            flask_app.execute_db(
                "INSERT INTO transacoes"
                " (tipo, valor, data, descricao, status, metodo_pagamento, cartao_id, categoria_id)"
                " VALUES ('despesa', 55.0, '2026-03-10', 'Farmácia', 'realizado',"
                "         'cartao', ?, ?)",
                (self.cartao_id, cat_id)
            )

        self.client = flask_app.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(flask_app.app.config['DATABASE'])

    def test_card_no_fatura_falls_back_to_date(self):
        """Card transaction without fatura uses transacoes.data as fallback."""
        resp = self.client.get('/api/dashboard?mes=2026-03')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertAlmostEqual(data['despesas_realizadas'], 55.0)

    def test_card_no_fatura_absent_in_other_month(self):
        """The fallback transaction does not bleed into other months."""
        resp = self.client.get('/api/dashboard?mes=2026-04')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertAlmostEqual(data['despesas_realizadas'], 0.0)


if __name__ == '__main__':
    unittest.main()
