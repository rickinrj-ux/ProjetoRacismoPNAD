#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hook_revisao.py — Hook PostToolUse (Claude Code) da skill /revisao-livros.

Dispara quando uma ferramenta altera algo que muda as análises ou os entregáveis
do TCC (scripts de análise/geradores, src/, tabelas de saída, relatório .tex,
ou execução de um script de análise via shell). Roda o verificador mecânico e
devolve o sumário como contexto adicional para o Claude, com a instrução de
executar a revisão qualitativa completa (/revisao-livros) antes de encerrar.

Lê o JSON do evento no stdin; nunca bloqueia (exit 0).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VERIF = Path(__file__).with_name("verificar_analises.py")

# Caminhos cuja edição altera análises ou entregáveis
PATHS = re.compile(
    r"(scripts[\\/](analise|geradores|R)[\\/]|src[\\/]|tcc[\\/]scripts[\\/]|outputs[\\/]tables[\\/]"
    r"|relatorio_tcc_enxuto\.tex$|tcc[\\/]run_tcc\.ps1$)", re.I)
# Comandos de shell que (re)EXECUTAM análises (não basta citar o nome: `sed`/`cat` não contam)
CMDS = re.compile(
    r"(?:python[\w.]*(?:\.exe)?|Rscript|pwsh|powershell|&|\./tcc/)[\"']?\s*[\"']?\S*?"
    r"(run_tcc\.ps1|run_\w+\.py|gerar_\w+\.py|\w+\.R)\b", re.I)


def main() -> int:
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    tool = ev.get("tool_name", "")
    inp = ev.get("tool_input", {}) or {}
    alvo = ""
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        fp = str(inp.get("file_path") or inp.get("notebook_path") or "")
        if PATHS.search(fp):
            alvo = fp
    elif tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", ""))
        m = CMDS.search(cmd)
        if m:
            alvo = m.group(1)
    if not alvo:
        return 0

    try:
        out = subprocess.run([sys.executable, str(VERIF), "--quiet", "--arquivo", alvo],
                             capture_output=True, text=True, encoding="utf-8", errors="replace",
                             cwd=str(ROOT), timeout=120).stdout.strip()
    except Exception as e:  # noqa: BLE001
        out = f"(verificador falhou: {e})"

    linhas = out.splitlines()
    resumo = linhas[-1] if linhas else ""
    # só os ALTO no contexto (o relatório completo fica em tcc/revisoes/)
    corpo = "\n".join(l for l in linhas[:-1] if l.startswith("[ALTO]"))[:2500]
    ctx = (
        f"[revisao-livros] Alteração em análise/entregável detectada ({alvo}). "
        f"Verificação mecânica: {resumo}\n{corpo}\n"
        "Relatório salvo em tcc/revisoes/. Antes de encerrar a tarefa, invoque a skill "
        "`revisao-livros` para a revisão qualitativa dos critérios afetados (MHE, Fávero, "
        "Knaflic, Alencar) e corrija ou reporte ao usuário os achados ALTO."
    )
    # ensure_ascii=True: stdout do Windows pode ser cp1252; o JSON continua válido
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                             "additionalContext": ctx}}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
