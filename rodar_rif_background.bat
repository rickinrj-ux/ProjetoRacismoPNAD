@echo off
cd /d "%~dp0"
echo Iniciando RIF-OB 100%% em segundo plano...
echo Log: logs\rif_decomp_full.log
start "RIF-OB 100pct" /MIN cmd /c "python run_rif_decomp.py --sample 0 > logs\rif_decomp_full.log 2>&1"
echo.
echo Processo iniciado. Feche esta janela.
echo Para acompanhar: type logs\rif_decomp_full.log
pause
