# Escada educacional (03/10): LR corrigido + versão within-UPA nacional, em sequência.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_escada.ps1' -WindowStyle Hidden
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_escada_status.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$passos = @(
    @("escada_fe_nacional", "python -u scripts/analise/run_hlm_negro_educ_uf.py --nacional"),
    @("escada_re_lr",       "python -u scripts/analise/run_hlm_negro_por_educ.py")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\escada_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $res = if ($LASTEXITCODE -eq 0) { "OK" } else { "FALHOU(rc=$LASTEXITCODE)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
