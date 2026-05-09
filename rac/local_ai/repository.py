import psycopg

from rac.config import Settings


class AIInteractionRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def record(
        self,
        *,
        environment: str,
        interaction_type: str,
        prompt_template_id: str,
        prompt_version: str,
        model_name: str | None,
        input_ref: str | None,
        prompt: str,
        response: str | None,
        status: str,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ai_interactions (
                        environment,
                        interaction_type,
                        prompt_template_id,
                        prompt_version,
                        model_name,
                        input_ref,
                        prompt,
                        response,
                        status,
                        latency_ms,
                        error
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        environment,
                        interaction_type,
                        prompt_template_id,
                        prompt_version,
                        model_name,
                        input_ref,
                        prompt,
                        response,
                        status,
                        latency_ms,
                        error,
                    ),
                )
            conn.commit()

