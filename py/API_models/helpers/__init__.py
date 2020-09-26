from typing import Type

from pydantic import BaseModel

# Typing alias as we have DB Model as well, which might be confusing
PydanticModelT = Type[BaseModel]
