from dataclasses import dataclass
from enum import Enum
from logging import INFO, basicConfig, getLogger
from requests import Response, Session
from requests.exceptions import RequestException
from types import TracebackType
from typing import Any, Dict, Final, List, Optional, Type, Union, cast
from urllib.parse import urljoin

basicConfig(level=INFO, format="%(levelname)s: %(message)s")
logger = getLogger(__name__)


class FHIRClientError(Exception):
    """Exceção para erros de serviço."""

    pass


class EndpointCategory(str, Enum):
    VITAL_SIGNS = "vital-signs"


@dataclass(frozen=True)
class CodeableConcept:
    text: str


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str


@dataclass(frozen=True)
class Observation:
    """DTO para o recurso FHIR Observation."""

    code: CodeableConcept
    valueQuantity: Quantity

    @classmethod
    def from_dict(cls, resource: Dict[str, Any]) -> Optional["Observation"]:
        try:
            categories: List[Any] = cast(List[Any], resource.get("category", []))

            def is_vital_sign_category(category: Any) -> bool:
                if not isinstance(category, dict):
                    return False

                category_dict: Dict[str, Any] = cast(Dict[str, Any], category)
                coding: List[Any] = cast(
                    List[Dict[str, Any]], category_dict.get("coding", [])
                )

                if not coding or not isinstance(coding[0], dict):
                    return False

                first_coding: Dict[str, Any] = cast(Dict[str, Any], coding[0])
                return first_coding.get("code") == EndpointCategory.VITAL_SIGNS.value

            if not any(is_vital_sign_category(category) for category in categories):
                return None

            code_data: Dict[str, Any] = cast(Dict[str, Any], resource.get("code", {}))
            code_text: Any = code_data.get("text", "")
            value_quantity_data: Dict[str, Any] = cast(
                Dict[str, Any], resource.get("valueQuantity", {})
            )
            value_quantity_unit: str = cast(str, value_quantity_data.get("unit", ""))

            value_quantity_value = value_quantity_data.get("value")
            if value_quantity_value is None:
                return None

            return cls(
                code=CodeableConcept(text=code_text),
                valueQuantity=Quantity(
                    value=float(value_quantity_value), unit=value_quantity_unit
                ),
            )
        except (KeyError, TypeError, ValueError, IndexError) as e:
            logger.debug(f"Ignorando recurso com falha: {e}")
            return None

    def to_line(self) -> str:
        """Formatação para saída em console."""
        return (
            f"{self.code.text}|{self.valueQuantity.value:.2f} {self.valueQuantity.unit}"
        )


class FHIRClient:
    """Cliente de serviço para recursos FHIR."""

    def __init__(
        self, base_url: str, resource_type: str, session: Optional[Session] = None
    ):
        self.base_url: str = base_url if base_url.endswith("/") else f"{base_url}/"
        self.resource_type: str = resource_type
        self._session: Session = session if session else Session()

    def __enter__(self) -> "FHIRClient":
        """Permite usar a classe como: with FHIRClient(...) as client:"""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Garante que a sessão foi fechada."""
        self.close()

    def close(self) -> None:
        """Fecha o pool de conexões."""
        self._session.close()

    def get_vital_signs(self, patient_id: str) -> List[Observation]:
        """Busca sinais vitais aplicando filtros e ordenação."""
        params: Dict[str, Union[str, int]] = {
            "patient": patient_id,
            "_sort": "date,code",
            "category": EndpointCategory.VITAL_SIGNS.value,
        }

        endpoint: str = urljoin(self.base_url, self.resource_type)

        try:
            logger.info(
                f"Requisitando recursos do tipo {self.resource_type} para o paciente {patient_id}..."
            )
            response: Response = self._session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            return self._parse_bundle(response.json())

        except RequestException as e:
            logger.error(f"Erro na requisição ao servidor: {e}")
            raise FHIRClientError(f"Erro na requisição ao servidor: {e}")

    def _parse_bundle(self, data: Dict[str, Any]) -> List[Observation]:
        """Mapper para processar Bundles retornados pelo servidor FHIR."""
        entries: List[Any] = cast(List[Dict[str, Any]], data.get("entry", []))

        observations = [
            Observation.from_dict(cast(Dict[str, Any], entry.get("resource")))
            for entry in entries
            if isinstance(entry.get("resource"), dict)
        ]

        return [observation for observation in observations if observations is not None]


if __name__ == "__main__":
    CONFIG: Final[Dict[str, str]] = {
        "FHIR_ENDPOINT": "http://fhirserver.hl7fundamentals.org/fhir/",
        "RESOURCE_TYPE": "Observation",
        "TARGET_PATIENT_ID": "X12984",
    }

    with FHIRClient(CONFIG["FHIR_ENDPOINT"], CONFIG["RESOURCE_TYPE"]) as client:
        try:
            resources = client.get_vital_signs(CONFIG["TARGET_PATIENT_ID"])

            print(f"Recursos retornados para o paciente {CONFIG["TARGET_PATIENT_ID"]}:")
            if not resources:
                print("Nenhum recurso encontrado.")
            else:
                for observation in resources:
                    print(observation.to_line())

        except FHIRClientError as e:
            logger.critical(f"Erro no aplicação: {e}")
