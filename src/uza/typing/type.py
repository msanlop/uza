from ..token import *

class UzaType:
    integer = "int"
    fp = "float"
    string = "string"
    boolean = "bool"
    object = "object"
    void = "void"
    
    get_python_type = {
        int: integer,
        float: fp,
        str: string,
        bool: boolean,
        None: void
    }
    
    _uza_to_enum = {
        "int" : integer,
        "float": fp,
        "string": string,
        "bool": boolean,
        "void": void,
    }
    
    def to_type(type_ : Token) -> int :
        assert type_.kind == token_identifier
        return UzaType._uza_to_enum.get(type_.repr)
