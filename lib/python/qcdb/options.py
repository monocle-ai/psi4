#
#@BEGIN LICENSE
#
# PSI4: an ab initio quantum chemistry software package
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#@END LICENSE
#

import math
from exceptions import *


def format_option_for_cfour(opt, val):
    """Function to reformat value *val* for option *opt* from python
    into cfour-speak. Arrays are the primary target.

    """
    text = ''

    # Transform list from [[3, 0, 1, 1], [2, 0, 1, 0]] --> 3-0-1-1/2-0-1-0
    if isinstance(val, list):
        if type(val[0]).__name__ == 'list':
            if type(val[0][0]).__name__ == 'list':
                raise ValidationError('Option has level of array nesting inconsistent with CFOUR.')
            else:
                # option is 2D array
                for no in range(len(val)):
                    for ni in range(len(val[no])):
                        text += str(val[no][ni])
                        if ni < (len(val[no]) - 1):
                            text += '-'
                    if no < (len(val) - 1):
                        text += '/'
        else:
            # option is plain 1D array
            for n in range(len(val)):
                text += str(val[n])
                if n < (len(val) - 1):
                    text += '-'

    # Transform booleans into integers
    elif str(val) == 'True':
        text += '1'
    elif str(val) == 'False':
        text += '0'

    # Transform the basis sets that *must* be lowercase (dratted c4 input)
    elif (opt == 'CFOUR_BASIS') and (val.upper() in ['SVP', 'DZP', 'TZP', 'TZP2P', 'QZ2P', 'PZ3D2F', '13S9P4D3F']):
        text += str(val.lower())

    # No Transform
    else:
        text += str(val)

    return opt[6:], text


def prepare_options_for_cfour(options):
    """Function to take the full snapshot of the liboptions object
    encoded in dictionary *options*, find the options directable toward
    Cfour (options['CFOUR']['CFOUR_**']) that aren't default, then write
    a CFOUR deck with those options.

    """
    text = ''

    for opt, val in options['CFOUR'].items():
        if opt.startswith('CFOUR_'):
            if val['has_changed']:
                if not text:
                    text += """*CFOUR("""
                text += """%s=%s\n""" % (format_option_for_cfour(opt, val['value']))
    if text:
        text = text[:-1] + ')\n\n'

    return text


def reconcile_options(full, partial):
    """Function to take the full snapshot of the liboptions object
    encoded in dictionary *full* and reconcile it with proposed options
    value changes in *partial*. Overwrites *full* with *partial* if
    option untouched, touches *full* if *full* and *partial* are in
    agreement, balks if *full* and *partial* conflict. Returns *full*.

    """
    try:
        for module, modopts in partial.items():
            for kw, kwprop in modopts.items():
                if full[module][kw]['has_changed']:
                    if full[module][kw]['value'] != kwprop['value']:
                        if 'clobber' in kwprop and kwprop['clobber']:
                            if 'superclobber' in kwprop and kwprop['superclobber']:
                                # kw in full is touched, conflicts with value in partial,
                                #   but value in partial is paramount, overwrite full with
                                #   value in partial
                                full[module][kw]['value'] = kwprop['value']
                                full[module][kw]['has_changed'] = True
                                #print '@P4C4 Overwriting %s with %s' % (kw, kwprop['value'])
                            else:
                                raise ValidationError("""
    Option %s value `%s` set by options block incompatible with
    value `%s` in memory/molecule/command/psi4options block.""" %
                                (kw, full[module][kw]['value'], kwprop['value']))
                        else:
                            # kw in full is touched, conflicts with value in partial,
                            #   but value in partial is recommended, not required, no change
                            pass
                    else:
                        # kw in full is touched, but in agreement with value in partial, no change
                        pass
                else:
                    # If kw in full is untouched, overwrite it with value in partial
                    full[module][kw]['value'] = kwprop['value']
                    full[module][kw]['has_changed'] = True
                    #print '@P4C4 Overwriting %s with %s' % (kw, kwprop['value'])

    except KeyError as e:  # not expected but want to trap
        raise ValidationError("""Unexpected KeyError reconciling keywords: %s.""" % (repr(e)))

    return full


def conv_float2negexp(val):
    """Returns the least restrictive negative exponent of the power 10
    that would achieve the floating point convergence criterium *val*.

    """
    return -1 * int(math.floor(math.log(val, 10)))
