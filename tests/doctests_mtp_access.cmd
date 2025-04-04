@echo off
cls
echo ------------------------------------------------------------------------------------
cd ..

rem set up virtual environment
call .\venv\Scripts\Activate.bat

echo.
echo.
echo.
echo.
echo.
echo #####################################################################################
python -m doctest mtp\win_access.py
cd .\tests
