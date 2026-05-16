"""
ingestion_rais.py
=================
Ingestão e limpeza dos microdados RAIS (Relação Anual de Informações Sociais)
a partir dos arquivos brutos do MTE (.txt semicolonados, cp1252).

Harmoniza as variáveis RAIS com as definições da PNAD Contínua usadas em
feature_engineering.py, permitindo validação cruzada dos achados.

Fluxo:
    Arquivos .txt RAIS (por UF/ano)
        → leitura chunked (memória)
        → seleção de vínculos ativos e raças de interesse
        → mapeamento de variáveis para escala PNAD
        → winsorização de salário (1%)
        → log_renda, negro, educ_ord, horas_c, UF_str, ...
        → parquet em data/external/rais_processada.parquet

Período coberto: 2016-2025 (espelho da PNAD Contínua).
    Obs.: RAIS é divulgada com ~12 meses de defasagem. Em 2026, o dado mais
    recente disponível costuma ser o de 2024.

Como obter os dados:
    1. Acesse ftp://ftp.mtecaged.gov.br/ftp/rais/  (ou via IPEA/basedosdados)
    2. Baixe os arquivos de Vínculos por UF/ano (ex: RAIS_VINC_PUB_RJ_2022.txt.7z)
    3. Descompacte os .7z → .txt
    4. Coloque todos os .txt em um mesmo diretório (ex: data/external/rais_raw/)
    5. Execute: python run_ingestion_rais.py --rais_dir data/external/rais_raw/

Referências de layout:
    MTE. Dicionário de Variáveis RAIS — Vínculos (2016+). Brasília, 2024.
    Raca/Cor RAIS: 1=Indígena 2=Branca 4=Preta 6=Amarela 8=Parda 9=N.I.
    Grau Instrução: 1(Analfabeto) ... 11(Doutorado)
    Salário mínimo: 2016=R$880 → 2025=R$1.518
"""

import re
import logging
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

OUT_DIR = Path("data/external")


# ── Constantes de mapeamento ───────────────────────────────────────────────────

# RAIS Raça Cor → negro (espelho do PNAD: Preto+Pardo)
RAIS_NEGRO  = {4, 8}    # 4=Preta, 8=Parda
RAIS_BRANCO = {2}       # 2=Branca

# RAIS Grau Instrução após 2005 (1-11) → educ_ord (0-7, escala PNAD)
RAIS_EDUC_ORD = {
    1: 0,   # Analfabeto           → sem_instrucao
    2: 1,   # Até 5ª Incompleto    → fund_incompleto
    3: 2,   # 5ª Completo          → fund_completo
    4: 1,   # 6ª a 9ª Fundamental  → fund_incompleto
    5: 2,   # Fundamental Completo → fund_completo
    6: 3,   # Médio Incompleto     → medio_incompleto
    7: 4,   # Médio Completo       → medio_completo
    8: 5,   # Superior Incompleto  → superior_incompleto
    9: 6,   # Superior Completo    → superior_completo
    10: 7,  # Mestrado             → pos_graduacao
    11: 7,  # Doutorado            → pos_graduacao
}

# Salário mínimo mensal nominal por ano (Decreto presidencial)
# Período espelho da PNAD Contínua: 2016-2025
SALARIO_MINIMO = {
    2016: 880,  2017: 937,  2018: 954,  2019: 998,
    2020: 1045, 2021: 1100, 2022: 1212, 2023: 1320,
    2024: 1412, 2025: 1518,
}

# Código IBGE UF (2 primeiros dígitos do município) → sigla
UF_IBGE = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

