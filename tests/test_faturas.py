"""
Unit tests for the credit-card invoice assignment logic (calcular_fechamento
and obter_ou_criar_fatura helpers extracted from app.py) and the
/api/faturas/recalcular endpoint.

Rules under test
----------------
- Closing date (fechamento) = vencimento_day - dias_antes_fechamento.
  Python date - timedelta handles month-boundary roll-back automatically
  (e.g. date(2026, 3, 10) - timedelta(10) → date(2026, 2, 28)).
- Closing day is EXCLUSIVE: a purchase made ON the closing date belongs to
  the NEXT invoice.
"""

import sys
import os
import json
import tempfile
import unittest
from datetime import date, timedelta
from calendar import monthrange

# ---------------------------------------------------------------------------
# Standalone copies of the helpers (no Flask/DB dependency)
# ---------------------------------------------------------------------------

def calcular_fechamento(dia_vencimento: int, dias_antes: int, ano: int, mes: int) -> date:
    """Return the closing date for a given billing month."""
    vencimento = date(ano, mes, min(dia_vencimento, monthrange(ano, mes)[1]))
    return vencimento - timedelta(days=dias_antes)


def _fatura_vencimento(dia_venc: int, dias_antes: int, data_compra: date) -> date:
    """Return the *vencimento* date of the invoice a purchase belongs to.

    Mirrors the production logic in obter_ou_criar_fatura without any
    Flask / SQLite dependency.
    """
    year = data_compra.year
    month = data_compra.month

    for delta in range(0, 13):
        m = month + delta
        y = year + (m - 1) // 12
        m = ((m - 1) % 12) + 1

        fechamento = calcular_fechamento(dia_venc, dias_antes, y, m)
        dia_venc_safe = min(dia_venc, monthrange(y, m)[1])
        vencimento = date(y, m, dia_venc_safe)

        # Closing day is exclusive: purchase must be strictly before fechamento.
        if data_compra < fechamento:
            return vencimento

    raise ValueError("Não foi possível determinar a fatura para esta data")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCalcularFechamento(unittest.TestCase):
    """Tests for the closing-date calculation helper."""

    def test_normal_case_venc10_dias7(self):
        # 10 - 7 = 3 → closing on the 3rd
        self.assertEqual(calcular_fechamento(10, 7, 2026, 3), date(2026, 3, 3))

    def test_rollback_to_previous_month(self):
        # venc=10, dias_antes=10 → day 0 rolls back to last day of Feb 2026
        self.assertEqual(calcular_fechamento(10, 10, 2026, 3), date(2026, 2, 28))

    def test_rollback_leap_year(self):
        # venc=10, dias_antes=10, march 2024 (leap year) → last day of Feb = 29
        self.assertEqual(calcular_fechamento(10, 10, 2024, 3), date(2024, 2, 29))

    def test_rollback_nonleap_february(self):
        # venc=10, dias_antes=10, march 2023 (non-leap) → 28 Feb
        self.assertEqual(calcular_fechamento(10, 10, 2023, 3), date(2023, 2, 28))


