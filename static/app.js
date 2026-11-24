/* ZincRevise – front em JS puro. Todo texto vindo do servidor entra como textContent (nunca HTML). */
(function () {
  "use strict";

  const raiz = document.getElementById("raiz");
  const G = window.Graficos;

  /* =====================================================================
     utilidades
     ===================================================================== */

  function h(tag, attrs, ...filhos) {
    const el = document.createElement(tag);
    // botão só envia formulário quando pedido explicitamente (type: "submit")
    if (tag === "button") el.type = "button";
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else if (k === "class") el.className = v;
      else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
      else if (k === "value") el.value = v;
      else if (k === "checked") el.checked = !!v;
      else if (v === true) el.setAttribute(k, "");
      else el.setAttribute(k, v);
    }
    adicionar(el, filhos);
    return el;
  }
  function adicionar(el, filhos) {
    for (const f of filhos.flat(Infinity)) {
      if (f === null || f === undefined || f === false) continue;
      el.appendChild(f instanceof Node ? f : document.createTextNode(String(f)));
    }
    return el;
  }
  function limpar(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }

  /* ícones de traço (24x24) */
  const ICONES = {
    hoje: ["M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"],
    cadastrar: ["M12 8v8", "M8 12h8", "M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"],
    sessao: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M10 8.5v7l5.5-3.5z"],
    topicos: ["M8 6h13", "M8 12h13", "M8 18h13", "M3.5 6h.01", "M3.5 12h.01", "M3.5 18h.01"],
    estatisticas: ["M4 20V10", "M10 20V4", "M16 20v-7", "M22 20H2"],
    leis: ["M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z", "M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"],
    config: ["M4 6h10", "M18 6h2", "M4 12h4", "M12 12h8", "M4 18h12", "M16 4v4", "M10 10v4", "M18 16v4"],
    sair: ["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "M16 17l5-5-5-5", "M21 12H9"],
    colar: ["M9 4h6a1 1 0 0 1 1 1v1H8V5a1 1 0 0 1 1-1z", "M8 5H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2", "M9 13h6", "M9 17h4"],
    link: ["M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7", "M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"],
    certo: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M8 12.5l2.7 2.7L16 9.8"],
    errado: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M9 9l6 6", "M15 9l-6 6"],
    livro: ["M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z", "M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"],
    bandeira: ["M4 22V4", "M4 4h13l-2 4 2 4H4"],
    mais: ["M12 5v14", "M5 12h14"],
    menos: ["M5 12h14"],
    menu: ["M4 7h16", "M4 12h16", "M4 17h16"],
    voltar: ["M15 18l-6-6 6-6"],
    avancar: ["M9 18l6-6-6-6"],
    alerta: ["M12 9v4", "M12 17h.01", "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"],
    info: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 16v-4", "M12 8h.01"],
    gerar: ["M21 12a9 9 0 1 1-3-6.7L21 8", "M21 3v5h-5"],
  };
  function icone(nome) {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "ico");
    svg.setAttribute("aria-hidden", "true");
    for (const d of ICONES[nome] || []) {
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", d);
      svg.appendChild(p);
    }
    return svg;
  }

  function autoAltura(ta) {
    const ajustar = () => { ta.style.height = "auto"; ta.style.height = ta.scrollHeight + 2 + "px"; };
    ta.addEventListener("input", ajustar);
    requestAnimationFrame(ajustar);
    return ta;
  }

  class ErroApi extends Error {
    constructor(msg, status, dados) { super(msg); this.status = status; this.dados = dados || {}; }
  }

  async function api(caminho, opcoes = {}) {
    const init = { method: opcoes.method || "GET", headers: {}, credentials: "same-origin" };
    if (opcoes.form) init.body = opcoes.form;
    else if (opcoes.body !== undefined) { init.body = JSON.stringify(opcoes.body); init.headers["Content-Type"] = "application/json"; }
    let r;
    try { r = await fetch(caminho, init); }
    catch (e) { throw new ErroApi("Sem conexão com o servidor.", 0); }
    let dados = null;
    try { dados = await r.json(); } catch (e) { dados = null; }
    if (r.status === 401 && caminho !== "/api/login" && caminho !== "/api/senha") { telaLogin(); throw new ErroApi("Não autenticado.", 401); }
    if (!r.ok) throw new ErroApi((dados && (dados.erro || dados.detail)) || ("Erro " + r.status), r.status, dados);
    return dados;
  }

  let toastTimer = null;
  function toast(msg, erro) {
    let t = document.querySelector(".toast");
    if (!t) { t = h("div", { class: "toast", role: "status" }); document.body.appendChild(t); }
    t.className = "toast" + (erro ? " erro" : "");
    t.textContent = msg;
    t.style.display = "block";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.style.display = "none"; }, erro ? 6000 : 3200);
  }

  const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
  const DIAS = ["domingo", "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado"];
  const DIAS_C = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
  function dataISO(s) { const [a, m, d] = s.slice(0, 10).split("-").map(Number); return new Date(a, m - 1, d); }
  function fmtData(s) { if (!s) return "—"; const p = s.slice(0, 10).split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }
  function fmtLonga(s) { const d = dataISO(s); const t = DIAS[d.getDay()] + ", " + d.getDate() + " de " + MESES[d.getMonth()]; return t.charAt(0).toUpperCase() + t.slice(1); }
  function diasEntre(a, b) { return Math.round((dataISO(b) - dataISO(a)) / 86400000); }
  function relativo(s, hoje) {
    if (!s) return "—";
    const d = diasEntre(hoje, s);
    if (d === 0) return "hoje";
    if (d === 1) return "amanhã";
    if (d === -1) return "ontem";
    if (d < 0) return "há " + (-d) + " dias";
    return "em " + d + " dias";
  }
  function hojeISO() { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function somaDias(s, n) { const d = dataISO(s); d.setDate(d.getDate() + n); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function pct(a, t) { return t ? Math.round((100 * a) / t) : 0; }
  function plural(n, s, p) { return n + " " + (n === 1 ? s : (p || s + "s")); }

  function etapas(etapa, max) {
    const manut = etapa >= max;
    return h("span", { class: "etapas" + (manut ? " manut" : ""), title: manut ? "manutenção" : "etapa " + etapa },
      Array.from({ length: max }, (_, i) => h("i", { class: i < etapa || manut ? "f" : "" })));
  }
  function nomeEtapa(etapa, max) { return etapa >= max ? "Manutenção" : "Etapa " + etapa; }

  /* texto do Claude: parágrafos, listas com "- " e **negrito**, tudo como texto */
  function textoRico(txt) {
    const cont = h("div", { class: "explicacao" });
    for (const b of String(txt || "").replace(/\r/g, "").split(/\n{2,}/)) {
      const linhas = b.split("\n").filter((l) => l.trim());
      if (!linhas.length) continue;
      if (linhas.every((l) => /^\s*([-*•]|\d+[.)])\s+/.test(l))) {
        cont.appendChild(h("ul", null, linhas.map((l) => h("li", null, inline(l.replace(/^\s*([-*•]|\d+[.)])\s+/, ""))))));
      } else {
        for (const l of linhas) {
          if (/^\s*[-*•]\s+/.test(l)) cont.appendChild(h("ul", null, h("li", null, inline(l.replace(/^\s*[-*•]\s+/, "")))));
          else cont.appendChild(h("p", null, inline(l.replace(/^#+\s*/, ""))));
        }
      }
    }
    return cont;
  }
  function inline(t) {
    return t.split(/(\*\*[^*]+\*\*)/g).map((p) => (p.startsWith("**") && p.endsWith("**") ? h("strong", null, p.slice(2, -2)) : p));
  }

  function carregando(msg) { return h("div", { class: "carregando" }, msg || "Carregando…"); }
  function alerta(tipo, ...conteudo) {
    const ic = { aviso: "alerta", erro: "alerta", ok: "certo", info: "info" }[tipo];
    return h("div", { class: "alerta " + tipo, role: tipo === "erro" ? "alert" : null }, icone(ic), h("div", null, conteudo));
  }
  function card(titulo, sub, acoes, ...corpo) {
    return h("section", { class: "card" },
      titulo ? h("div", { class: "card-cab" }, h("div", null, h("h2", null, titulo), sub ? h("div", { class: "sub" }, sub) : null), acoes || null) : null,
      corpo);
  }

  /* =====================================================================
     tema
     ===================================================================== */
  const TEMAS = [["claro", "Claro"], ["suave", "Claro suave"], ["escuro", "Escuro"]];
  function temaAtual() { return document.documentElement.getAttribute("data-tema") || "claro"; }
  function setTema(t) {
    document.documentElement.setAttribute("data-tema", t);
    try { localStorage.setItem("zinc-tema", t); } catch (e) { /* sem storage */ }
  }

  /* =====================================================================
     login
     ===================================================================== */
  async function telaLogin() {
    pararPolling();
    limpar(raiz);
    let info = { bloqueado_ate: null };
    try { info = await api("/api/auth"); } catch (e) { /* ignora */ }
    if (info.logado) { iniciarApp(); return; }
    const msg = h("div", { class: "oculto" });
    const inp = h("input", { class: "inp", type: "password", inputmode: "numeric", autocomplete: "current-password", "aria-label": "Senha" });
    const btn = h("button", { class: "btn prim lg", type: "submit" }, "Entrar");
    function mostrarErro(t) { limpar(msg); msg.appendChild(alerta("erro", t)); msg.classList.remove("oculto"); }
    if (info.bloqueado_ate) mostrarErro("Login bloqueado até " + info.bloqueado_ate.slice(11, 16) + ".");
    const form = h("form", {
      onsubmit: async (ev) => {
        ev.preventDefault();
        btn.disabled = true;
        try {
          await api("/api/login", { method: "POST", body: { senha: inp.value } });
          iniciarApp();
        } catch (e) {
          mostrarErro(e.message);
          inp.value = ""; inp.focus();
        } finally { btn.disabled = false; }
      }
    }, h("div", { class: "logo" }, h("span", { class: "selo" }, "Z"), "ZincRevise"),
      h("div", { class: "sub" }, "Revisão espaçada para concursos"),
      h("label", { class: "campo" }, h("span", null, "Senha"), inp), btn, msg);
    raiz.appendChild(h("div", { class: "login" }, h("div", { class: "card" }, form)));
    inp.focus();
  }

  /* =====================================================================
     estrutura e rotas
     ===================================================================== */
  let main = null, nav = null, jobsInd = null, navBaixo = null, jobsMini = null, folhaMais = null;
  let limpeza = [];
  let painelCache = null;
  let pollTimer = null;

  const ROTAS = [
    ["hoje", "Hoje"], ["cadastrar", "Cadastrar questão"], ["sessao", "Sessão diária"], ["topicos", "Assuntos"],
    ["estatisticas", "Estatísticas"], ["leis", "Biblioteca de leis"], ["config", "Configurações"],
  ];

  function iniciarApp() {
    limpar(raiz);
    nav = h("nav", { class: "nav", "aria-label": "Seções" });
    jobsInd = h("div", { class: "jobs-ind oculto", "aria-live": "polite" });
    main = h("main", { id: "conteudo" });
    navBaixo = h("nav", { class: "nav-baixo", "aria-label": "Seções" });
    jobsMini = h("span", { class: "jobs-mini oculto" });
    folhaMais = h("div", { class: "folha-mais oculto", onclick: (ev) => { if (ev.target === folhaMais) fecharMais(); } });
    raiz.appendChild(h("div", { class: "app" },
      h("header", { class: "topo-movel" }, h("div", { class: "logo" }, h("span", { class: "selo" }, "Z"), "ZincRevise"), jobsMini),
      h("aside", { class: "lateral" },
        h("div", { class: "logo" }, h("span", { class: "selo" }, "Z"), "ZincRevise"),
        nav,
        h("div", { class: "lateral-pe" }, jobsInd,
          h("button", { class: "sair", onclick: sair }, icone("sair"), h("span", null, "Sair")))),
      main, navBaixo, folhaMais));
    window.removeEventListener("hashchange", rotear);
    window.addEventListener("hashchange", rotear);
    rotear();
  }

  async function sair() {
    try { await api("/api/logout", { method: "POST" }); } catch (e) { /* ignora */ }
    telaLogin();
  }

  // nomes da barra inferior no celular

  function fecharMais() { folhaMais.classList.add("oculto"); }
  function abrirMais(atual) {
    limpar(folhaMais);
    folhaMais.appendChild(h("div", { class: "folha" },
      [["estatisticas", "Estatísticas"], ["leis", "Biblioteca de leis"], ["config", "Configurações"]].map(([r, n]) =>
        h("a", { href: "#/" + r, class: r === atual ? "ativo" : "", onclick: fecharMais }, icone(r), n)),
      h("button", { onclick: () => { fecharMais(); sair(); } }, icone("sair"), "Sair")));
    folhaMais.classList.remove("oculto");
  }

  function desenharNavBaixo(atual, contagens) {
    if (!navBaixo) return;
    limpar(navBaixo);
    const itens = [["hoje", "Hoje"], ["cadastrar", "Cadastrar"], ["sessao", "Sessão"], ["topicos", "Assuntos"]];
    for (const [r, nome] of itens) {
      const c = contagens[r];
      navBaixo.appendChild(h("a", { href: "#/" + r, class: r === atual ? "ativo" : "", "aria-current": r === atual ? "page" : null },
        h("span", { class: "ic" }, icone(r), c && c.d ? h("span", { class: "ponto" }, String(c.v)) : null), h("span", null, nome)));
    }
    const noMais = ["estatisticas", "leis", "config"].includes(atual);
    navBaixo.appendChild(h("button", { class: noMais ? "ativo" : "", onclick: () => abrirMais(atual) },
      h("span", { class: "ic" }, icone("menu")), h("span", null, "Mais")));
  }

  function desenharNav(atual) {
    limpar(nav);
    const p = painelCache;
    const contagens = {
      hoje: p && p.vencidos_na_sessao ? { v: p.vencidos_na_sessao, d: true } : null,
      sessao: p && p.sessao_aberta ? { v: p.sessao_aberta.respondidas + "/" + p.sessao_aberta.total, d: true } : null,
      topicos: p ? { v: p.totais.topicos } : null,
      leis: p ? { v: p.totais.leis } : null,
    };
    for (const [r, nome] of ROTAS) {
      const c = contagens[r];
      nav.appendChild(h("a", { href: "#/" + r, class: r === atual ? "ativo" : "", "aria-current": r === atual ? "page" : null, title: nome },
        icone(r), h("span", { class: "nome" }, nome),
        c ? h("span", { class: "cont" + (c.d ? " destaque" : "") }, String(c.v)) : null));
    }
    desenharNavBaixo(atual, contagens);
  }

  async function atualizarPainel() {
    try { painelCache = await api("/api/painel"); } catch (e) { /* ignora */ }
    desenharJobs(painelCache ? painelCache.jobs : []);
    return painelCache;
  }

  function desenharJobs(lista) {
    if (!jobsInd) return;
    const ativos = (lista || []).filter((j) => j.status === "pendente" || j.status === "rodando");
    limpar(jobsInd);
    if (jobsMini) { jobsMini.textContent = ativos.length ? "Gerando questões…" : ""; jobsMini.classList.toggle("oculto", !ativos.length); }
    if (!ativos.length) { jobsInd.classList.add("oculto"); pararPolling(); return; }
    jobsInd.classList.remove("oculto");
    adicionar(jobsInd, ["Gerando questões · " + plural(ativos.length, "assunto"), h("div", { class: "mudo", style: { fontWeight: 500, marginTop: "2px" } }, rotuloModelo("gerar")), h("div", { class: "barra" }, h("i"))]);
    agendarPolling();
  }

  function agendarPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(async () => {
      let lista = [];
      try { lista = await api("/api/jobs"); } catch (e) { return; }
      const ativos = lista.filter((j) => j.status === "pendente" || j.status === "rodando");
      desenharJobs(lista);
      if (!ativos.length) {
        const erros = lista.filter((j) => j.status === "erro").length;
        toast(erros ? "Geração terminou com " + plural(erros, "erro") + ". Veja em Hoje." : "Questões geradas.", !!erros);
        if (["hoje", "topicos", "topico"].includes(rotaAtual().nome)) rotear();
      }
    }, 4000);
  }
  function pararPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  function rotaAtual() {
    const partes = (location.hash || "#/hoje").replace(/^#\/?/, "").split("/");
    return { nome: partes[0] || "hoje", arg: partes[1] };
  }

  function rodarLimpeza() {
    limpeza.forEach((f) => { try { f(); } catch (e) { /* ignora */ } });
    limpeza = [];
  }

  async function rotear() {
    rodarLimpeza();
    G.esconderTip();
    const { nome, arg } = rotaAtual();
    const paginas = {
      hoje: pagHoje, cadastrar: pagCadastrar, sessao: pagSessao, topicos: pagTopicos, topico: pagTopico,
      estatisticas: pagEstatisticas, leis: pagLeis, lei: pagLei, config: pagConfig,
    };
    const fn = paginas[nome] || pagHoje;
    const navNome = nome === "topico" ? "topicos" : nome === "lei" ? "leis" : nome;
    desenharNav(navNome);
    limpar(main);
    main.appendChild(carregando());
    await atualizarPainel();
    desenharNav(navNome);
    try {
      await fn(arg);
    } catch (e) {
      if (e.status === 401) return;
      limpar(main);
      main.appendChild(alerta("erro", e.message || String(e)));
    }
    window.scrollTo(0, 0);
  }

  function aoTeclar(fn) {
    const handler = (ev) => {
      const alvo = ev.target;
      if (alvo && (alvo.tagName === "INPUT" || alvo.tagName === "TEXTAREA" || alvo.tagName === "SELECT" || alvo.isContentEditable)) return;
      fn(ev);
    };
    document.addEventListener("keydown", handler);
    limpeza.push(() => document.removeEventListener("keydown", handler));
  }

  function bannerTeste() {
    if (!painelCache || !painelCache.modo_teste) return null;
    return h("div", { class: "banner-teste" }, icone("alerta"),
      h("span", null, "Modo de teste da sessão ligado: a sessão traz todas as questões e não altera a revisão espaçada. ",
        h("a", { href: "#/config" }, "Desligar em Configurações")));
  }

  function cabecalho(titulo, sub, ...acoes) {
    return h("div", { class: "pag-cab" },
      h("div", null, h("h1", null, titulo), sub ? h("div", { class: "sub" }, sub) : null),
      acoes.length ? h("div", { class: "linha" }, acoes) : null);
  }

  function caixaErroIA(e, tentar) {
    return alerta("erro", h("div", null, e.message),
      h("div", { class: "linha", style: { marginTop: "10px" } },
        h("button", { class: "btn sm", onclick: () => tentar(null) }, "Tentar de novo"),
        e.dados && e.dados.pode_tentar_api ? h("button", { class: "btn sm", onclick: () => tentar("api") }, "Tentar com API key") : null));
  }

  const NOME_MODELO = { "claude-haiku-5-5": "Haiku", "claude-sonnet-5-5": "Sonnet", "claude-opus-5-5": "Opus", "claude-fable-5-2": "Fable" };
  const NOME_ESFORCO = { low: "baixo", medium: "médio", high: "alto", xhigh: "muito alto", max: "máximo" };
  /* "Haiku – baixo": modelo e esforço configurados para a tarefa */
  function rotuloModelo(tarefa) {
    const m = painelCache && painelCache.modelos && painelCache.modelos[tarefa];
    if (!m) return "";
    return (NOME_MODELO[m.modelo] || m.modelo) + " – " + (NOME_ESFORCO[m.esforco] || m.esforco);
  }

  /* campo de quantidade + botão "Gerar questões" */
  function botaoGerar(topicoId, opc = {}) {
    const qtd = h("input", { class: "inp qtd", type: "number", min: "1", max: "50", value: "5", "aria-label": "Quantidade de questões (reais novas + geradas)", title: "Quantas questões entram no banco: as reais novas são copiadas e o resto é gerado" });
    const btn = h("button", { class: "btn " + (opc.classe || "prim"), disabled: !!opc.desabilitado, title: opc.titulo || null,
      onclick: () => gerar(topicoId, null, parseInt(qtd.value, 10) || 5) }, icone("gerar"), opc.rotulo || "Gerar questões");
    return h("span", { class: "gerar-grupo" + (opc.pequeno ? " sm" : "") }, qtd, btn);
  }

  async function gerar(topicoId, modo, quantidade) {
    const r = await api("/api/gerar", { method: "POST", body: { topico_id: topicoId || null, modo: modo || null, quantidade: quantidade || null } });
    if (!r.jobs.length) toast(topicoId ? "Esse tópico já está na fila." : "Nenhum tópico com questões novas.");
    else toast("Geração iniciada para " + plural(r.jobs.length, "tópico") + ". Pode continuar usando o app.");
    await atualizarPainel();
  }

  /* =====================================================================
     HOJE
     ===================================================================== */
  async function pagHoje() {
    const p = painelCache || (await atualizarPainel());
    limpar(main);
    main.appendChild(cabecalho("Hoje", fmtLonga(p.hoje)));
    const bt = bannerTeste(); if (bt) main.appendChild(bt);

    const aberta = p.sessao_aberta;
    const nSessao = p.vencidos_na_sessao;
    const esq = h("div");
    if (aberta) {
      adicionar(esq, [
        h("div", { class: "rotulo" }, "Sessão em andamento"),
        h("div", { class: "grande-num", style: { marginTop: "8px" } }, aberta.respondidas + "/" + aberta.total),
        h("div", { class: "grande-leg" }, "questões respondidas" + (aberta.data !== p.hoje ? " · iniciada em " + fmtData(aberta.data) : "")),
        h("a", { class: "btn prim lg", href: "#/sessao" }, icone("sessao"), "Continuar sessão"),
      ]);
    } else {
      adicionar(esq, [
        h("div", { class: "rotulo" }, "Revisão de hoje"),
        h("div", { class: "grande-num", style: { marginTop: "8px" } }, String(nSessao)),
        h("div", { class: "grande-leg" }, nSessao === 1 ? "tópico para revisar" : "tópicos para revisar"),
        nSessao ? h("a", { class: "btn prim lg", href: "#/sessao" }, icone("sessao"), "Começar sessão")
          : h("div", { class: "t2" }, "Nada vencido hoje. Cadastre as questões que você fizer no Tec."),
      ]);
      if (p.vencidos.length > nSessao) esq.appendChild(h("p", { class: "ajuda" }, (p.vencidos.length - nSessao) + " tópicos ficam para amanhã pelo limite diário."));
    }
    esq.appendChild(h("div", { class: "mini-stats" },
      h("div", null, h("b", null, String(p.totais.topicos)), "tópicos"),
      h("div", null, h("b", null, String(p.totais.questoes)), "questões no banco"),
      h("div", null, h("b", null, String(p.totais.leis)), "leis na biblioteca")));

    const max = Math.max(1, ...p.proximos.map((d) => d.topicos));
    const agenda = h("div", { class: "agenda", role: "img", "aria-label": "Tópicos que vencem nos próximos 14 dias" },
      p.proximos.map((d) => {
        const dia = h("div", { class: "dia" },
          h("span", { class: "val" }, d.topicos ? String(d.topicos) : ""),
          h("div", { class: "col" + (d.topicos ? "" : " zero"), style: { height: (d.topicos / max) * 76 + "px" } }),
          h("span", { class: "rot" }, DIAS_C[dataISO(d.data).getDay()]),
          h("span", { class: "rot" }, d.data.slice(8, 10)));
        G.comTip(dia, () => [fmtLonga(d.data), plural(d.topicos, "tópico") + " para revisar"]);
        return dia;
      }));
    main.appendChild(h("section", { class: "card destaque-hoje" }, esq, h("div", null, h("div", { class: "rotulo" }, "Próximos 14 dias"), agenda)));

    if (p.topicos_com_novas) {
      main.appendChild(alerta("info", h("div", { class: "linha" },
        h("span", { class: "espaco" }, plural(p.topicos_com_novas, "tópico") + " com questões novas desde a última geração."),
        botaoGerar(null, { pequeno: true }))));
    }

    let jobsRecentes = [];
    try { jobsRecentes = await api("/api/jobs"); } catch (e) { /* ignora */ }
    const vistos = new Set();
    const comErro = jobsRecentes.filter((j) => j.status === "erro" && !vistos.has(j.topico_id) && vistos.add(j.topico_id));
    if (comErro.length) {
      main.appendChild(h("h2", { class: "secao-tit" }, "Gerações com erro", h("span", { class: "sub" }, "últimas 24 horas")));
      main.appendChild(h("section", { class: "card" }, h("ul", { class: "lista" }, comErro.map((j) => h("li", null,
        h("div", { class: "princ" }, h("a", { class: "t", href: "#/topico/" + j.topico_id }, j.topico), h("div", { class: "s erro" }, j.erro)),
        h("div", { class: "linha" },
          h("button", { class: "btn sm", onclick: () => gerar(j.topico_id) }, "Tentar de novo"),
          j.pode_tentar_api ? h("button", { class: "btn sm", onclick: () => gerar(j.topico_id, "api") }, "Tentar com API key") : null))))));
    }

    if (p.sem_questoes.length) {
      main.appendChild(h("h2", { class: "secao-tit" }, "Vencidos sem questões", h("span", { class: "sub" }, "ficam fora da sessão até terem questões")));
      main.appendChild(h("section", { class: "card" }, h("ul", { class: "lista" }, p.sem_questoes.map((t) => h("li", null,
        h("div", { class: "princ" }, h("a", { class: "t", href: "#/topico/" + t.id }, t.nome), h("div", { class: "s" }, t.materia)),
        botaoGerar(t.id, { pequeno: true, classe: "" }))))));
    }

    if (p.banco_baixo.length) {
      main.appendChild(h("h2", { class: "secao-tit" }, "Banco baixo", h("span", { class: "sub" }, "menos de 6 questões não vistas recentemente")));
      main.appendChild(h("section", { class: "card" }, h("ul", { class: "lista" }, p.banco_baixo.slice(0, 30).map((t) => h("li", null,
        h("div", { class: "princ" }, h("a", { class: "t", href: "#/topico/" + t.id }, t.nome), h("div", { class: "s" }, t.materia + " · " + plural(t.frescas, "questão fresca", "questões frescas"))),
        botaoGerar(t.id, { pequeno: true, classe: "" }))))));
    }
  }

  /* =====================================================================
     CADASTRAR
     ===================================================================== */
  async function pagCadastrar() {
    const [materias, topicosResp] = await Promise.all([api("/api/materias"), api("/api/topicos")]);
    const topicos = topicosResp.topicos;
    limpar(main);
    main.appendChild(cabecalho("Cadastrar questão"));
    const area = h("div");
    main.appendChild(area);
    let estado = null;

    function telaColar() {
      estado = null;
      limpar(area);
      const toque = window.matchMedia("(max-width: 860px), (pointer: coarse)").matches;
      const zona = h("div", { class: "colar", tabindex: "0", role: toque ? "button" : null, "aria-label": toque ? "Escolher o print da questão" : "Área para colar a questão" },
        icone("colar"),
        toque ? h("div", { class: "tit" }, "Toque para escolher o print")
          : h("div", { class: "tit" }, "Cole a questão aqui"),
        toque ? h("div", { class: "sub" }, "Abre a galeria ou a câmera do celular")
          : h("div", { class: "sub" }, "Pressione ", h("kbd", null, "Ctrl"), " + ", h("kbd", null, "V"), " com o print ou o texto copiado do Tec"));
      const arquivo = h("input", { type: "file", accept: "image/*", class: "oculto", onchange: () => { if (arquivo.files[0]) ler({ imagem: arquivo.files[0] }); } });
      const txt = autoAltura(h("textarea", { class: "inp", rows: "3", placeholder: "Ou cole o texto da questão aqui…" }));
      area.appendChild(zona);
      area.appendChild(h("section", { class: "card", style: { marginTop: "16px" } }, h("div", { class: "card-corpo" },
        h("div", { class: "campo" }, h("span", null, "Outras formas"), txt),
        h("div", { class: "linha", style: { marginTop: "12px" } },
          h("button", { class: "btn prim", onclick: () => { if (txt.value.trim()) ler({ texto: txt.value }); } }, "Ler texto"),
          h("button", { class: "btn", onclick: () => arquivo.click() }, "Escolher imagem"), arquivo))));
      zona.addEventListener("click", () => { if (toque) arquivo.click(); else zona.focus(); });
      if (!toque) zona.focus();
    }

    function aoColar(ev) {
      if (estado) return;
      const itens = ev.clipboardData ? Array.from(ev.clipboardData.items) : [];
      const img = itens.find((i) => i.kind === "file" && i.type.startsWith("image/"));
      if (img) { ev.preventDefault(); ler({ imagem: img.getAsFile() }); return; }
      if (ev.target && ev.target.tagName === "TEXTAREA") return;
      const texto = ev.clipboardData && ev.clipboardData.getData("text/plain");
      if (texto && texto.trim()) { ev.preventDefault(); ler({ texto }); }
    }
    document.addEventListener("paste", aoColar);
    limpeza.push(() => document.removeEventListener("paste", aoColar));

    async function ler({ imagem, texto, reler, uploadId, modo, imagemURL }) {
      limpar(area);
      const url = imagemURL || (imagem ? URL.createObjectURL(imagem) : null);
      const box = h("section", { class: "card" });
      if (url) box.appendChild(h("div", { class: "print-box" }, h("img", { src: url, alt: "Print da questão" })));
      box.appendChild(h("div", { class: "card-corpo" }, carregando(reler ? "Relendo a questão com o " + rotuloModelo("reler") + "…" : "Lendo a questão com o " + rotuloModelo("ler") + "…")));
      area.appendChild(box);
      const fd = new FormData();
      if (imagem) fd.append("imagem", imagem, imagem.name || "print.png");
      if (texto) fd.append("texto", texto);
      if (uploadId) fd.append("upload_id", uploadId);
      if (reler) fd.append("reler", "true");
      if (modo) fd.append("modo", modo);
      try {
        const dados = await api("/api/ler", { method: "POST", form: fd });
        estado = { dados, imagemURL: url, texto };
        cartao();
      } catch (e) {
        limpar(area);
        area.appendChild(caixaErroIA(e, (m) => ler({ imagem, texto, reler, uploadId, modo: m, imagemURL: url })));
        area.appendChild(h("div", { style: { marginTop: "12px" } }, h("button", { class: "btn", onclick: telaColar }, "Voltar")));
      }
    }

    function cartao() {
      const d = estado.dados;
      limpar(area);
      const temas = [...new Set(materias.map((m) => m.tema).filter(Boolean))];
      const dlTema = h("datalist", { id: "lista-temas" }, temas.map((t) => h("option", { value: t })));
      const dlMat = h("datalist", { id: "lista-materias" }, materias.map((m) => h("option", { value: m.nome })));
      const dlAss = h("datalist", { id: "lista-assuntos" });
      const fTema = h("input", { class: "inp", value: d.tema || "", list: "lista-temas" });
      const fMateria = h("input", { class: "inp", value: d.materia, list: "lista-materias" });
      const fAssunto = h("input", { class: "inp", value: d.assunto || "", list: "lista-assuntos" });
      const fProva = h("input", { class: "inp", value: d.tec_prova || "", placeholder: "VUNESP - 2026 - Cargo (Órgão)" });
      const daMateria = () => topicos.filter((t) => t.materia.toLowerCase() === fMateria.value.trim().toLowerCase());
      function atualizarListas() {
        limpar(dlAss);
        daMateria().forEach((t) => dlAss.appendChild(h("option", { value: t.nome })));
      }
      const avisoTop = h("div", { class: "ajuda" });
      function checarTopico() {
        const existe = daMateria().find((t) => t.nome.toLowerCase() === fAssunto.value.trim().toLowerCase());
        avisoTop.textContent = existe ? "Assunto já cadastrado · " + nomeEtapa(existe.etapa, topicosResp.max_etapa).toLowerCase() + " · próxima revisão " + relativo(existe.proxima_revisao, hojeISO())
          : "Assunto novo: primeira revisão amanhã.";
      }
      fMateria.addEventListener("input", () => {
        atualizarListas(); checarTopico();
        const m = materias.find((x) => x.nome.toLowerCase() === fMateria.value.trim().toLowerCase());
        if (m && m.tema) fTema.value = m.tema;
      });
      fAssunto.addEventListener("input", checarTopico);
      atualizarListas(); checarTopico();

      const fEnun = h("textarea", { class: "inp", "aria-label": "Enunciado", rows: "2", style: { fontSize: "16px" } });
      fEnun.value = d.enunciado;
      autoAltura(fEnun);
      const alts = (d.alternativas || []).map((a) => ({ letra: a.letra, texto: a.texto }));
      let gabarito = d.gabarito || "";
      let gabEditado = false;
      let situacao = d.situacao;
      let marcada = d.marcada || "";
      const altsBox = h("div", { class: "alts" });
      const situacaoBox = h("div");

      function desenharAlts() {
        limpar(altsBox);
        alts.forEach((a) => {
          const ta = autoAltura(h("textarea", { class: "inp", rows: "1", "aria-label": "Alternativa " + a.letra,
            style: { border: "0", background: "transparent", padding: "1px 0", minHeight: "0", resize: "none", boxShadow: "none", overflow: "hidden" },
            oninput: (ev) => { a.texto = ev.target.value; } }));
          ta.value = a.texto;
          const certa = gabarito === a.letra;
          const errada = situacao === "errou" && marcada === a.letra && !certa;
          altsBox.appendChild(h("div", { class: "alt" + (certa ? " certa" : "") + (errada ? " errada" : ""), style: { cursor: "default" } },
            h("button", { class: "l", title: "Marcar " + a.letra + " como gabarito", "aria-label": "Gabarito " + a.letra, style: { cursor: "pointer", padding: 0 },
              onclick: () => { gabarito = a.letra; gabEditado = true; if (situacao === "acertou") marcada = a.letra; desenharAlts(); desenharSituacao(); } }, a.letra),
            ta));
        });
      }

      function desenharSituacao() {
        limpar(situacaoBox);
        situacaoBox.appendChild(h("div", { class: "linha" },
          h("div", { class: "seg cores", role: "group", "aria-label": "Situação no Tec" }, [["errou", "Errei"], ["acertou", "Acertei"], ["nao_respondeu", "Não respondi"]].map(([v, n]) =>
            h("button", { "data-v": v, "aria-pressed": String(situacao === v), onclick: () => { situacao = v; if (v === "acertou") marcada = gabarito; if (v === "nao_respondeu") marcada = ""; desenharSituacao(); desenharAlts(); } }, n))),
          situacao === "errou" ? h("label", { class: "linha", style: { gap: "8px" } }, h("span", { class: "rotulo" }, "Marquei"),
            h("select", { class: "inp", style: { width: "80px" }, onchange: (ev) => { marcada = ev.target.value; desenharAlts(); } },
              h("option", { value: "" }, "—"), alts.map((a) => h("option", { value: a.letra, selected: marcada === a.letra }, a.letra)))) : null));
        if (situacao === "nao_respondeu") situacaoBox.appendChild(h("div", { class: "ajuda", style: { marginTop: "6px" } }, "Gabarito provisório sugerido pelo Claude. Ele é conferido com o texto da lei ao gerar questões."));
      }
      desenharAlts();
      desenharSituacao();

      const btnSalvar = h("button", { class: "btn prim lg", onclick: salvar }, "Confirmar");
      const imgBox = estado.imagemURL ? h("div", { class: "print-box" }, h("img", { src: estado.imagemURL, alt: "Print da questão", title: "Clique para ampliar",
        onclick: (ev) => ev.currentTarget.parentElement.classList.toggle("aberto") })) : null;

      area.appendChild(h("section", { class: "card" },
        imgBox,
        h("div", { class: "card-corpo" },
          d.confianca < 0.8 ? h("div", { style: { marginBottom: "16px" } }, alerta("aviso", "Leitura com pouca confiança. Confira os campos. " + (d.observacoes || ""))) : null,
          h("div", { class: "cad-campos" },
            h("label", { class: "campo" }, h("span", null, "Tema"), fTema),
            h("label", { class: "campo" }, h("span", null, "Matéria"), fMateria),
            h("label", { class: "campo" }, h("span", null, "Assunto"), fAssunto, avisoTop),
            h("label", { class: "campo largo" }, h("span", null, "Prova"), fProva)),
          h("div", { class: "campo", style: { marginTop: "18px" } }, h("span", null, "Enunciado"), fEnun),
          h("div", { class: "campo", style: { marginTop: "14px" } }, h("span", null, "Alternativas"), altsBox),
          h("div", { class: "campo", style: { marginTop: "16px" } }, h("span", null, "Situação no Tec"), situacaoBox)),
        h("div", { class: "cad-rodape" }, btnSalvar,
          h("button", { class: "btn", onclick: () => ler({ texto: estado.texto, uploadId: d.upload_id, reler: true, imagemURL: estado.imagemURL }) }, "Reler com Sonnet"),
          h("button", { class: "btn fant", onclick: telaColar }, "Descartar"),
          h("span", { class: "espaco" }),
          h("span", { class: "leitura", title: d.observacoes || "" }, "Leitura " + Math.round((d.confianca || 0) * 100) + "% confiável")),
        dlTema, dlMat, dlAss));

      async function salvar() {
        btnSalvar.disabled = true;
        try {
          const r = await api("/api/questoes", { method: "POST", body: {
            tema: fTema.value, materia: fMateria.value, assunto: fAssunto.value, lei_seca: d.lei_seca, dispositivo_ref: d.dispositivo_ref || "",
            tec_codigo: d.tec_codigo || "", tec_prova: fProva.value,
            enunciado: fEnun.value, alternativas: alts, situacao, marcada, gabarito, gabarito_editado: gabEditado, upload_id: d.upload_id,
          } });
          let msg = "Questão salva em " + fAssunto.value + ".";
          if (r.voltou_etapa_0) msg += " Erro novo no Tec: o assunto volta para revisão amanhã.";
          toast(msg);
          if (r.topico_novo) topicos.push({ id: r.topico_id, nome: fAssunto.value, materia: fMateria.value, etapa: 0, proxima_revisao: somaDias(hojeISO(), 1) });
          if (!materias.find((m) => m.nome.toLowerCase() === fMateria.value.trim().toLowerCase())) materias.push({ nome: fMateria.value.trim(), tema: fTema.value.trim() });
          atualizarPainel();
          telaColar();
          window.scrollTo(0, 0);
        } catch (e) {
          toast(e.message, true);
          btnSalvar.disabled = false;
        }
      }
      const atalho = (ev) => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey) && estado) { ev.preventDefault(); salvar(); } };
      document.addEventListener("keydown", atalho);
      limpeza.push(() => document.removeEventListener("keydown", atalho));
    }

    telaColar();
  }

  /* =====================================================================
     QUESTÃO NO ESTILO DO TEC
     ===================================================================== */
  function cabecalhoQuestao(q, opc) {
    const c = opc.contagem;
    const cab = h("div", { class: "q-cab" },
      h("div", { class: "info" },
        h("div", { class: "titulo" }, opc.titulo,
          c ? h("span", { class: "cont" }, " (", h("b", null, String(c.resolvidas)), " Resolvidas, ", h("b", { class: "ok" }, String(c.acertos)), " Acertos e ", h("b", { class: "erro" }, String(c.erros)), " Erros)") : null),
        h("div", null, "Matéria: ", h("a", { href: "#/topicos" }, opc.materia)),
        h("div", null, "Assunto: ", h("a", { href: "#/topico/" + q.topico_id }, opc.topico || opc.assunto))),
      opc.acoes && opc.acoes.length ? h("div", { class: "acoes-q" }, opc.acoes) : null);
    let prova;
    if (q.origem === "real") {
      prova = h("div", { class: "q-prova" }, icone("link"),
        q.tec_codigo ? h("span", { class: "cod" }, "#" + q.tec_codigo) : null,
        h("span", null, q.tec_prova || "Questão real do TecConcursos"),
        h("span", { class: "espaco" }));
    } else {
      prova = h("div", { class: "q-prova" }, icone("link"), h("span", null, "Inédita – estilo Vunesp"),
        h("span", { class: "espaco" }));
    }
    return [cab, prova];
  }

  /* =====================================================================
     SESSÃO
     ===================================================================== */
  async function pagSessao(arg) {
    let st = arg ? await api("/api/sessao/" + arg) : await api("/api/sessao");
    limpar(main);
    const bt = bannerTeste();

    if (!st.sessao) {
      const p = painelCache;
      const n = p ? p.vencidos_na_sessao : 0;
      main.appendChild(cabecalho("Sessão diária", "Todas as matérias vencidas, misturadas, como num simulado."));
      if (bt) main.appendChild(bt);
      if (!n) {
        main.appendChild(card(null, null, null, h("div", { class: "vazio" }, "Nenhum tópico com questões vence hoje.",
          p && p.sem_questoes.length ? h("div", { style: { marginTop: "6px" } }, plural(p.sem_questoes.length, "tópico vencido", "tópicos vencidos") + " sem questões. Gere questões para eles em Hoje.") : null)));
        return;
      }
      const btn = h("button", { class: "btn prim lg", onclick: async () => {
        btn.disabled = true;
        try {
          st = await api("/api/sessao/iniciar", { method: "POST" });
          if (!st.sessao) { toast("Nenhuma questão disponível para os tópicos vencidos.", true); btn.disabled = false; return; }
          await atualizarPainel(); desenharNav("sessao");
          rodar();
        } catch (e) { toast(e.message, true); btn.disabled = false; }
      } }, icone("sessao"), "Começar sessão");
      const nq = p && p.modo_teste ? Math.min(60, p.totais.questoes) : n;
      main.appendChild(card(null, null, null, h("div", { class: "card-corpo", style: { textAlign: "center", padding: "40px 18px" } },
        h("div", { class: "grande-num" }, String(nq)),
        h("div", { class: "grande-leg" }, p && p.modo_teste ? (nq === 1 ? "questão no modo de teste" : "questões no modo de teste") : (n === 1 ? "assunto para revisar" : "assuntos para revisar")), btn)));
      aoTeclar((ev) => { if (ev.key === "Enter" && !btn.disabled) btn.click(); });
      return;
    }

    if (st.sessao.status === "concluida") { resumo(); return; }
    rodar();

    function rodar() {
      const i = st.itens.findIndex((it) => it.resposta === null && !it.invalidada);
      if (i === -1) { concluir(); return; }
      mostrar(i);
    }

    async function concluir() {
      limpar(main);
      main.appendChild(carregando("Fechando a sessão…"));
      try {
        st = await api("/api/sessao/" + st.sessao.id + "/concluir", { method: "POST" });
        await atualizarPainel(); desenharNav("sessao");
        resumo();
      } catch (e) { limpar(main); main.appendChild(alerta("erro", e.message)); }
    }

    function contagem() {
      const feitos = st.itens.filter((x) => x.resposta !== null && !x.invalidada);
      const acertos = feitos.filter((x) => x.correta).length;
      return { resolvidas: feitos.length, acertos, erros: feitos.length - acertos };
    }

    function mostrar(i) {
      rodarLimpeza();
      const it = st.itens[i];
      const q = it.questao;
      const total = st.itens.length;
      const feitas = st.itens.filter((x) => x.resposta !== null || x.invalidada).length;
      let selecionada = it.resposta;
      let respondida = it.resposta !== null;
      const riscadas = new Set();

      limpar(main);
      if (bannerTeste()) main.appendChild(bannerTeste());
      main.appendChild(h("div", { class: "sessao-barra" },
        h("span", { class: "num" }, feitas + " de " + total + " respondidas"),
        h("div", { class: "progresso", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(feitas) },
          h("i", { style: { width: (100 * feitas) / total + "%" } })),
        h("a", { href: "#/hoje", class: "btn sm" }, "Pausar")));

      const altsBox = h("div", { class: "alts", role: "radiogroup", "aria-label": "Alternativas" });
      const acoes = h("div", { class: "q-acoes q-acoes-fixas" });
      const fb = h("div");
      const invBox = h("div");
      const invalidar = h("button", { class: "ico-btn", title: "Essa questão está errada", "aria-label": "Essa questão está errada", onclick: () => {
        limpar(invBox);
        invBox.appendChild(h("div", { style: { marginBottom: "14px" } }, painelInvalidar(q, () => { it.invalidada = true; toast("Questão invalidada. Ela não conta nesta revisão."); rodar(); }, () => limpar(invBox))));
      } }, icone("bandeira"));
      const opcCab = () => ({ titulo: "Questão " + (i + 1) + " de " + total, contagem: contagem(), materia: it.materia, assunto: it.assunto, topico: it.topico, acoes: [invalidar] });
      let cabEls = cabecalhoQuestao(q, opcCab());
      main.appendChild(h("article", { class: "card q-card" },
        cabEls,
        h("div", { class: "q-corpo" }, invBox, h("p", { class: "q-enun" }, q.enunciado), altsBox, fb, acoes)));
      function atualizarCab() {
        const novo = cabecalhoQuestao(q, opcCab());
        cabEls[0].replaceWith(novo[0]);
        cabEls = novo;
      }

      function desenharAlts() {
        limpar(altsBox);
        q.alternativas.forEach((a) => {
          let cls = "alt";
          if (respondida) {
            if (a.letra === q.gabarito) cls += " certa";
            if (a.letra === selecionada) cls += a.letra === q.gabarito ? " sel" : " errada";
          } else if (a.letra === selecionada) cls += " sel";
          if (riscadas.has(a.letra) && !respondida) cls += " riscada";
          altsBox.appendChild(h("button", {
            class: cls, disabled: respondida, role: "radio", "aria-checked": String(a.letra === selecionada),
            onclick: () => { selecionada = a.letra; desenharAlts(); desenharAcoes(); },
            oncontextmenu: (ev) => { ev.preventDefault(); if (riscadas.has(a.letra)) riscadas.delete(a.letra); else riscadas.add(a.letra); desenharAlts(); },
            title: respondida ? null : "Clique para marcar · botão direito para riscar",
          }, h("span", { class: "l" }, a.letra), h("span", { class: "t" }, a.texto)));
        });
      }

      const vizinho = (passo) => {
        for (let j = i + passo; j >= 0 && j < total; j += passo) if (!st.itens[j].invalidada) return j;
        return -1;
      };
      const anterior = vizinho(-1), seguinte = vizinho(1);
      function desenharAcoes() {
        limpar(acoes);
        acoes.appendChild(h("button", { class: "btn lg seta", disabled: anterior === -1, title: "Questão anterior", "aria-label": "Questão anterior", onclick: () => mostrar(anterior) }, icone("voltar")));
        if (!respondida) {
          acoes.appendChild(h("button", { class: "btn prim lg", disabled: !selecionada, onclick: responder }, "Responder"));
        } else {
          const terminou = st.itens.every((x) => x.resposta !== null || x.invalidada);
          acoes.appendChild(h("button", { class: "btn prim lg", onclick: () => rodar() }, terminou ? "Ver resultado" : "Próxima questão"));
        }
        acoes.appendChild(h("button", { class: "btn lg seta", disabled: seguinte === -1, title: "Próxima questão", "aria-label": "Próxima questão", onclick: () => mostrar(seguinte) }, icone("avancar")));
      }

      async function responder() {
        if (!selecionada || respondida) return;
        try {
          const r = await api("/api/sessao/responder", { method: "POST", body: { item_id: it.item_id, resposta: selecionada } });
          it.resposta = selecionada; it.correta = r.correta;
          Object.assign(q, r.questao);
          respondida = true;
          desenharAlts(); desenharAcoes(); atualizarCab();
          limpar(fb); fb.appendChild(blocoFeedback(q, selecionada, r.correta));
          if (painelCache && painelCache.sessao_aberta) { painelCache.sessao_aberta.respondidas++; desenharNav("sessao"); }
        } catch (e) { toast(e.message, true); }
      }

      desenharAlts(); desenharAcoes();
      if (respondida) fb.appendChild(blocoFeedback(q, selecionada, it.correta));

      aoTeclar((ev) => {
        if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
        const k = ev.key.toUpperCase();
        if (!respondida && q.alternativas.some((a) => a.letra === k)) { selecionada = k; desenharAlts(); desenharAcoes(); ev.preventDefault(); }
        else if (ev.key === "Enter") { ev.preventDefault(); if (!respondida) responder(); else rodar(); }
        else if (ev.key === "ArrowLeft" && anterior !== -1) { ev.preventDefault(); mostrar(anterior); }
        else if (ev.key === "ArrowRight" && seguinte !== -1) { ev.preventDefault(); mostrar(seguinte); }
      });
    }

    function resumo() {
      rodarLimpeza();
      const r = st.resumo;
      limpar(main);
      main.appendChild(cabecalho(r.teste ? "Sessão de teste concluída" : "Sessão concluída", fmtLonga(st.sessao.data), h("a", { href: "#/hoje", class: "btn" }, "Voltar para Hoje")));
      if (r.teste) main.appendChild(alerta("aviso", "Sessão de teste: etapas e datas de revisão não foram alteradas, e ela não entra nas estatísticas."));
      main.appendChild(h("section", { class: "card geral", style: { gridTemplateColumns: "1fr 1fr" } },
        h("div", { class: "numeros" },
          numero("Questões", r.total), numero("Aproveitamento", Math.round(r.pct) + "%"),
          numero("Acertos", r.acertos, "ok"), numero("Erros", r.total - r.acertos, "erro")),
        h("div", { class: "grafico" }, G.rosca(r.acertos, r.total - r.acertos, 170))));

      main.appendChild(h("h2", { class: "secao-tit" }, "Resultado por tópico"));
      main.appendChild(h("section", { class: "card tab-wrap" }, h("table", { class: "tab" },
        h("thead", null, h("tr", null, h("th", null, "Tópico"), h("th", { class: "dir" }, "Acertos"), h("th", null, "Etapa"), h("th", null, "Próxima revisão"))),
        h("tbody", null, r.topicos.map((t) => {
          const p = pct(t.acertos, t.total);
          const subiu = t.etapa_depois > t.etapa_antes, caiu = t.etapa_depois < t.etapa_antes;
          return h("tr", null,
            h("td", null, h("a", { href: "#/topico/" + t.topico_id }, t.topico), h("div", { class: "mudo", style: { fontSize: "13px" } }, t.materia)),
            h("td", { class: "dir num" }, t.acertos + "/" + t.total + " ", h("span", { class: "etq " + (p >= 80 ? "ok" : p < 50 ? "erro" : "aviso") }, p + "%")),
            h("td", null, nomeEtapa(t.etapa_antes, 6) + " → ", h("b", { class: subiu ? "ok" : caiu ? "erro" : "" }, nomeEtapa(t.etapa_depois, 6))),
            h("td", { class: "num" }, fmtData(t.proxima)));
        })))));

      if (r.erradas.length) {
        main.appendChild(h("h2", { class: "secao-tit" }, "Questões que você errou", h("span", { class: "sub" }, "clique para rever e pedir explicação")));
        r.erradas.forEach((e, n) => {
          const it = st.itens.find((x) => x.item_id === e.item_id);
          if (!it) return;
          main.appendChild(questaoExpansivel(it.questao, { titulo: "Erro " + (n + 1), materia: it.materia, assunto: it.assunto, topico: it.topico, resposta: e.resposta }));
        });
      }
    }
  }

  function questaoExpansivel(q, opc) {
    const corpo = h("div", { class: "oculto" });
    const extras = opc.extras || null;
    const resumoBtn = h("button", { class: "alt", style: { gridTemplateColumns: "1fr auto", background: "var(--sup)", borderBottom: "0" }, onclick: () => {
      if (!corpo.firstChild) {
        adicionar(corpo, cabecalhoQuestao(q, { titulo: opc.titulo, materia: opc.materia, assunto: opc.assunto, topico: opc.topico }));
        corpo.appendChild(h("div", { class: "q-corpo" }, h("p", { class: "q-enun" }, q.enunciado),
          h("div", { class: "alts" }, q.alternativas.map((a) => h("div", { class: "alt" + (a.letra === q.gabarito ? " certa" : "") + (a.letra === opc.resposta && a.letra !== q.gabarito ? " errada" : "") + (a.letra === opc.resposta && a.letra === q.gabarito ? " sel" : ""), style: { cursor: "default" } },
            h("span", { class: "l" }, a.letra), h("span", { class: "t" }, a.texto)))),
          blocoFeedback(q, opc.resposta, opc.resposta === q.gabarito)));
        if (extras) corpo.appendChild(extras);
      }
      corpo.classList.toggle("oculto");
    } }, h("span", { class: "t" }, h("b", null, opc.topico + " — "), q.enunciado.slice(0, 150) + (q.enunciado.length > 150 ? "…" : "")),
      opc.tags || h("span", { class: "mudo num", style: { fontSize: "13px" } }, opc.resposta ? "marcou " + opc.resposta + " · gabarito " + q.gabarito : "gabarito " + (q.gabarito || "?")));
    return h("section", { class: "card q-card", style: { marginBottom: "10px", opacity: q.status && q.status !== "ativa" ? 0.6 : 1 } }, resumoBtn, corpo);
  }

  function blocoFeedback(q, resposta, correta) {
    const box = h("div");
    if (resposta) {
      box.appendChild(h("div", { class: "resultado " + (correta ? "ok" : "erro") }, icone(correta ? "certo" : "errado"),
        correta ? [h("b", null, "Você acertou!"), " Boa!"] : [h("b", null, "Você errou."), " Gabarito: " + q.gabarito + "."]));
    }
    const corpo = h("div", { class: "corpo" });
    if (q.justificativa) corpo.appendChild(h("div", null, q.justificativa));
    if (q.explicacoes && q.explicacoes.length) corpo.appendChild(h("dl", null, q.explicacoes.flatMap((x) => [h("dt", null, x.letra), h("dd", null, x.motivo)])));
    if (q.trecho_base) corpo.appendChild(h("div", { class: "trecho" }, q.trecho_base));
    const meta = [];
    if (q.dispositivo_ref) meta.push("Dispositivo: " + q.dispositivo_ref);
    if (q.gabarito_origem === "claude_provisorio") meta.push("gabarito provisório, ainda não conferido");
    if (q.gabarito_origem === "claude_conferido") meta.push("gabarito definido pelo Claude");
    if (meta.length) corpo.appendChild(h("div", { class: "ajuda", style: { marginTop: "10px" } }, meta.join(" · ")));
    if (corpo.firstChild) box.appendChild(h("div", { class: "comentario" }, h("div", { class: "cab" }, icone("livro"), "Comentário"), corpo));

    const expl = h("div");
    const btn = h("button", { class: "btn", onclick: () => pedir(null) }, icone("info"), "Explicar melhor");
    async function pedir(modo) {
      btn.disabled = true;
      limpar(expl);
      expl.appendChild(h("div", { style: { marginTop: "14px" } }, carregando("Explicando com o " + rotuloModelo("explicar") + "…")));
      try {
        const r = await api("/api/questoes/" + q.id + "/explicar", { method: "POST", body: { resposta, modo } });
        mostrarExpl(r.texto);
      } catch (e) {
        limpar(expl);
        expl.appendChild(h("div", { style: { marginTop: "14px" } }, caixaErroIA(e, pedir)));
        btn.disabled = false;
      }
    }
    function mostrarExpl(t) {
      limpar(expl);
      expl.appendChild(h("div", { class: "comentario" }, h("div", { class: "cab" }, icone("info"), "Explicação do professor"), h("div", { class: "corpo" }, textoRico(t))));
      btn.classList.add("oculto");
    }
    box.appendChild(h("div", { class: "q-acoes" }, btn));
    box.appendChild(expl);
    if (q.explicacao_detalhada) mostrarExpl(q.explicacao_detalhada);
    return box;
  }

  function painelInvalidar(q, depois, cancelar) {
    const sel = h("select", { class: "inp", style: { width: "auto" }, "aria-label": "Motivo" },
      h("option", { value: "" }, "Motivo (opcional)"),
      h("option", { value: "gabarito errado" }, "Gabarito errado"),
      h("option", { value: "ambígua" }, "Ambígua"),
      h("option", { value: "fora do tópico" }, "Fora do tópico"));
    return alerta("aviso", h("div", { style: { marginBottom: "8px" } }, "Invalidar esta questão? Ela sai do banco e não conta em nenhuma estatística."),
      h("div", { class: "linha" }, sel,
        h("button", { class: "btn sm perigo", onclick: async () => {
          try { await api("/api/questoes/" + q.id + "/invalidar", { method: "POST", body: { motivo: sel.value } }); depois(); }
          catch (e) { toast(e.message, true); }
        } }, "Invalidar"),
        h("button", { class: "btn sm fant", onclick: cancelar }, "Cancelar")));
  }

  /* =====================================================================
     TÓPICOS
     ===================================================================== */
  const filtroTopicos = { busca: "", tipo: "todos" };
  async function pagTopicos() {
    const { topicos, max_etapa } = await api("/api/topicos");
    const hoje = painelCache ? painelCache.hoje : hojeISO();
    limpar(main);
    const novas = topicos.filter((t) => t.novas > 0).length;
    main.appendChild(cabecalho("Assuntos", plural(topicos.length, "assunto") + " em " + plural(new Set(topicos.map((t) => t.materia)).size, "matéria"),
      botaoGerar(null, { desabilitado: !novas, titulo: "Gera para todos os assuntos com questões novas", rotulo: "Gerar questões" + (novas ? " (" + novas + ")" : "") })));

    const busca = h("input", { class: "inp", type: "search", placeholder: "Buscar tema, matéria ou assunto", value: filtroTopicos.busca, style: { maxWidth: "340px" } });
    const tipos = [["todos", "Todos"], ["vencidos", "Vencidos"], ["novas", "Com questões novas"], ["baixo", "Banco baixo"], ["semtexto", "Sem texto-base"]];
    const seg = h("div", { class: "seg" });
    const corpo = h("div");
    function desenharSeg() {
      limpar(seg);
      tipos.forEach(([v, n]) => seg.appendChild(h("button", { "aria-pressed": String(filtroTopicos.tipo === v), onclick: () => { filtroTopicos.tipo = v; desenharSeg(); desenhar(); } }, n)));
    }
    busca.addEventListener("input", () => { filtroTopicos.busca = busca.value; desenhar(); });
    main.appendChild(h("div", { class: "linha", style: { marginBottom: "16px" } }, busca, seg));
    main.appendChild(corpo);
    desenharSeg();

    function desenhar() {
      limpar(corpo);
      const b = filtroTopicos.busca.trim().toLowerCase();
      const lista = topicos.filter((t) => {
        if (b && !(t.nome + " " + (t.tema || "") + " " + t.materia).toLowerCase().includes(b)) return false;
        if (filtroTopicos.tipo === "vencidos") return t.proxima_revisao <= hoje;
        if (filtroTopicos.tipo === "novas") return t.novas > 0;
        if (filtroTopicos.tipo === "baixo") return t.banco_baixo;
        if (filtroTopicos.tipo === "semtexto") return t.sem_texto_base;
        return true;
      });
      if (!lista.length) { corpo.appendChild(card(null, null, null, h("div", { class: "vazio" }, topicos.length ? "Nenhum assunto com esse filtro." : "Nenhum assunto ainda. Comece cadastrando uma questão."))); return; }
      const tbody = h("tbody");
      let temaAtual = null, matAtual = null;
      for (const t of lista) {
        if ((t.tema || "") !== temaAtual) { temaAtual = t.tema || ""; matAtual = null; tbody.appendChild(h("tr", { class: "grupo" }, h("td", { colspan: "5" }, temaAtual || "Sem tema"))); }
        if (t.materia !== matAtual) { matAtual = t.materia; tbody.appendChild(h("tr", { class: "subgrupo" }, h("td", { colspan: "5" }, t.materia))); }
        const venc = t.proxima_revisao <= hoje;
        tbody.appendChild(h("tr", { class: "clic", onclick: () => { location.hash = "#/topico/" + t.id; } },
          h("td", { style: { paddingLeft: "36px" } }, h("a", { href: "#/topico/" + t.id, onclick: (ev) => ev.stopPropagation(), style: { fontWeight: 600 } }, t.nome)),
          h("td", { class: "col-etapa" }, etapas(t.etapa, max_etapa)),
          h("td", null, venc ? h("span", { class: "etq azul" }, t.proxima_revisao === hoje ? "hoje" : "vencido " + relativo(t.proxima_revisao, hoje)) : h("span", { class: "t2" }, relativo(t.proxima_revisao, hoje))),
          h("td", { class: "num t2 col-banco", style: { whiteSpace: "nowrap" } }, t.reais + " reais · " + t.geradas + " geradas"),
          h("td", null, h("span", { class: "linha", style: { gap: "5px" } },
            t.novas ? h("span", { class: "etq azul" }, t.novas + " nova" + (t.novas > 1 ? "s" : "")) : null,
            t.banco_baixo ? h("span", { class: "etq aviso" }, "banco baixo") : null,
            t.sem_texto_base ? h("span", { class: "etq aviso", title: "Sem texto-base, conferir dispositivos" }, "sem texto-base") : null))));
      }
      corpo.appendChild(h("section", { class: "card tab-wrap" }, h("table", { class: "tab" },
        h("thead", null, h("tr", null, h("th", { style: { paddingLeft: "36px" } }, "Assunto"), h("th", { class: "col-etapa" }, "Etapa"), h("th", null, "Próxima revisão"), h("th", { class: "col-banco" }, "Banco"), h("th", { class: "col-tags" }, ""))),
        tbody)));
    }
    desenhar();
  }

  async function pagTopico(id) {
    const d = await api("/api/topicos/" + id);
    const t = d.topico;
    const hoje = painelCache ? painelCache.hoje : hojeISO();
    limpar(main);
    main.appendChild(h("a", { class: "voltar", href: "#/topicos" }, icone("voltar"), "Assuntos"));
    main.appendChild(cabecalho(t.nome, [t.tema, t.materia].filter(Boolean).join(" › "),
      botaoGerar(t.id)));

    const b = d.banco;
    main.appendChild(h("div", { class: "grade g4" },
      [["Etapa", h("div", { class: "linha" }, etapas(t.etapa, d.max_etapa), nomeEtapa(t.etapa, d.max_etapa))],
        ["Próxima revisão", fmtData(t.proxima_revisao) + " · " + relativo(t.proxima_revisao, hoje)],
        ["Questões reais", String(b.reais)],
        ["Questões geradas", b.geradas + " · " + b.frescas + " frescas"]].map(([k, v]) =>
        h("section", { class: "card card-corpo" }, h("div", { class: "rotulo" }, k), h("div", { style: { fontSize: "17px", fontWeight: 600, marginTop: "4px" } }, v)))));

    if (b.novas) main.appendChild(alerta("info", plural(b.novas, "questão real nova", "questões reais novas") + " desde a última geração. Elas já entram na sessão; aperte \"Gerar questões\" para completar o banco."));
    if (b.banco_baixo) main.appendChild(alerta("aviso", "Banco baixo: " + plural(b.frescas, "questão não vista", "questões não vistas") + " recentemente."));

    const fNome = h("input", { class: "inp", value: t.nome });
    const fMat = h("input", { class: "inp", value: t.materia });
    const fTema = h("input", { class: "inp", value: t.tema || "" });
    main.appendChild(h("h2", { class: "secao-tit" }, "Dados do assunto"));
    main.appendChild(card(null, null, null, h("div", { class: "card-corpo" },
      h("div", { class: "cad-campos" },
        h("label", { class: "campo" }, h("span", null, "Tema"), fTema),
        h("label", { class: "campo" }, h("span", null, "Matéria"), fMat),
        h("label", { class: "campo" }, h("span", null, "Assunto"), fNome)),
      h("div", { class: "linha", style: { marginTop: "16px" } },
        h("button", { class: "btn prim", onclick: async () => {
          try { await api("/api/topicos/" + t.id, { method: "PATCH", body: { nome: fNome.value, materia: fMat.value, tema: fTema.value } }); toast("Assunto atualizado."); rotear(); }
          catch (e) { toast(e.message, true); }
        } }, "Salvar"),
        h("span", { class: "espaco" }),
        h("button", { class: "btn perigo", onclick: async () => {
          if (!confirm("Apagar o assunto \"" + t.nome + "\" com todas as questões e revisões? Não dá para desfazer.")) return;
          await api("/api/topicos/" + t.id, { method: "DELETE" }); location.hash = "#/topicos";
        } }, "Apagar assunto")))));

    if (t.lei_seca) {
      main.appendChild(h("h2", { class: "secao-tit" }, "Texto-base", d.lei ? h("a", { class: "sub", href: "#/lei/" + d.lei.id }, d.lei.sigla + " – " + d.lei.nome) : null));
      if (d.texto_base) {
        const pre = h("div", { class: "card-corpo lei-texto" });
        d.texto_base.split("\n").forEach((l, i) => {
          if (i) pre.appendChild(document.createTextNode("\n"));
          if (l.startsWith(">>> ")) pre.appendChild(h("span", { class: "alvo" }, l.slice(4)));
          else pre.appendChild(document.createTextNode(l));
        });
        main.appendChild(h("section", { class: "card" }, pre));
      } else {
        main.appendChild(alerta("aviso", "Sem texto-base, conferir dispositivos. ",
          "Envie o PDF da lei na Biblioteca de leis. O app liga os artigos cobrados nas questões deste assunto automaticamente."));
      }
    }

    main.appendChild(h("h2", { class: "secao-tit" }, "Material de apoio", h("span", { class: "sub" }, t.lei_seca ? "opcional; lei seca usa o texto-base" : "PDF de teoria para ancorar a geração")));
    const arq = h("input", { type: "file", accept: "application/pdf", class: "oculto", onchange: async () => {
      if (!arq.files[0]) return;
      const fd = new FormData(); fd.append("arquivo", arq.files[0]); fd.append("nome", arq.files[0].name);
      try { await api("/api/topicos/" + t.id + "/material", { method: "POST", form: fd }); toast("Material enviado."); rotear(); }
      catch (e) { toast(e.message, true); }
    } });
    main.appendChild(h("section", { class: "card" },
      d.materiais.length ? h("ul", { class: "lista" }, d.materiais.map((m) => h("li", null,
        h("div", { class: "princ" }, h("div", { class: "t" }, m.nome), h("div", { class: "s" }, m.tamanho.toLocaleString("pt-BR") + " caracteres · enviado em " + fmtData(m.enviado_em))),
        h("button", { class: "btn sm perigo", onclick: async () => { await api("/api/materiais/" + m.id, { method: "DELETE" }); rotear(); } }, "Remover"))))
        : h("div", { class: "card-corpo mudo" }, t.lei_seca ? "Nenhum material." : "Sem material. A geração usa as questões reais e o conhecimento do Claude."),
      h("div", { class: "cad-rodape", style: { position: "static" } }, h("button", { class: "btn", onclick: () => arq.click() }, "Enviar PDF"), arq)));

    const ativas = d.questoes.filter((q) => q.status === "ativa");
    const inval = d.questoes.filter((q) => q.status !== "ativa");
    main.appendChild(h("h2", { class: "secao-tit" }, "Questões", h("span", { class: "sub" }, ativas.length + " ativas" + (inval.length ? " · " + inval.length + " invalidadas" : ""))));
    if (!d.questoes.length) main.appendChild(card(null, null, null, h("div", { class: "vazio" }, "Nenhuma questão.")));
    d.questoes.forEach((q) => main.appendChild(itemQuestao(q, t)));

    if (d.revisoes.length) {
      main.appendChild(h("h2", { class: "secao-tit" }, "Histórico de revisões"));
      main.appendChild(h("section", { class: "card tab-wrap" }, h("table", { class: "tab" },
        h("thead", null, h("tr", null, h("th", null, "Data"), h("th", { class: "dir" }, "Acertos"), h("th", null, "Etapa"), h("th", null, "Próxima"))),
        h("tbody", null, d.revisoes.map((r) => h("tr", null, h("td", { class: "num" }, fmtData(r.data)),
          h("td", { class: "dir num" }, r.acertos + "/" + r.total),
          h("td", null, nomeEtapa(r.etapa_antes, d.max_etapa) + " → " + nomeEtapa(r.etapa_depois, d.max_etapa)),
          h("td", { class: "num" }, fmtData(r.proxima))))))));
    }
  }

  function itemQuestao(q, t) {
    const tags = h("span", { class: "linha", style: { gap: "5px", justifyContent: "flex-end" } },
      q.origem === "real" ? h("span", { class: "etq azul" }, "real") : h("span", { class: "etq" }, "inédita"),
      q.origem === "real" && !q.no_banco ? h("span", { class: "etq aviso" }, "nova") : null,
      q.status !== "ativa" ? h("span", { class: "etq erro" }, "invalidada" + (q.motivo_invalidacao ? ": " + q.motivo_invalidacao : "")) : null,
      h("span", { class: "mudo num", style: { fontSize: "13px" } }, "gab. " + (q.gabarito || "?")));
    const acoes = h("div", { class: "cad-rodape", style: { position: "static", borderRadius: 0 } });
    if (q.imagem) acoes.appendChild(h("a", { href: "/api/imagens/" + q.imagem, target: "_blank", rel: "noopener", class: "btn sm" }, "Ver print"));
    const invBox = h("div", { style: { width: "100%" } });
    if (q.status === "ativa") acoes.appendChild(h("button", { class: "btn sm", onclick: () => { limpar(invBox); invBox.appendChild(painelInvalidar(q, () => { toast("Questão invalidada."); rotear(); }, () => limpar(invBox))); } }, icone("bandeira"), "Essa questão está errada"));
    if (q.origem === "real") acoes.appendChild(h("button", { class: "btn sm perigo", onclick: async () => {
      if (!confirm("Apagar esta questão real? Não dá para desfazer.")) return;
      await api("/api/questoes/" + q.id, { method: "DELETE" }); rotear();
    } }, "Apagar"));
    acoes.appendChild(h("span", { class: "espaco" }));
    acoes.appendChild(h("span", { class: "ajuda" }, "vista " + plural(q.vezes_vista, "vez", "vezes") + " · criada em " + fmtData(q.criado_em)));
    acoes.appendChild(invBox);
    return questaoExpansivel(q, {
      titulo: q.origem === "real" ? "Questão real" : "Questão inédita", materia: t.materia, assunto: t.nome, topico: t.nome,
      resposta: q.origem === "real" && q.resultado_no_tec !== "nao_respondeu" ? q.marcada_no_tec : null, tags, extras: acoes,
    });
  }

  /* =====================================================================
     SELETOR DE PERÍODO (atalhos + dois meses, como no Tec)
     ===================================================================== */
  const MESES_CAP = MESES.map((m) => m.charAt(0).toUpperCase() + m.slice(1));
  function isoDe(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function somaMeses(s, n) { const d = dataISO(s); d.setMonth(d.getMonth() + n); return isoDe(d); }
  function textoPeriodo(ini, fim) { return ini === "tudo" ? "Tudo" : fmtData(ini) + " - " + fmtData(fim); }

  function atalhosPeriodo(hoje) {
    const d = dataISO(hoje);
    const inicioMes = isoDe(new Date(d.getFullYear(), d.getMonth(), 1));
    const iniPassado = isoDe(new Date(d.getFullYear(), d.getMonth() - 1, 1));
    const fimPassado = isoDe(new Date(d.getFullYear(), d.getMonth(), 0));
    return [
      ["Hoje", hoje, hoje], ["Ontem", somaDias(hoje, -1), somaDias(hoje, -1)],
      ["Últimos 7 dias", somaDias(hoje, -6), hoje], ["Últimos 15 dias", somaDias(hoje, -14), hoje],
      ["Este mês", inicioMes, hoje], ["Mês passado", iniPassado, fimPassado],
      ["Últimos 6 meses", somaDias(somaMeses(hoje, -6), 1), hoje], ["Último ano", somaDias(somaMeses(hoje, -12), 1), hoje],
      ["Tudo", "tudo", hoje],
    ];
  }

  function seletorPeriodo(valor, hoje) {
    // valor: { inicio, fim } (inicio pode ser "tudo"); devolve { el, valor() }
    let ini = valor.inicio, fim = valor.fim;
    let tIni = ini, tFim = fim;                       // seleção temporária, antes de "Selecionar"
    let mesDir = dataISO(fim === "tudo" ? hoje : fim); // mês do calendário da direita
    mesDir = new Date(mesDir.getFullYear(), mesDir.getMonth(), 1);
    const rot = h("span");
    const pop = h("div", { class: "periodo-pop oculto", role: "dialog", "aria-label": "Escolher período" });
    const botao = h("button", { class: "inp periodo-btn", "aria-haspopup": "dialog", onclick: (ev) => { ev.stopPropagation(); if (pop.classList.contains("oculto")) abrir(); else fechar(); } }, rot);
    const el = h("div", { class: "periodo" }, botao, pop);
    function atualizarRotulo() { rot.textContent = textoPeriodo(ini, fim); }

    function abrir() {
      tIni = ini; tFim = fim;
      const base = dataISO(fim === "tudo" ? hoje : fim);
      mesDir = new Date(base.getFullYear(), base.getMonth(), 1);
      desenhar();
      pop.classList.remove("oculto");
    }
    function fechar() { pop.classList.add("oculto"); }

    function mes(ano, m) {
      const primeiro = new Date(ano, m, 1);
      const desloc = (primeiro.getDay() + 6) % 7; // semana começa na segunda
      const inicio = new Date(ano, m, 1 - desloc);
      const dias = [];
      for (let k = 0; k < 42; k++) dias.push(new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + k));
      const ri = tIni === "tudo" ? null : tIni, rf = tFim;
      return h("div", { class: "cal" },
        h("table", null,
          h("thead", null, h("tr", null, ["S", "T", "Q", "Q", "S", "S", "D"].map((x) => h("th", null, x)))),
          h("tbody", null, [0, 1, 2, 3, 4, 5].map((w) => h("tr", null, dias.slice(w * 7, w * 7 + 7).map((dd) => {
            const iso = isoDe(dd);
            const futuro = iso > hoje;
            const fora = dd.getMonth() !== m;
            let cls = "";
            if (fora) cls += " fora";
            if (futuro) cls += " futuro";
            if (ri && rf && iso >= ri && iso <= rf) cls += " faixa";
            if (iso === ri || (iso === rf && ri)) cls += " ponta";
            return h("td", null, h("button", { class: "dia" + cls, disabled: futuro, onclick: (ev) => { ev.stopPropagation(); clicar(iso); } }, String(dd.getDate())));
          }))))));
    }

    function clicar(iso) {
      if (!tIni || tIni === "tudo" || (tIni && tFim)) { tIni = iso; tFim = null; }
      else if (iso < tIni) { tFim = tIni; tIni = iso; }
      else tFim = iso;
      desenhar();
    }

    function desenhar() {
      limpar(pop);
      const atalhos = atalhosPeriodo(hoje);
      const ativo = atalhos.find(([, a, b]) => a === tIni && b === tFim);
      const esq = new Date(mesDir.getFullYear(), mesDir.getMonth() - 1, 1);
      const podeAvancar = isoDe(new Date(mesDir.getFullYear(), mesDir.getMonth() + 1, 1)) <= hoje;
      adicionar(pop, [
        h("div", { class: "periodo-corpo" },
          h("ul", { class: "periodo-atalhos" },
            atalhos.map(([n, a, b]) => h("li", null, h("button", { class: ativo && ativo[0] === n ? "ativo" : "", onclick: (ev) => { ev.stopPropagation(); tIni = a; tFim = b; if (a !== "tudo") { const x = dataISO(b); mesDir = new Date(x.getFullYear(), x.getMonth(), 1); } desenhar(); } }, n))),
            h("li", null, h("button", { class: ativo ? "" : "ativo", onclick: (ev) => ev.stopPropagation() }, "Customizado"))),
          h("div", { class: "periodo-cals" },
            h("div", { class: "cal-mes" },
              h("div", { class: "cal-cab" },
                h("button", { class: "cal-nav", "aria-label": "Mês anterior", onclick: (ev) => { ev.stopPropagation(); mesDir = new Date(mesDir.getFullYear(), mesDir.getMonth() - 1, 1); desenhar(); } }, icone("voltar")),
                h("span", null, MESES_CAP[esq.getMonth()] + " " + esq.getFullYear()), h("span", { class: "cal-nav-vazio" })),
              mes(esq.getFullYear(), esq.getMonth())),
            h("div", { class: "cal-mes" },
              h("div", { class: "cal-cab" },
                h("span", { class: "cal-nav-vazio so-desktop" }),
                h("button", { class: "cal-nav so-mobile", "aria-label": "Mês anterior", onclick: (ev) => { ev.stopPropagation(); mesDir = new Date(mesDir.getFullYear(), mesDir.getMonth() - 1, 1); desenhar(); } }, icone("voltar")),
                h("span", null, MESES_CAP[mesDir.getMonth()] + " " + mesDir.getFullYear()),
                h("button", { class: "cal-nav", "aria-label": "Próximo mês", disabled: !podeAvancar, onclick: (ev) => { ev.stopPropagation(); mesDir = new Date(mesDir.getFullYear(), mesDir.getMonth() + 1, 1); desenhar(); } }, icone("avancar"))),
              mes(mesDir.getFullYear(), mesDir.getMonth())))),
        h("div", { class: "periodo-rodape" },
          h("span", { class: "num" }, tIni && tFim ? textoPeriodo(tIni, tFim) : tIni ? fmtData(tIni) + " - …" : ""),
          h("button", { class: "btn sm", onclick: (ev) => { ev.stopPropagation(); fechar(); } }, "Cancelar"),
          h("button", { class: "btn sm prim", disabled: !(tIni && tFim), onclick: (ev) => { ev.stopPropagation(); ini = tIni; fim = tFim; atualizarRotulo(); fechar(); el.dispatchEvent(new Event("change")); } }, "Selecionar")),
      ]);
    }

    pop.addEventListener("click", (ev) => ev.stopPropagation());
    document.addEventListener("click", fechar);
    limpeza.push(() => document.removeEventListener("click", fechar));
    atualizarRotulo();
    return { el, valor: () => ({ inicio: ini, fim }) };
  }

  /* =====================================================================
     ESTATÍSTICAS
     ===================================================================== */
  const filtroStats = { inicio: "", fim: "", fonte: "app", origem: "todas", materias: [], ordem: "indice", grafico: true, texto: true };
  async function pagEstatisticas() {
    const materias = await api("/api/estatisticas/materias");
    const hoje = painelCache ? painelCache.hoje : hojeISO();
    if (!filtroStats.fim) { filtroStats.fim = hoje; filtroStats.inicio = somaDias(hoje, -29); }
    limpar(main);
    main.appendChild(cabecalho("Estatísticas"));

    const periodo = seletorPeriodo({ inicio: filtroStats.inicio, fim: filtroStats.fim }, hoje);
    periodo.el.addEventListener("change", () => filtrar());
    const fFonte = h("select", { class: "inp" }, [["app", "Revisões no app"], ["tec", "Registros do Tec"], ["ambos", "Ambos"]].map(([v, n]) => h("option", { value: v, selected: filtroStats.fonte === v }, n)));
    const fOrigem = h("select", { class: "inp" }, [["todas", "Todas"], ["real", "Reais"], ["gerada", "Inéditas"]].map(([v, n]) => h("option", { value: v, selected: filtroStats.origem === v }, n)));
    const multi = multiSelect(materias, filtroStats.materias);
    main.appendChild(h("section", { class: "card filtros" },
      h("div", { class: "campo", style: { minWidth: "230px" } }, h("span", null, "Período"), periodo.el),
      h("div", { class: "campo", style: { minWidth: "220px" } }, h("span", null, "Matérias"), multi.el),
      h("label", { class: "campo" }, h("span", null, "Fonte"), fFonte),
      h("label", { class: "campo" }, h("span", null, "Questões"), fOrigem),
      h("button", { class: "btn prim", onclick: filtrar }, "Filtrar")));

    const corpo = h("div");
    main.appendChild(corpo);

    async function filtrar() {
      const pv = periodo.valor();
      Object.assign(filtroStats, { inicio: pv.inicio, fim: pv.fim, fonte: fFonte.value, origem: fOrigem.value, materias: multi.valor() });
      limpar(corpo);
      corpo.appendChild(h("div", { style: { marginTop: "20px" } }, carregando()));
      const q = new URLSearchParams({ inicio: filtroStats.inicio, fim: filtroStats.fim, fonte: filtroStats.fonte, origem: filtroStats.origem, materias: filtroStats.materias.join(",") });
      try { desenhar(await api("/api/estatisticas?" + q.toString())); }
      catch (e) { limpar(corpo); corpo.appendChild(alerta("erro", e.message)); }
    }

    function desenhar(d) {
      limpar(corpo);
      const g = d.geral;
      corpo.appendChild(h("h2", { class: "secao-tit" }, "Desempenho geral", h("span", { class: "sub num" }, fmtData(d.periodo.inicio) + " a " + fmtData(d.periodo.fim))));
      const radarItens = d.materias.map((m) => ({ rot: m.sigla, val: m.pct, tip: [m.nome, G.fmtPct(m.pct) + " de acerto", m.acertos + " acertos · " + m.erros + " erros"] }));
      corpo.appendChild(h("section", { class: "card geral" },
        h("div", { class: "numeros" },
          numero("Questões resolvidas", g.resolvidas), numero("Acertos", g.acertos, "ok"),
          numero("Total de matérias", g.total_materias), numero("Erros", g.erros, "erro")),
        h("div", { class: "grafico" }, G.rosca(g.acertos, g.erros, 180),
          h("div", { class: "legenda" }, h("span", null, h("i", { style: { background: "var(--ok-marca)" } }), "Acertos"), h("span", null, h("i", { style: { background: "var(--erro-marca)" } }), "Erros"))),
        h("div", { class: "grafico" + (radarItens.length < 3 ? " radar-vazio" : "") }, G.radar(radarItens, 250))));

      corpo.appendChild(h("h2", { class: "secao-tit" }, "Desempenho por matéria e assunto"));
      const tabBox = h("div");
      const ordem = h("span", { class: "grupo" }, h("span", { class: "rotulo" }, "Ordem de exibição:"),
        [["indice", "Índice"], ["fortes", "Pontos fortes"], ["fracos", "Pontos fracos"]].map(([v, n]) =>
          h("label", null, h("input", { type: "radio", name: "ordem", checked: filtroStats.ordem === v, onchange: () => { filtroStats.ordem = v; tabela(); } }), n)));
      const exibir = h("span", { class: "grupo" }, h("span", { class: "rotulo" }, "Exibir:"),
        h("label", null, h("input", { type: "checkbox", checked: filtroStats.grafico, onchange: (ev) => { filtroStats.grafico = ev.target.checked; tabela(); } }), "Gráfico"),
        h("label", null, h("input", { type: "checkbox", checked: filtroStats.texto, onchange: (ev) => { filtroStats.texto = ev.target.checked; tabela(); } }), "Texto"));
      corpo.appendChild(h("section", { class: "card" }, h("div", { class: "por-mat-cab" }, ordem, exibir), tabBox));
      const abertos = new Set();

      function ordenar(lista) {
        const l = lista.slice();
        if (filtroStats.ordem === "fortes") l.sort((a, b) => b.pct - a.pct || b.resolvidas - a.resolvidas);
        if (filtroStats.ordem === "fracos") l.sort((a, b) => a.pct - b.pct || b.resolvidas - a.resolvidas);
        return l;
      }
      function celDesemp(x) {
        const tds = [];
        if (filtroStats.grafico) {
          const barra = h("div", { class: "barra-ae" },
            x.acertos ? h("i", { class: "a", style: { flex: String(x.acertos) } }) : null,
            x.erros ? h("i", { class: "e", style: { flex: String(x.erros) } }) : null);
          G.comTip(barra, () => [x.nome, x.acertos + " acertos (" + G.fmtPct(x.pct) + ")", x.erros + " erros (" + G.fmtPct(100 - x.pct) + ")"]);
          tds.push(h("td", { style: { width: "32%" } }, barra));
        }
        if (filtroStats.texto) {
          tds.push(h("td", { class: "desemp" },
            h("span", { class: "p ok" }, Math.round(x.pct) + "%"), h("span", { class: "mudo" }, " (" + x.acertos + ")  "),
            h("span", { class: "p erro" }, (x.resolvidas ? 100 - Math.round(x.pct) : 0) + "%"), h("span", { class: "mudo" }, " (" + x.erros + ")")));
        }
        return tds;
      }
      function tabela() {
        limpar(tabBox);
        if (!d.materias.length) { tabBox.appendChild(h("div", { class: "vazio" }, "Nenhuma questão respondida nesse período.")); return; }
        const tb = h("tbody");
        ordenar(d.materias).forEach((m) => {
          const aberto = abertos.has(m.id);
          tb.appendChild(h("tr", null,
            h("td", { style: { width: "40px" } }, h("button", { class: "exp", "aria-expanded": String(aberto), "aria-label": (aberto ? "Recolher " : "Expandir ") + m.nome, onclick: () => { if (aberto) abertos.delete(m.id); else abertos.add(m.id); tabela(); } }, icone(aberto ? "menos" : "mais"))),
            h("td", { style: { fontWeight: 600 } }, m.nome), h("td", { class: "dir num col-resol" }, String(m.resolvidas)), celDesemp(m)));
          if (aberto) ordenar(m.topicos).forEach((t) => tb.appendChild(h("tr", { class: "sub" },
            h("td", { colspan: "2" }, t.nome), h("td", { class: "dir num col-resol" }, String(t.resolvidas)), celDesemp(t))));
        });
        const ths = [h("th"), h("th", null, "Matéria / Assunto"), h("th", { class: "dir col-resol" }, "Questões resolvidas")];
        if (filtroStats.grafico) ths.push(h("th", null, "Desempenho"));
        if (filtroStats.texto) ths.push(h("th", null, filtroStats.grafico ? "" : "Desempenho"));
        tabBox.appendChild(h("div", { class: "tab-wrap" }, h("table", { class: "tab tab-mat" }, h("thead", null, h("tr", null, ths)), tb)));
      }
      tabela();

      corpo.appendChild(h("h2", { class: "secao-tit" }, "Evolução diária"));
      const evo = h("div", { class: "card-corpo grafico-evo" });
      corpo.appendChild(h("section", { class: "card" }, evo));
      const desenharEvo = () => {
        limpar(evo);
        evo.appendChild(G.colunasDia(d.dias, Math.max(300, Math.floor(evo.getBoundingClientRect().width) - 40), 200));
        evo.appendChild(h("div", { class: "legenda" }, h("span", null, h("i", { style: { background: "var(--ok-marca)" } }), "Acertos"), h("span", null, h("i", { style: { background: "var(--erro-marca)" } }), "Erros")));
      };
      desenharEvo();
      window.addEventListener("resize", desenharEvo);
      limpeza.push(() => window.removeEventListener("resize", desenharEvo));

      const rv = d.revisao;
      corpo.appendChild(h("h2", { class: "secao-tit" }, "Revisão espaçada", h("span", { class: "sub" }, plural(rv.topicos, "tópico") + " · " + rv.vencidos + " vencidos")));
      const maxE = Math.max(1, ...rv.etapas.map((e) => e.n));
      const nomes = ["Etapa 0 · 1 dia", "Etapa 1 · 3 dias", "Etapa 2 · 7 dias", "Etapa 3 · 15 dias", "Etapa 4 · 30 dias", "Etapa 5 · 60 dias", "Manutenção · 30 dias"];
      corpo.appendChild(h("section", { class: "card" }, h("table", { class: "tab" }, h("tbody", null,
        nomes.map((n, i) => {
          const e = rv.etapas.find((x) => x.etapa === i) || { n: 0 };
          const barra = h("div", { style: { height: "12px", width: (100 * e.n) / maxE + "%", minWidth: e.n ? "4px" : "0", background: i === 6 ? "var(--ok)" : "var(--prim)", borderRadius: "3px" } });
          return h("tr", null, h("td", { style: { width: "200px" } }, n), h("td", { class: "dir num", style: { width: "60px" } }, String(e.n)), h("td", null, barra));
        })))));
    }
    filtrar();
  }

  function numero(rot, val, cls) {
    return h("div", { class: "numero" }, h("div", { class: "rot" }, rot), h("div", { class: "val " + (cls || "") }, typeof val === "number" ? val.toLocaleString("pt-BR") : val));
  }

  function multiSelect(opcoes, selecionados) {
    const sel = new Set(selecionados);
    const rot = h("span");
    const painel = h("div", { class: "painel oculto" });
    const btn = h("button", { class: "inp", "aria-haspopup": "true", onclick: (ev) => { ev.stopPropagation(); painel.classList.toggle("oculto"); } }, rot, h("span", { class: "mudo" }, "▾"));
    function atualizar() { rot.textContent = !sel.size ? "Todos itens selecionados" : sel.size === 1 ? (opcoes.find((o) => sel.has(o.id)) || {}).nome : sel.size + " selecionadas"; }
    painel.appendChild(h("label", null, h("input", { type: "checkbox", checked: !sel.size, onchange: () => { sel.clear(); painel.querySelectorAll("input[data-id]").forEach((i) => { i.checked = false; }); atualizar(); } }), "Todas"));
    opcoes.forEach((o) => painel.appendChild(h("label", null, h("input", { type: "checkbox", "data-id": o.id, checked: sel.has(o.id), onchange: (ev) => {
      if (ev.target.checked) sel.add(o.id); else sel.delete(o.id);
      painel.querySelector("input:not([data-id])").checked = !sel.size;
      atualizar();
    } }), o.nome)));
    painel.addEventListener("click", (ev) => ev.stopPropagation());
    const fechar = () => painel.classList.add("oculto");
    document.addEventListener("click", fechar);
    limpeza.push(() => document.removeEventListener("click", fechar));
    atualizar();
    return { el: h("div", { class: "multi" }, btn, painel), valor: () => Array.from(sel) };
  }

  /* =====================================================================
     BIBLIOTECA DE LEIS
     ===================================================================== */
  async function pagLeis() {
    const leis = await api("/api/leis");
    limpar(main);
    main.appendChild(cabecalho("Biblioteca de leis", "PDFs oficiais. A geração e a conferência de gabarito se baseiam neles."));
    const fNome = h("input", { class: "inp", placeholder: "Constituição Federal" });
    const fSigla = h("input", { class: "inp", placeholder: "CF/88" });
    const fArq = h("input", { class: "inp", type: "file", accept: "application/pdf" });
    const status = h("div");
    const btn = h("button", { class: "btn prim", onclick: async () => {
      if (!fArq.files[0] || !fNome.value.trim() || !fSigla.value.trim()) { toast("Preencha nome, sigla e escolha o PDF.", true); return; }
      btn.disabled = true;
      limpar(status); status.appendChild(carregando("Lendo o PDF e separando artigos, parágrafos e incisos…"));
      const fd = new FormData(); fd.append("arquivo", fArq.files[0]); fd.append("nome", fNome.value.trim()); fd.append("sigla", fSigla.value.trim());
      try {
        const r = await api("/api/leis", { method: "POST", form: fd });
        toast("Lei importada: " + r.artigos + " artigos, " + r.dispositivos + " dispositivos.");
        rotear();
      } catch (e) { limpar(status); status.appendChild(alerta("erro", e.message)); btn.disabled = false; }
    } }, "Enviar lei");
    main.appendChild(card("Enviar PDF", "Enviar uma lei com a mesma sigla substitui a versão anterior.", null, h("div", { class: "card-corpo" },
      h("div", { class: "grade g3", style: { gap: "14px" } }, h("label", { class: "campo" }, h("span", null, "Nome"), fNome), h("label", { class: "campo" }, h("span", null, "Sigla (como nas referências)"), fSigla), h("label", { class: "campo" }, h("span", null, "Arquivo PDF"), fArq)),
      h("div", { class: "linha", style: { marginTop: "14px" } }, btn), h("div", { style: { marginTop: "10px" } }, status))));

    main.appendChild(h("h2", { class: "secao-tit" }, "Leis na biblioteca"));
    if (!leis.length) { main.appendChild(card(null, null, null, h("div", { class: "vazio" }, "Nenhuma lei ainda. Comece pela CF/88 e pelas leis do edital."))); return; }
    main.appendChild(h("section", { class: "card tab-wrap" }, h("table", { class: "tab" },
      h("thead", null, h("tr", null, h("th", null, "Sigla"), h("th", null, "Nome"), h("th", { class: "dir" }, "Artigos"), h("th", { class: "dir" }, "Dispositivos"), h("th", { class: "dir" }, "Tópicos ligados"), h("th", null, "Versão"), h("th", null, "Enviada em"))),
      h("tbody", null, leis.map((l) => h("tr", { class: "clic", onclick: () => { location.hash = "#/lei/" + l.id; } },
        h("td", { style: { fontWeight: 700 } }, h("a", { href: "#/lei/" + l.id }, l.sigla)), h("td", null, l.nome),
        h("td", { class: "dir num" }, String(l.artigos)), h("td", { class: "dir num" }, String(l.dispositivos)), h("td", { class: "dir num" }, String(l.topicos)),
        h("td", null, h("span", { class: "etq" }, "v" + l.versao)), h("td", { class: "num" }, fmtData(l.enviado_em))))))));
  }

  async function pagLei(id) {
    let d = await api("/api/leis/" + id);
    limpar(main);
    main.appendChild(h("a", { class: "voltar", href: "#/leis" }, icone("voltar"), "Biblioteca de leis"));
    main.appendChild(cabecalho(d.lei.sigla + " – " + d.lei.nome, "Versão " + d.lei.versao + " · enviada em " + fmtData(d.lei.enviado_em),
      h("button", { class: "btn perigo", onclick: async () => {
        if (!confirm("Remover a lei " + d.lei.sigla + " da biblioteca? Os tópicos ligados ficam sem texto-base.")) return;
        await api("/api/leis/" + id, { method: "DELETE" }); location.hash = "#/leis";
      } }, "Remover lei")));
    const busca = h("input", { class: "inp", type: "search", placeholder: "Buscar no texto da lei", style: { maxWidth: "400px" } });
    const lista = h("section", { class: "card" });
    main.appendChild(h("div", { style: { marginBottom: "14px" } }, busca));
    main.appendChild(lista);
    function desenhar() {
      limpar(lista);
      if (!d.dispositivos.length) { lista.appendChild(h("div", { class: "vazio" }, "Nada encontrado.")); return; }
      d.dispositivos.forEach((x) => lista.appendChild(h("div", { class: "disp nivel-" + x.nivel }, h("div", { class: "ref" }, x.referencia), h("div", null, x.texto))));
    }
    let tm = null;
    busca.addEventListener("input", () => { clearTimeout(tm); tm = setTimeout(async () => { d = await api("/api/leis/" + id + "?busca=" + encodeURIComponent(busca.value)); desenhar(); }, 250); });
    desenhar();
  }

  /* =====================================================================
     CONFIGURAÇÕES
     ===================================================================== */
  async function pagConfig() {
    const c = await api("/api/config");
    limpar(main);
    main.appendChild(cabecalho("Configurações"));

    async function salvar(campos, msg) {
      try { await api("/api/config", { method: "PUT", body: campos }); toast(msg || "Salvo."); }
      catch (e) { toast(e.message, true); }
    }

    const segTema = h("div", { class: "seg" });
    function desenharTema() {
      limpar(segTema);
      TEMAS.forEach(([t, n]) => segTema.appendChild(h("button", { "aria-pressed": String(temaAtual() === t), onclick: () => { setTema(t); desenharTema(); } }, n)));
    }
    desenharTema();
    main.appendChild(card("Aparência", "O tema vale para este navegador.", null, h("div", { class: "card-corpo" }, h("div", { class: "campo" }, h("span", null, "Tema"), h("div", null, segTema)))));

    let teste = !!c.modo_teste_sessao;
    const segTeste = h("div", { class: "seg" });
    function desenharTeste() {
      limpar(segTeste);
      [[false, "Normal (revisão espaçada)"], [true, "Teste (todas as questões)"]].forEach(([v, n]) => segTeste.appendChild(h("button", { "aria-pressed": String(teste === v), onclick: async () => {
        teste = v; desenharTeste();
        await salvar({ modo_teste_sessao: v }, v ? "Modo de teste ligado. A sessão diária traz todas as questões." : "Modo normal. Sessões de teste descartadas.");
        await atualizarPainel(); desenharNav("config");
      } }, n)));
    }
    desenharTeste();
    main.appendChild(card("Sessão diária", "No modo de teste, a sessão traz todas as questões cadastradas, sem olhar a data de revisão. Responder não muda etapas, datas nem estatísticas. Ao voltar para o normal, as sessões de teste são descartadas.", null,
      h("div", { class: "card-corpo" }, h("div", { class: "campo" }, h("span", null, "Modo"), h("div", null, segTeste)))));

    let modo = c.modo_ia;
    const segModo = h("div", { class: "seg" });
    function desenharModo() {
      limpar(segModo);
      [["assinatura", "Assinatura (Claude Code)"], ["api", "API key"]].forEach(([v, n]) => segModo.appendChild(h("button", { "aria-pressed": String(modo === v), onclick: async () => {
        if (v === "api" && !c.api_key_configurada) { toast("Configure a API key antes.", true); return; }
        modo = v; desenharModo(); await salvar({ modo_ia: v }, v === "api" ? "Usando API key a partir da próxima chamada." : "Usando a assinatura a partir da próxima chamada.");
      } }, n)));
    }
    desenharModo();
    const fKey = h("input", { class: "inp", type: "password", placeholder: c.api_key_configurada ? c.api_key_mascarada : "sk-ant-…", autocomplete: "off" });
    const fBin = h("input", { class: "inp", value: c.claude_bin, placeholder: "padrão: %USERPROFILE%\\.local\\bin\\claude.exe" });
    const testeBox = h("div");
    main.appendChild(card("Inteligência artificial", "A troca de modo vale na próxima chamada. No modo API key, a geração usa a Batch API (50% mais barata).", null, h("div", { class: "card-corpo" },
      h("div", { class: "campo" }, h("span", null, "Modo"), h("div", null, segModo)),
      h("div", { class: "grade g2", style: { gap: "14px", marginTop: "16px" } },
        h("label", { class: "campo" }, h("span", null, "API key " + (c.api_key_configurada ? "(configurada: " + c.api_key_mascarada + ")" : "(não configurada)")), fKey),
        h("label", { class: "campo" }, h("span", null, "Caminho do Claude Code"), fBin)),
      h("div", { class: "linha", style: { marginTop: "16px" } },
        h("button", { class: "btn prim", onclick: async () => {
          const campos = { claude_bin: fBin.value.trim() };
          if (fKey.value.trim()) campos.api_key = fKey.value.trim();
          await salvar(campos); rotear();
        } }, "Salvar"),
        h("button", { class: "btn", onclick: async () => {
          limpar(testeBox); testeBox.appendChild(h("div", { style: { marginTop: "12px" } }, carregando("Chamando o Claude…")));
          try { const r = await api("/api/config/testar-ia", { method: "POST", body: {} }); limpar(testeBox); testeBox.appendChild(h("div", { style: { marginTop: "12px" } }, alerta("ok", "Funcionando no modo " + (modo === "api" ? "API key" : "assinatura") + ". Resposta: " + r.resposta))); }
          catch (e) { limpar(testeBox); testeBox.appendChild(h("div", { style: { marginTop: "12px" } }, alerta("erro", e.message))); }
        } }, "Testar conexão"),
        h("span", { class: "espaco" }),
        c.api_key_configurada ? h("button", { class: "btn perigo", onclick: async () => {
          if (!confirm("Remover a API key?")) return;
          await salvar({ api_key: "", modo_ia: "assinatura" }, "API key removida."); rotear();
        } }, "Remover API key") : null),
      testeBox)));

    const MODELOS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-2"];
    const ESFORCOS = [["low", "baixo"], ["medium", "médio"], ["high", "alto"], ["xhigh", "muito alto"], ["max", "máximo"]];
    const NOMES_T = { ler: "Ler print ou texto colado", reler: "Reler com Sonnet", gerar: "Gerar questões e conferir gabaritos", explicar: "Explicar melhor" };
    const modelos = JSON.parse(JSON.stringify(c.modelos));
    main.appendChild(card("Modelo e esforço por tarefa", null, null, h("div", { class: "tab-wrap" }, h("table", { class: "tab" },
      h("thead", null, h("tr", null, h("th", null, "Tarefa"), h("th", null, "Modelo"), h("th", null, "Esforço"))),
      h("tbody", null, Object.keys(NOMES_T).map((k) => h("tr", null, h("td", null, NOMES_T[k]),
        h("td", null, h("select", { class: "inp", onchange: (ev) => { modelos[k].modelo = ev.target.value; salvar({ modelos }); } }, MODELOS.map((m) => h("option", { value: m, selected: modelos[k].modelo === m }, m)))),
        h("td", null, h("select", { class: "inp", onchange: (ev) => { modelos[k].esforco = ev.target.value; salvar({ modelos }); } }, ESFORCOS.map(([e, n]) => h("option", { value: e, selected: modelos[k].esforco === e }, n)))))))))));

    const campos = {
      intervalos: h("input", { class: "inp", value: c.intervalos.join(", ") }),
      intervalo_manutencao: h("input", { class: "inp", type: "number", min: "1", value: c.intervalo_manutencao }),
      limiar_avancar: h("input", { class: "inp", type: "number", min: "1", max: "100", value: c.limiar_avancar }),
      limiar_repetir: h("input", { class: "inp", type: "number", min: "0", max: "100", value: c.limiar_repetir }),
      questoes_primeira: h("input", { class: "inp", type: "number", min: "1", value: c.questoes_primeira }),
      questoes_demais: h("input", { class: "inp", type: "number", min: "1", value: c.questoes_demais }),
      limite_diario: h("input", { class: "inp", type: "number", min: "0", value: c.limite_diario }),
      proporcao_reais: h("input", { class: "inp", type: "number", min: "0", max: "100", value: c.proporcao_reais }),
      minimo_geradas: h("input", { class: "inp", type: "number", min: "0", value: c.minimo_geradas }),
      limiar_banco_baixo: h("input", { class: "inp", type: "number", min: "0", value: c.limiar_banco_baixo }),
    };
    const rot = {
      intervalos: "Intervalos em dias (etapa 0 em diante)", intervalo_manutencao: "Manutenção (dias)",
      limiar_avancar: "Avança com acerto a partir de (%)", limiar_repetir: "Repete a partir de (%); abaixo volta",
      questoes_primeira: "Questões na 1ª revisão", questoes_demais: "Questões nas demais", limite_diario: "Limite diário de tópicos (0 = sem limite)",
      proporcao_reais: "Proporção de questões reais (%)", minimo_geradas: "Mínimo de geradas por tópico", limiar_banco_baixo: "Aviso de banco baixo abaixo de",
    };
    main.appendChild(card("Revisão espaçada e banco", null, null, h("div", { class: "card-corpo" },
      h("div", { class: "grade g3", style: { gap: "14px" } }, Object.keys(campos).map((k) => h("label", { class: "campo" }, h("span", null, rot[k]), campos[k]))),
      h("div", { class: "linha", style: { marginTop: "16px" } }, h("button", { class: "btn prim", onclick: async () => {
        const v = {};
        try {
          v.intervalos = campos.intervalos.value.split(/[,;\s]+/).filter(Boolean).map((x) => { const n = parseInt(x, 10); if (!(n > 0)) throw new Error("Intervalo inválido: " + x); return n; });
        } catch (e) { toast(e.message, true); return; }
        for (const k of Object.keys(campos)) if (k !== "intervalos") v[k] = parseInt(campos[k].value, 10) || 0;
        await salvar(v);
      } }, "Salvar")))));

    const fEstilo = autoAltura(h("textarea", { class: "inp", rows: "8" }));
    fEstilo.value = c.estilo_banca;
    main.appendChild(card("Estilo da banca", "Instruções usadas na geração de questões inéditas.", null, h("div", { class: "card-corpo" }, fEstilo,
      h("div", { class: "linha", style: { marginTop: "14px" } },
        h("button", { class: "btn prim", onclick: () => salvar({ estilo_banca: fEstilo.value }) }, "Salvar"),
        h("button", { class: "btn", onclick: async () => { await api("/api/config/restaurar-estilo", { method: "POST" }); toast("Estilo Vunesp restaurado."); rotear(); } }, "Restaurar padrão Vunesp")))));

    const fAtual = h("input", { class: "inp", type: "password", autocomplete: "current-password" });
    const fNova = h("input", { class: "inp", type: "password", autocomplete: "new-password" });
    main.appendChild(card("Acesso", "Trocar a senha desloga todos os dispositivos.", null, h("div", { class: "card-corpo" },
      h("div", { class: "grade g3", style: { gap: "14px" } }, h("label", { class: "campo" }, h("span", null, "Senha atual"), fAtual), h("label", { class: "campo" }, h("span", null, "Senha nova"), fNova)),
      h("div", { class: "linha", style: { marginTop: "16px" } },
        h("button", { class: "btn prim", onclick: async () => {
          try { await api("/api/senha", { method: "POST", body: { atual: fAtual.value, nova: fNova.value } }); toast("Senha trocada. Entre de novo."); telaLogin(); }
          catch (e) { toast(e.message, true); }
        } }, "Trocar senha"),
        h("button", { class: "btn", onclick: sair }, "Sair deste dispositivo")))));
  }

  /* ===================================================================== */
  telaLogin();
})();
