import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cm
import pandas as pd
import re
import io
import os
import astropy.constants as cst
import astropy.units as units
import scipy.interpolate as interp

from collections import deque


def read_model_BHAC2015(path):
    '''
    Read the BHAC2015 models

    Parameters
    ----------
    path : str
        Full path to the file containing the models

    Returns
    -------
    data : array_like
        Pandas array with all the data. Age in Myr, mass in Mjup, Teff in K, logL in Lsun, radius in Rjup.
    '''
    
    # read general data
    data = pd.read_csv(path, sep='\s+', header=None, comment='!')

    # add ages
    data.insert(0, 'age', 0)

    # read column headers and age values
    p_cols = re.compile('!\s+(mass)\s+(Teff)')
    p_ages = re.compile('!\s+t\s+\(Gyr\)\s+=\s+([0-9]+\.[0-9]+)')
    p_vals = re.compile('\s+([0-9]+\.[0-9]+)\s+([0-9]+\.[0-9]+)')

    cols = ['age']
    ages = []
    cage = 0

    file = open(path, 'r')
    for line in file:
        # skip non-comment lines
        if (line[0] != '!'):
            m = p_vals.match(line)
            if (m is not None):
                ages.append(cage)
            continue

        # column names
        if (len(cols) == 1):
            m = p_cols.match(line)
            if (m is not None):
                cols.extend(line[1:].split())

        # age value
        m = p_ages.match(line)
        if (m is not None):
            cage = float(m.group(1))

    file.close()

    # rename columns and add age values
    data.columns = cols    
    data.age = ages

    # unit conversion
    data.age    *= 1000
    data.mass   *= cst.M_sun / cst.M_jup
    data.radius *= cst.R_sun / cst.R_jup
    
    return data


def read_model_PHOENIX_websim(path):
    '''
    Read models from the PHOENIX web simulator

    Parameters
    ----------
    Path : str
        Full path to the file containing the models

    Returns
    -------
    data : array_like
        Pandas array with all the data. Ages in Myr, mass in Mjup, Teff in K, logL in Lsun, radius in Rjup.
    '''

    # read column headers and number of values
    p_cols = re.compile('\s+M/Ms\s*Teff.K.\s+L/Ls\s+lg\(g\)\s+R.(\w+).\s+D\s+Li\s+([A-Za-z0-9\\s_.\']+)')
    p_ages = re.compile('\s+t\s+\(Gyr\)\s+=\s+([0-9]+\.[0-9]+)')
    p_vals = re.compile('(\s+[+-]*[0-9]+\.[0-9]*){3}')

    cols  = ['age', 'mass', 'Teff', 'logL', 'logg', 'radius', 'D', 'Li']
    cage  = 0
    ages  = []
    unit  = None
    lines = []
    
    # get column names
    file = open(path, 'r')
    for line in file:
        # age value
        m = p_ages.match(line)
        if (m is not None):            
            cage = float(m.group(1))
            continue
        
        # column names
        if (len(cols) == 8):
            m = p_cols.match(line)
            if (m is not None):
                unit = m.group(1)

                names = m.group(2)
                names = names.replace("'", "p")
                
                cols.extend(names.split())
                
                continue
            
        # model values
        m = p_vals.match(line)
        if (m is not None):
            lines.append(line)
            ages.append(cage)
            
    file.close()
                
    # create data frame
    lines = ''.join(lines)
    data = pd.read_csv(io.StringIO(lines), sep='\s+', header=None)

    # add ages
    data.insert(0, 'age', 0)
    data.age = ages

    # rename columns
    data.columns = cols    
    
    # unit conversion
    data.age  *= 1000
    data.mass *= cst.M_sun / cst.M_jup
    if unit == 'Gm':
        # data.radius /= cst.R_jup.to(units.Gm)
        pass
    elif unit == 'Gcm':
        #data.radius /= cst.R_jup.to(units.Gm*100)
        pass
    else:
        pass
        
    return data