# Nomes alternativos de colunas nas diferentes versões dos arquivos RAIS
# (MTE alterou cabeçalhos entre 2017 e 2023)
_ALIASES: dict[str, list[str]] = {
    "raca_cor":       ["Raça Cor", "Raca Cor", "RAÇA COR", "RACA COR",
                       "raça cor", "Raça/Cor"],
    "grau_instrucao": ["Grau Instrução após 2005", "Grau Instrucao apos 2005",
                       "Escolaridade após 2005", "GRAU INSTRUÇÃO APÓS 2005",
                       "Grau de Instrução", "grau instrucao"],
    "sexo":           ["Sexo Trabalhador", "SEXO TRABALHADOR", "Sexo",
                       "sexo trabalhador"],
    "idade":          ["Idade", "IDADE", "idade"],
    "municipio":      ["Município", "MUNICÍPIO", "Municipio", "municipio",
                       "Município do Empregado"],
    "vl_remun_dez":   ["Vl Remun Dezembro Nom", "VL REMUN DEZEMBRO NOM",
                       "Vl Remun Dezembro Nom.", "vl remun dezembro nom",
                       "Vlr Remun Dezembro Nom"],
    "vl_remun_media": ["Vl Remun Média Nom", "VL REMUN MÉDIA NOM",
                       "Vl Remun Media Nom", "vl remun media nom"],
    "vl_remun_sm":    ["Vl Remun Dezembro (SM)", "Vl Remun Dezembro (Sm)",
                       "Vl Remun Media (SM)", "Vl Remun Média (SM)"],
    "horas_contr":    ["Qtd Hora Contr", "QTD HORA CONTR", "Qtd Horas Contr",
                       "qtd hora contr", "Quantidade de Horas Contratadas"],
    "nat_juridica":   ["Natureza Jurídica", "NATUREZA JURÍDICA",
                       "Natureza Juridica", "natureza juridica"],
    "cbo":            ["CBO Ocupação 2002", "CBO OCUPAÇÃO 2002",
                       "CBO Ocup 2002", "cbo ocupacao 2002", "CBO Ocupacao 2002"],
    "cnae":           ["CNAE 2.0 Empregado", "CNAE 2.0 Subclasse",
                       "CNAE2.0 Empregado", "cnae 2.0 empregado", "CNAE 2 Subclasse"],
    "vinculo_ativo":  ["Vínculo Ativo 31/12", "VÍNCULO ATIVO 31/12",
                       "Vinculo Ativo 3112", "vinculo ativo 31/12",
                       "Vínculo Ativo 3112"],
    "tipo_vinculo":   ["Tipo Vínculo", "TIPO VÍNCULO", "Tipo Vinculo",
                       "tipo vinculo"],
    "tempo_emprego":  ["Tempo Emprego", "TEMPO EMPREGO", "tempo emprego"],
}


# ── Utilitários ───────────────────────────────────────────────────────────────

def _mapear_colunas(cols_disponiveis: list[str]) -> dict[str, str]:
    """
    Recebe a lista de colunas do arquivo e retorna um mapa
    {nome_original → nome_canonico} para as colunas reconhecidas.
    """
    cols_norm = {c: re.sub(r"\s+", " ", c.strip()) for c in cols_disponiveis}
    mapa = {}
    for canonico, aliases in _ALIASES.items():
        for alias in aliases:
            for original, normalizado in cols_norm.items():
                if normalizado.lower() == alias.lower():
                    mapa[original] = canonico
                    break
    return mapa


def _salario_para_reais(df: pd.DataFrame, ano: int) -> pd.Series:
    """
    Retorna a coluna de salário em R$ nominais.
    Prioridade: vl_remun_dez > vl_remun_media > vl_remun_sm * SM.
    Converte separador decimal (vírgula → ponto).
    """
    def _to_float(s: pd.Series) -> pd.Series:
        return (
            s.astype(str)
             .str.replace(".", "", regex=False)
             .str.replace(",", ".", regex=False)
             .pipe(pd.to_numeric, errors="coerce")
        )

    sm = SALARIO_MINIMO.get(ano, 1100)
    if "vl_remun_dez" in df.columns:
        sal = _to_float(df["vl_remun_dez"])
        if sal.notna().mean() > 0.5:
            return sal
    if "vl_remun_media" in df.columns:
        sal = _to_float(df["vl_remun_media"])
        if sal.notna().mean() > 0.5:
            return sal
    if "vl_remun_sm" in df.columns:
        return _to_float(df["vl_remun_sm"]) * sm
    raise ValueError("Nenhuma coluna de salário encontrada no arquivo RAIS.")


