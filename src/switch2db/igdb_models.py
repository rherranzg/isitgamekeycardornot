from pydantic import BaseModel, Field


class IgdbCompany(BaseModel):
    """Compañía de IGDB; solo interesa su nombre."""

    name: str = Field(..., description="Nombre de la compañía")


class IgdbInvolvedCompany(BaseModel):
    """Relación entre un juego y una compañía en IGDB."""

    company: IgdbCompany = Field(..., description="Compañía implicada")
    publisher: bool = Field(False, description="True si la compañía publica el juego")


class IgdbGameType(BaseModel):
    """Tipo de juego en IGDB (juego principal, port, bundle...)."""

    type: str = Field(..., description="Nombre del tipo de juego")


class IgdbPlatform(BaseModel):
    """Plataforma de IGDB."""

    id: int = Field(..., description="Id de la plataforma en IGDB")
    name: str = Field(..., description="Nombre de la plataforma")


class IgdbGame(BaseModel):
    """Juego de IGDB con los campos que pide GAME_FIELDS."""

    id: int = Field(..., description="Id del juego en IGDB")
    name: str = Field(..., description="Nombre del juego")
    first_release_date: int | None = Field(None, description="Primer lanzamiento, timestamp Unix en segundos")
    game_type: IgdbGameType | None = Field(None, description="Tipo de juego")
    involved_companies: list[IgdbInvolvedCompany] = Field(
        default_factory=list, description="Compañías implicadas en el juego"
    )
