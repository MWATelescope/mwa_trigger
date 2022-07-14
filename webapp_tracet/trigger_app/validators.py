from django.core.exceptions import ValidationError
from django import forms
from django.utils.translation import gettext

import os
import logging
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time

from tracet.triggerservice import trigger_mwa
import atca_rapid_response_api as arrApi

logger = logging.getLogger(__name__)

def mwa_freqspecs(input_spec, numchannels=24, separator=";"):
    """
    Validate the frequency specification given on the command line
    that can take the form of::

      <channel>
      <center>,<width>,<increment>
      <start>:<stop>:<increment>

    where the increments default to 1.  Multiple entries can be given separated by <separator>,
    which defaults to ;
    if using ;, entries should be enclosed in quotes

    :param input_spec: input string
    :param numchannels: number of frequency channels (int)
    :param separator: separator between the frequency channels (string)
    :return: list of frequency channels (ints)

    """
    freqs = []
    atoms = input_spec.split(separator)
    for atom in atoms:
        if not (":" in atom or "," in atom or "-" in atom):
            # just a number
            try:
                freqs.append(int(atom))
            except ValueError:
                raise ValidationError(
                    f"Unable to parse frequency channel: {atom}",
                    params={'input_spec': input_spec},
                )
        elif (":" in atom):
            sub_seperator = ":"
        elif ("-" in atom):
            sub_seperator = "-"
        elif ("," in atom):
            sub_seperator = ","

        # assumes <channelstart>:<channelstop>:<increment>
        increment = 1
        res = atom.split(sub_seperator)
        if (len(res) > 2):
            try:
                increment = int(res[2])
            except ValueError:
                raise ValidationError(
                    f"Unable to parse frequency increment: {res[2]}",
                    params={'input_spec': input_spec},
                )
        try:
            freqstart_center = int(res[0])
        except ValueError:
            raise ValidationError(
                f"Unable to parse frequency start: {res[0]}",
                params={'input_spec': input_spec},
            )
        try:
            freqstop_width = int(res[1])
        except ValueError:
            raise ValidationError(
                f"Unable to parse frequency stop: {res[1]}",
                params={'input_spec': input_spec},
            )
        if ":" in atom or "-" in atom:
            freqstart = freqstart_center
            freqstop = freqstop_width
            for freq in range(freqstart, freqstop + 1, increment):
                freqs.append(freq)
        else:
            freqcenter = freqstart_center
            freqwidth = freqstop_width
            for freq in range(freqcenter - int(freqwidth / 2.0), freqcenter + int(freqwidth / 2.0 + 0.5), increment):
                freqs.append(freq)

    # remove duplicates
    origfreqs = freqs
    freqs = list(set(freqs))
    if (len(freqs) < len(origfreqs)):
        raise ValidationError(
            f"Removed duplicate items from frequency list",
            params={'input_spec': input_spec},
        )
    # sort
    freqs.sort()
    # trim if necessary
    if len(freqs) > numchannels:
        raise ValidationError(
            f"Too many frequency channels supplied (>{numchannels}).",
            params={'input_spec': input_spec},
        )

    if (len(freqs) == 1):
        # only a single frequency
        logger.warning('--freq=%d requested, but interpreting it as --freq=%d,24' % (freqs[0], freqs[0]))
        freqcenter = freqs[0]
        freqwidth = 24
        increment = 1
        freqs = list(range(freqcenter - int(freqwidth / 2.0), freqcenter + int(freqwidth / 2.0 + 0.5), increment))

    if len(freqs) < numchannels:  # Pad to numchannels
        if freqs[-1] <= 255 - (24 - len(freqs)):
            freqs += list(range(freqs[-1] + 1, freqs[-1] + (24 - len(freqs)) + 1))
        elif freqs[0] > (24 - len(freqs)):
            freqs = list(range(freqs[0] - (24 - len(freqs)), freqs[0], 1)) + freqs
        else:
            freqs += [x for x in range(60, 200) if x not in freqs][:(24 - len(freqs))]
            freqs.sort()

    if (min(freqs) < 0) or (max(freqs) > 255):
        raise ValidationError(
            "Centre channel too close to 0 or 255, some channels would be < 0 or > 255",
            params={'input_spec': input_spec},
        )

    return freqs