class TestFaturaAssignment(unittest.TestCase):
    """Integration-style tests for invoice assignment with exclusive closing."""

    # ------------------------------------------------------------------
    # Scenario A: venc=10, dias_antes=10 – non-leap year (2026)
    # fechamento of March 2026 = 28/02/2026 (exclusive)
    # ------------------------------------------------------------------

    def test_compra_dia_antes_fechamento_2026(self):
        """27/02/2026 is one day before closing → belongs to March fatura."""
        vencimento = _fatura_vencimento(10, 10, date(2026, 2, 27))
        self.assertEqual(vencimento, date(2026, 3, 10))

    def test_compra_no_dia_fechamento_2026(self):
        """28/02/2026 IS the closing day (exclusive) → belongs to NEXT (April) fatura."""
        vencimento = _fatura_vencimento(10, 10, date(2026, 2, 28))
        self.assertEqual(vencimento, date(2026, 4, 10))

    # ------------------------------------------------------------------
    # Scenario B: venc=10, dias_antes=10 – leap year (2024)
    # fechamento of March 2024 = 29/02/2024 (exclusive, leap day)
    # ------------------------------------------------------------------

    def test_compra_dia_antes_fechamento_2024_leap(self):
        """28/02/2024 is one day before leap closing → belongs to March fatura."""
        vencimento = _fatura_vencimento(10, 10, date(2024, 2, 28))
        self.assertEqual(vencimento, date(2024, 3, 10))

    def test_compra_no_dia_fechamento_2024_leap(self):
        """29/02/2024 IS the closing day (leap, exclusive) → belongs to April fatura."""
        vencimento = _fatura_vencimento(10, 10, date(2024, 2, 29))
        self.assertEqual(vencimento, date(2024, 4, 10))

    # ------------------------------------------------------------------
    # Scenario C: venc=10, dias_antes=7 – normal case (no regression)
    # fechamento = 10 - 7 = 3rd of the month
    # ------------------------------------------------------------------

    def test_normal_compra_before_fechamento(self):
        """2/03/2026 is before closing (3/03) → March fatura."""
        vencimento = _fatura_vencimento(10, 7, date(2026, 3, 2))
        self.assertEqual(vencimento, date(2026, 3, 10))

    def test_normal_compra_on_fechamento(self):
        """3/03/2026 IS closing day (exclusive) → April fatura."""
        vencimento = _fatura_vencimento(10, 7, date(2026, 3, 3))
        self.assertEqual(vencimento, date(2026, 4, 10))

    def test_normal_compra_after_fechamento(self):
        """5/03/2026 is after closing (3/03) → April fatura."""
        vencimento = _fatura_vencimento(10, 7, date(2026, 3, 5))
        self.assertEqual(vencimento, date(2026, 4, 10))

    # ------------------------------------------------------------------
    # Scenario D: month-end edge cases
    # ------------------------------------------------------------------

    def test_last_day_of_january_is_closing_goes_to_next(self):
        """venc=10, dias_antes=10: closing of Feb fatura = 31/01.
        Purchase on 31/01 (exclusive) → March fatura."""
        vencimento = _fatura_vencimento(10, 10, date(2026, 1, 31))
        self.assertEqual(vencimento, date(2026, 3, 10))

    def test_day_before_january_closing_stays_in_feb(self):
        """30/01/2026 is before closing (31/01) → February fatura."""
        vencimento = _fatura_vencimento(10, 10, date(2026, 1, 30))
        self.assertEqual(vencimento, date(2026, 2, 10))


# ---------------------------------------------------------------------------
# Integration tests for the /api/faturas/recalcular endpoint
# ---------------------------------------------------------------------------

# Add the repo root to sys.path so we can import app directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import app as flask_app  # noqa: E402