#######################################
# models definitions
#
models = {
    'path': os.path.expanduser('/Users/avigan/Work/Models/Evolution/'),
    'properties': [
        {'instrument': 'nicmos', 'name': 'dusty2000', 'file': 'model.AMES-dusty-2000.M-0.0.HST', 'function': read_model_PHOENIX_websim},
        {'instrument': 'naco',   'name': 'dusty2000', 'file': 'model.AMES-dusty-2000.M-0.0.NaCo', 'function': read_model_PHOENIX_websim},
        {'instrument': 'irdis',  'name': 'dusty2000', 'file': 'model.AMES-dusty-2000.M-0.0.SPHERE.Vega', 'function': read_model_PHOENIX_websim},
    
        {'instrument': 'nicmos', 'name': 'cond2003',  'file': 'model.AMES-Cond-2003.M-0.0.HST', 'function': read_model_PHOENIX_websim},
        {'instrument': 'naco',   'name': 'cond2003',  'file': 'model.AMES-Cond-2003.M-0.0.NaCo', 'function': read_model_PHOENIX_websim},
        {'instrument': 'irdis',  'name': 'cond2003',  'file': 'model.AMES-Cond-2003.M-0.0.SPHERE.Vega', 'function': read_model_PHOENIX_websim},
    
        {'instrument': 'irdis',  'name': 'bhac2015+dusty2000', 'file': 'BHAC15_DUSTY00_iso_t10_10.SPHERE', 'function': read_model_BHAC2015},
        {'instrument': 'irdis',  'name': 'bhac2015+cond2003',  'file': 'BHAC15_COND03_iso_t10_10.SPHERE', 'function': read_model_BHAC2015},
    ],
    'data': {}
}



def reshape_data(dataframe):
    '''
    Reshape the data frame in a regular grid that can be used as input in scipy functions.

    Parameters
    ----------
    dataframe : pandas DataFrame
        Data frame with all the data

    Returns
    -------
    data : array
        Numpy data array

    ages : vector
        Numpy vector with unique ages

    masses : vector
        Numpy vector with unique masses

    values : array
        Array with names of parameters
    '''

    # unique ages and masses
    masses = dataframe.mass.unique()
    ages = dataframe.age.unique()

    # values
    values = dataframe.columns.values[2:]

    # fill array
    data = np.full((masses.size, ages.size, values.size), np.nan)
    for m, mass in enumerate(masses):
        for a, age in enumerate(ages):
            mask = (dataframe.mass == mass) & (dataframe.age == age)
            
            if mask.any():
                data[m, a, :] = dataframe.loc[mask, 'Teff':].values.squeeze()

    return masses, ages, values, data


def monotonic_sublists(lst):
    '''
    Extract monotonic sublists from a list of values
    
    Given a list of values that is not sorted (such that for some valid
    indices i,j, i<j, sometimes lst[i] > lst[j]), produce a new
    list-of-lists, such that in the new list, each sublist *is*
    sorted: for all sublist \elem returnval: assert_is_sorted(sublist)
    and furthermore this is the minimal set of sublists required to
    achieve the condition.

    Thus, if the input list lst is actually sorted, this returns
    [list(lst)].

    Parameters
    ----------
    lst : list or array
        List of values

    Returns
    -------
    ret_i : list
        List of indices of monotonic sublists
    
    ret_v : list
        List of values of monotonic sublists
    '''

    # Make a copy of lst before modifying it; use a deque so that
    # we can pull entries off it cheaply.
    idx = deque(range(len(lst)))
    deq = deque(lst)
    ret_i = []
    ret_v = []
    while deq:
        sub_i = [idx.popleft()]
        sub_v = [deq.popleft()]

        if len(deq) > 1:
            if deq[0] <= sub_v[-1]:
                while deq and deq[0] <= sub_v[-1]:
                    sub_i.append(idx.popleft())
                    sub_v.append(deq.popleft())
            else:
                while deq and deq[0] >= sub_v[-1]:
                    sub_i.append(idx.popleft())
                    sub_v.append(deq.popleft())
                    
        ret_i.append(sub_i)
        ret_v.append(sub_v)
        
    return ret_i, ret_v


