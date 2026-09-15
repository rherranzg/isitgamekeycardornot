from switch2db.igdb_models import IgdbGame
from switch2db.models import Title, TitleSeed, TitleStatus

PUBLISHER_SEPARATOR = " / "


def list_publishers(game: IgdbGame) -> list[str]:
    """Devuelve, sin repetir y en orden, las compañías que IGDB marca como publisher."""
    return list(
        dict.fromkeys(involved.company.name for involved in game.involved_companies if involved.publisher)
    )


def extract_publisher(game: IgdbGame) -> str:
    """Une los publishers que IGDB marca para el juego; falla si no hay ninguno."""
    publishers = list_publishers(game)
    if not publishers:
        raise ValueError(f"IGDB {game.id} ('{game.name}') no tiene ningún publisher marcado")
    return PUBLISHER_SEPARATOR.join(publishers)


def map_game_to_title(seed: TitleSeed, game: IgdbGame) -> Title:
    """Construye el Title de una semilla con los metadatos de su juego de IGDB, pendiente de revisar."""
    return Title(
        title_id=seed.title_id,
        igdb_id=seed.igdb_id,
        name=game.name,
        publisher=extract_publisher(game),
        status=TitleStatus.PENDING,
    )


def map_games_to_titles(seeds: list[TitleSeed], games: list[IgdbGame]) -> list[Title]:
    """Empareja cada semilla con su juego de IGDB por id; falla si IGDB no devolvió alguno."""
    games_by_id = {game.id: game for game in games}
    missing_ids = [seed.igdb_id for seed in seeds if seed.igdb_id not in games_by_id]
    if missing_ids:
        raise ValueError(f"IGDB no devolvió los ids {missing_ids}; revisa title_seeds.yaml")
    return [map_game_to_title(seed, games_by_id[seed.igdb_id]) for seed in seeds]
