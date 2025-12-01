

import geolipi.symbolic as gls
from geolipi.symbolic.registry import register_symbol

class MillableExtrusion(gls.Primitive3D):
    @classmethod
    def default_spec(cls):
        return {"expr": {"type": "Expr"}, "plane": {"type": "Expr"}, "height": {"type": "float"}}

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