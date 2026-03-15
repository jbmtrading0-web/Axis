PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS contas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    saldo_inicial REAL DEFAULT 0,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS cartoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    dia_vencimento INTEGER NOT NULL CHECK(dia_vencimento BETWEEN 1 AND 31),
    dias_antes_fechamento INTEGER NOT NULL DEFAULT 7,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
    cor TEXT DEFAULT '#6c757d',
    icone TEXT DEFAULT 'tag',
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS subcategorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    categoria_id INTEGER NOT NULL,
    criado_em TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS faturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cartao_id INTEGER NOT NULL,
    mes_referencia TEXT NOT NULL,
    data_fechamento TEXT NOT NULL,
    data_vencimento TEXT NOT NULL,
    total REAL DEFAULT 0,
    status TEXT DEFAULT 'aberta' CHECK(status IN ('aberta', 'fechada', 'paga')),
    conta_pagamento_id INTEGER,
    criado_em TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (cartao_id) REFERENCES cartoes(id) ON DELETE CASCADE,
    FOREIGN KEY (conta_pagamento_id) REFERENCES contas(id) ON DELETE SET NULL,
    UNIQUE(cartao_id, mes_referencia)
);

CREATE TABLE IF NOT EXISTS transferencias_grupos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
    valor REAL NOT NULL CHECK(valor > 0),
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    status TEXT DEFAULT 'previsto' CHECK(status IN ('realizado', 'previsto')),
    categoria_id INTEGER,
    subcategoria_id INTEGER,
    metodo_pagamento TEXT DEFAULT 'conta' CHECK(metodo_pagamento IN ('conta', 'cartao')),
    conta_id INTEGER,
    cartao_id INTEGER,
    fatura_id INTEGER,
    observacao TEXT,
    recorrente INTEGER DEFAULT 0,
    parcela_atual INTEGER,
    total_parcelas INTEGER,
    grupo_recorrencia TEXT,
    transferencia_grupo_id INTEGER,
    criado_em TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
    FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(id) ON DELETE SET NULL,
    FOREIGN KEY (conta_id) REFERENCES contas(id) ON DELETE SET NULL,
    FOREIGN KEY (cartao_id) REFERENCES cartoes(id) ON DELETE SET NULL,
    FOREIGN KEY (fatura_id) REFERENCES faturas(id) ON DELETE SET NULL,
    FOREIGN KEY (transferencia_grupo_id) REFERENCES transferencias_grupos(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Default configuration values
INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES
('onboarding_completed', 'false'),
('ui_mode', 'simples');

-- Default categories
INSERT OR IGNORE INTO categorias (id, nome, tipo, cor, icone) VALUES
(1, 'Salário', 'receita', '#28a745', 'wallet'),
(2, 'Freelance', 'receita', '#20c997', 'laptop'),
(3, 'Investimentos', 'receita', '#17a2b8', 'trending-up'),
(4, 'Outros (Receita)', 'receita', '#6f42c1', 'plus-circle'),
(5, 'Alimentação', 'despesa', '#fd7e14', 'shopping-cart'),
(6, 'Transporte', 'despesa', '#ffc107', 'car'),
(7, 'Moradia', 'despesa', '#dc3545', 'home'),
(8, 'Saúde', 'despesa', '#e83e8c', 'heart'),
(9, 'Educação', 'despesa', '#6610f2', 'book'),
(10, 'Lazer', 'despesa', '#fd7e14', 'smile'),
(11, 'Vestuário', 'despesa', '#20c997', 'shopping-bag'),
(12, 'Outros (Despesa)', 'despesa', '#6c757d', 'more-horizontal');
