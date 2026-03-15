/**
 * app.js – global JS initialisation for Axis
 * Page-specific logic lives in each template's {% block scripts %}.
 * Modal ESC handling is managed by ui/modal.js.
 */

// Highlight active nav link (server-side Jinja handles this; kept for fallback)
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.href === location.href) link.classList.add('active');
});

// ─────────────────────────────────────────────
// Onboarding Wizard
// ─────────────────────────────────────────────

const OB_STEPS = 5;
let obCurrentStep = 1;
let obData = { cartaoChoice: null }; // persist choices across steps

function obShowStep(step) {
  obCurrentStep = step;
  const progress = document.getElementById('onboarding-progress');
  const title = document.getElementById('onboarding-title');
  const subtitle = document.getElementById('onboarding-subtitle');
  const body = document.getElementById('onboarding-body');
  const btnBack = document.getElementById('ob-btn-back');
  const btnNext = document.getElementById('ob-btn-next');

  // Update progress dots
  progress.innerHTML = '';
  for (let i = 1; i <= OB_STEPS; i++) {
    const dot = document.createElement('span');
    dot.className = 'onboarding-step-dot' +
      (i < step ? ' done' : i === step ? ' active' : '');
    progress.appendChild(dot);
  }
  const lbl = document.createElement('span');
  lbl.className = 'onboarding-step-label';
  lbl.textContent = `Passo ${step} de ${OB_STEPS}`;
  progress.appendChild(lbl);

  btnBack.style.visibility = step > 1 ? 'visible' : 'hidden';

  switch (step) {
    case 1:
      title.textContent = 'Bem-vindo ao Axis 👋';
      subtitle.textContent = 'Controle suas finanças de um jeito simples. Vamos configurar o básico em cerca de 3 minutos.';
      body.innerHTML = `
        <ul class="onboarding-summary-list">
          <li><span class="item-icon">🏦</span><span class="item-text"><strong>Criar sua primeira conta</strong>Banco, carteira ou onde seu dinheiro está.</span></li>
          <li><span class="item-icon">💳</span><span class="item-text"><strong>Cartão de crédito (opcional)</strong>Configure agora ou adicione depois.</span></li>
          <li><span class="item-icon">🏷️</span><span class="item-text"><strong>Categorias</strong>Use as padrão ou personalize depois.</span></li>
          <li><span class="item-icon">✅</span><span class="item-text"><strong>Pronto!</strong>Comece a registrar suas transações.</span></li>
        </ul>`;
      btnNext.textContent = 'Começar →';
      break;

    case 2:
      title.textContent = 'Sua primeira conta';
      subtitle.textContent = 'Adicione uma conta para começar. Pode ser seu banco, sua carteira — onde seu dinheiro está agora.';
      body.innerHTML = `
        <div class="form-group">
          <label>Nome da conta *</label>
          <input type="text" id="ob-conta-nome" placeholder="Ex: Banco, Nubank, Carteira" />
        </div>
        <div class="form-group">
          <label>Saldo atual (R$) *</label>
          <input type="number" id="ob-conta-saldo" step="0.01" min="0" placeholder="0,00" />
          <span class="form-hint">Quanto você tem nessa conta hoje.</span>
        </div>`;
      btnNext.textContent = 'Continuar →';
      // Restore previous values if going back and forth
      if (obData.contaNome) document.getElementById('ob-conta-nome').value = obData.contaNome;
      if (obData.contaSaldo !== undefined) document.getElementById('ob-conta-saldo').value = obData.contaSaldo;
      break;

    case 3:
      title.textContent = 'Cartão de crédito';
      subtitle.textContent = 'Você usa cartão de crédito? Pode configurar agora ou adicionar depois em Cartões.';
      body.innerHTML = `
        <div class="onboarding-option-cards">
          <div class="onboarding-option-card ${obData.cartaoChoice === 'agora' ? 'selected' : ''}" onclick="obSelectCartao('agora')" tabindex="0" role="button" aria-pressed="${obData.cartaoChoice === 'agora'}">
            <div class="card-icon">⚡</div>
            <div class="card-label">Configurar agora</div>
            <div class="card-hint">Cadastrar um cartão hoje</div>
          </div>
          <div class="onboarding-option-card ${obData.cartaoChoice === 'depois' ? 'selected' : ''}" onclick="obSelectCartao('depois')" tabindex="0" role="button" aria-pressed="${obData.cartaoChoice === 'depois'}">
            <div class="card-icon">⏰</div>
            <div class="card-label">Depois</div>
            <div class="card-hint">Adicionar em Cartões quando quiser</div>
          </div>
        </div>
        <div id="ob-cartao-form" style="margin-top:20px;display:${obData.cartaoChoice === 'agora' ? 'block' : 'none'}">
          <div class="form-group">
            <label>Nome do cartão</label>
            <input type="text" id="ob-cartao-nome" placeholder="Ex: Nubank, Itaú Visa" value="${obData.cartaoNome || ''}" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Dia do vencimento</label>
              <input type="number" id="ob-cartao-venc" min="1" max="31" placeholder="10" value="${obData.cartaoVenc || ''}" />
              <span class="form-hint">Dia em que você paga a fatura.</span>
            </div>
            <div class="form-group">
              <label>Dia do fechamento</label>
              <input type="number" id="ob-cartao-fech" min="1" max="31" placeholder="3" value="${obData.cartaoFech || ''}" />
              <span class="form-hint">Dia em que a fatura fecha (corta novas compras).</span>
            </div>
          </div>
          <div class="form-hint" style="padding:8px 0;color:var(--yellow)">⚠️ Compras no dia do fechamento entram na <strong>próxima fatura</strong>.</div>
        </div>`;
      btnNext.textContent = 'Continuar →';
      if (!obData.cartaoChoice) obData.cartaoChoice = 'depois';
      // Highlight default
      document.querySelectorAll('.onboarding-option-card').forEach(c => c.classList.remove('selected'));
      const defaultCard = obData.cartaoChoice === 'agora'
        ? document.querySelector('[onclick="obSelectCartao(\'agora\')"]')
        : document.querySelector('[onclick="obSelectCartao(\'depois\')"]');
      if (defaultCard) defaultCard.classList.add('selected');
      break;

    case 4:
      title.textContent = 'Categorias';
      subtitle.textContent = 'Categorias organizam seus gastos. Recomendamos usar as padrão para começar — você pode personalizar depois.';
      body.innerHTML = `
        <div class="onboarding-option-cards">
          <div class="onboarding-option-card selected" id="ob-cat-padrao" onclick="obSelectCat('padrao')" tabindex="0" role="button">
            <div class="card-icon">✅</div>
            <div class="card-label">Usar categorias padrão</div>
            <div class="card-hint">Alimentação, Moradia, Transporte… já prontas</div>
          </div>
          <div class="onboarding-option-card" id="ob-cat-depois" onclick="obSelectCat('depois')" tabindex="0" role="button">
            <div class="card-icon">✏️</div>
            <div class="card-label">Personalizar depois</div>
            <div class="card-hint">Editar em Categorias quando quiser</div>
          </div>
        </div>`;
      btnNext.textContent = 'Continuar →';
      if (obData.catChoice) {
        document.querySelectorAll('.onboarding-option-card').forEach(c => c.classList.remove('selected'));
        document.getElementById(obData.catChoice === 'padrao' ? 'ob-cat-padrao' : 'ob-cat-depois').classList.add('selected');
      }
      break;

    case 5:
      title.textContent = '🎉 Tudo pronto!';
      subtitle.textContent = 'Você configurou o essencial. Veja o que fazer em seguida:';
      body.innerHTML = `
        <ul class="onboarding-summary-list">
          <li><span class="item-icon">💰</span><span class="item-text"><strong>Registre transações</strong>Clique em "Nova transação" na tela de Transações.</span></li>
          <li><span class="item-icon">💳</span><span class="item-text"><strong>Gastos no cartão</strong>Vão automaticamente para a fatura do mês.</span></li>
          <li><span class="item-icon">📊</span><span class="item-text"><strong>Dashboard</strong>Troque o mês no seletor para ver outros períodos.</span></li>
          <li><span class="item-icon">❓</span><span class="item-text"><strong>Precisa de ajuda?</strong>Clique em "? Ajuda" no topo de qualquer tela.</span></li>
        </ul>`;
      btnNext.textContent = 'Ir para o Dashboard ✓';
      break;
  }
}

