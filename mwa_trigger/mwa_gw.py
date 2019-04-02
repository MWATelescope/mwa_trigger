import email
import sys
import os


import numpy,sys,glob,math
import healpy
from astropy.io import fits
from astropy.time import Time
from astropy.table import Table,Column
import scipy.interpolate

try:
    from matplotlib import _cntr as cntr
    import matplotlib.pyplot as plt
    _plotting=True
except ImportError:
    _plotting=False

import mwatools as mwapy
from mwapy import ephem_utils
from mwa_pb import primary_beam

"""
Tools to parse LIGO/Virgo GCN notices
to download the skymaps containing trigger probabilities
and to figure out how/where to point the MWA
"""


import logging
logging.basicConfig()
DEFLOGGER = logging.getLogger('mwa_gw_default')

################################################################################
class MWA_grid_points():
    file=os.path.join(os.path.split(mwapy.__file__)[0],
                      'data','grid_points.fits')
    
    def __init__(self, obstime, logger=DEFLOGGER):
        try:
            self.logger = logger
            self.obstime=obstime
            self.data=Table.read(MWA_grid_points.file)
            gridRA,gridDec=self.get_radec()
            self.data.add_column(Column(gridRA,name='RA'))
            self.data.add_column(Column(gridDec,name='Dec'))
        except:
            self.logger.critical('Cannot open MWA grid points file %s' % MWA_grid_points.file)
            self.data=None

    ##################################################
    def get_radec(self):
        """
        gridRA,gridDec=MWA_grid_points.get_radec()
        RA,Dec of grid at a particular obstime
        """
        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]

        gridHA,gridDec=ephem_utils.horz2eq(self.data['azimuth'],
                                           self.data['elevation'],
                                           mwa.lat)
        gridRA=float(self.obstime.LST)-gridHA
        return gridRA,gridDec


    ##################################################
    def find_closest_grid_pointing(self, RA, Dec):
        """
        Returns the grid pointing that is closest to the requested position (Ra,Dec) in degrees
        along with the distance to that point in degrees
        
        also requires a MWA_Time object
        
        """

        if RA is None:
            return None,None

        if self.data is None:
            self.logger.critical('Unable to find MWA grid points')
            return None,None        

        HA=-RA+float(self.obstime.LST)
        
        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
        az,el=ephem_utils.eq2horz(HA,Dec,mwa.lat)
        
        closest=None
        # in degrees
        closest_distance=180
        for g in self.data:
            x1 = math.cos(az/ephem_utils.DEG_IN_RADIAN)*math.cos(el/ephem_utils.DEG_IN_RADIAN)
            y1 = math.sin(az/ephem_utils.DEG_IN_RADIAN)*math.cos(el/ephem_utils.DEG_IN_RADIAN)
            z1 = math.sin(el/ephem_utils.DEG_IN_RADIAN)
            x2 = math.cos(g['azimuth']/ephem_utils.DEG_IN_RADIAN)*math.cos(g['elevation']/ephem_utils.DEG_IN_RADIAN)
            y2 = math.sin(g['azimuth']/ephem_utils.DEG_IN_RADIAN)*math.cos(g['elevation']/ephem_utils.DEG_IN_RADIAN)
            z2 = math.sin(g['elevation']/ephem_utils.DEG_IN_RADIAN)
            arg=x1*x2+y1*y2+z1*z2
            if (arg>1):
                arg=1
            if (arg<-1):
                arg=-1
            theta = math.acos(arg)*ephem_utils.DEG_IN_RADIAN
            if (theta < closest_distance):
                closest_distance=theta
                closest=g

        return closest,closest_distance

    

