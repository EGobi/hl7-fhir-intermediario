from logging import INFO, Logger, basicConfig, getLogger
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from requests import Response, Session
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from typing import Any, Dict, Final, List, Optional, Self, Type
from urllib.parse import urljoin
from urllib3.util import Retry

basicConfig(level=INFO, format="%(levelname)s: %(message)s")
logger: Logger = getLogger(__name__)


class FHIRClientError(Exception):
    """Exceção para erros de serviço."""

    pass


class FHIRResourceNotFound(FHIRClientError):
    """Erro levantado se o código 404 for retornado pela requisição."""

    pass


class FHIRBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, frozen=True, extra="ignore"
    )


class CodeableConcept(FHIRBaseModel):
    text: str
    coding: List[Dict[str, Any]] = Field(default_factory=list)


class Quantity(FHIRBaseModel):
    value: float
    unit: str


class Observation(FHIRBaseModel):
    """DTO para o recurso FHIR Observation."""

    id: Optional[str] = None
    status: str
    code: CodeableConcept
    value_quantity: Quantity
    category: List[CodeableConcept] = Field(default_factory=list)
    effective_date_time: str

    @field_validator("category", mode="before")
    @classmethod
    def ensure_vital_signs(cls, v: Any) -> Any:
        """Validador garantidor de observações com a categoria de sinais vitais."""

        str_v: str = str(v)
        if "vital-signs" not in str_v:
            raise ValueError("A observação não está na categoria dos sinais vitais.")
        return v

    def to_line(self) -> str:
        """Formatação para saída em console."""
        return f"{self.code.text}|{self.value_quantity.value:.2f} {self.value_quantity.unit}"


class FHIRClient:
    """Cliente de serviço para recursos FHIR."""

    def __init__(self, base_url: str, timeout: int = 10):
        suffix: str = "/"
        self.base_url: str = base_url.rstrip(suffix) + suffix
        self.timeout: int = timeout
        self._session: Session = self._build_section()

    def _build_section(self) -> Session:
        session: Session = Session()
        status_forcelist: list[int] = [429, 500, 502, 503, 504]
        max_retries: Retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=status_forcelist,
            raise_on_status=False,
        )
        adapter: HTTPAdapter = HTTPAdapter(max_retries=max_retries)
        prefixes: list[str] = ["http://", "https://"]
        session.mount(prefixes[0], adapter=adapter)
        session.mount(prefixes[1], adapter=adapter)

        return session

    def __enter__(self) -> Self:
        """Permite usar a classe como: with FHIRClient(...) as client:"""
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], *args: Any) -> None:
        """Garante que a sessão foi fechada e fecha o pool de conexões."""
        self._session.close()

    def get_resources(
        self, resource_type: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        url: str = urljoin(self.base_url, resource_type)
        try:
            response: Response = self._session.get(url=url, params=params, timeout=self.timeout)

            if response.status_code >= 400:
                logger.error(f"Erro do servidor FHIR: {response.text}")
                response.raise_for_status()

            data: Any = response.json()
            return [
                item["resource"] for item in data.get("entry", []) if "resource" in item
            ]
        except RequestException as e:
            raise FHIRClientError(f"Connection failed: {e}")

    def get_vital_signs(self, patient_id: str) -> List[Observation]:
        """Busca sinais vitais aplicando filtros e ordenação."""
        params: Dict[str, str] = {
            "patient": patient_id,
            "_sort": "date,code",
            "category": "vital-signs",
        }

        raw_resources: List[Dict[str, Any]] = self.get_resources("Observation", params=params)
        observations = []

        for res in raw_resources:
            try:
                observations.append(Observation.model_validate(res))
            except ValueError as e:
                logger.warning(f"Pulando recurso {res.get('id')}: {e}")
                continue

        return observations


if __name__ == "__main__":
    CONFIG: Final[Dict[str, str]] = {
        "BASE_URL": "http://fhirserver.hl7fundamentals.org/fhir/",
        "RESOURCE_URL": "Observation",
        "PATIENT_ID": "X12984",
        "SORT_VALUE": "date,code",
    }

    with FHIRClient(CONFIG["BASE_URL"]) as client:
        try:
            vital_signs = client.get_vital_signs(CONFIG["PATIENT_ID"])

            print(f"Sinais vitais retornados para o paciente {CONFIG['PATIENT_ID']}:")
            for obs in vital_signs:
                print(obs.to_line())

        except FHIRClientError as e:
            logger.critical(f"Erro no aplicação: {e}")
