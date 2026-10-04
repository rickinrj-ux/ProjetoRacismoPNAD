# Passos que entram DEPOIS da fila_reestima (que já leu a própria lista e não aceita
# acréscimos): espera o FIM_FILA e roda em sequência, um processo por passo.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_pos_reestima.ps1' -WindowStyle Hidden
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$prev = "$root\outputs\logs\fila_reestima_status.log"
$st   = "$root\outputs\logs\fila_pos_reestima_status.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"

Add-Content $st "$(Get-Date -Format s) AGUARDANDO fila_reestima"
while ($true) {
    if ((Test-Path $prev) -and ((Get-Content $prev -Tail 1) -match "FIM_FILA")) { break }
    Start-Sleep -Seconds 60
}

$passos = @(
    # penalidade racial por nível de escolaridade (M3 do núcleo + negro:C(nivel)); usa o
    # cache do M3 regravado pela fila_reestima para o LR
    @("hlm_negro_educ", "python -u scripts/analise/run_hlm_negro_por_educ.py"),
    # a mesma penalidade por nível, agora por estado, com efeitos aleatórios de UF
    @("hlm_negro_educ_uf", "python -u scripts/analise/run_hlm_negro_educ_uf.py")
)
foreach ($p in $passos) {
    $nome = $p[0]; $log = "$root\outputs\logs\pos_$nome.log"
    Add-Content $st "$(Get-Date -Format s) INICIO $nome"
    cmd /c "$($p[1]) > `"$log`" 2>&1"
    $res = if ($LASTEXITCODE -eq 0) { "OK" } else { "FALHOU(rc=$LASTEXITCODE)" }
    Add-Content $st "$(Get-Date -Format s) $res $nome"
}
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
