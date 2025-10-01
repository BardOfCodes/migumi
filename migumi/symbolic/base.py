

import geolipi.symbolic as gls
from geolipi.symbolic.registry import register_symbol


class MXGFunction(gls.GLFunction):
    symbol_category = "mxg"

@register_symbol
class RegisterGeometry(MXGFunction):

    @classmethod
    def default_spec(cls):
        return {"expr": {"type": "Expr"}, "name": {"type": "str"},  "bbox": {"type": "Vector[3]"}}

@register_symbol
class RegisterState(MXGFunction):
    
    @classmethod
    def default_spec(cls):
        return {"expr": {"type": "Expr"}, "state": {"type": "float"}}

@register_symbol
class NamedGeometry(MXGFunction):
    @classmethod
    def default_spec(cls):
        return {"name": {"type": "str"}}

@register_symbol
class LinkedHeightField3D(MXGFunction):
    @classmethod
    def default_spec(cls):
        return {"plane": {"type": "Expr"}, "apply_height": {"type": "Expr"}}

@register_symbol
class ApplyHeight(MXGFunction):
    @classmethod
    def default_spec(cls):
        return {"expr": {"type": "Expr"}, "height": {"type": "float"}}

@register_symbol
class MarkerNode(MXGFunction):
    @classmethod
    def default_spec(cls):
        return {"expr": {"type": "Expr"}}

@register_symbol
class SetMaterial(MXGFunction):
    @classmethod
    def default_spec(cls):
        return {"expr": {"type": "Expr"}, "material": {"type": "float"}}
