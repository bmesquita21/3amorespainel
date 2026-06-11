@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Iniciando o Painel Financeiro 3 Amores...
echo (Para fechar, feche esta janela.)
rem limpa bytecode antigo p/ nunca carregar versao fantasma em cache
if exist "app\__pycache__" rmdir /s /q "app\__pycache__"
py -m streamlit run "app\painel.py"
pause
