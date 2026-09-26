from pydantic import BaseModel, Field


class IgdbCompany(BaseModel):
    """IGDB company; only its name matters."""

    name: str = Field(..., description="Company name")


class IgdbInvolvedCompany(BaseModel):
    """Link between a game and a company on IGDB."""

    company: IgdbCompany = Field(..., description="Involved company")
    publisher: bool = Field(False, description="True if the company publishes the game")


class IgdbGameType(BaseModel):
    """Game type on IGDB (main game, port, bundle...)."""

    type: str = Field(..., description="Game type name")


class IgdbPlatform(BaseModel):
    """IGDB platform."""

    id: int = Field(..., description="Platform id on IGDB")
    name: str = Field(..., description="Platform name")


class IgdbDateFormat(BaseModel):
    """Precision of an IGDB date: YYYYMMDD, YYYYMM, YYYY, YYYYQ1..YYYYQ4 or TBD."""

    format: str = Field(..., description="Date format name")


class IgdbReleaseDate(BaseModel):
    """Release of a game on a platform and region according to IGDB."""

    platform: int | None = Field(None, description="Platform id on IGDB")
    date: int | None = Field(
        None, description="Unix timestamp in seconds; for a year or quarter it is the last day of the period"
    )
    y: int | None = Field(None, description="Release year")
    m: int | None = Field(None, description="Release month")
    date_format: IgdbDateFormat | None = Field(None, description="Precision with which the date is known")


class IgdbGame(BaseModel):
    """IGDB game with the fields requested by GAME_FIELDS."""

    id: int = Field(..., description="Game id on IGDB")
    name: str = Field(..., description="Game name")
    release_dates: list[IgdbReleaseDate] = Field(
        default_factory=list, description="Game releases by platform and region"
    )
    game_type: IgdbGameType | None = Field(None, description="Game type")
    version_parent: int | None = Field(
        None,
        description="Id of the game this entry is an edition of (Deluxe, Gold...); None if it is not one",
    )
    involved_companies: list[IgdbInvolvedCompany] = Field(
        default_factory=list, description="Companies involved in the game"
    )