function obSelectCartao(choice) {
  obData.cartaoChoice = choice;
  document.querySelectorAll('.onboarding-option-card').forEach(c => c.classList.remove('selected'));
  const selected = choice === 'agora'
    ? document.querySelector('[onclick="obSelectCartao(\'agora\')"]')
    : document.querySelector('[onclick="obSelectCartao(\'depois\')"]');
  if (selected) selected.classList.add('selected');
  const form = document.getElementById('ob-cartao-form');
  if (form) form.style.display = choice === 'agora' ? 'block' : 'none';
}

function obSelectCat(choice) {
  obData.catChoice = choice;
  document.querySelectorAll('.onboarding-option-card').forEach(c => c.classList.remove('selected'));
  document.getElementById(choice === 'padrao' ? 'ob-cat-padrao' : 'ob-cat-depois').classList.add('selected');
}

async function obNext() {
  // Validate current step
  if (obCurrentStep === 2) {
    const nome = (document.getElementById('ob-conta-nome') || {}).value || '';
    const saldo = (document.getElementById('ob-conta-saldo') || {}).value || '';
    if (!nome.trim()) {
      showToast('Por favor, informe o nome da conta.', 'error');
      document.getElementById('ob-conta-nome').focus();
      return;
    }
    obData.contaNome = nome.trim();
    obData.contaSaldo = parseFloat(saldo) || 0;
    // Create account in DB
    const result = await apiPost('/api/contas', { nome: obData.contaNome, saldo_inicial: obData.contaSaldo });
    if (!result) return; // error shown by apiPost
  }

  if (obCurrentStep === 3 && obData.cartaoChoice === 'agora') {
    const nome = (document.getElementById('ob-cartao-nome') || {}).value || '';
    const venc = parseInt((document.getElementById('ob-cartao-venc') || {}).value) || 0;
    const fech = parseInt((document.getElementById('ob-cartao-fech') || {}).value) || 0;
    if (!nome.trim() || !venc || !fech) {
      showToast('Preencha nome, vencimento e fechamento do cartão.', 'error');
      return;
    }
    if (venc < 1 || venc > 31 || fech < 1 || fech > 31) {
      showToast('Dia de vencimento e fechamento devem ser entre 1 e 31.', 'error');
      return;
    }
    obData.cartaoNome = nome.trim();
    obData.cartaoVenc = venc;
    obData.cartaoFech = fech;
    // Calculate days before due date that the invoice closes.
    // Same-month case: dias_antes = venc - fech
    // Cross-month case (fech > venc): use 30-day average to estimate days
    const diasAntes = venc > fech ? venc - fech : Math.max(1, 30 - fech + venc);
    const result = await apiPost('/api/cartoes', {
      nome: obData.cartaoNome,
      dia_vencimento: venc,
      dias_antes_fechamento: diasAntes > 0 ? diasAntes : 1,
    });
    if (!result) return;
  }

  if (obCurrentStep === OB_STEPS) {
    // Finish onboarding
    await apiPut('/api/configuracoes/onboarding_completed', { valor: 'true' });
    window.ONBOARDING_COMPLETED = 'true';
    document.getElementById('onboarding-overlay').classList.remove('active');
    document.body.style.overflow = '';
    showToast('Configuração concluída! Bem-vindo ao Axis. 🎉', 'success');
    return;
  }

  obShowStep(obCurrentStep + 1);
}

