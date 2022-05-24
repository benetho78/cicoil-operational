# Scripts para el sistema operacional de pronostico de derrames de petroleo

## Requerimientos

 - OpenDrift-CiCOil
 - TAMOC
 - python > 3.7
 - xarray
 
## Herramientas:

 - `bin/run_nearfield.py` : Ejecuta el modelo TAMOC para una localizacion especifica.
 - `bin/run_farfield.py`  : Ejecuta el modelo OpenDrift-CiCOil para una localizacion especifica.

## Sobre los datos:

**Fleet Numerical Meteorology and Oceanography Center AMSEAS Forecast**

Pronostico de corrientes con modelo HYCOM para la region de los mares americanos
(AMerican SEAS) que se compone por el Golfo de México y parte central este del Atlantico.
Este pronostico se genera diariamente y contiene 4 dias de pronostico con un paso de tiempo
de 3 horas, con resolución horizontal de 3km y 40 niveles en vertical.

Variables disponibles:
 temperatura agua,salinidad, elevacion, corrientes en componentes u y v.


Servidores descarga de datos:

Servidor thredds ncei:
https://www.ncei.noaa.gov/thredds-coastal/catalog/amseas/catalog.html
Carpeta con pronostico: amseas_20201218_to_current/ 


