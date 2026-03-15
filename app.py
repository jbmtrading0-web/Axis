"""
Axis – Sistema de Controle Financeiro Pessoal
Flask + SQLite, funciona 100% offline em http://localhost:5000
"""

import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from calendar import monthrange

from flask import (
    Flask, g, jsonify, redirect, render_template, request, url_for, abort
)

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'database.db')

# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur


def parse_money(v, default=0.0):
    """Parse monetary values accepting None, empty string, and pt-BR comma notation.

    Examples:
        parse_money('')         -> 0.0
        parse_money(None)       -> 0.0
        parse_money('10,50')    -> 10.5
        parse_money('1.234,56') -> 1234.56
        parse_money('10.5')     -> 10.5
        parse_money('1,234.56') -> 1234.56
    """
    if v is None:
        return float(default)
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == '':
        return float(default)
    has_dot = '.' in s
    has_comma = ',' in s
    if has_dot and has_comma:
        # Determine format by which separator appears last
        if s.rindex('.') > s.rindex(','):
            # en-US: "1,234.56" — remove commas
            s = s.replace(',', '')
        else:
            # pt-BR: "1.234,56" — remove dots, swap comma to dot
            s = s.replace('.', '').replace(',', '.')
    elif has_comma:
        # pt-BR decimal only: "10,50" -> "10.50"
        s = s.replace(',', '.')
    # elif has_dot or neither: already valid float string ("10.5" or "10")
    return float(s)


# ─────────────────────────────────────────────
# Credit card / invoice helpers
# ─────────────────────────────────────────────

def calcular_fechamento(dia_vencimento: int, dias_antes: int, ano: int, mes: int) -> date:
    """Return the closing date for a given billing month."""
    vencimento = date(ano, mes, min(dia_vencimento, monthrange(ano, mes)[1]))
    return vencimento - timedelta(days=dias_antes)


def obter_ou_criar_fatura(cartao_id: int, data_compra: date) -> int:
    """Given a card and purchase date, return the fatura_id it belongs to.

    Logic:
    - For each month cycle, the invoice period is (prev_fechamento + 1) to fechamento.
    - If purchase_date <= fechamento of month M  →  belongs to fatura of month M.
    - We look at the current month and adjacent months to find the right cycle.
    """
    cartao = query_db("SELECT * FROM cartoes WHERE id=?", (cartao_id,), one=True)
    if not cartao:
        raise ValueError("Cartão não encontrado")

    dia_venc = cartao['dia_vencimento']
    dias_antes = cartao['dias_antes_fechamento']

    # Try current, next, and previous months to find the right invoice cycle
    year = data_compra.year
    month = data_compra.month

    for delta in range(0, 13):
        # Try delta months ahead
        m = month + delta
        y = year + (m - 1) // 12
        m = ((m - 1) % 12) + 1

        fechamento = calcular_fechamento(dia_venc, dias_antes, y, m)
        dia_venc_safe = min(dia_venc, monthrange(y, m)[1])
        vencimento = date(y, m, dia_venc_safe)

        # Previous closing date (the start of this cycle)
        pm = m - 1 if m > 1 else 12
        py = y if m > 1 else y - 1
        prev_fechamento = calcular_fechamento(dia_venc, dias_antes, py, pm)

        # Does the purchase fall in this cycle?
        inicio_ciclo = prev_fechamento + timedelta(days=1)
        if inicio_ciclo <= data_compra <= fechamento:
            mes_ref = f"{y:04d}-{m:02d}"
            return _garantir_fatura(cartao_id, mes_ref, fechamento, vencimento)

    raise ValueError("Não foi possível determinar a fatura para esta data")