def _uf_from_municipio(mun: pd.Series) -> pd.Series:
    """Extrai código UF (2 dígitos) do código IBGE de município e mapeia para sigla."""
    cod_uf = (
        pd.to_numeric(mun, errors="coerce")
          .dropna()
          .astype(int)
          .floordiv(10000)
    )
    return cod_uf.map(UF_IBGE).astype("category")


# ── Leitura dos arquivos brutos ───────────────────────────────────────────────

def _detectar_separador(path: Path) -> str:
    """Detecta se o arquivo usa ';' ou '\t' como separador."""
    with open(path, encoding="cp1252", errors="replace") as f:
        primeira = f.readline()
    return ";" if primeira.count(";") > primeira.count("\t") else "\t"


def ler_arquivo_rais(path: Path, ano: int,
                     chunksize: int = 200_000,
                     sample_frac: Optional[float] = None) -> pd.DataFrame:
    """
    Lê um arquivo .txt RAIS (vínculos) em chunks e retorna DataFrame limpo.

    Filtra:
        - vinculo_ativo == 1  (empregado em 31/12)
        - raca_cor em {2, 4, 8}  (Branca, Preta, Parda)
        - salário > 0

    Parameters
    ----------
    path : Path — caminho do arquivo .txt descompactado
    ano  : int  — ano de referência (usado para converter SM → R$)
    chunksize : int — linhas por chunk (padrão 200k)
    sample_frac : float | None — fração aleatória (para testes)
    """
    sep = _detectar_separador(path)
    logger.info(f"  Lendo {path.name} | sep={repr(sep)} | enc=cp1252")

    chunks = []
    col_map = None
    n_total = 0
    n_validos = 0

    try:
        reader = pd.read_csv(
            path,
            sep=sep,
            encoding="cp1252",
            dtype=str,
            chunksize=chunksize,
            low_memory=False,
            on_bad_lines="skip",
        )
        for chunk in reader:
            n_total += len(chunk)
            chunk.columns = [c.strip() for c in chunk.columns]

            if col_map is None:
                col_map = _mapear_colunas(chunk.columns.tolist())
                ausentes = [k for k in ["raca_cor", "municipio"] if k not in col_map.values()]
                if ausentes:
                    logger.warning(f"    Colunas não encontradas: {ausentes} — verifique o layout.")
                logger.info(f"    Colunas mapeadas: {list(col_map.values())}")

            chunk = chunk.rename(columns=col_map)

            # ── Filtro: vínculo ativo ──────────────────────────────────────
            if "vinculo_ativo" in chunk.columns:
                chunk = chunk[chunk["vinculo_ativo"].astype(str).str.strip() == "1"]

            # ── Filtro: raça de interesse ──────────────────────────────────
            if "raca_cor" in chunk.columns:
                raca = pd.to_numeric(chunk["raca_cor"], errors="coerce")
                chunk = chunk[raca.isin({2, 4, 8})]

            if sample_frac and sample_frac < 1.0:
                chunk = chunk.sample(frac=sample_frac, random_state=42)

            n_validos += len(chunk)
            chunks.append(chunk)

    except Exception as exc:
        logger.error(f"    Erro ao ler {path.name}: {exc}")
        return pd.DataFrame()

    if not chunks:
        logger.warning(f"    Nenhum registro válido em {path.name}")
        return pd.DataFrame()

    logger.info(f"    {path.name}: {n_total:,} linhas → {n_validos:,} válidos")
    return pd.concat(chunks, ignore_index=True)


# ── Harmonização com PNAD ─────────────────────────────────────────────────────