function obBack() {
  if (obCurrentStep > 1) obShowStep(obCurrentStep - 1);
}

function initOnboarding() {
  if (window.ONBOARDING_COMPLETED !== 'true') {
    document.getElementById('onboarding-overlay').classList.add('active');
    document.body.style.overflow = 'hidden';
    obShowStep(1);
  }
}

// ─────────────────────────────────────────────
// Help Drawer
// ─────────────────────────────────────────────

const HELP_CONTENT = {
  dashboard: {
    page: 'Dashboard',
    bullets: [
      'Use <strong>Mês anterior / Este mês</strong> ou o seletor de mês para navegar.',
      'Gastos de <strong>Conta/Pix/Débito</strong> entram pelo <strong>dia do lançamento</strong>.',
      'Gastos no <strong>Cartão de crédito</strong> entram pelo <strong>mês da fatura</strong>.',
      '"Saldo disponível" = confirmados; "Saldo previsto" inclui agendados.',
    ],
    more: [
      {
        type: 'example',
        html: 'Exemplo: uma compra no cartão em <strong>28/02/2026</strong> pode aparecer no Dashboard de <strong>abril/2026</strong> se cair na fatura de abril.',
      },
      {
        type: 'error',
        html: 'Algo não aparece? Confira: <strong>mês selecionado</strong>, <strong>status</strong> (Agendado/Confirmado) e se foi lançado como <strong>Conta ou Cartão</strong>.',
      },
    ],
  },
  transacoes: {
    page: 'Transações',
    bullets: [
      'Clique em <strong>+ Nova Transação</strong> para registrar entradas e saídas.',
      'Escolha como foi pago: <strong>Conta</strong> (Pix/Débito/Dinheiro) ou <strong>Cartão</strong> (crédito).',
      'Use <strong>Agendado</strong> para coisas futuras e <strong>Confirmado</strong> para o que já aconteceu.',
      'Parcelas e recorrência criam lançamentos automaticamente.',
    ],
    more: [
      {
        type: 'example',
        html: 'Cartão: a compra vai para uma <strong>fatura</strong> — por isso pode aparecer em outro mês no Dashboard.',
      },
      {
        type: 'example',
        html: 'Assinatura mensal → use <strong>recorrência</strong>. Compra grande parcelada → use <strong>parcelado</strong>.',
      },
      {
        type: 'error',
        html: 'Erro comum: lançar compra no cartão como "Conta" → o valor aparece no <strong>mês errado</strong>.',
      },
    ],
  },
  categorias: {
    page: 'Categorias',
    bullets: [
      'Categorias organizam seus gastos (ex.: Alimentação, Moradia).',
      'Dá para lançar "Sem categoria" e organizar depois.',
      'Manter poucas categorias deixa tudo mais claro.',
    ],
    more: [
      {
        type: 'example',
        html: 'Dica: <strong>8–15 categorias principais</strong> costuma ser o ideal.',
      },
      {
        type: 'error',
        html: 'Erro comum: criar categorias demais e depois não usar sempre → <strong>gráficos ficam pouco úteis</strong>.',
      },
    ],
  },
  contas: {
    page: 'Contas',
    bullets: [
      'Contas representam onde seu dinheiro está (banco, carteira etc.).',
      'O <strong>saldo inicial</strong> é seu ponto de partida no controle.',
      'Entradas/saídas <strong>confirmadas</strong> alteram o saldo.',
    ],
    more: [
      {
        type: 'error',
        html: 'Saldo "não bate"? Procure <strong>duplicidade</strong>, lançamentos agendados ou despesas de cartão lançadas como conta.',
      },
      {
        type: 'example',
        html: 'Dica: comece com <strong>1 conta "Banco"</strong> e (opcional) <strong>1 "Dinheiro"</strong>.',
      },
    ],
  },
  cartoes: {
    page: 'Cartões',
    bullets: [
      'Você pode cadastrar <strong>vários cartões</strong>.',
      'Cada cartão tem <strong>vencimento</strong> (dia de pagar) e <strong>fechamento</strong> (dia que corta novas compras).',
      'Compras no <strong>dia do fechamento</strong> entram na <strong>próxima fatura</strong>.',
    ],
    more: [
      {
        type: 'example',
        html: 'Exemplo: fechamento dia 3, vencimento dia 10. Compra feita no dia 3 → vai para a <strong>fatura do próximo mês</strong>.',
      },
      {
        type: 'error',
        html: 'Se ajustar as datas do cartão depois de lançar compras, use <strong>Recalcular faturas</strong> na tela de Faturas.',
      },
    ],
  },
  faturas: {
    page: 'Faturas',
    bullets: [
      'Aqui ficam as faturas por cartão e por mês.',
      'Você vê itens, total e o status da fatura.',
      '"Recalcular faturas" corrige o mês correto das compras.',
    ],
    more: [
      {
        type: 'example',
        html: 'Quando usar "Recalcular": depois de mudar vencimento/fechamento, ou se compras antigas caíram no mês errado.',
      },
      {
        type: 'error',
        html: 'Ao recalcular, os valores do Dashboard podem mudar — isso é <strong>esperado</strong> quando o fechamento foi alterado.',
      },
    ],
  },
  configuracoes: {
    page: 'Configurações',
    bullets: [
      'Troque entre <strong>Modo simples</strong> e <strong>Modo avançado</strong>.',
      'Modo simples: linguagem mais fácil, menos opções na tela.',
      'Modo avançado: mostra campos técnicos e detalhes para controle fino.',
    ],
    more: [
      {
        type: 'example',
        html: 'No modo simples: status aparecem como <strong>Confirmado / Agendado</strong>. No modo avançado: <strong>Realizado / Previsto</strong>.',
      },
    ],
  },
};