def interpolate_model(masses, ages, values, data, age, filt, param, Mabs, fill):
    '''
    Interpolate model grid

    Parameters
    ----------
    masses : array
        Mass values in the model grid

    ages : array
        Age values in the model grid
    
    values : array
        Name of filters (and other parameters) in the model grid

    data : array
        Data of the model grid

    age : float
        Age at which interpolation is needed

    filt : str
        Filter in which the magnitude is provided

    param : str
        Parameter to be interpolated

    Mabs : array
        Absolute magnitude

    fill : bool
        Fill interpolated values with min/max values in the models when
        trying to interpolate outside the values in the models
    
    Returns
    -------
    values : array
        Interpolated values
    '''

    # age indices
    ii = np.abs(ages-age).argmin()
    if age <= ages[ii]:
        imin = ii-1
        imax = ii
    elif age > ages[ii]:
        imin = ii
        imax = ii+1

    agemin = ages[imin]
    agemax = ages[imax]
        
    # parameter value
    if param == 'Mass':
        ifilt = np.where(values == filt)[0]

        Zmin = data[:, imin, ifilt].squeeze()
        Zmax = data[:, imax, ifilt].squeeze()

        Znew = (Zmin - Zmax) / (agemin - agemax) * (age - agemin) + Zmin

        # remove missing values
        masses = masses[np.isfinite(Znew)]
        Znew   = Znew[np.isfinite(Znew)]
        
        # find monotonic parts of the signal
        mono_i, mono_v = monotonic_sublists(Znew)
        
        nsub = len(mono_i)
        sub_idx = np.zeros((2*nsub-1, 2), dtype=np.int)
        for s in range(nsub):
            sub_idx[s, 0] = mono_i[s][0]
            sub_idx[s, 1] = mono_i[s][-1]
        for s in range(nsub-1):
            sub_idx[s+nsub, 0] = mono_i[s][-1]
            sub_idx[s+nsub, 1] = mono_i[s+1][0]

        sub_idx = np.sort(sub_idx, axis=0)

        # interpolate over each part
        values = np.zeros((2*nsub-1, Mabs.size))
        for i, s in enumerate(sub_idx):
            sub_Znew   = Znew[s[0]:s[1]+1]
            sub_masses = masses[s[0]:s[1]+1]

            if len(sub_Znew) < 2:
                continue
            
            interp_func = interp.interp1d(sub_Znew, sub_masses, bounds_error=False, fill_value=np.nan)
            values[i] = interp_func(Mabs)

            # fill if outside of available values
            if fill:
                if Mabs < sub_Znew.min():
                    values[i] = masses.max()
                elif Mabs > sub_Znew.max():
                    values[i] = masses.min()
        
        # combine
        values = np.nanmax(values, axis=0)
    else:
        raise ValueError('Interpolation for parameter {0} is not implemented yet.'.format(param))

    return values


def mag_to_mass(age, distance, mag, Dmag, filt,
                instrument='IRDIS', model='bhac2015+cond2003', fill=False,
                age_range=None, distance_range=None, mag_err=None, Dmag_range=None):
    '''
    Convert a contrast value into mass

    Parameters
    ----------
    age : float
        Age of the target in Myr

    distance : float
        Distance of the target in pc

    mag : float
        Magnitude of the target in the filter

    Dmag : array
        Contrast value(s) in the filter

    filt : str
        Name of the filter

    instrument : str
        Name of the instrument. The default is IRDIS

    model : str
        Name of the evolutionary model. The default is bhac2015+cond2003

    fill : bool
        Fill interpolated values with min/max values in the models when
        trying to interpolate outside the values in the models
    
    age_range : list
        [min, max] age estimations for the target

    distance_range : list
        [min, max] distance estimations for the target

    mag_err : float
        Error on the target magnitude

    Dmag_range : array
        [min, max] contrast estimations

    Returns
    -------
    mass, mass_min, mass_max : array
        Values of the mass interpolated into the model
    '''    
    
    # -------------------------------
    # get model data
    # -------------------------------
    # df = read_model_data(instrument, model)
    # masses, ages, values, data = reshape_data(df)
    masses, ages, values, data = model_data(instrument, model)

    # check ages
    if (age < ages.min()) or (age > ages.max()):
        raise ValueError('Age {0} Myr outside of model range [{1}, {2}]'.format(age, ages.min(), ages.max()))

    # check filter
    if filt not in values:
        raise ValueError('Filter {0} not available in list: {1}'.format(filt, values))
    
    # -------------------------------
    # explicit variable names
    # -------------------------------
    
    # age range
    if age_range is not None:
        if not isinstance(age_range, list):
            raise ValueError('Age range must be a 2-elements array')

        age_min = np.min(age_range)
        age_max = np.max(age_range)
    else:
        age_min = age
        age_max = age
                
    # dist range
    if distance_range is not None:
        if not isinstance(distance_range, list):
            raise ValueError('Dist range must be a 2-elements array')

        dist_min = np.min(distance_range)
        dist_max = np.max(distance_range)
    else:
        dist_min = distance
        dist_max = distance

    # Stellar mag range
    if mag_err is not None:
        if not isinstance(mag_err, (int, float)):
            raise ValueError('Stellar mag error must be a float')

        mag_min = mag - mag_err
        mag_max = mag + mag_err
    else:
        mag_min = mag
        mag_max = mag

    # delta mag range
    if Dmag_range is not None:
        raise ValueError('Dmag error not implemented')
    else:
        Dmag_faint  = Dmag
        Dmag_bright = Dmag

    # -------------------------------
    # absolute magnitude conversion
    # -------------------------------

    # nominal values
    Mabs_nom = mag - 5*np.log10(distance) + 5 + Dmag

    # taking errors into account
    Mabs_faint  = mag_min - 5*np.log10(dist_min) + 5 + Dmag_faint
    Mabs_bright = mag_max - 5*np.log10(dist_max) + 5 + Dmag_bright

    # -------------------------------
    # interpolate models
    # -------------------------------
    param = 'Mass'   # only parameter currently available
    values_nom = interpolate_model(masses, ages, values, data, age, filt, param, Mabs_nom, fill)
    values_min = interpolate_model(masses, ages, values, data, age_min, filt, param, Mabs_faint, fill)
    values_max = interpolate_model(masses, ages, values, data, age_max, filt, param, Mabs_bright, fill)
    
    values_all = np.vstack((values_min, values_nom, values_max))
    values_min = np.nanmin(values_all, axis=0)
    values_max = np.nanmax(values_all, axis=0)
        
    return values_nom, values_min, values_max


