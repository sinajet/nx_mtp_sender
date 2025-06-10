from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    EXCEPINFO, OLE_HANDLE, OLE_XSIZE_CONTAINER, OLE_XPOS_CONTAINER,
    Checked, dispid, IDispatch, VgaColor, OLE_YSIZE_PIXELS,
    FontEvents, OLE_COLOR, VARIANT_BOOL, IPictureDisp, OLE_CANCELBOOL,
    OLE_XPOS_HIMETRIC, OLE_YPOS_HIMETRIC, OLE_XPOS_PIXELS, DISPMETHOD,
    Gray, Font, OLE_OPTEXCLUSIVE, FONTSIZE, Unchecked, IFont,
    DISPPROPERTY, OLE_YPOS_PIXELS, _lcid, Monochrome, FONTNAME,
    IEnumVARIANT, OLE_XSIZE_HIMETRIC, COMMETHOD, OLE_YSIZE_CONTAINER,
    IUnknown, StdPicture, CoClass, OLE_ENABLEDEFAULTBOOL,
    IFontEventsDisp, GUID, Library, DISPPARAMS, StdFont, HRESULT,
    OLE_YSIZE_HIMETRIC, OLE_YPOS_CONTAINER, typelib_path,
    FONTUNDERSCORE, FONTITALIC, _check_version, Picture,
    OLE_XSIZE_PIXELS, IFontDisp, IPicture, FONTBOLD, Color, Default,
    BSTR, FONTSTRIKETHROUGH
)


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


__all__ = [
    'FONTNAME', 'OLE_XSIZE_HIMETRIC', 'OLE_HANDLE',
    'OLE_XSIZE_CONTAINER', 'OLE_XPOS_CONTAINER', 'Checked',
    'VgaColor', 'OLE_YSIZE_PIXELS', 'FontEvents',
    'OLE_YSIZE_CONTAINER', 'OLE_COLOR', 'StdPicture',
    'OLE_ENABLEDEFAULTBOOL', 'IFontEventsDisp', 'OLE_TRISTATE',
    'IPictureDisp', 'Library', 'StdFont', 'OLE_YPOS_CONTAINER',
    'OLE_CANCELBOOL', 'OLE_XPOS_HIMETRIC', 'typelib_path',
    'FONTUNDERSCORE', 'OLE_YPOS_HIMETRIC', 'OLE_XPOS_PIXELS',
    'FONTITALIC', 'Gray', 'Font', 'LoadPictureConstants', 'Picture',
    'OLE_OPTEXCLUSIVE', 'FONTSIZE', 'OLE_XSIZE_PIXELS', 'IFontDisp',
    'IPicture', 'FONTSTRIKETHROUGH', 'FONTBOLD', 'Unchecked', 'IFont',
    'Color', 'OLE_YPOS_PIXELS', 'Default', 'Monochrome',
    'OLE_YSIZE_HIMETRIC'
]

