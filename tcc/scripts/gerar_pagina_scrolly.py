# -*- coding: utf-8 -*-
"""Página de reportagem em rolagem ("Bairro, porta e topo") com os números do TCC.

Inspirada no formato de scrollytelling de jornalismo de dados (texto em etapas, gráfico fixo).
Todo número sai do params_nucleo e dos csv de outputs/tables — a mesma fonte do TCC —, para
a página não divergir do texto (regra dos números fósseis).

Entrada: tcc/scripts/pagina_scrolly_modelo.html
Saída:   outputs/web/bairro_porta_topo.html
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from params_nucleo import P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
MODELO = Path(__file__).with_name("pagina_scrolly_modelo.html")
SAIDA = ROOT / "outputs" / "web" / "bairro_porta_topo.html"

# código IBGE da UF -> (sigla, coluna, linha) num mapa em grade do Brasil
GRADE = {11: ("RO", 1, 2), 12: ("AC", 0, 2), 13: ("AM", 1, 1), 14: ("RR", 2, 0), 15: ("PA", 2, 1),
         16: ("AP", 3, 0), 17: ("TO", 2, 2), 21: ("MA", 3, 1), 22: ("PI", 3, 2), 23: ("CE", 4, 1),
         24: ("RN", 5, 1), 25: ("PB", 5, 2), 26: ("PE", 4, 2), 27: ("AL", 5, 3), 28: ("SE", 4, 3),
         29: ("BA", 3, 3), 31: ("MG", 3, 4), 32: ("ES", 4, 4), 33: ("RJ", 3, 5), 35: ("SP", 2, 5),
         41: ("PR", 2, 6), 42: ("SC", 2, 7), 43: ("RS", 2, 8), 50: ("MS", 1, 4), 51: ("MT", 1, 3),
         52: ("GO", 2, 3), 53: ("DF", 2, 4)}
REF_UF = 11                                  # referência dos efeitos fixos de UF no M3: Rondônia


def _br(v: float, c: int = 1) -> str:
    return f"{v:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _ler(nome: str) -> list[dict]:
    with (TAB / nome).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))



def _ch(v: float) -> str:
    """Razão de chances em linguagem comum: 0,81 → '19% menores'; 1,31 → '31% maiores'."""
    return f"{_br(abs(v - 1) * 100, 0)}% {'menores' if v < 1 else 'maiores'}"


def _cor_genero() -> dict:
    """Colorismo por sexo (scripts/analise/run_colorismo_genero.py): barras e textos do cartão."""
    cg = {(r["sexo"], r["grupo"], r["desfecho"]): float(r["valor"]) for r in _ler("colorismo_genero.csv")}
    n = {r["sexo"]: int(r["N"]) for r in _ler("colorismo_genero.csv")}
    ordem = (("mulheres", "preto", "Pretas"), ("mulheres", "pardo", "Pardas"),
             ("homens", "preto", "Pretos"), ("homens", "pardo", "Pardos"))
    out = {}
    # salário: duas leituras com a mesma escala, para a barra crescer ao trocar a referência
    # a = contra brancos do mesmo sexo; b = contra o homem branco (desfecho log_renda_ref_hb)
    sal = (("mulheres", "preto", "Pretas", "pretas"), ("mulheres", "pardo", "Pardas", "pardas"),
           ("mulheres", "branco", "Brancas", "brancas"), ("homens", "preto", "Pretos", "pretos"),
           ("homens", "pardo", "Pardos", "pardos"), ("homens", "branco", "Brancos", None))
    va = lambda s_, g_: 0.0 if g_ == "branco" else cg[(s_, g_, "log_renda")]          # noqa: E731
    vb = lambda k: 0.0 if k is None else cg[("todos", k, "log_renda_ref_hb")]          # noqa: E731
    topo = max(max(va(s_, g_), vb(k)) for s_, g_, _, k in sal)
    rot_v = lambda v: "referência" if v == 0 else f"{_br(v)}%"                          # noqa: E731
    linhas = []
    for i, (s_, g_, rot, k) in enumerate(sal):
        a, b = va(s_, g_), vb(k)
        linhas.append(f'<div class="cg-linha{" sep" if i == 3 else ""}" data-a="{a / topo * 100:.1f}" '
                      f'data-b="{b / topo * 100:.1f}" data-ta="{rot_v(a)}" data-tb="{rot_v(b)}"><span>{rot}</span>'
                      f'<div class="cg-barra {g_}" style="width:{a / topo * 100:.1f}%"></div><b>{rot_v(a)}</b></div>')
    out["__CG_RENDA__"] = "".join(linhas)
    ordem_q = ordem
    topo = max(cg[(s_, g_, "qualif")] for s_, g_, _ in ordem_q)
    linhas = []
    for i, (s_, g_, rot) in enumerate(ordem_q):
        v = cg[(s_, g_, "qualif")]
        linhas.append(f'<div class="cg-linha{" sep" if i == 2 else ""}"><span>{rot}</span>'
                      f'<div class="cg-barra {g_}" style="width:{v / topo * 100:.1f}%"></div><b>{_br(v)} p.p.</b></div>')
    out["__CG_QUALIF__"] = "".join(linhas)
    out["__CG_HB_PARDAS__"] = _br(vb("pardas"))
    out["__CG_HB_PRETOS__"] = _br(vb("pretos"))
    out["__CG_HB_BRANCAS__"] = _br(vb("brancas"))
    out["__CG_ARIA__"] = "Penalidade salarial: " + ", ".join(
        f"{rot} {_br(cg[(s, g, 'log_renda')])}%" for s, g, rot in ordem) + ". Cargo qualificado: " + ", ".join(
        f"{rot} {_br(cg[(s, g, 'qualif')])} pontos" for s, g, rot in ordem) + ". Contra o homem branco, salário: " + ", ".join(
        f"{r} {_br(cg[('todos', k, 'log_renda_ref_hb')])}%" for r, k in (("pretas", "pretas"), ("pardas", "pardas"),
        ("brancas", "brancas"), ("pretos", "pretos"), ("pardos", "pardos"))) + "."
    out["__CG_H_PRETO_R__"] = _br(cg[("homens", "preto", "log_renda")])
    out["__CG_M_PRETO_Q__"] = _br(cg[("mulheres", "preto", "qualif")])
    out["__CG_N__"] = _br((n["homens"] + n["mulheres"]) / 1e6)
    return out


def _jornada() -> dict:
    """Seção "Hora e jornada" (scripts/analise/run_jornada_raca.py): tempo, hora, horas e subocupação por cor."""
    import datetime as _dt
    gap = P["GAP_M3"] / 100
    extra = 1 / (1 - gap) - 1                       # quanto a mais de trabalho para igualar a renda anual
    dia = _dt.date(2026, 12, 31) + _dt.timedelta(days=round(extra * 365))
    meses = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
             "outubro", "novembro", "dezembro")
    hr = {r["desfecho"]: abs(float(r["pct"])) for r in _ler("jornada_raca_hora.csv")}
    mi = {(r["periodo"], r["grupo"], r["sexo"]): r for r in _ler("jornada_raca_pnad.csv")}
    v = lambda g, m, s="todos": float(mi[("2016-2025", g, s)][m])          # noqa: E731
    faixas = (("h_menos30", "Menos de 30h"), ("h_30_39", "30 a 39h"), ("h_40_44", "40 a 44h"), ("h_mais44", "Mais de 44h"))
    topo = max(v(g, k) for g in ("negro", "branco") for k, _ in faixas)
    lin = []
    for i, (k, rot) in enumerate(faixas):
        for g in ("negro", "branco"):
            x = v(g, k)
            lin.append(f'<div class="cg-linha{" par" if g == "negro" else ""}{" sep" if g == "negro" and i else ""}">'
                       f'<span>{rot if g == "negro" else ""}</span><div class="cg-barra {"preto" if g == "negro" else "branco"}" '
                       f'style="width:{x / topo * 100:.1f}%"></div><b>{_br(x)}%</b></div>')
    sub = (("mulheres", "Mulheres"), ("homens", "Homens"), ("todos", "Todos"))
    topo_s = max(v(g, "subocup", s) for g in ("negro", "branco") for s, _ in sub)
    lin_s = []
    for i, (s_, rot) in enumerate(sub):
        for g in ("negro", "branco"):
            x = v(g, "subocup", s_)
            lin_s.append(f'<div class="cg-linha{" par" if g == "negro" else ""}{" sep" if g == "negro" and i else ""}">'
                         f'<span>{rot if g == "negro" else ""}</span><div class="cg-barra {"preto" if g == "negro" else "branco"}" '
                         f'style="width:{x / topo_s * 100:.1f}%"></div><b>{_br(x)}%</b></div>')
    aria = ("Horas por semana, negros e brancos: " + "; ".join(
        f"{rot}: {_br(v('negro', k))}% e {_br(v('branco', k))}%" for k, rot in faixas) +
        ". Querem trabalhar mais e não conseguem: " + "; ".join(
        f"{rot}: negros {_br(v('negro', 'subocup', s_))}%, brancos {_br(v('branco', 'subocup', s_))}%" for s_, rot in sub) + ".")
    return {
        "__DIA_IGUAL__": f"{dia.day} de {meses[dia.month - 1]}",
        "__SEMANAS__": _br(extra * 52), "__DIAS_UTEIS__": _br(extra * 250, 0),
        "__HORA__": _br(hr["log_hora"]), "__MES__": _br(hr["log_renda"]), "__HORAS__": _br(hr["log_horas_mes"]),
        "__JOR_HORAS__": "".join(lin), "__JOR_SUB__": "".join(lin_s), "__JOR_ARIA__": aria,
        "__SUB_N__": _br(v("negro", "subocup")), "__SUB_B__": _br(v("branco", "subocup")),
        "__SUB_MN__": _br(v("negro", "subocup", "mulheres")),
        "__H30_N__": _br(v("negro", "h_menos30")), "__H30_B__": _br(v("branco", "h_menos30")),
        "__H40_N__": _br(v("negro", "h_mais40")), "__H40_B__": _br(v("branco", "h_mais40")),
        **_jornada_uf(),
    }


def _jornada_territorio() -> dict:
    """Mapa da jornada: estado × área (0 todo o estado, 1 capital, 2 região metropolitana, 3 interior)."""
    from dados_pagina_bairros import SIGLA as SIGLAS
    num = lambda x: None if x in ("", None) else round(float(x), 2)        # noqa: E731
    grupos = []
    for r in _ler("jornada_raca_territorio.csv"):
        grupos.append({"uf": SIGLAS[int(r["uf"])], "area": int(r["area"]),
                       **{k: num(r.get(k)) for k in ("sub_n", "sub_b", "h40_n", "h40_b", "h30_n", "h30_b", "hora_pen")},
                       "n_n": int(float(r["n_n"])), "n_b": int(float(r["n_b"]))})
    mi = {(r["periodo"], r["grupo"], r["sexo"]): r for r in _ler("jornada_raca_pnad.csv")}
    nb, bb = mi[("2016-2025", "negro", "todos")], mi[("2016-2025", "branco", "todos")]
    hr = {r["desfecho"]: float(r["pct"]) for r in _ler("jornada_raca_hora.csv")}
    brasil = {"sub_n": num(nb["subocup"]), "sub_b": num(bb["subocup"]), "h40_n": num(nb["h_mais40"]),
              "h40_b": num(bb["h_mais40"]), "hora_pen": round(-hr["log_hora"], 2),
              "n_n": int(nb["n"]), "n_b": int(bb["n"])}
    return {"grupos": grupos, "brasil": brasil}


def _jornada_dados() -> dict:
    """Números do capítulo 9 para os gráficos (mesmas fontes de _jornada)."""
    import datetime as _dt
    gap = P["GAP_M3"] / 100
    extra = 1 / (1 - gap) - 1
    dia = _dt.date(2026, 12, 31) + _dt.timedelta(days=round(extra * 365))
    meses = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
             "outubro", "novembro", "dezembro")
    hr = {r["desfecho"]: abs(float(r["pct"])) for r in _ler("jornada_raca_hora.csv")}
    mi = {(r["periodo"], r["grupo"], r["sexo"]): r for r in _ler("jornada_raca_pnad.csv")}
    v = lambda g, m, s="todos": float(mi[("2016-2025", g, s)][m])          # noqa: E731
    faixas = (("h_menos30", "Menos de 30h"), ("h_30_39", "30 a 39h"), ("h_40_44", "40 a 44h"), ("h_mais44", "Mais de 44h"))
    return {"extra": extra, "dia": f"{dia.day} de {meses[dia.month - 1]}",
            "mes": hr["log_renda"], "hora": hr["log_hora"], "horas": hr["log_horas_mes"],
            "faixas": [{"k": k, "rot": rot, "n": v("negro", k), "b": v("branco", k)} for k, rot in faixas],
            "sub": [{"k": s_, "rot": rot, "n": v("negro", "subocup", s_), "b": v("branco", "subocup", s_)}
                    for s_, rot in (("mulheres", "Mulheres"), ("homens", "Homens"), ("todos", "Todos"))],
            "h40": {"n": v("negro", "h_mais40"), "b": v("branco", "h_mais40")}}


def _jornada_uf() -> dict:
    """Marcadores do mapa da jornada: no nível do estado (área 0)."""
    uf = [r for r in _ler("jornada_raca_territorio.csv") if int(r["area"]) == 0]
    hora = [float(r["hora_pen"]) for r in uf if r.get("hora_pen")]
    pos = sum(float(r["sub_n"]) > float(r["sub_b"]) for r in uf)
    frase = "Em <strong>todos os 27</strong> estados" if pos == len(uf) else f"Em <strong>{pos}</strong> dos {len(uf)} estados"
    return {"__SUB_UF_FRASE__": frase, "__HORA_UF_MIN__": _br(min(hora)) + "%", "__HORA_UF_MAX__": _br(max(hora)) + "%"}

def dados() -> dict:
    ufs = {int(r["UF"]): float(r["coef"]) for r in _ler("hlm_stepup_efeitos_uf.csv")}
    ufs.setdefault(REF_UF, 0.0)
    mapa = [{"uf": GRADE[k][0], "c": GRADE[k][1], "r": GRADE[k][2],
             "pct": round((math.exp(v) - 1) * 100, 1)} for k, v in ufs.items() if k in GRADE]

    b19 = float(_ler("covid_evento_resumo.csv")[0]["beta_negro_2019"])
    pen = lambda b: abs(math.exp(b) - 1) * 100                      # noqa: E731
    anos = [{"ano": int(float(r["ano"])), "v": round(pen(b19 + float(r["delta"])), 2),
             "lo": round(pen(b19 + float(r["ic_hi"])), 2), "hi": round(pen(b19 + float(r["ic_lo"])), 2)}
            for r in _ler("covid_evento.csv") if r["desfecho"] == "log_renda"]

    return {
        "degraus": [{"rotulo": "Sem comparar vizinhos", "valor": P["GAP_POOL"]},
                    {"rotulo": "Entre vizinhos", "valor": P["GAP_M1"]},
                    {"rotulo": "+ bairro rico ou pobre", "valor": P["GAP_M2"]},
                    {"rotulo": "+ estado", "valor": P["GAP_M3"]},
                    {"rotulo": "+ mesma ocupação", "valor": P["GAP_M4"]}],
        "ufs": mapa,
        "educ": [{"rotulo": "Sem fundamental", "valor": P["NE_GAP_SEMFUND"]},
                 {"rotulo": "Fundamental", "valor": P["NE_GAP_FUND"]},
                 {"rotulo": "Médio", "valor": P["NE_GAP_MEDIO"]},
                 {"rotulo": "Superior", "valor": P["NE_GAP_SUP"]},
                 {"rotulo": "Pós-graduação", "valor": P["NE_GAP_POS"]}],
        "or_pos": round(1 - P["PCTPOS_ocp_qualif"] / 100, 3),
        "qr": [{"q": q, "v": P[f"QR_GAP_Q{q}"]} for q in (10, 25, 50, 75, 90, 95)],
        "ors": [{"rotulo": "Cargo qualificado", "valor": P["OR_ocp_qualif_M2"]},
                {"rotulo": "20% mais ricos", "valor": P["OR_y_top20_M2"]},
                {"rotulo": "10% mais ricos", "valor": P["OR_y_top10_M2"]}],
        "cbo": [{"chave": "agreg", "rotulo": "Cargo qualificado", "mn": P["GRG_MN_OCP_QUALIF"],
                 "mb": P["GRG_MB_OCP_QUALIF"], "hn": P["GRG_HN_OCP_QUALIF"]},
                {"chave": "dir", "rotulo": "Dirigentes", "mn": P["CBO_MN_dirigente"],
                 "mb": P["CBO_MB_dirigente"], "hn": P["CBO_HN_dirigente"]},
                {"chave": "prof", "rotulo": "Profissionais", "mn": P["CBO_MN_profissional"],
                 "mb": P["CBO_MB_profissional"], "hn": P["CBO_HN_profissional"]},
                {"chave": "tec", "rotulo": "Técnicos", "mn": P["CBO_MN_tecnico"],
                 "mb": P["CBO_MB_tecnico"], "hn": P["CBO_HN_tecnico"]},
                {"chave": "adm", "rotulo": "Apoio administrativo", "mn": P["CBO_MN_administrativo"],
                 "mb": P["CBO_MB_administrativo"], "hn": P["CBO_HN_administrativo"]},
                {"chave": "t10", "rotulo": "10% mais ricos", "mn": P["GRG_MN_TOP10"],
                 "mb": P["GRG_MB_TOP10"], "hn": P["GRG_HN_TOP10"]}],
        "anos": anos,
    }


def main() -> int:
    import dados_pagina_bairros as DB
    d = dados()
    bai = DB.dados(P["B_M3_RS"])
    rs = bai["resumo"]
    real = lambda v: "R$ " + _br(v, 0)                            # noqa: E731
    uf_min = f"{_br(rs['uf_med_min'])}% ({rs['uf_med_min_sigla']})"
    uf_max = f"{_br(rs['uf_med_max'])}% ({rs['uf_med_max_sigla']})"
    NOMES = {"RO": "Rondônia", "AC": "Acre", "AM": "Amazonas", "RR": "Roraima", "PA": "Pará", "AP": "Amapá",
             "TO": "Tocantins", "MA": "Maranhão", "PI": "Piauí", "CE": "Ceará", "RN": "Rio Grande do Norte",
             "PB": "Paraíba", "PE": "Pernambuco", "AL": "Alagoas", "SE": "Sergipe", "BA": "Bahia",
             "MG": "Minas Gerais", "ES": "Espírito Santo", "RJ": "Rio de Janeiro", "SP": "São Paulo",
             "PR": "Paraná", "SC": "Santa Catarina", "RS": "Rio Grande do Sul", "MS": "Mato Grosso do Sul",
             "MT": "Mato Grosso", "GO": "Goiás", "DF": "Distrito Federal"}
    eco = DB.economia(P["GAP_M3"], P["AME_ocp_qualif_M2"])
    des = DB.desigualdade(P["GAP_M3"])
    d.update({"geo": bai["geo"], "ufs": bai["ufs"], "nomes": [NOMES[s] for s in bai["ufs"]],
              "busca": bai["busca"], "txt": {"pct_bairros": _br(rs["pct_bairros_penalidade"])},
              "quem": {"cor": [{"rotulo": "Pardos", "valor": P["HET_HLM_PARDO"]},
                               {"rotulo": "Pretos", "valor": P["HET_HLM_PRETO"]}],
                       "cor_or": {"pardo": P["HET_OR_PARDO_OCP"], "preto": P["HET_OR_PRETO_OCP"]},
                       "idade": [{"rotulo": r, "valor": P[f"HET_IDADE_{k}"]} for r, k in
                                 (("14 a 29 anos", "14_29"), ("30 a 39", "30_39"), ("40 a 49", "40_49"),
                                  ("50 a 64", "50_64"), ("65 ou mais", "65MAIS"))],
                       "setor": [{"rotulo": "Cargo qualificado", "priv": P["HET_OR_SETOR0_OCP"], "pub": P["HET_OR_SETOR1_OCP"]},
                                 {"rotulo": "10% mais ricos", "priv": P["HET_OR_SETOR0_T10"], "pub": P["HET_OR_SETOR1_T10"]}]}})
    d["jornada"] = _jornada_territorio()
    # capítulos 7 a 11 (gráficos com rolagem)
    cg = {(r["sexo"], r["grupo"], r["desfecho"]): float(r["valor"]) for r in _ler("colorismo_genero.csv")}
    or_menor = lambda k: (1 - P[k]) * 100                                   # noqa: E731
    d["cor2"] = {"sal": {"preto": P["HET_HLM_PRETO"], "pardo": P["HET_HLM_PARDO"]},
                 "ocp": {"preto": or_menor("HET_OR_PRETO_OCP"), "pardo": or_menor("HET_OR_PARDO_OCP")},
                 "t10": {"preto": or_menor("HET_OR_PRETO_T10"), "pardo": or_menor("HET_OR_PARDO_T10")},
                 "q90": {"preto": P["HET_QR_PRETO_Q90"], "pardo": P["HET_QR_PARDO_Q90"]},
                 "cg_sexo": {"pretas": cg[("mulheres", "preto", "log_renda")], "pardas": cg[("mulheres", "pardo", "log_renda")],
                             "pretos": cg[("homens", "preto", "log_renda")], "pardos": cg[("homens", "pardo", "log_renda")]},
                 "cg_hb": {k: cg[("todos", k, "log_renda_ref_hb")] for k in ("pretas", "pardas", "brancas", "pretos", "pardos")}}
    d["eco"] = {"ocup": eco["ocupados_negros"], "talento": eco["talento_fora"], "massa": eco["massa_negros_ano"],
                "renda": eco["renda_nao_paga"]}
    d["des"] = {"pop": des["parcela_pop_negros"], "massa": des["parcela_massa_negros"],
                "massa_sp": des["parcela_massa_negros_sem_pen"], "gini": des["gini"], "gini_sp": des["gini_sem_penalidade"],
                "gini_ig": des["gini_medias_iguais"], "theil_entre": des["pct_theil_entre"]}
    d["jor"] = _jornada_dados()
    d["crit"] = {"med_bairro": P["MED_BAIRRO"], "gap_pool": P["GAP_POOL"]}
    d["roteiro"] = [
        {"lente": "mapa", "nascer": True, "s": 7,
         "legenda": f"{_br(rs['n_bairros'], 0)} bairros. Cada ponto, uma vizinhança entrevistada pela PNAD."},
        {"lente": "mapa", "s": 6, "legenda": "Azul: onde negros ganham menos que brancos de mesmo perfil, no mesmo bairro."},
        {"lente": "divisao", "s": 7, "legenda": f"Em {_br(rs['pct_bairros_penalidade'])}% dos bairros, a diferença existe."},
        {"lente": "negros", "s": 8, "legenda": (f"Onde mais de {_br(rs['pneg_q4_corte'], 0)}% são negros, a renda mediana é "
                                                f"{real(rs['renda_med_q4_pneg'])}. Onde são menos de "
                                                f"{_br(rs['pneg_q1_corte'], 0)}%, {real(rs['renda_med_q1_pneg'])}.")},
        {"lente": "renda", "s": 7, "legenda": "E nos bairros mais ricos, a penalidade é maior."},
        {"lente": "estados", "s": 7, "legenda": (f"Em todos os 27 estados, o bairro mediano tem penalidade: de "
                                                 f"{_br(rs['uf_med_min'])}% a {_br(rs['uf_med_max'])}%.")},
        {"lente": "mapa", "s": 8, "legenda": (f"Entre vizinhos, negros ganham {_br(P['GAP_M3'])}% menos. Com pós-graduação, "
                                              f"têm {_br(P['PCTPOS_ocp_qualif'], 0)}% menos chances de cargo qualificado.")},
        {"lente": "mapa", "s": 8, "legenda": (f"A barreira deixa cerca de {_br(eco['talento_fora'] / 1e6, 1)} milhão de "
                                              f"trabalhadores negros fora de cargos qualificados. Talento formado, e não aproveitado.")},
        {"lente": "mapa", "s": 8, "legenda": "Bairro, porta e topo: três barreiras, três políticas. Role a página para ver as propostas."},
    ]
    for c in d["roteiro"]:                      # tempo para a narração ler a legenda inteira
        c["s"] = max(c["s"], round(len(c["legenda"].split()) / 2.4 + 1.5, 1))
    troca = {
        "__N_OCUP__": _br(P["N_GLMM"] / 1e6, 1) + " milhões de",
        "__N_BAIRROS__": _br(rs["n_bairros"], 0),
        "__MED_BAIRRO__": _br(P["MED_BAIRRO"]),
        "__OCP_MENOR__": _br((1 - P["OR_ocp_qualif_M2"]) * 100, 0),
        "__QR10__": _br(P["QR_GAP_Q10"]), "__QR90__": _br(P["QR_GAP_Q90"]),
        "__PCT_BAIRROS__": _br(rs["pct_bairros_penalidade"]), "__PEN_MED__": _br(rs["pen_mediana"]),
        "__PNEG_Q4__": _br(rs["pneg_q4_corte"], 0), "__PNEG_Q1__": _br(rs["pneg_q1_corte"], 0),
        "__RENDA_Q4__": real(rs["renda_med_q4_pneg"]), "__RENDA_Q1__": real(rs["renda_med_q1_pneg"]),
        "__UF_MIN__": uf_min, "__UF_MAX__": uf_max,
        "__GAP_POOL__": _br(P["GAP_POOL"]), "__GAP_M1__": _br(P["GAP_M1"]),
        "__GAP_M3__": _br(P["GAP_M3"]), "__GAP_M4__": _br(P["GAP_M4"]),
        "__NE_SEMFUND__": _br(P["NE_GAP_SEMFUND"]), "__NE_POS__": _br(P["NE_GAP_POS"]),
        "__PCTPOS__": _br(P["PCTPOS_ocp_qualif"], 0),
        "__OR_OCP__": _ch(P["OR_ocp_qualif_M2"]), "__OR_T20__": _ch(P["OR_y_top20_M2"]),
        "__OR_T10__": _ch(P["OR_y_top10_M2"]),
        "__T10_MENOR__": _br((1 - P["OR_y_top10_M2"]) * 100, 0),
        "__PRIV_T10__": _ch(P["HET_OR_SETOR0_T10"]), "__PUB_T10__": _ch(P["HET_OR_SETOR1_T10"]),
        "__MN_AGREG__": _ch(P["GRG_MN_OCP_QUALIF"]), "__MN_ADM__": _ch(P["CBO_MN_administrativo"]),
        "__MN_DIR__": _ch(P["CBO_MN_dirigente"]), "__MN_T10__": _ch(P["GRG_MN_TOP10"]),
        "__COV19__": _br(P["COV_PEN_2019"]), "__COV20__": _br(P["COV_PEN_2020"]),
        "__COV25__": _br(P["COV_PEN_2025"]),
        "__HET_PRETO__": _br(P["HET_HLM_PRETO"]), "__HET_PARDO__": _br(P["HET_HLM_PARDO"]),
        "__IDADE_JOVEM__": _br(P["HET_IDADE_14_29"]), "__IDADE_65__": _br(P["HET_IDADE_65MAIS"]),
        "__PRIV_OCP__": _ch(P["HET_OR_SETOR0_OCP"]), "__PUB_OCP__": _ch(P["HET_OR_SETOR1_OCP"]),
        "__ECO_ANO__": str(eco["ano"]), "__ECO_OCUP__": _br(eco["ocupados_negros"] / 1e6, 1) + " milhões",
        "__ECO_TALENTO__": _br(eco["talento_fora"] / 1e6, 1) + " milhão",
        "__ECO_RENDA__": "R$ " + _br(eco["renda_nao_paga"] / 1e9, 0) + " bi",
        "__ECO_MASSA__": "R$ " + _br(eco["massa_negros_ano"] / 1e12, 2) + " trilhão",
        "__AME__": _br(abs(P["AME_ocp_qualif_M2"])),
        "__DES_POP__": _br(des["parcela_pop_negros"]), "__DES_MASSA__": _br(des["parcela_massa_negros"]),
        "__DES_MASSA_SP__": _br(des["parcela_massa_negros_sem_pen"]),
        "__GINI__": _br(des["gini"], 3), "__GINI_SP__": _br(des["gini_sem_penalidade"], 3),
        "__GINI_IG__": _br(des["gini_medias_iguais"], 3), "__THEIL_ENTRE__": _br(des["pct_theil_entre"]),
        "__OR_PRETO_OCP__": _ch(P["HET_OR_PRETO_OCP"]), "__OR_PARDO_OCP__": _ch(P["HET_OR_PARDO_OCP"]),
        "__OR_PRETO_T10__": _ch(P["HET_OR_PRETO_T10"]), "__OR_PARDO_T10__": _ch(P["HET_OR_PARDO_T10"]),
        "__QR_PRETO_Q90__": _br(P["HET_QR_PRETO_Q90"]), "__QR_PARDO_Q90__": _br(P["HET_QR_PARDO_Q90"]),
        **_cor_genero(),
        **_jornada(),
        "__COR_IC__": " A diferença entre os dois grupos é maior que a margem de erro." if P.get("HET_COR_SEPARA") else "",
    }
    html = MODELO.read_text(encoding="utf-8")
    for k, v in troca.items():
        html = html.replace(k, v)
    html = html.replace("/*__DADOS__*/null", json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("/*__BAIRROS__*/null", json.dumps(bai["b"], separators=(",", ":")))
    import re as _re
    restos = sorted(set(_re.findall(r"__[A-Z0-9_]+__", html)))
    if restos:
        print(f"ERRO: marcadores não preenchidos: {restos}")
        return 1
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(html, encoding="utf-8")
    # roteiro para gravar a narração com voz própria (uma linha por cena, com o tempo de cada uma)
    linhas = ["# Roteiro da narração — Bairro, porta e topo (1 minuto)", "",
              "Leia cada cena no tempo indicado; o áudio é sincronizado com a animação.", ""]
    t0 = 0.0
    for j, c in enumerate(d["roteiro"], 1):
        linhas.append(f"{j}. [{int(t0) // 60}:{int(t0) % 60:02d}–{int(t0 + c['s']) // 60}:{int(t0 + c['s']) % 60:02d}] {c['legenda']}")
        t0 += c["s"]
    (SAIDA.parent / "roteiro_narracao.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"OK -> {SAIDA.relative_to(ROOT)} ({len(html) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