def _garantir_fatura(cartao_id: int, mes_ref: str, fechamento: date, vencimento: date) -> int:
    existing = query_db(
        "SELECT id FROM faturas WHERE cartao_id=? AND mes_referencia=?",
        (cartao_id, mes_ref), one=True
    )
    if existing:
        return existing['id']
    cur = execute_db(
        "INSERT INTO faturas (cartao_id, mes_referencia, data_fechamento, data_vencimento) VALUES (?,?,?,?)",
        (cartao_id, mes_ref, fechamento.isoformat(), vencimento.isoformat())
    )
    return cur.lastrowid


def recalcular_total_fatura(fatura_id: int):
    row = query_db(
        "SELECT COALESCE(SUM(valor),0) as total FROM transacoes WHERE fatura_id=?",
        (fatura_id,), one=True
    )
    execute_db("UPDATE faturas SET total=? WHERE id=?", (row['total'], fatura_id))


# ─────────────────────────────────────────────
# Application initialization
# ─────────────────────────────────────────────

def _ensure_db():
    with app.app_context():
        if not os.path.exists(app.config['DATABASE']):
            init_db()
        else:
            # ensure schema is up to date (idempotent)
            init_db()


# ─────────────────────────────────────────────
# Page routes
# ─────────────────────────────────────────────

@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/transacoes')
def transacoes():
    return render_template('transacoes.html')


@app.route('/categorias')
def categorias():
    return render_template('categorias.html')


@app.route('/contas')
def contas():
    return render_template('contas.html')


@app.route('/cartoes')
def cartoes():
    return render_template('cartoes.html')


@app.route('/faturas')
def faturas():
    return render_template('faturas.html')


@app.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')


# ─────────────────────────────────────────────
# API – Dashboard
# ─────────────────────────────────────────────

@app.route('/api/dashboard')
def api_dashboard():
    mes = request.args.get('mes', date.today().strftime('%Y-%m'))
    ano, m = map(int, mes.split('-'))
    inicio = f"{ano:04d}-{m:02d}-01"
    ultimo_dia = monthrange(ano, m)[1]
    fim = f"{ano:04d}-{m:02d}-{ultimo_dia:02d}"

    # Summary
    receitas_realizadas = query_db(
        "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE tipo='receita' AND status='realizado' AND data BETWEEN ? AND ?",
        (inicio, fim), one=True
    )['v']
    despesas_realizadas = query_db(
        "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE tipo='despesa' AND status='realizado' AND data BETWEEN ? AND ?",
        (inicio, fim), one=True
    )['v']
    receitas_previstas = query_db(
        "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE tipo='receita' AND data BETWEEN ? AND ?",
        (inicio, fim), one=True
    )['v']
    despesas_previstas = query_db(
        "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE tipo='despesa' AND data BETWEEN ? AND ?",
        (inicio, fim), one=True
    )['v']

    # Expenses by category (realized)
    desp_cat = query_db(
        """SELECT c.nome, c.cor, COALESCE(SUM(t.valor),0) as total
           FROM transacoes t
           LEFT JOIN categorias c ON t.categoria_id = c.id
           WHERE t.tipo='despesa' AND t.status='realizado' AND t.data BETWEEN ? AND ?
           GROUP BY t.categoria_id ORDER BY total DESC LIMIT 10""",
        (inicio, fim)
    )

    # Monthly bars – last 6 months
    bars = []
    for i in range(5, -1, -1):
        d = date(ano, m, 1) - timedelta(days=i * 30)
        d = d.replace(day=1)
        mi = f"{d.year:04d}-{d.month:02d}-01"
        uf = monthrange(d.year, d.month)[1]
        mf = f"{d.year:04d}-{d.month:02d}-{uf:02d}"
        r = query_db(
            "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE tipo='receita' AND status='realizado' AND data BETWEEN ? AND ?",
            (mi, mf), one=True
        )['v']
        d2 = query_db(
            "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE tipo='despesa' AND status='realizado' AND data BETWEEN ? AND ?",
            (mi, mf), one=True
        )['v']
        bars.append({'label': f"{d.month:02d}/{d.year}", 'receitas': r, 'despesas': d2})

    # Latest transactions
    ultimas = query_db(
        """SELECT t.*, c.nome as categoria_nome, c.cor as categoria_cor,
                  ct.nome as conta_nome, ca.nome as cartao_nome
           FROM transacoes t
           LEFT JOIN categorias c ON t.categoria_id=c.id
           LEFT JOIN contas ct ON t.conta_id=ct.id
           LEFT JOIN cartoes ca ON t.cartao_id=ca.id
           WHERE t.data BETWEEN ? AND ?
           ORDER BY t.data DESC, t.id DESC LIMIT 10""",
        (inicio, fim)
    )

    return jsonify({
        'mes': mes,
        'receitas_realizadas': receitas_realizadas,
        'despesas_realizadas': despesas_realizadas,
        'saldo_disponivel': receitas_realizadas - despesas_realizadas,
        'saldo_previsto': receitas_previstas - despesas_previstas,
        'receitas_previstas': receitas_previstas,
        'despesas_previstas': despesas_previstas,
        'despesas_por_categoria': [
            {'nome': r['nome'] or 'Sem categoria', 'cor': r['cor'] or '#6c757d', 'total': r['total']}
            for r in desp_cat
        ],
        'barras_mensais': bars,
        'ultimas_transacoes': [dict(r) for r in ultimas],
    })


