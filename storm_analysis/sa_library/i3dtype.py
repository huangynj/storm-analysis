#!/usr/bin/env python
"""
Insight3 data type definition & manipulation.

Hazen 4/09
"""

import numpy

import storm_analysis.sa_library.ia_utilities_c as utilC


def i3DataType():
    return numpy.dtype([('x', numpy.float32),   # original x location
                        ('y', numpy.float32),   # original y location
                        ('xc', numpy.float32),  # drift corrected x location
                        ('yc', numpy.float32),  # drift corrected y location
                        ('h', numpy.float32),   # fit height
                        ('a', numpy.float32),   # fit area
                        ('w', numpy.float32),   # fit width
                        ('phi', numpy.float32), # fit angle (for unconstrained elliptical gaussian)
                        ('ax', numpy.float32),  # peak aspect ratio
                        ('bg', numpy.float32),  # fit background
                        ('i', numpy.float32),   # sum - baseline for pixels included in the peak
                        ('c', numpy.int32),     # peak category ([0..9] for STORM images)
                        ('fi', numpy.int32),    # fit iterations
                        ('fr', numpy.int32),    # frame
                        ('tl', numpy.int32),    # track length
                        ('lk', numpy.int32),    # link (id of the next molecule in the trace)
                        ('z', numpy.float32),   # original z coordinate
                        ('zc', numpy.float32)]) # drift corrected z coordinate


def convertToMultiFit(i3data, x_size, y_size, frame, nm_per_pixel, inverted=False):
    """
    Create a 3D-DAOSTORM, sCMOS or Spliner analysis compatible peak array from I3 data.

    Notes:
      (1) This uses the non-drift corrected positions.
      (2) This sets the initial fitting error to zero and the status to RUNNING.
    """
    i3data = maskData(i3data, (i3data['fr'] == frame))

    peaks = numpy.zeros((i3data.size, utilC.getNPeakPar()))
    
    peaks[:,utilC.getBackgroundIndex()] = i3data['bg']
    peaks[:,utilC.getHeightIndex()] = i3data['h']
    peaks[:,utilC.getZCenterIndex()] = i3data['z'] * 0.001

    if inverted:
        peaks[:,utilC.getXCenterIndex()] = y_size - i3data['x']
        peaks[:,utilC.getYCenterIndex()] = x_size - i3data['y']
        ax = i3data['ax']
        ww = i3data['w']
        peaks[:,utilC.getYWidthIndex()] = 0.5*numpy.sqrt(ww*ww/ax)/nm_per_pixel
        peaks[:,utilC.getXWidthIndex()] = 0.5*numpy.sqrt(ww*ww*ax)/nm_per_pixel
    else:
        peaks[:,utilC.getYCenterIndex()] = i3data['x'] - 1
        peaks[:,utilC.getXCenterIndex()] = i3data['y'] - 1
        ax = i3data['ax']
        ww = i3data['w']
        peaks[:,utilC.getXWidthIndex()] = 0.5*numpy.sqrt(ww*ww/ax)/nm_per_pixel
        peaks[:,utilC.getYWidthIndex()] = 0.5*numpy.sqrt(ww*ww*ax)/nm_per_pixel

    return peaks
    

def createFromMultiFit(molecules, x_size, y_size, frame, nm_per_pixel, inverted=False):
    """
    Create an I3 data from the output of 3D-DAOSTORM, sCMOS or Spliner.
    """
    n_molecules = molecules.shape[0]
        
    h = molecules[:,0]
    if inverted:
        xc = y_size - molecules[:,utilC.getXCenterIndex()]
        yc = x_size - molecules[:,utilC.getYCenterIndex()]
        wx = 2.0*molecules[:,utilC.getXWidthIndex()]*nm_per_pixel
        wy = 2.0*molecules[:,utilC.getYWidthIndex()]*nm_per_pixel
    else:
        xc = molecules[:,utilC.getYCenterIndex()] + 1
        yc = molecules[:,utilC.getXCenterIndex()] + 1
        wx = 2.0*molecules[:,utilC.getYWidthIndex()]*nm_per_pixel
        wy = 2.0*molecules[:,utilC.getXWidthIndex()]*nm_per_pixel

    bg = molecules[:,utilC.getBackgroundIndex()]
    zc = molecules[:,utilC.getZCenterIndex()] * 1000.0  # fitting is done in um, insight works in nm
    st = numpy.round(molecules[:,utilC.getStatusIndex()])
    err = molecules[:,utilC.getErrorIndex()]

    #
    # Calculate peak area, which is saved in the "a" field.
    #
    # Note that this is assuming that the peak is a 2D gaussian. This
    # will not calculate the correct area for a Spline..
    #
    parea = 2.0*3.14159*h*molecules[:,utilC.getXWidthIndex()]*molecules[:,utilC.getYWidthIndex()]

    ax = wy/wx
    ww = numpy.sqrt(wx*wy)
        
    i3data = createDefaultI3Data(xc.size)
    posSet(i3data, 'x', xc)
    posSet(i3data, 'y', yc)
    posSet(i3data, 'z', zc)
    setI3Field(i3data, 'h', h)
    setI3Field(i3data, 'bg', bg)
    setI3Field(i3data, 'fi', st)
    setI3Field(i3data, 'a', parea)
    setI3Field(i3data, 'w', ww)
    setI3Field(i3data, 'ax', ax)
    setI3Field(i3data, 'fr', frame)
    setI3Field(i3data, 'i', err)

    return i3data


def createDefaultI3Data(size):
    data = numpy.zeros(size, dtype = i3DataType())
    defaults = [['x', 1.0],
                ['y', 1.0],
                ['xc', 1.0],
                ['yc', 1.0],
                ['h', 100.0],
                ['a', 10000.0],
                ['w', 300.0],
                ['phi', 0.0],
                ['ax', 1.0],
                ['bg', 0.0],
                ['i', 10000.0],
                ['c', 1],
                ['fi', 1],
                ['fr', 1],
                ['tl', 1],
                ['lk', -1],
                ['z', 0.0],
                ['zc', 0.0]]

    for elt in defaults:
        setI3Field(data, elt[0], elt[1])

    return data


def getI3DataTypeSize():
    data = numpy.zeros(1, dtype = i3DataType())
    return len(data.dtype.names)


def maskData(i3data, mask):
    """
    Creates a new i3 data structure containing only
    those elements where mask is True.
    """
    new_i3data = numpy.zeros(mask.sum(), dtype = i3DataType())
    for field in i3data.dtype.names:
        new_i3data[field] = i3data[field][mask]
    return new_i3data


def posSet(i3data, field, value):
    """
    Convenience function for setting both a position
    and it's corresponding drift corrected value.
    """
    setI3Field(i3data, field, value)
    setI3Field(i3data, field + 'c', value)

    
def setI3Field(i3data, field, value):
    if field in i3data.dtype.names:
        data_type = i3data.dtype.fields[field][0]
        if isinstance(value, numpy.ndarray):
            i3data[field] = value.astype(data_type)
        else:
            i3data[field] = value * numpy.ones(i3data[field].size, dtype = data_type)


#
# The MIT License
#
# Copyright (c) 2012 Zhuang Lab, Harvard University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
