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


class IgdbDateFormat(BaseModel):
    """Precisión de una fecha de IGDB: YYYYMMDD, YYYYMM, YYYY, YYYYQ1..YYYYQ4 o TBD."""

    format: str = Field(..., description="Nombre del formato de fecha")


class IgdbReleaseDate(BaseModel):
    """Lanzamiento de un juego en una plataforma y región según IGDB."""

    platform: int | None = Field(None, description="Id de la plataforma en IGDB")
    date: int | None = Field(
        None, description="Timestamp Unix en segundos; con año o trimestre es el último día del periodo"
    )
    y: int | None = Field(None, description="Año del lanzamiento")
    m: int | None = Field(None, description="Mes del lanzamiento")
    date_format: IgdbDateFormat | None = Field(None, description="Precisión con la que se conoce la fecha")


class IgdbGame(BaseModel):
    """Juego de IGDB con los campos que pide GAME_FIELDS."""

    id: int = Field(..., description="Id del juego en IGDB")
    name: str = Field(..., description="Nombre del juego")
    release_dates: list[IgdbReleaseDate] = Field(
        default_factory=list, description="Lanzamientos del juego por plataforma y región"
    )
    game_type: IgdbGameType | None = Field(None, description="Tipo de juego")
    version_parent: int | None = Field(
        None,
        description="Id del juego del que esta entrada es una edición (Deluxe, Gold...); None si no lo es",
    )
    involved_companies: list[IgdbInvolvedCompany] = Field(
        default_factory=list, description="Compañías implicadas en el juego"
    )