def harmonizar_rais(df_raw: pd.DataFrame, ano: int) -> pd.DataFrame:
    """
    Transforma variáveis RAIS brutas para a mesma escala/nomenclatura da PNAD.

    Variáveis produzidas (subconjunto para validação cruzada):
        negro, sexo_fem, idade_c, idade_sq,
        educ_ord, educ_superior_completo, educ_medio_completo,
        log_renda, emprego_formal, setor_publico,
        horas_c, UF_str, ocp_grupo_cbo, cnae_setor,
        Ano, fonte (="RAIS")
    """
    out = pd.DataFrame()
    out["Ano"] = ano
    out["fonte"] = "RAIS"

    # ── Raça ──────────────────────────────────────────────────────────────────
    if "raca_cor" in df_raw.columns:
        raca = pd.to_numeric(df_raw["raca_cor"], errors="coerce")
        out["negro"] = np.nan
        out.loc[raca.isin(RAIS_NEGRO),  "negro"] = 1.0
        out.loc[raca.isin(RAIS_BRANCO), "negro"] = 0.0

    # ── Sexo ──────────────────────────────────────────────────────────────────
    if "sexo" in df_raw.columns:
        # RAIS: 1=Masculino, 3=Feminino
        out["sexo_fem"] = (pd.to_numeric(df_raw["sexo"], errors="coerce") == 3).astype("int8")

    # ── Idade ─────────────────────────────────────────────────────────────────
    if "idade" in df_raw.columns:
        idade = pd.to_numeric(df_raw["idade"], errors="coerce")
        idade = idade.where(idade.between(14, 80))
        mean_age = idade.mean()
        out["idade_c"]  = idade - mean_age
        out["idade_sq"] = out["idade_c"] ** 2

    # ── Educação ──────────────────────────────────────────────────────────────
    if "grau_instrucao" in df_raw.columns:
        grau = pd.to_numeric(df_raw["grau_instrucao"], errors="coerce")
        out["educ_ord"] = grau.map(RAIS_EDUC_ORD).astype("float32")
        out["educ_medio_completo"]    = (grau >= 7).astype("int8")
        out["educ_superior_completo"] = (grau >= 9).astype("int8")
        out["educ_pos_graduacao"]     = (grau >= 10).astype("int8")

    # ── Salário → log_renda ───────────────────────────────────────────────────
    try:
        sal = _salario_para_reais(df_raw, ano)
        sal = sal.where(sal > 0)
        # winsorização 1% (consistente com feature_engineering.py)
        p01 = sal.quantile(0.01)
        p99 = sal.quantile(0.99)
        sal = sal.clip(p01, p99)
        out["log_renda"] = np.log1p(sal)
    except ValueError as exc:
        logger.warning(f"  Salário: {exc}")

    # ── Horas contratadas ─────────────────────────────────────────────────────
    if "horas_contr" in df_raw.columns:
        horas = pd.to_numeric(df_raw["horas_contr"], errors="coerce")
        horas = horas.where(horas.between(1, 99))
        out["horas_c"] = horas - horas.mean()

    # ── Vínculo / setor público ───────────────────────────────────────────────
    # Na RAIS todos os vínculos ativos são formais por definição
    out["emprego_formal"] = 1
    if "nat_juridica" in df_raw.columns:
        nat = pd.to_numeric(df_raw["nat_juridica"], errors="coerce")
        # Nat. jurídica < 2000 = administração pública (CNPJ)
        out["setor_publico"] = (nat < 2000).astype("int8")
    else:
        out["setor_publico"] = np.nan

    # ── UF ────────────────────────────────────────────────────────────────────
    if "municipio" in df_raw.columns:
        out["UF_str"] = _uf_from_municipio(df_raw["municipio"]).values

    # ── CBO → grupo ocupacional ───────────────────────────────────────────────
    if "cbo" in df_raw.columns:
        out["ocp_grupo_cbo"] = (
            df_raw["cbo"].astype(str).str.strip().str[:1]
        )

    # ── CNAE → macro-setor ────────────────────────────────────────────────────
    if "cnae" in df_raw.columns:
        out["cnae_setor"] = df_raw["cnae"].astype(str).str.strip()

    # ── Tempo de emprego (proxy de duração) ───────────────────────────────────
    if "tempo_emprego" in df_raw.columns:
        out["tempo_emprego_meses"] = pd.to_numeric(
            df_raw["tempo_emprego"], errors="coerce"
        )

    # ── Limpeza final ─────────────────────────────────────────────────────────
    out = out.dropna(subset=["negro", "log_renda"])
    out["negro"] = out["negro"].astype("float32")

    return out.reset_index(drop=True)


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_ingestion_rais(
    rais_dir: str | Path,
    anos: Optional[list[int]] = None,
    output_path: str | Path = "data/external/rais_processada.parquet",
    sample_frac: Optional[float] = None,
    ufs: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Lê todos os arquivos RAIS .txt em rais_dir, harmoniza e salva parquet.

    Parameters
    ----------
    rais_dir    : diretório com arquivos .txt descompactados
    anos        : lista de anos a incluir (None = todos encontrados)
    output_path : caminho de saída do parquet
    sample_frac : fração amostral para testes
    ufs         : lista de UFs a incluir ex: ["SP", "RJ"] (None = todas)

    Returns
    -------
    DataFrame com variáveis harmonizadas, pronto para run_validacao.py --rais_path
    """
    rais_dir = Path(rais_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(rais_dir.glob("*.txt"))
    if not arquivos:
        arquivos = sorted(rais_dir.glob("*.TXT"))
    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo .txt encontrado em {rais_dir}. "
            "Descompacte os .7z do MTE e coloque os .txt nesse diretório."
        )

    logger.info(f"Diretório RAIS: {rais_dir} | {len(arquivos)} arquivo(s) .txt")

    frames = []
    for path in arquivos:
        # ── Detectar ano a partir do nome do arquivo ───────────────────────
        ano_match = re.search(r"(20\d{2})", path.stem)
        if not ano_match:
            logger.warning(f"  Ano não detectado em {path.name} — pulando.")
            continue
        ano = int(ano_match.group(1))
        if anos and ano not in anos:
            continue

        # ── Detectar UF a partir do nome do arquivo ────────────────────────
        uf_match = re.search(
            r"_(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)[\._]",
            path.stem.upper()
        )
        uf_arquivo = uf_match.group(1) if uf_match else None
        if ufs and uf_arquivo and uf_arquivo not in [u.upper() for u in ufs]:
            continue

        logger.info(f"Processando: {path.name} | ano={ano} | UF={uf_arquivo or 'detectar'}")
        df_raw = ler_arquivo_rais(path, ano, sample_frac=sample_frac)
        if df_raw.empty:
            continue

        df_harm = harmonizar_rais(df_raw, ano)

        # ── Filtrar por UF se informado e UF_str disponível ───────────────
        if ufs and "UF_str" in df_harm.columns:
            df_harm = df_harm[df_harm["UF_str"].isin([u.upper() for u in ufs])]

        logger.info(
            f"  Harmonizado: {len(df_harm):,} obs | "
            f"negro={df_harm['negro'].mean():.1%} | "
            f"gap bruto={df_harm.groupby('negro')['log_renda'].mean().diff().iloc[-1]:+.4f}"
        )
        frames.append(df_harm)

    if not frames:
        raise ValueError("Nenhum dado válido processado. Verifique os arquivos e parâmetros.")

    df_final = pd.concat(frames, ignore_index=True)

    # ── Estatísticas finais ────────────────────────────────────────────────────
    n_total = len(df_final)
    gap = df_final.groupby("negro")["log_renda"].mean()
    gap_pct = (np.exp(gap[1.0] - gap[0.0]) - 1) * 100

    logger.info(f"RAIS processada: {n_total:,} obs | anos={df_final['Ano'].unique().tolist()}")
    logger.info(f"  % negro: {df_final['negro'].mean():.1%}")
    logger.info(f"  gap bruto log-renda: {gap[1.0] - gap[0.0]:+.4f} ({gap_pct:+.1f}%)")

    df_final.to_parquet(output_path, index=False)
    logger.info(f"Salvo em: {output_path}")

    return df_final