class TestRecalcularEndpoint(unittest.TestCase):
    """Tests for POST /api/faturas/recalcular."""

    def setUp(self):
        self.db_fd, db_path = tempfile.mkstemp(suffix='.db')
        flask_app.app.config['DATABASE'] = db_path
        flask_app.app.config['TESTING'] = True
        with flask_app.app.app_context():
            flask_app.init_db()
            # Insert a card: vencimento=10, dias_antes=10
            flask_app.execute_db(
                "INSERT INTO cartoes (nome, dia_vencimento, dias_antes_fechamento)"
                " VALUES ('Teste', 10, 10)"
            )
            self.cartao_id = flask_app.query_db(
                "SELECT id FROM cartoes WHERE nome='Teste'", one=True
            )['id']

            # Insert a category to satisfy FK
            flask_app.execute_db(
                "INSERT INTO categorias (nome, tipo) VALUES ('Cat', 'despesa')"
            )
            self.cat_id = flask_app.query_db(
                "SELECT id FROM categorias WHERE nome='Cat'", one=True
            )['id']

            # Insert a transaction on 28/02/2026 (the closing day → should be in April)
            # but intentionally assign it to the March fatura (wrong)
            march_fatura_id = flask_app.obter_ou_criar_fatura(
                self.cartao_id, date(2026, 2, 27)
            )
            flask_app.execute_db(
                """INSERT INTO transacoes
                   (tipo, valor, data, descricao, status, metodo_pagamento,
                    cartao_id, fatura_id, categoria_id)
                   VALUES ('despesa', 47.0, '2026-02-28', 'Pamonha', 'realizado',
                           'cartao', ?, ?, ?)""",
                (self.cartao_id, march_fatura_id, self.cat_id)
            )
            self.transacao_id = flask_app.query_db(
                "SELECT id FROM transacoes WHERE descricao='Pamonha'", one=True
            )['id']
            self.march_fatura_id = march_fatura_id

        self.client = flask_app.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(flask_app.app.config['DATABASE'])

    def test_missing_cartao_id_returns_400(self):
        resp = self.client.post(
            '/api/faturas/recalcular',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_cartao_id_returns_404(self):
        resp = self.client.post(
            '/api/faturas/recalcular',
            data=json.dumps({'cartao_id': 9999, 'months_back': 6}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 404)

    def test_recalcular_moves_transaction_to_correct_fatura(self):
        """28/02/2026 is closing day (exclusive) → must be in April, not March."""
        resp = self.client.post(
            '/api/faturas/recalcular',
            data=json.dumps({
                'cartao_id': self.cartao_id,
                'data_inicio': '2026-01-01',
                'data_fim': '2026-12-31',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body['total_analisado'], 1)
        self.assertEqual(body['total_movido'], 1)
        self.assertEqual(len(body['erros']), 0)

        with flask_app.app.app_context():
            t = flask_app.query_db(
                "SELECT fatura_id FROM transacoes WHERE id=?",
                (self.transacao_id,), one=True
            )
            nova_fatura = flask_app.query_db(
                "SELECT data_vencimento FROM faturas WHERE id=?",
                (t['fatura_id'],), one=True
            )
            # Should now be in the April fatura (vencimento 2026-04-10)
            self.assertEqual(nova_fatura['data_vencimento'], '2026-04-10')

    def test_recalcular_is_idempotent(self):
        """Running recalculate twice should move 1 transaction on first run, 0 on second."""
        payload = json.dumps({
            'cartao_id': self.cartao_id,
            'data_inicio': '2026-01-01',
            'data_fim': '2026-12-31',
        })
        resp1 = self.client.post(
            '/api/faturas/recalcular', data=payload, content_type='application/json'
        )
        body1 = json.loads(resp1.data)
        self.assertEqual(body1['total_movido'], 1)

        resp2 = self.client.post(
            '/api/faturas/recalcular', data=payload, content_type='application/json'
        )
        body2 = json.loads(resp2.data)
        self.assertEqual(body2['total_movido'], 0)

    def test_recalcular_with_months_back(self):
        """months_back parameter should work without explicit dates."""
        # Transaction is in 2026-02-28; use months_back large enough to cover it
        resp = self.client.post(
            '/api/faturas/recalcular',
            data=json.dumps({'cartao_id': self.cartao_id, 'months_back': 24}),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, (200,))
        body = json.loads(resp.data)
        self.assertIn('total_analisado', body)
        self.assertIn('total_movido', body)
        self.assertIn('erros', body)

    def test_recalcular_no_transactions_returns_zero(self):
        """Empty date range should return 0 analysed."""
        resp = self.client.post(
            '/api/faturas/recalcular',
            data=json.dumps({
                'cartao_id': self.cartao_id,
                'data_inicio': '2020-01-01',
                'data_fim': '2020-01-31',
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body['total_analisado'], 0)
        self.assertEqual(body['total_movido'], 0)


if __name__ == "__main__":
    unittest.main()
