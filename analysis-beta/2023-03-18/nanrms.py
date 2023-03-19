import numpy as np
import warnings
from numpy.core import multiarray as mu
from numpy.core import umath as um
from numpy.core.multiarray import asanyarray
from numpy.core import numerictypes as nt
from numpy.core._ufunc_config import _no_nep50_warning

# __all__ = [
#     'nansumsq',
#     'nanrms',
# ]

umr_sum = um.add.reduce
umr_any = um.logical_or.reduce

# Complex types to -> (2,)float view for fast-path computation in _var()
_complex_to_float = {
    nt.dtype(nt.csingle) : nt.dtype(nt.single),
    nt.dtype(nt.cdouble) : nt.dtype(nt.double),
}
# Special case for windows: ensure double takes precedence
if nt.dtype(nt.longdouble) != nt.dtype(nt.double):
    _complex_to_float.update({
        nt.dtype(nt.clongdouble) : nt.dtype(nt.longdouble),
    })

def _count_reduce_items(arr, axis, keepdims=False, where=True):
    # fast-path for the default case
    if where is True:
        # no boolean mask given, calculate items according to axis
        if axis is None:
            axis = tuple(range(arr.ndim))
        elif not isinstance(axis, tuple):
            axis = (axis,)
        items = 1
        for ax in axis:
            items *= arr.shape[mu.normalize_axis_index(ax, arr.ndim)]
        items = nt.intp(items)
    else:
        # TODO: Optimize case when `where` is broadcast along a non-reduction
        # axis and full sum is more excessive than needed.

        # guarded to protect circular imports
        from numpy.lib.stride_tricks import broadcast_to
        # count True values in (potentially broadcasted) boolean mask
        items = umr_sum(broadcast_to(where, arr.shape), axis, nt.intp, None,
                        keepdims)
    return items

def _sumsq(a, axis=None, dtype=None, out=None, ddof=0, keepdims=False, *,
         where=True):
    arr = asanyarray(a)

    rcount = _count_reduce_items(arr, axis, keepdims=keepdims, where=where)
    # Make this warning show up on top.
    if ddof >= rcount if where is True else umr_any(ddof >= rcount, axis=None):
        warnings.warn("Degrees of freedom <= 0 for slice", RuntimeWarning,
                      stacklevel=2)

    # Cast bool, unsigned int, and int to float64 by default
    if dtype is None and issubclass(arr.dtype.type, (nt.integer, nt.bool_)):
        dtype = mu.dtype('f8')

    # Compute the mean.
    # Note that if dtype is not of inexact type then arraymean will
    # not be either.
    arrmean = umr_sum(arr, axis, dtype, keepdims=True, where=where)
    # The shape of rcount has to match arrmean to not change the shape of out
    # in broadcasting. Otherwise, it cannot be stored back to arrmean.
    if rcount.ndim == 0:
        # fast-path for default case when where is True
        div = rcount
    else:
        # matching rcount to arrmean when where is specified as array
        div = rcount.reshape(arrmean.shape)
    if isinstance(arrmean, mu.ndarray):
        with _no_nep50_warning():
            arrmean = um.true_divide(arrmean, div, out=arrmean,
                                     casting='unsafe', subok=False)
    elif hasattr(arrmean, "dtype"):
        arrmean = arrmean.dtype.type(arrmean / rcount)
    else:
        arrmean = arrmean / rcount

    # Compute sum of squared deviations from mean
    # Note that x may not be inexact and that we need it to be an array,
    # not a scalar.
    # x = asanyarray(arr - arrmean)
    x = asanyarray(arr)

    if issubclass(arr.dtype.type, (nt.floating, nt.integer)):
        x = um.multiply(x, x, out=x)
    # Fast-paths for built-in complex types
    elif x.dtype in _complex_to_float:
        xv = x.view(dtype=(_complex_to_float[x.dtype], (2,)))
        um.multiply(xv, xv, out=xv)
        x = um.add(xv[..., 0], xv[..., 1], out=x.real).real
    # Most general case; includes handling object arrays containing imaginary
    # numbers and complex types with non-native byteorder
    else:
        x = um.multiply(x, um.conjugate(x), out=x).real

    ret = umr_sum(x, axis, dtype, out, keepdims=keepdims, where=where)

    # Compute degrees of freedom and make sure it is not negative.
    rcount = um.maximum(rcount - ddof, 0)

    # divide by degrees of freedom
    if isinstance(ret, mu.ndarray):
        with _no_nep50_warning():
            ret = um.true_divide(
                    ret, rcount, out=ret, casting='unsafe', subok=False)
    elif hasattr(ret, 'dtype'):
        ret = ret.dtype.type(ret / rcount)
    else:
        ret = ret / rcount
    return ret