# ─────────────────────────────────────────────
# API – Transações
# ─────────────────────────────────────────────

@app.route('/api/transacoes', methods=['GET'])
def api_transacoes_list():
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    tipo = request.args.get('tipo')
    status = request.args.get('status')
    categoria_id = request.args.get('categoria_id')
    conta_id = request.args.get('conta_id')
    cartao_id = request.args.get('cartao_id')

    sql = """SELECT t.*, c.nome as categoria_nome, c.cor as categoria_cor,
                    sc.nome as subcategoria_nome,
                    ct.nome as conta_nome, ca.nome as cartao_nome
             FROM transacoes t
             LEFT JOIN categorias c ON t.categoria_id=c.id
             LEFT JOIN subcategorias sc ON t.subcategoria_id=sc.id
             LEFT JOIN contas ct ON t.conta_id=ct.id
             LEFT JOIN cartoes ca ON t.cartao_id=ca.id
             WHERE 1=1"""
    params = []

    if inicio:
        sql += " AND t.data >= ?"
        params.append(inicio)
    if fim:
        sql += " AND t.data <= ?"
        params.append(fim)
    if tipo:
        sql += " AND t.tipo = ?"
        params.append(tipo)
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    if categoria_id:
        sql += " AND t.categoria_id = ?"
        params.append(categoria_id)
    if conta_id:
        sql += " AND t.conta_id = ?"
        params.append(conta_id)
    if cartao_id:
        sql += " AND t.cartao_id = ?"
        params.append(cartao_id)

    sql += " ORDER BY t.data DESC, t.id DESC"
    rows = query_db(sql, params)
    return jsonify([dict(r) for r in rows])


