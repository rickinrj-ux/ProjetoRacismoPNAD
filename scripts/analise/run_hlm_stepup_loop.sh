#!/usr/bin/env bash
# Ajusta o step-up um degrau por processo, para a memória ser devolvida ao SO
# entre modelos — os seis juntos estouram a RAM em 7,7 milhões de observações.
# Degraus já em cache são pulados; ao final, a execução sem --fit reaproveita
# tudo e escreve os csv, o .tex e a figura.
#
# Uso: bash scripts/analise/run_hlm_stepup_loop.sh
set -u
cd "$(dirname "$0")/../.." || exit 1

PY=${PY:-python}
MODELOS="M0 M0_REML M1 M2 M3 M4 M3_RS"

for m in $MODELOS; do
    if [ -f "outputs/_cache/hlm_stepup/${m}.pkl" ]; then
        echo "== ${m}: já em cache, pulando"
        continue
    fi
    echo "== ${m}: ajustando ($(date +%H:%M:%S))"
    "$PY" scripts/analise/run_hlm_stepup.py --fit "$m" || {
        echo "!! ${m} falhou (exit $?) — interrompendo"; exit 1; }
done

echo "== agregando e escrevendo csv/tex/figura ($(date +%H:%M:%S))"
"$PY" scripts/analise/run_hlm_stepup.py