def sumsq(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue, *,
        where=np._NoValue):
    kwargs = {}
    if keepdims is not np._NoValue:
        kwargs['keepdims'] = keepdims
    if where is not np._NoValue:
        kwargs['where'] = where

    if type(a) is not mu.ndarray:
        try:
            sumsq = a.sumsq
        except AttributeError:
            pass
        else:
            return sumsq(axis=axis, dtype=dtype, out=out, ddof=ddof, **kwargs)
    return _sumsq(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                         **kwargs)

def _copyto(a, val, mask):
    if isinstance(a, np.ndarray):
        np.copyto(a, val, where=mask, casting='unsafe')
    else:
        a = a.dtype.type(val)
    return a

def _divide_by_count(a, b, out=None):
    with np.errstate(invalid='ignore', divide='ignore'):
        if isinstance(a, np.ndarray):
            if out is None:
                return np.divide(a, b, out=a, casting='unsafe')
            else:
                return np.divide(a, b, out=out, casting='unsafe')
        else:
            if out is None:
                # Precaution against reduced object arrays
                try:
                    return a.dtype.type(a / b)
                except AttributeError:
                    return a / b
            else:
                # This is questionable, but currently a numpy scalar can
                # be output to a zero dimensional array.
                return np.divide(a, b, out=out, casting='unsafe')

def _replace_nan(a, val):
    a = np.asanyarray(a)

    if a.dtype == np.object_:
        # object arrays do not support `isnan` (gh-9009), so make a guess
        mask = np.not_equal(a, a, dtype=bool)
    elif issubclass(a.dtype.type, np.inexact):
        mask = np.isnan(a)
    else:
        mask = None

    if mask is not None:
        a = np.array(a, subok=True, copy=True)
        np.copyto(a, val, where=mask)
    return a, mask

def nansumsq(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue,
           *, where=np._NoValue):
    arr, mask = _replace_nan(a, 0)
    if mask is None:
        return sumsq(arr, axis=axis, dtype=dtype, out=out, ddof=ddof,
                      keepdims=keepdims, where=where)

    if dtype is not None:
        dtype = np.dtype(dtype)
    if dtype is not None and not issubclass(dtype.type, np.inexact):
        raise TypeError("If a is inexact, then dtype must be inexact")
    if out is not None and not issubclass(out.dtype.type, np.inexact):
        raise TypeError("If a is inexact, then out must be inexact")

    # Compute mean
    if type(arr) is np.matrix:
        _keepdims = np._NoValue
    else:
        _keepdims = True
    # we need to special case matrix for reverse compatibility
    # in order for this to work, these sums need to be called with
    # keepdims=True, however matrix now raises an error in this case, but
    # the reason that it drops the keepdims kwarg is to force keepdims=True
    # so this used to work by serendipity.
    cnt = np.sum(~mask, axis=axis, dtype=np.intp, keepdims=_keepdims,
                 where=where)
    avg = np.sum(arr, axis=axis, dtype=dtype, keepdims=_keepdims, where=where)
    avg = _divide_by_count(avg, cnt)

    # Compute squared deviation from mean.
    # np.subtract(arr, avg, out=arr, casting='unsafe', where=where)
    arr = _copyto(arr, 0, mask)
    if issubclass(arr.dtype.type, np.complexfloating):
        sqr = np.multiply(arr, arr.conj(), out=arr, where=where).real
    else:
        sqr = np.multiply(arr, arr, out=arr, where=where)

    # Compute variance.
    var = np.sum(sqr, axis=axis, dtype=dtype, out=out, keepdims=keepdims,
                 where=where)

    # Precaution against reduced object arrays
    try:
        var_ndim = var.ndim
    except AttributeError:
        var_ndim = np.ndim(var)
    if var_ndim < cnt.ndim:
        # Subclasses of ndarray may ignore keepdims, so check here.
        cnt = cnt.squeeze(axis)
    dof = cnt - ddof
    var = _divide_by_count(var, dof)

    isbad = (dof <= 0)
    if np.any(isbad):
        warnings.warn("Degrees of freedom <= 0 for slice.", RuntimeWarning,
                      stacklevel=3)
        # NaN, inf, or negative numbers are all possible bad
        # values, so explicitly replace them with NaN.
        var = _copyto(var, np.nan, isbad)
    return var

def nanrms(a, axis=None, dtype=None, out=None, ddof=0, keepdims=np._NoValue,
           *, where=np._NoValue):
    var = nansumsq(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
                 keepdims=keepdims, where=where)
    if isinstance(var, np.ndarray):
        std = np.sqrt(var, out=var)
    elif hasattr(var, 'dtype'):
        std = var.dtype.type(np.sqrt(var))
    else:
        std = np.sqrt(var)
    return std