function openHelp(pageKey) {
  const content = HELP_CONTENT[pageKey];
  if (!content) return;
  document.getElementById('help-drawer-page').textContent = content.page;
  const body = document.getElementById('help-drawer-body');
  body.innerHTML = `
    <p class="help-section-title">Resumo</p>
    <ul class="help-bullets">
      ${content.bullets.map(b => `<li>${b}</li>`).join('')}
    </ul>
    <button class="btn-help-more" onclick="toggleHelpMore(this)" aria-expanded="false">▶ Mostrar mais</button>
    <div class="help-more-section" id="help-more">
      ${content.more.map(item => `
        <div class="help-example">${item.html}</div>
      `).join('')}
    </div>`;
  document.getElementById('help-overlay').classList.add('active');
  document.getElementById('help-drawer').classList.add('active');
  document.getElementById('help-drawer').querySelector('.modal-close').focus();
}

function closeHelp() {
  document.getElementById('help-overlay').classList.remove('active');
  document.getElementById('help-drawer').classList.remove('active');
}

function toggleHelpMore(btn) {
  const more = document.getElementById('help-more');
  const expanded = more.classList.toggle('visible');
  btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
  btn.textContent = expanded ? '▼ Mostrar menos' : '▶ Mostrar mais';
}

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initOnboarding();
});