def list_models():
    '''
    Print the list of available models
    '''
    print()
    print('Models path: {0}'.format(models['path']))
    print()

    for i in range(len(models['properties'])):
        prop = models['properties'][i]
        
        print(prop['file'])
        print(' * name:       {0}'.format(prop['name']))
        print(' * instrument: {0}'.format(prop['instrument']))
        print(' * function:   {0}'.format(prop['function'].__name__))
        print()


def model_data(instrument, model):
    '''
    Return the model data for a given instrument

    Directly returns the data if it has been read and stored
    already. Otherwise read and store it before returning.
    
    Parameters
    ----------
    instrument : str
        Instrument name

    model : str
        Model name

    Returns
    -------
    data : tuple 
        Tuple (masses, ages, values, data)
    '''
    key = instrument.lower()+'_'+model.lower()

    if key not in models['data'].keys():
        print('Loading model {0} for {1}'.format(model, instrument))
        
        df = read_model_data(instrument, model)
        masses, ages, values, data = reshape_data(df)

        models['data'][key] = (masses, ages, values, data)

    return models['data'][key]

        
def read_model_data(instrument, model):
    '''
    Return the data from a model and instrument

    Parameters
    ----------
    instrument : str
        Instrument name

    model : str
        Model name

    Returns
    -------
    path : str
        The complete path to the model file
    '''

    # lower case
    model = model.lower()
    instrument = instrument.lower()

    # find proper model
    data = None
    for mod in models['properties']:
        if (mod['name'] == model) and (mod['instrument'] == instrument):
            path = os.path.join(models['path'], mod['file'])

            if not os.path.exists(path):
                raise ValueError('File {0} for model {1} and instrument {2} does not exists'.format(path, model, instrument))
            
            data = mod['function'](path)

    # not found
    if data is None:
        raise ValueError('Could not find model {0} for instrument {1}'.format(model, instrument))

    return data


def plot_model(instrument, model, param, ages=None, masses=None):
    '''
    Plot parameter evolution as a function of age for a model and instrument

    Parameters
    ----------
    instrument : str
        Instrument name

    model : str
        Model name

    param : str
        Parameter of the model to be plotted
    
    ages : array
        List of ages to use for the plots. Default is None, so it will 
        use all available ages

    masses : array
        List of masses to use for the plots. Default is None, so it will 
        use all available masses

    Returns
    -------
    path : str
        The complete path to the model file
    '''
    
    data = read_model_data(instrument, model)

    if masses:
        masses = np.array(masses)
    else:
        masses = data.mass.unique()

    if ages:
        ages = np.array(ages)
    else:
        ages = data.age.unique()

    cmap = cm.plasma
    norm = colors.LogNorm(vmin=ages.min(), vmax=ages.max())
    
    #
    # param vs. age
    #
    fig = plt.figure(0, figsize=(12, 9))
    plt.clf()
    ax = fig.add_subplot(111)
    
    for mass in masses:
        if (mass <= 75):
            ax.plot(data.loc[data.mass == mass, 'age'], data.loc[data.mass == mass, param], label=r'{0:.1f} MJup'.format(mass), color=cmap(mass/75.))

    ax.set_xscale('log')
    ax.set_yscale('linear')
    
    ax.set_xlabel('Age [Myr]')
    ax.set_ylabel(param)

    ax.set_title('{0}, {1}'.format(model, instrument))
    
    ax.legend(loc='upper right')
    
    plt.tight_layout()

    #
    # param vs. mass
    #
    fig = plt.figure(1, figsize=(12, 9))
    plt.clf()
    ax = fig.add_subplot(111)
    
    for age in ages:
        ax.plot(data.loc[data.age == age, 'mass'], data.loc[data.age == age, param], label=r'{0:.0f} Myr'.format(age), color=cmap(norm(age)))

    ax.set_xlim(0, 75)
        
    ax.set_xscale('linear')
    ax.set_yscale('linear')
    
    ax.set_xlabel(r'Mass [$M_{Jup}$]')
    ax.set_ylabel(param)

    ax.set_title('{0}, {1}'.format(model, instrument))
    
    ax.legend(loc='upper right')
    
    plt.tight_layout()