@app.route('/api/transacoes', methods=['POST'])
def api_transacoes_criar():
    data = request.get_json(force=True)

    tipo = data.get('tipo')
    valor = float(data.get('valor', 0))
    dt = data.get('data')
    descricao = data.get('descricao', '').strip()
    status = data.get('status', 'previsto')
    categoria_id = data.get('categoria_id') or None
    subcategoria_id = data.get('subcategoria_id') or None
    metodo = data.get('metodo_pagamento', 'conta')
    conta_id = data.get('conta_id') or None
    cartao_id = data.get('cartao_id') or None
    observacao = data.get('observacao', '')
    recorrente = int(data.get('recorrente', 0))
    total_parcelas = data.get('total_parcelas')
    total_parcelas = int(total_parcelas) if total_parcelas else None
    meses_recorrencia = data.get('meses_recorrencia')
    meses_recorrencia = int(meses_recorrencia) if meses_recorrencia else None

    if not tipo or not valor or not dt or not descricao:
        abort(400, "Campos obrigatórios: tipo, valor, data, descricao")

    data_obj = date.fromisoformat(dt)
    ids_criados = []

    def _inserir(data_t: date, parcela_atual=None, grupo_rec=None, fatura_id=None):
        c_id = cartao_id
        f_id = fatura_id
        if metodo == 'cartao' and c_id:
            if f_id is None:
                f_id = obter_ou_criar_fatura(c_id, data_t)
        cur = execute_db(
            """INSERT INTO transacoes
               (tipo, valor, data, descricao, status, categoria_id, subcategoria_id,
                metodo_pagamento, conta_id, cartao_id, fatura_id, observacao,
                recorrente, parcela_atual, total_parcelas, grupo_recorrencia)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tipo, valor, data_t.isoformat(), descricao, status,
             categoria_id, subcategoria_id, metodo, conta_id if metodo == 'conta' else None,
             c_id if metodo == 'cartao' else None, f_id,
             observacao, recorrente, parcela_atual, total_parcelas, grupo_rec)
        )
        t_id = cur.lastrowid
        if f_id:
            recalcular_total_fatura(f_id)
        return t_id

    if total_parcelas and total_parcelas > 1:
        grupo = str(uuid.uuid4())
        for i in range(total_parcelas):
            m = data_obj.month + i
            y = data_obj.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            last = monthrange(y, m)[1]
            d = date(y, m, min(data_obj.day, last))
            ids_criados.append(_inserir(d, i + 1, grupo))
    elif recorrente and meses_recorrencia and meses_recorrencia > 1:
        grupo = str(uuid.uuid4())
        for i in range(meses_recorrencia):
            m = data_obj.month + i
            y = data_obj.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            last = monthrange(y, m)[1]
            d = date(y, m, min(data_obj.day, last))
            ids_criados.append(_inserir(d, None, grupo))
    else:
        ids_criados.append(_inserir(data_obj))

    return jsonify({'ids': ids_criados}), 201


@app.route('/api/transacoes/<int:tid>', methods=['GET'])
def api_transacoes_get(tid):
    row = query_db("SELECT * FROM transacoes WHERE id=?", (tid,), one=True)
    if not row:
        abort(404)
    return jsonify(dict(row))


@app.route('/api/transacoes/<int:tid>', methods=['PUT'])
def api_transacoes_update(tid):
    existing = query_db("SELECT * FROM transacoes WHERE id=?", (tid,), one=True)
    if not existing:
        abort(404)
    data = request.get_json(force=True)

    tipo = data.get('tipo', existing['tipo'])
    valor = float(data.get('valor', existing['valor']))
    dt = data.get('data', existing['data'])
    descricao = data.get('descricao', existing['descricao'])
    status = data.get('status', existing['status'])
    categoria_id = data.get('categoria_id', existing['categoria_id'])
    subcategoria_id = data.get('subcategoria_id', existing['subcategoria_id'])
    metodo = data.get('metodo_pagamento', existing['metodo_pagamento'])
    conta_id = data.get('conta_id', existing['conta_id'])
    cartao_id = data.get('cartao_id', existing['cartao_id'])
    observacao = data.get('observacao', existing['observacao'])
    fatura_id = existing['fatura_id']

    # Recalculate invoice if card/date changed
    if metodo == 'cartao' and cartao_id:
        data_obj = date.fromisoformat(dt)
        fatura_id = obter_ou_criar_fatura(int(cartao_id), data_obj)
    else:
        fatura_id = None

    execute_db(
        """UPDATE transacoes SET tipo=?, valor=?, data=?, descricao=?, status=?,
           categoria_id=?, subcategoria_id=?, metodo_pagamento=?,
           conta_id=?, cartao_id=?, fatura_id=?, observacao=?
           WHERE id=?""",
        (tipo, valor, dt, descricao, status, categoria_id or None, subcategoria_id or None,
         metodo, conta_id if metodo == 'conta' else None,
         cartao_id if metodo == 'cartao' else None,
         fatura_id, observacao, tid)
    )

    # Recalculate old and new invoices
    if existing['fatura_id']:
        recalcular_total_fatura(existing['fatura_id'])
    if fatura_id:
        recalcular_total_fatura(fatura_id)

    return jsonify({'ok': True})


@app.route('/api/transacoes/<int:tid>', methods=['DELETE'])
def api_transacoes_delete(tid):
    existing = query_db("SELECT * FROM transacoes WHERE id=?", (tid,), one=True)
    if not existing:
        abort(404)
    fatura_id = existing['fatura_id']
    execute_db("DELETE FROM transacoes WHERE id=?", (tid,))
    if fatura_id:
        recalcular_total_fatura(fatura_id)
    return jsonify({'ok': True})


# ─────────────────────────────────────────────
# API – Categorias
# ─────────────────────────────────────────────

@app.route('/api/categorias', methods=['GET'])
def api_categorias_list():
    tipo = request.args.get('tipo')
    if tipo:
        rows = query_db("SELECT * FROM categorias WHERE tipo=? ORDER BY nome", (tipo,))
    else:
        rows = query_db("SELECT * FROM categorias ORDER BY tipo, nome")
    result = []
    for r in rows:
        subs = query_db("SELECT * FROM subcategorias WHERE categoria_id=? ORDER BY nome", (r['id'],))
        d = dict(r)
        d['subcategorias'] = [dict(s) for s in subs]
        result.append(d)
    return jsonify(result)


@app.route('/api/categorias', methods=['POST'])
def api_categorias_criar():
    data = request.get_json(force=True)
    nome = data.get('nome', '').strip()
    tipo = data.get('tipo')
    cor = data.get('cor', '#6c757d')
    icone = data.get('icone', 'tag')
    if not nome or not tipo:
        abort(400)
    cur = execute_db(
        "INSERT INTO categorias (nome, tipo, cor, icone) VALUES (?,?,?,?)",
        (nome, tipo, cor, icone)
    )
    return jsonify({'id': cur.lastrowid}), 201


@app.route('/api/categorias/<int:cid>', methods=['PUT'])
def api_categorias_update(cid):
    data = request.get_json(force=True)
    execute_db(
        "UPDATE categorias SET nome=?, tipo=?, cor=?, icone=? WHERE id=?",
        (data['nome'], data['tipo'], data.get('cor', '#6c757d'), data.get('icone', 'tag'), cid)
    )
    return jsonify({'ok': True})


@app.route('/api/categorias/<int:cid>', methods=['DELETE'])
def api_categorias_delete(cid):
    execute_db("DELETE FROM categorias WHERE id=?", (cid,))
    return jsonify({'ok': True})


# ─────────────────────────────────────────────
# API – Subcategorias
# ─────────────────────────────────────────────

@app.route('/api/subcategorias', methods=['POST'])
def api_subcategorias_criar():
    data = request.get_json(force=True)
    nome = data.get('nome', '').strip()
    categoria_id = data.get('categoria_id')
    if not nome or not categoria_id:
        abort(400)
    cur = execute_db(
        "INSERT INTO subcategorias (nome, categoria_id) VALUES (?,?)",
        (nome, categoria_id)
    )
    return jsonify({'id': cur.lastrowid}), 201


@app.route('/api/subcategorias/<int:sid>', methods=['PUT'])
def api_subcategorias_update(sid):
    data = request.get_json(force=True)
    execute_db("UPDATE subcategorias SET nome=? WHERE id=?", (data['nome'], sid))
    return jsonify({'ok': True})


@app.route('/api/subcategorias/<int:sid>', methods=['DELETE'])
def api_subcategorias_delete(sid):
    execute_db("DELETE FROM subcategorias WHERE id=?", (sid,))
    return jsonify({'ok': True})


# ─────────────────────────────────────────────
# API – Contas
# ─────────────────────────────────────────────

@app.route('/api/contas', methods=['GET'])
def api_contas_list():
    rows = query_db("SELECT * FROM contas ORDER BY nome")
    result = []
    for r in rows:
        d = dict(r)
        # Current balance = initial + received - paid
        rec = query_db(
            "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE conta_id=? AND tipo='receita' AND status='realizado'",
            (r['id'],), one=True
        )['v']
        desp = query_db(
            "SELECT COALESCE(SUM(valor),0) as v FROM transacoes WHERE conta_id=? AND tipo='despesa' AND status='realizado'",
            (r['id'],), one=True
        )['v']
        d['saldo_atual'] = round(r['saldo_inicial'] + rec - desp, 2)
        result.append(d)
    return jsonify(result)


@app.route('/api/contas', methods=['POST'])
def api_contas_criar():
    data = request.get_json(force=True)
    nome = data.get('nome', '').strip()
    saldo_inicial = parse_money(data.get('saldo_inicial', 0))
    if not nome:
        abort(400)
    cur = execute_db("INSERT INTO contas (nome, saldo_inicial) VALUES (?,?)", (nome, saldo_inicial))
    return jsonify({'id': cur.lastrowid}), 201


@app.route('/api/contas/<int:cid>', methods=['PUT'])
def api_contas_update(cid):
    data = request.get_json(force=True)
    execute_db("UPDATE contas SET nome=?, saldo_inicial=? WHERE id=?",
               (data['nome'], parse_money(data.get('saldo_inicial', 0)), cid))
    return jsonify({'ok': True})


@app.route('/api/contas/<int:cid>', methods=['DELETE'])
def api_contas_delete(cid):
    execute_db("DELETE FROM contas WHERE id=?", (cid,))
    return jsonify({'ok': True})


# ─────────────────────────────────────────────
# API – Cartões
# ─────────────────────────────────────────────

@app.route('/api/cartoes', methods=['GET'])
def api_cartoes_list():
    rows = query_db("SELECT * FROM cartoes ORDER BY nome")
    result = []
    for r in rows:
        d = dict(r)
        hoje = date.today()
        try:
            dia_fechamento = hoje.day - r['dias_antes_fechamento']
            if dia_fechamento <= 0:
                dia_fechamento = r['dia_vencimento'] - r['dias_antes_fechamento']
        except Exception:
            dia_fechamento = None
        d['dia_fechamento'] = r['dia_vencimento'] - r['dias_antes_fechamento']
        result.append(d)
    return jsonify(result)


@app.route('/api/cartoes', methods=['POST'])
def api_cartoes_criar():
    data = request.get_json(force=True)
    nome = data.get('nome', '').strip()
    dia_venc = int(data.get('dia_vencimento', 10))
    dias_antes = int(data.get('dias_antes_fechamento', 7))
    if not nome:
        abort(400)
    cur = execute_db(
        "INSERT INTO cartoes (nome, dia_vencimento, dias_antes_fechamento) VALUES (?,?,?)",
        (nome, dia_venc, dias_antes)
    )
    return jsonify({'id': cur.lastrowid}), 201


@app.route('/api/cartoes/<int:cid>', methods=['PUT'])
def api_cartoes_update(cid):
    data = request.get_json(force=True)
    execute_db(
        "UPDATE cartoes SET nome=?, dia_vencimento=?, dias_antes_fechamento=? WHERE id=?",
        (data['nome'], int(data['dia_vencimento']), int(data['dias_antes_fechamento']), cid)
    )
    return jsonify({'ok': True})


@app.route('/api/cartoes/<int:cid>', methods=['DELETE'])
def api_cartoes_delete(cid):
    execute_db("DELETE FROM cartoes WHERE id=?", (cid,))
    return jsonify({'ok': True})


# ─────────────────────────────────────────────
# API – Faturas
# ─────────────────────────────────────────────

@app.route('/api/faturas', methods=['GET'])
def api_faturas_list():
    cartao_id = request.args.get('cartao_id')
    if cartao_id:
        rows = query_db(
            """SELECT f.*, c.nome as cartao_nome FROM faturas f
               JOIN cartoes c ON f.cartao_id=c.id
               WHERE f.cartao_id=? ORDER BY f.mes_referencia DESC""",
            (cartao_id,)
        )
    else:
        rows = query_db(
            """SELECT f.*, c.nome as cartao_nome FROM faturas f
               JOIN cartoes c ON f.cartao_id=c.id
               ORDER BY f.mes_referencia DESC, c.nome"""
        )
    return jsonify([dict(r) for r in rows])


@app.route('/api/faturas/<int:fid>', methods=['GET'])
def api_faturas_get(fid):
    row = query_db(
        """SELECT f.*, c.nome as cartao_nome FROM faturas f
           JOIN cartoes c ON f.cartao_id=c.id WHERE f.id=?""",
        (fid,), one=True
    )
    if not row:
        abort(404)
    transacoes = query_db(
        "SELECT * FROM transacoes WHERE fatura_id=? ORDER BY data DESC",
        (fid,)
    )
    d = dict(row)
    d['transacoes'] = [dict(t) for t in transacoes]
    return jsonify(d)


@app.route('/api/faturas/<int:fid>/pagar', methods=['POST'])
def api_faturas_pagar(fid):
    data = request.get_json(force=True) or {}
    fatura = query_db("SELECT * FROM faturas WHERE id=?", (fid,), one=True)
    if not fatura:
        abort(404)
    conta_id = data.get('conta_id')
    execute_db("UPDATE faturas SET status='paga', conta_pagamento_id=? WHERE id=?",
               (conta_id, fid))
    return jsonify({'ok': True})


# ─────────────────────────────────────────────
# API – Transferências
# ─────────────────────────────────────────────

@app.route('/api/transferencias', methods=['POST'])
def api_transferencias_criar():
    data = request.get_json(force=True)
    conta_origem = data.get('conta_origem_id')
    conta_destino = data.get('conta_destino_id')
    valor = float(data.get('valor', 0))
    dt = data.get('data', date.today().isoformat())
    descricao = data.get('descricao', 'Transferência')
    status = data.get('status', 'realizado')

    if not conta_origem or not conta_destino or not valor:
        abort(400, "conta_origem_id, conta_destino_id e valor são obrigatórios")

    if conta_origem == conta_destino:
        abort(400, "Conta de origem e destino não podem ser iguais")

    # Create transfer group
    cur = execute_db("INSERT INTO transferencias_grupos DEFAULT VALUES")
    grupo_id = cur.lastrowid

    # Debit (despesa) from origin
    execute_db(
        """INSERT INTO transacoes (tipo, valor, data, descricao, status,
           metodo_pagamento, conta_id, transferencia_grupo_id)
           VALUES ('despesa',?,?,?,?,'conta',?,?)""",
        (valor, dt, descricao, status, conta_origem, grupo_id)
    )

    # Credit (receita) to destination
    execute_db(
        """INSERT INTO transacoes (tipo, valor, data, descricao, status,
           metodo_pagamento, conta_id, transferencia_grupo_id)
           VALUES ('receita',?,?,?,?,'conta',?,?)""",
        (valor, dt, descricao, status, conta_destino, grupo_id)
    )

    return jsonify({'grupo_id': grupo_id}), 201


# ─────────────────────────────────────────────
# API – Utility
# ─────────────────────────────────────────────

@app.route('/api/contas_cartoes', methods=['GET'])
def api_contas_cartoes():
    """Return both accounts and cards for form selects."""
    contas = query_db("SELECT id, nome FROM contas ORDER BY nome")
    cartoes = query_db("SELECT id, nome FROM cartoes ORDER BY nome")
    return jsonify({
        'contas': [dict(c) for c in contas],
        'cartoes': [dict(c) for c in cartoes],
    })


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == '__main__':
    _ensure_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