################################################################################
class MWA_GW_fast():
    """
    improvements over base class:
    stay in nested format
    do not do any calculations in full resolution
    """

    def __init__(self, gwfile, nside=64, logger=DEFLOGGER):

        self.logger = logger
        self.gwfile=gwfile
        try:
            self.gwmap,gwheader=healpy.read_map(self.gwfile,
                                                    h=True,nest=True,verbose=False)
            self.logger.debug('Read in GW map %s' % self.gwfile)
        except:
            self.logger.error('Unable to read GW sky probability map %s' % self.gwfile)
        self.header={}
        for i in xrange(len(gwheader)):
            self.header[gwheader[i][0]]=gwheader[i][1]

        # compute the pointings for now
        # i.e., as soon as possible after the alert
        self.obstime=ephem_utils.MWATime(Time.now().datetime)
        self.logger.debug('Current time is %s (LST=%s)' % (
            self.obstime.strftime('%Y-%m-%dT%H:%M:%S UTC'),
            self.obstime.LST.strftime('%H:%M:%S')))

        self.nside=self.header['NSIDE']
        self.npix=healpy.nside2npix(self.nside)
        self.logger.debug('Original NSIDE=%d, NPIX=%d' % (self.nside,
                                                         self.npix))

        try:
            self.ID=self.header['OBJECT'].split(':')[-1]
        except KeyError:
            self.ID=self.gwfile
        self.logger.debug('Event ID %s' % self.ID)
        self.MWA_grid=MWA_grid_points(self.obstime, logger=self.logger)
        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
        
        self.nside_down=nside
        self.npix_down=healpy.nside2npix(self.nside_down)
        self.gwmap_down=healpy.ud_grade(self.gwmap, self.nside_down, power=-2,
                                        order_in='NESTED',
                                        order_out='NESTED')
        self.logger.debug('Downsampled to NSIDE=%d' % self.nside_down)
        # theta is co-latitude
        # phi is longitude
        # both in radians
        theta,phi=healpy.pix2ang(self.nside_down, numpy.arange(self.npix_down),
                                 nest=True)

        # now in degrees
        self.Dec_down=90-numpy.degrees(theta)
        self.RA_down=numpy.degrees(phi)

        self.HA_down=-self.RA_down+float(self.obstime.LST)
        
        self.Az_down,self.Alt_down=ephem_utils.eq2horz(self.HA_down,
                                                       self.Dec_down,mwa.lat)

    ##################################################
    def recompute(self):
        """
        MWA_GW_fast.recompute()
        redoes the time/Alt/Az computation
        """

        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
                
        # theta is co-latitude
        # phi is longitude
        # both in radians
        theta,phi=healpy.pix2ang(self.nside_down, numpy.arange(self.npix_down),
                                 nest=True)

        # now in degrees
        self.Dec_down=90-numpy.degrees(theta)
        self.RA_down=numpy.degrees(phi)

        self.HA_down=-self.RA_down+float(self.obstime.LST)
        
        self.Az_down,self.Alt_down=ephem_utils.eq2horz(self.HA_down,
                                                       self.Dec_down,mwa.lat)


    ##################################################
    def interp(self, RA, Dec):
        return healpy.get_interp_val(self.gwmap_down,
                                     numpy.radians(90-Dec),
                                     numpy.radians(RA),
                                     nest=True)

    ##################################################
    def get_mwapointing(self, frequency=150e6, minprob=0.01, ZAweight=False):
        """
        RA,Dec=MWA_GW.get_mwapointing(frequency=150e6, minprob=0.01, ZAweight=False)
        return RA,Dec in degrees of brightest GW pixel
        constrained to be above horizon.
        Will additionally weight by cos(ZA) if desired
        """

        # figure out what fraction is above horizon
        if (self.gwmap_down*(self.Alt_down>0)).sum() < minprob:
            self.logger.info('Insufficient power above horizon\n')
            return None,None
    
        # first go from altitude to zenith angle
        theta_horz=numpy.radians((90-self.Alt_down))
        phi_horz=numpy.radians(self.Az_down)

        # make sure we don't try to point below the horizon
        pointingmap=self.gwmap_down*(self.Alt_down>0)

        if ZAweight:
            # weight the map by cos(ZA) if desired
            # will account for projection of MWA tile beam
            pointingmap*=numpy.cos(theta_horz)

        return self.RA_down[pointingmap==pointingmap.max()][0],self.Dec_down[pointingmap==pointingmap.max()][0]
    

    ##################################################
    def get_mwabeam(self, delays, frequency=150e6):
        """
        beam=MWA_GW.get_mwa_gwmap(delays, frequency=150e6)
        """
    
        # first go from altitude to zenith angle
        theta_horz=numpy.radians((90-self.Alt_down))
        phi_horz=numpy.radians(self.Az_down)

        beamX,beamY=primary_beam.MWA_Tile_analytic(theta_horz, phi_horz,
                                                   freq=frequency,
                                                   delays=delays,
                                                   zenithnorm=True,
                                                   power=True)
        return ((beamX+beamY)*0.5)


    ##################################################
    def get_mwa_gwpower(self, delays, frequency=150e6):
        """
        power=MWA_GW.get_mwapower(delays, frequency=150e6)
        """
    
        beam=self.get_mwabeam(delays, frequency=frequency)
        return (beam*self.gwmap_down).sum()

    ##################################################
    def interp_mwa(self, delays, RA, Dec, frequency=150e6):
        """
        beam=MWA_GW.interp_mwa(delays, RA, Dec, frequency=150e6)
        """
        beam=self.get_mwabeam(delays, frequency=frequency)
        return healpy.get_interp_val(beam,
                                     numpy.radians(90-Dec),
                                     numpy.radians(RA),
                                     nest=True)



    ##################################################
    def get_mwapointing_grid(self, frequency=150e6, minprob=0.01, minelevation=45,
                             returndelays=False, returnpower=False):
        """
        RA,Dec=MWA_GW.get_mwapointing_grid(frequency=150e6, minprob=0.01, minelevation=45
        returndelays=False, returnpower=False)
        if returndelays=True, returns:
        RA,Dec,delays
        
        if returnpower=True, returns:
        RA,Dec,delays,power
        """

        
        if self.MWA_grid.data is None:
            self.logger.critical('Unable to find MWA grid points')
            if not (returndelays or returnpower):                
                return None,None
            else:
                if returnpower:
                    return None,None,None,None
                else:
                    return None,None,None

        # has it been downsampled already
        npix=self.npix_down
        nside=self.nside_down
        gwmap=self.gwmap_down
        RA=self.RA_down
        Dec=self.Dec_down
        HA=self.HA_down
        Alt=self.Alt_down
        Az=self.Az_down

        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]

        gridHA,gridDec=ephem_utils.horz2eq(self.MWA_grid.data['azimuth'],
                                           self.MWA_grid.data['elevation'],
                                           mwa.lat)
        self.logger.debug('Computing pointing for %s (LST=%s)' % (
            self.obstime.strftime('%Y-%m-%dT%H:%M:%S UTC'),
            self.obstime.LST.strftime('%H:%M:%S')))
        gridRA=float(self.obstime.LST)-gridHA

        # figure out what fraction is above horizon
        if (gwmap*(Alt>0)).sum() < minprob:
            self.logger.info('Insufficient power above horizon\n')
            if not (returndelays or returnpower):                
                return None,None
            else:
                if returnpower:
                    return None,None,None,None
                else:
                    return None,None,None
        # first go from altitude to zenith angle
        theta_horz=numpy.radians((90-Alt))
        phi_horz=numpy.radians(Az)
        mapsum=numpy.zeros((len(self.MWA_grid.data)))
        for igrid in xrange(len(self.MWA_grid.data)):
            beamX,beamY=primary_beam.MWA_Tile_analytic(theta_horz, phi_horz,
                                                       freq=frequency,
                                                       delays=self.MWA_grid.data[igrid]['delays'],
                                                       zenithnorm=True,
                                                       power=True)
            
            mapsum[igrid]=((beamX+beamY)*0.5*gwmap).sum()
        # this is the best grid point
        # such that it is over our minimum elevation
        igrid=numpy.where(mapsum==mapsum[self.MWA_grid.data['elevation']>minelevation].max())[0][0]
        if not (self.MWA_grid.data['elevation'][igrid]>minelevation):
            self.logger.info('Elevation %.1f deg too low\n' % self.MWA_grid.data['elevation'][igrid])
            # too close to horizon
            if not (returndelays or returnpower):
                return None,None
            else:
                if returnpower:
                    return None,None,None,None
                else:
                    return None,None,None
        self.logger.info('Best pointing at RA,Dec=%.1f,%.1f; Az,El=%.1f,%.1f: power=%.3f' %
                         (gridRA[igrid],gridDec[igrid],
                         self.MWA_grid.data['azimuth'][igrid],
                         self.MWA_grid.data['elevation'][igrid],
                         mapsum[igrid]))
        
        if mapsum[igrid]<minprob:
            self.logger.info('Pointing at Az,El=%.1f,%.1f has power=%.3f < min power\n' % 
                  (self.MWA_grid.data['azimuth'][igrid],
                  self.MWA_grid.data['elevation'][igrid],
                  mapsum[igrid]))
                  
            if not (returndelays or returnpower):
                return None,None
            else:
                if returnpower:
                    return None,None,None,None
                else:
                    return None,None,None
                             

        if not (returndelays or returnpower):
            return gridRA[igrid],gridDec[igrid]
        else:
            if not returnpower:
                return gridRA[igrid],gridDec[igrid],self.MWA_grid.data[igrid]['delays']
            else:
                return gridRA[igrid],gridDec[igrid],self.MWA_grid.data[igrid]['delays'],mapsum[igrid]                

    ##################################################
    def get_skytemp(self,RA,Dec,frequency=150e6):
        # convert the LST in hours to an integer for 1/100h
        LST_index=int((float(self.obstime.LST)/15)*100+0.5)
        # and round to the nearest 0.2h
        LST_index=int(round(LST_index/20.0)*20)

        grid,dist=self.MWA_grid.find_closest_grid_pointing(RA,Dec)

        skytemptable=Table.read('skytemp.fits')

        t=skytemptable[(skytemptable['gridnum']==grid['number']) & (skytemptable['LST']==LST_index)]
        return ((t['T1'].data[0]+t['T2'].data[0])/2)*(frequency/150e6)**-2.6