def atca_freq_bands(min_freq, max_freq, freq, field_name):
    """Check the users picked frequencies within the bandwidth of the reciever

    Parameters
    ----------
    min_freq : `float`
        Minimum frequency of the reciever in MHz.
    max_freq : `float`
        Maximum frequency of the reciever in MHz.
    freq : `float`
        The frequency to check in MHz.
    field_name : `str`
        The name of the model field you are testing.
    """
    if freq > max_freq:
        raise forms.ValidationError(gettext(f"{field_name} error: A centre frequency of {freq} MHz would have a maximum above {max_freq} MHz which is outside the bands frequency range."))
    if freq < min_freq:
        raise forms.ValidationError(gettext(f"{field_name} error: A centre frequency of {freq} MHz would have a minimum below {min_freq} MHz which is outside the bands frequency range."))


def mwa_proposal_id(project_id, secure_key):
    """Check that the MWA project ID and secure key are valid.

    Parameters
    ----------
    project_id : `str`
        The project ID, e.g. T001.
    secure_key : `str`
        The secure key (password) for this project.
    """
    result = trigger_mwa(
        project_id=project_id,
        secure_key=secure_key,
        pretend=True,
        ra=0.,
        dec=0.,
        creator='VOEvent_Auto_Trigger',
        obsname='proposal_test',
        nobs=1,
        freqspecs="121,24", #Assume always using 24 contiguous coarse frequency channels
        avoidsun=True,
        inttime=0.5,
        freqres=10.0,
        exptime=900,
        calibrator=True,
        calexptime=120,
        vcsmode=True,
    )
    logger.debug(f"result: {result}")
    # Check if succesful
    if result is None:
        raise forms.ValidationError({"Web API error, possible server error"})
    if not result['success']:
        # Observation not succesful so record why
        error_message = ""
        for err_id in result['errors']:
            error_message += f"{result['errors'][err_id]}.\n "
        # Return an error as the trigger status
        raise forms.ValidationError({error_message})

def atca_proposal_id(project_id, secure_key, atca_email):
    """Check that the ATCA project ID and secure key are valid.

    Parameters
    ----------
    project_id : `str`
        The project ID, e.g. T001.
    secure_key : `str`
        The secure key (password) for this project.
    atca_email : `str`
        The email address of someone that was on the ATCA observing proposal. This is an authentication step.
    """
    # Setup current RA and Dec at zenith for ATCA
    atca = EarthLocation(lat='-30:18:46', lon='149:33:01', height=377.8 * u.m)
    atca_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=atca)
    ra = atca_coord.icrs.ra.to_string(unit=u.hour, sep=':')[:11]
    rq = {
        "source": "Test",
        "rightAscension": ra,
        "declination": "-30:18:46",
        "project": project_id,
        "maxExposureLength": "00:01:00",
        "minExposureLength": "00:00:01",
        "scanType": "Dwell",
        "4cm": {
            "use": True,
            "exposureLength": "00:00:20",
            "freq1": 5500,
            "freq2": 9000,
        },
    }

    # We have our request now, so we need to craft the service request to submit it to
    # the rapid response service.
    rapidObj = { 'requestDict': rq }
    rapidObj["authenticationToken"] = secure_key
    rapidObj["email"] = atca_email
    rapidObj["test"] = True
    rapidObj["noTimeLimit"] = True
    rapidObj["noScoreLimit"] = True

    request = arrApi.api(rapidObj)
    try:
        result = request.send()
    except arrApi.responseError as r:
        logger.error(f"ATCA return message: {r}")
        raise forms.ValidationError({r})

    # Check if succesful
    if result is None:
        raise forms.ValidationError({"Web API error, possible server error"})