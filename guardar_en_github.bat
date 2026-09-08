@echo off
title Guardar Clima Accesible en GitHub
cd /d "%~dp0"
echo.
echo ===========================================================
echo   GUARDAR CLIMA ACCESIBLE EN GITHUB
echo ===========================================================
echo.
echo Archivos que han cambiado desde la ultima vez que guardaste:
echo.
git status --short
echo.
echo -----------------------------------------------------------
echo Guardando...
git add -A
git commit -m "Correcciones y traducciones de ClimaAccesible" -m "- Corregido un fallo que impedia guardar la configuracion: se usaba un dato que no existia." -m "- Textos nuevos pasados al espanol neutro del resto del complemento." -m "- Unas 45 frases del vocabulario meteorologico marcadas por fin como traducibles, y traducidas al ingles." -m "- Nombres tecnicos que estaban marcados para traducir por error, desmarcados." -m "- Red de pruebas automaticas: 32 comprobaciones de estructura, traducciones y logica."
echo.
echo -----------------------------------------------------------
echo Subiendo a GitHub...
git push
echo.
echo ===========================================================
if errorlevel 1 (
  echo   NO SE PUDO SUBIR A GITHUB.
  echo   El trabajo SI quedo guardado en tu equipo, no se ha perdido nada.
  echo   Lo de arriba dice por que fallo la subida.
) else (
  echo   LISTO. Guardado en tu equipo y subido a GitHub.
)
echo ===========================================================
echo.
pause
