#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 08:39:37 2022

@author: jcerda
"""

import os
from datetime import datetime, timedelta
import yaml
import argparse
# import datetime as dt
import numpy as np

from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.tamoc_plume import Plume
from opendrift.readers import reader_ROMS_native
from opendrift.readers import reader_NEMO_native
from opendrift.models.ciceseoil import OpenCiceseOil

# from opendrift.readers import reader_basemap_landmask
# from opendrift.models.openplume3D import OpenPlume3D
# import netCDF4 as nc
# import xarray as xr
# from siphon.catalog import TDSCatalog
# from subprocess import Popen

def getSafeOutputFilename(proposedFilename, fextension, count=0):
    if os.path.exists(proposedFilename + '.' + fextension):
        if proposedFilename.split('_')[-1].isnumeric():
            count = int(proposedFilename.split('_')[-1])
            proposedFilename = '_'.join(proposedFilename.split('_')[0:-1])
        nproposedFilename = proposedFilename + '_' + str(count+1)
        return getSafeOutputFilename(nproposedFilename, fextension, count+1)
    else:
        return proposedFilename + '.' + fextension


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Run far field model OPENDRIFT', prog='run_farfield')
  parser.add_argument('--subset', '-s', action='store', dest='PtoParam', help='yaml file with the information about point.')
  parser.add_argument('--windfac', '-w', action='store', dest='WindFac', help='Wind Factor', required=False)
  parser.add_argument('--commands', '-c', action='store_true', dest='show_commands', help='Just show the commands to run')

  # args = parser.parse_args('--config-file', "../Pto_Config.yaml")
  args = parser.parse_args()
  # TODO Add verbose mode
  if args.PtoParam:
      with open(args.PtoParam, 'r') as stream:
          try: 
              PtoParam = yaml.safe_load(stream)
          except:
              print ('Something went wrong reading ' + args.subsetconfig)            

  # Wind factor as input argument
  if args.WindFac:
      wind_factor = float(args.WindFac)
      print('Factor del viento: ', wind_factor)

  # IF date is NOT given, run the present day
  if PtoParam['sim']['StartTime'] == None:
      starttime = (datetime.today().replace(microsecond=0, second=0, minute=0, hour=0) - timedelta(days=1))
      endtime = (datetime.today().replace(microsecond=0, second=0, minute=0, hour=0) + timedelta(days=PtoParam['cicoil']['sim_len']))
  else:
      starttime = datetime(int(PtoParam['sim']['StartTime'][0:4]), int(PtoParam['sim']['StartTime'][4:6]), int(PtoParam['sim']['StartTime'][6:8]),
                              PtoParam['sim']['Shour'], 0)
      endtime = datetime(int(PtoParam['sim']['EndTime'][0:4]), int(PtoParam['sim']['EndTime'][4:6]), int(PtoParam['sim']['EndTime'][6:8]),
                            PtoParam['sim']['Ehour'], 0)
      
  txtTime = starttime.strftime("%Y%m%d-%H")

  # Read or define wind_factor
  try:
      wind_factor
  except NameError:
      if PtoParam['cicoil']['wind_factor'] != None:
          wind_factor = float(PtoParam['cicoil']['wind_factor'])
      else: wind_factor = 0.035


  # Select Simulation location and results output file
  output_path = os.path.join(PtoParam['outdir'],PtoParam['point']['name'],txtTime[0:8])
  
  # TAMOC output dir
  txtTime = starttime.strftime("%Y%m%d-%H")  # str(starttime)[0:10]
  output_tamoc = os.path.join(PtoParam['outdir'],PtoParam['point']['name'],txtTime[0:8],'TAMOC_output_files/')
  
  # Create simulation name taken inputs values
  sim_name = ''.join([PtoParam['point']['name'], '_', PtoParam['oil']['name'], '_', PtoParam['input']['curr'][0], PtoParam['input']['wind'][0],
             '_', str(PtoParam['spill']['depth']), 'm'])

  sim_duration = timedelta(days=int(PtoParam['cicoil']['sim_len']))
  particles_number = float(PtoParam['cicoil']['N_parti'])
  step_time = float(PtoParam['cicoil']['step_time'])           # hours
  output_step_time = float(PtoParam['cicoil']['repo_time'])    # hours
  release_points = np.int(1)

  seed_duration = endtime - starttime
  leak_days = seed_duration.days
  leak_remainder = endtime - (starttime + timedelta(days=leak_days))
  seed_days_exact = seed_duration.total_seconds() / 86400.     # seconds per day
  particles_per_day = int(np.ceil(particles_number / seed_days_exact))
  remaining_particles = int(particles_per_day * divmod(seed_days_exact, leak_days)[1])
  if remaining_particles > 0: leak_days += 1

  lon = float(PtoParam['point']['lon'])
  lat = float(PtoParam['point']['lat'])
  oil_name = PtoParam['oil']['name']
  flow_rate = float(PtoParam['spill']['flow_rate'])       # kg/s
  verticle_angle = - np.pi / 180 * int(PtoParam['spill']['vertical_angle']) # convert degrees to radians
  horiz_angle = np.pi / 180 * int(PtoParam['spill']['horizont_angle'])      # convert degrees to radians
  GOR = float(PtoParam['spill']['GOR'])                   # scf/bbl
  release_depth = float(PtoParam['spill']['depth'])       # meters
  jet_diameter = float(PtoParam['spill']['jet_diam'])     # meters
  fluid_temp = 273.15 + float(PtoParam['spill']['temp'])  # convert Celsius to Kelvin
  bins = int(PtoParam['spill']['bins'])
  
  # Create and configure OpenCiceseOil
  weathering=PtoParam['model']['weathering']
  fartype=PtoParam['model']['fartype']

  o = OpenCiceseOil(loglevel=20, weathering_model=weathering)
  if fartype == '2D Sim.':
      o.disable_vertical_motion()
  else:
      o.set_config('processes:dispersion', False)

  o.set_config('drift:advection_scheme',PtoParam['model']['advection_scheme'])      # Added by "abgarcia"
  o._set_config_default('drift:current_uncertainty', 0.0)
  o._set_config_default('drift:wind_uncertainty', 0.0)

  # READERS
  if PtoParam['input']['curr'] == 'fnmoc':
      reader_current = reader_netCDF_CF_generic.Reader(filename=PtoParam['datadir'] + 'fnmoc-amseas/' + txtTime[0:8] + '/fnmoc-amseas-forecast-GoM-' + txtTime[0:8] + '-time*.nc', name='amseas_forecast')
  elif PtoParam['input']['curr'] == 'hycom':
      reader_current = reader_netCDF_CF_generic.Reader(filename=PtoParam['datadir'] + 'hycom/HYCOM-forecast-GoM-' + txtTime[0:8] + '.nc', name='hycom_forecast')
  if PtoParam['input']['wind'] == 'gfs':
      reader_winds = reader_netCDF_CF_generic.Reader(filename=PtoParam['datadir'] + 'gfs-winds/' + 'gfs-winds-forecast-GoM-' + txtTime[0:8] + '.nc', name='gfs_forecast')

  # o.add_reader([reader_basemap, reader_globcurrent, reader_oceanwind])
  o.add_reader([reader_current, reader_winds])
  o.set_oiltype(oil_name)

  # load TAMOC files
  tamoc_file= ''.join([output_tamoc, sim_name, '-tamoc_', txtTime])

  # Seed to Far-field and run
  spillets = particles_per_day
  for day in range(leak_days):
      tamoc_plume = Plume(plume_file=tamoc_file + '_plume.nc')
      tamoc_plume.get_particle_properties(particles_file=tamoc_file + '_particles.nc')
      
      stoptime = starttime + timedelta(days=day + 1)
      if day==leak_days - 1 and remaining_particles > 0:
          spillets = remaining_particles
          stoptime = starttime + timedelta(days=day) + leak_remainder
          
      o.seed_plume_elements(lon, lat, tamoc_plume, starttime+ timedelta(days=day), stoptime,
                               number=spillets, z_uncertainty=10, wind_drift_factor=wind_factor,
                               oiltype=oil_name)

  cicoil_path = os.path.join(output_path,'CICOIL_output_files/')
  try:
      os.makedirs(cicoil_path) 
  except OSError as error:
      print(error)

  output_file = ''.join([cicoil_path, sim_name, '_wf', str(wind_factor), '_', starttime.strftime("%Y%m%d-%H"),'_to_',endtime.strftime("%Y%m%d-%H"),  '.nc'])
  print(o)
  o.run(duration=sim_duration,
            time_step=timedelta(hours=step_time),
            time_step_output=timedelta(hours=output_step_time),
            outfile=output_file)
  print(o)
  
  # Post processing
  figs_path = os.path.join(output_path,'Figures/')
  try:
      os.makedirs(figs_path) 
  except OSError as error:
      print(error)

  postp_file=''.join((figs_path, sim_name, '_wf', str(wind_factor), '_',starttime.strftime("%Y%m%d-%H")))

  # Maps
  o.plot(filename=postp_file + '_trajectories_zoom.png')
  o.plot(filename=postp_file + '_trajectories.png', corners=PtoParam['point']['corners'])
  o.plot_oil_budget(filename=postp_file + '_budget-01.png')                                                          # Added by "abgarcia"
  o.plot_oil_budget(show_density_viscosity=True, show_wind_and_current=True, filename=postp_file + '_budget-02.png') # Added by "abgarcia"
  
  # Animations
  # currents
  o.animation(background=['x_sea_water_velocity', 'y_sea_water_velocity'],
              colorbar=True, fps=10, filename=postp_file + '_curr_zoom.gif',vmin=0, vmax=2.0)
  o.animation(background=['x_sea_water_velocity', 'y_sea_water_velocity'],
              colorbar=True, fps=10, filename=postp_file + '_curr.gif', corners=PtoParam['point']['corners'], vmin=0, vmax=2.0)
  # # winds
  # o.animation(background=['x_wind', 'y_wind'], cmap='turbo', skip=1, scale=50,
  #             colorbar=True, fps=10, filename=postp_file + '_wind_zoom.gif',vmin=0, vmax=10.0)
  o.animation(background=['x_wind', 'y_wind'], colorbar=True, fps=10, filename=postp_file + '_wind.gif',
              corners=[-98, -88, 17, 31], cmap='turbo', vmin=0, vmax=10.0, skip=1, scale=100)

  o.animation(color='viscosity', fsp=10, filename=postp_file + '_viscosity.gif') # Added by "abgarcia"
  o.animate_vertical_distribution(filename=postp_file + '_vertical.gif')
  o.animation_profile(fps=10, filename=postp_file + '_profile.gif')
