"""
gerar_descritivos_base.py — contagens da base que o texto cita, gravadas em csv.

Antes estavam digitadas nos geradores ("15.941.675 observações brutas", "cerca de 31%
da PEA com escolaridade registrada"). Lidas do parquet uma vez e gravadas aqui, viram
parâmetro (params_nucleo) sem que cada importação precise abrir 15,9 milhões de linhas.

Saída: outputs/tables/descritivos_base.csv (chave, valor)
"""
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "data" / "processed" / "features.parquet"
OUT = ROOT / "outputs" / "tables" / "descritivos_base.csv"

t = pq.read_table(PARQUET, columns=["educ_cat", "pea"])
pea = t.filter(pc.equal(t["pea"], 1))
n_pea = pea.num_rows
n_educ = n_pea - pea["educ_cat"].null_count

linhas = {
    "N_BRUTO": t.num_rows,                       # observações brutas 2016–2025
    "N_PEA": n_pea,                              # pessoas na PEA
    "N_PEA_EDUC": n_educ,                        # PEA com escolaridade detalhada registrada
    "EDUC_COBERTURA": 100 * n_educ / n_pea,      # % da PEA com escolaridade registrada
}
with OUT.open("w", encoding="utf-8") as f:
    f.write("chave,valor\n")
    for k, v in linhas.items():
        f.write(f"{k},{v}\n")
print(f"OK -> {OUT.relative_to(ROOT)}: " + ", ".join(f"{k}={v:,.2f}" for k, v in linhas.items()))
