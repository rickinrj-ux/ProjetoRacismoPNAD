# Reestimações com o M3 do núcleo: sensibilidade ao educ_missing (2 modelos na população)
# e série anual 2016–2025 (10 modelos), um modelo por processo; depois, a tendência temporal.
# Lançar destacado:  Start-Process powershell -ArgumentList '-File','tcc\scripts\fila_m3.ps1' -WindowStyle Hidden
$root = "C:\Users\user\Documents\ProjetoRacismoPNAD"
$st   = "$root\outputs\logs\fila_m3_status.log"
$log  = "$root\outputs\logs\fila_m3.log"
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
function Linhas($p) { if (Test-Path $p) { @(Import-Csv $p).Count } else { 0 } }
$sens  = "$root\outputs\tables\sensib_educ_missing.csv"
$serie = "$root\outputs\tables\validacao_temporal.novo.csv"

# a sensibilidade ao educ_missing saiu: com a VD3004 não há mais indicador de ausência
foreach ($etapa in @(,@("serie", $serie, 10))) {
    $nome, $csv, $alvo = $etapa
    for ($i = 1; $i -le ($alvo + 3); $i++) {
        $antes = Linhas $csv
        if ($antes -ge $alvo) { break }
        Add-Content $st "$(Get-Date -Format s) $nome $antes/$alvo"
        cmd /c "python -u scripts/analise/run_m3_serie_sensib.py --$nome --um >> `"$log`" 2>&1"
        if ((Linhas $csv) -le $antes) { Add-Content $st "$(Get-Date -Format s) FALHOU $nome sem progresso"; exit 1 }
    }
    Add-Content $st "$(Get-Date -Format s) OK $nome $(Linhas $csv)/$alvo"
}
# com os 10 anos gravados, uma última chamada consolida validacao_temporal.csv
cmd /c "python -u scripts/analise/run_m3_serie_sensib.py --serie --um >> `"$log`" 2>&1"
cmd /c "python -u scripts/analise/run_tendencia_temporal.py >> `"$log`" 2>&1"
Add-Content $st "$(Get-Date -Format s) tendencia rc=$LASTEXITCODE"
Add-Content $st "$(Get-Date -Format s) FIM_FILA"
