from pathlib import Path
from typing import IO, AnyStr, Type, Union

import numpy as np

from pandas.core.dtypes.dtypes import ExtensionDtype
from pandas.core.dtypes.generic import ABCExtensionArray

ArrayLike = Union[ABCExtensionArray, np.ndarray]
Dtype = Union[str, np.dtype, ExtensionDtype, Type]
FilePathOrBuffer = Union[str, Path, IO[AnyStr]]
