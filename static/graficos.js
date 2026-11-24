/* Gráficos em SVG feitos à mão. Cores vêm das variáveis do tema (var(--ok), var(--erro)...),
   então trocam sozinhas com o tema. Toda marca tem tooltip ao passar o mouse. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";

  function s(tag, attrs, filhos) {
    var el = document.createElementNS(NS, tag);
    for (var k in attrs || {}) {
      if (attrs[k] === null || attrs[k] === undefined) continue;
      el.setAttribute(k, attrs[k]);
    }
    (filhos || []).forEach(function (f) { if (f) el.appendChild(typeof f === "string" ? document.createTextNode(f) : f); });
    return el;
  }

  /* ---------- tooltip ---------- */
  var tip = null;
  function mostrarTip(ev, linhas) {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "tooltip";
      document.body.appendChild(tip);
    }
    tip.textContent = "";
    linhas.forEach(function (l, i) {
      var d = document.createElement("div");
      if (i === 0) { var b = document.createElement("b"); b.textContent = l; d.appendChild(b); }
      else d.textContent = l;
      tip.appendChild(d);
    });
    tip.style.display = "block";
    var x = ev.clientX + 14, y = ev.clientY + 14;
    var r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - 14;
    if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - 14;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  function esconderTip() { if (tip) tip.style.display = "none"; }
  function comTip(el, linhasFn) {
    el.addEventListener("mousemove", function (ev) { mostrarTip(ev, linhasFn()); });
    el.addEventListener("mouseleave", esconderTip);
    return el;
  }

  function fmtPct(v) { return (Math.round(v * 100) / 100).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + "%"; }

  /* ---------- rosca de acertos/erros ---------- */
  function rosca(acertos, erros, tam) {
    tam = tam || 180;
    var total = acertos + erros;
    var r = tam / 2 - 14, cx = tam / 2, cy = tam / 2, esp = 26;
    var svg = s("svg", { viewBox: "0 0 " + tam + " " + tam, width: tam, height: tam, role: "img",
      "aria-label": "Acertos " + acertos + ", erros " + erros });
    if (!total) {
      svg.appendChild(s("circle", { cx: cx, cy: cy, r: r, fill: "none", style: "stroke:var(--borda)", "stroke-width": esp }));
      svg.appendChild(s("text", { x: cx, y: cy + 6, "text-anchor": "middle", style: "fill:var(--mudo);font:500 15px var(--f)" }, ["sem dados"]));
      return svg;
    }
    var circ = 2 * Math.PI * r;
    var gap = (acertos && erros) ? 2 : 0; // 2px de respiro entre os segmentos
    var fa = acertos / total, fe = erros / total;
    function seg(frac, offFrac, cor, linhas) {
      var comp = Math.max(0, frac * circ - gap);
      var c = s("circle", {
        cx: cx, cy: cy, r: r, fill: "none", "stroke-width": esp, style: "stroke:" + cor,
        "stroke-dasharray": comp + " " + (circ - comp),
        "stroke-dashoffset": -(offFrac * circ + gap / 2),
        transform: "rotate(-90 " + cx + " " + cy + ")"
      });
      return comTip(c, function () { return linhas; });
    }
    if (acertos) svg.appendChild(seg(fa, 0, "var(--ok-marca)", ["Acertos", acertos + " questões · " + fmtPct(100 * fa)]));
    if (erros) svg.appendChild(seg(fe, fa, "var(--erro-marca)", ["Erros", erros + " questões · " + fmtPct(100 * fe)]));
    svg.appendChild(s("text", { x: cx, y: cy + 7, "text-anchor": "middle", style: "fill:var(--texto);font:700 22px var(--f)" },
      [fmtPct(100 * fa)]));
    return svg;
  }

  /* ---------- radar por matéria ---------- */
  function radar(itens, tam) {
    tam = tam || 240;
    var cx = tam / 2, cy = tam / 2, r = tam / 2 - 34;
    var svg = s("svg", { viewBox: "0 0 " + tam + " " + tam, width: tam, height: tam, role: "img",
      "aria-label": "Aproveitamento por matéria" });
    var n = itens.length;
    if (n < 3) {
      svg.appendChild(s("text", { x: cx, y: cy, "text-anchor": "middle", style: "fill:var(--mudo);font:13px var(--f)" },
        ["radar a partir de 3 matérias"]));
      return svg;
    }
    function pt(i, frac) {
      var a = -Math.PI / 2 + (2 * Math.PI * i) / n;
      return [cx + Math.cos(a) * r * frac, cy + Math.sin(a) * r * frac];
    }
    [0.25, 0.5, 0.75, 1].forEach(function (f) {
      var pts = itens.map(function (_, i) { return pt(i, f).join(","); }).join(" ");
      svg.appendChild(s("polygon", { points: pts, fill: "none", style: "stroke:var(--borda)", "stroke-width": 1 }));
    });
    itens.forEach(function (it, i) {
      var p = pt(i, 1);
      svg.appendChild(s("line", { x1: cx, y1: cy, x2: p[0], y2: p[1], style: "stroke:var(--borda)", "stroke-width": 1 }));
      var l = pt(i, 1.17);
      var anc = Math.abs(l[0] - cx) < 6 ? "middle" : (l[0] > cx ? "start" : "end");
      svg.appendChild(s("text", { x: l[0], y: l[1] + 4, "text-anchor": anc, style: "fill:var(--texto-2);font:500 10px var(--f)" }, [it.rot]));
    });
    [50, 100].forEach(function (v) {
      svg.appendChild(s("text", { x: cx + 3, y: cy - r * v / 100 + 10, style: "fill:var(--mudo);font:9px var(--f)" }, [String(v)]));
    });
    var pts = itens.map(function (it, i) { return pt(i, Math.max(0, it.val) / 100).join(","); }).join(" ");
    svg.appendChild(s("polygon", { points: pts, style: "fill:var(--prim);fill-opacity:0.15;stroke:var(--prim)", "stroke-width": 2, "stroke-linejoin": "round" }));
    itens.forEach(function (it, i) {
      var p = pt(i, Math.max(0, it.val) / 100);
      svg.appendChild(s("circle", { cx: p[0], cy: p[1], r: 4, style: "fill:var(--prim);stroke:var(--sup)", "stroke-width": 2 }));
      // alvo maior que a marca
      svg.appendChild(comTip(s("circle", { cx: p[0], cy: p[1], r: 11, fill: "transparent" }), function () { return it.tip; }));
    });
    return svg;
  }

  /* ---------- colunas diárias empilhadas (acertos embaixo, erros em cima) ---------- */
  function colunasDia(dias, larg, alt) {
    larg = larg || 900; alt = alt || 190;
    var me = 34, md = 8, mt = 10, mb = 24;
    var w = larg - me - md, h = alt - mt - mb;
    var max = Math.max.apply(null, dias.map(function (d) { return d.resolvidas; }).concat([1]));
    var passo = Math.pow(10, Math.floor(Math.log10(max)));
    var topo = Math.ceil(max / passo) * passo;
    if (topo / passo > 6) { passo *= 2; topo = Math.ceil(max / passo) * passo; }
    var svg = s("svg", { viewBox: "0 0 " + larg + " " + alt, width: larg, height: alt, role: "img", "aria-label": "Questões por dia" });
    for (var v = 0; v <= topo; v += passo) {
      var y = mt + h - (v / topo) * h;
      svg.appendChild(s("line", { x1: me, x2: larg - md, y1: y, y2: y, style: "stroke:var(--borda)", "stroke-width": 1 }));
      svg.appendChild(s("text", { x: me - 6, y: y + 3, "text-anchor": "end", style: "fill:var(--mudo);font:10px var(--f)" }, [String(v)]));
    }
    var n = dias.length, bw = w / n, barra = Math.max(2, Math.min(22, bw * 0.62));
    var rotEvery = Math.ceil(n / 12);
    dias.forEach(function (d, i) {
      var x = me + i * bw + (bw - barra) / 2;
      var ya = (d.acertos / topo) * h, ye = (d.erros / topo) * h;
      var base = mt + h;
      if (d.acertos) svg.appendChild(s("rect", { x: x, y: base - ya, width: barra, height: ya, style: "fill:var(--ok-marca)" }));
      if (d.erros) svg.appendChild(s("rect", { x: x, y: base - ya - ye - (d.acertos ? 2 : 0), width: barra, height: ye, style: "fill:var(--erro-marca)" }));
      if (i % rotEvery === 0) {
        var p = d.dia.split("-");
        svg.appendChild(s("text", { x: x + barra / 2, y: alt - 6, "text-anchor": "middle", style: "fill:var(--mudo);font:10px var(--f)" }, [p[2] + "/" + p[1]]));
      }
      svg.appendChild(comTip(s("rect", { x: me + i * bw, y: mt, width: bw, height: h, fill: "transparent" }), function () {
        var p = d.dia.split("-");
        return [p[2] + "/" + p[1] + "/" + p[0], d.resolvidas + " resolvidas",
          d.acertos + " acertos · " + d.erros + " erros" + (d.resolvidas ? " · " + fmtPct(d.pct) : "")];
      }));
    });
    svg.appendChild(s("line", { x1: me, x2: larg - md, y1: mt + h, y2: mt + h, style: "stroke:var(--borda-forte)", "stroke-width": 1 }));
    return svg;
  }

  window.Graficos = { rosca: rosca, radar: radar, colunasDia: colunasDia, comTip: comTip, mostrarTip: mostrarTip, esconderTip: esconderTip, fmtPct: fmtPct };
})();
