class C_NAType:
    ...


class NAType(C_NAType):
    ...

NA: NAType

def is_matching_na(left: object, right: object, nan_matches_none: bool = ...) -> bool:
    ...

