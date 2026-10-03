from pydantic import BaseModel, ConfigDict


class ModeloEstrito(BaseModel):

    model_config = ConfigDict(extra="forbid")
