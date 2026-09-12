"""Local private knowledge retriever.

The retriever supports:
- Markdown documents
- TXT documents
- CSV structured databases

Structured business questions are routed directly to the correct
CSV dataset before falling back to lexical document retrieval.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from application.ports.knowledge_retriever import KnowledgeMatch

DEFAULT_KNOWLEDGE_DIRECTORY = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "knowledge"
)

SUPPORTED_EXTENSIONS = {
    ".md",
    ".txt",
    ".csv",
}

IGNORED_FILENAMES = {
    "README_IMPORTANT.md",
    "INSTALLATION.txt",
    "questions_demo.md",
}

STOP_WORDS = {
    "a",
    "ai",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "comment",
    "dans",
    "de",
    "des",
    "du",
    "elle",
    "en",
    "est",
    "et",
    "il",
    "je",
    "la",
    "le",
    "les",
    "ma",
    "mais",
    "mes",
    "mon",
    "ne",
    "nous",
    "ou",
    "par",
    "pas",
    "pour",
    "que",
    "quel",
    "quelle",
    "quels",
    "quelles",
    "qui",
    "sa",
    "se",
    "ses",
    "son",
    "sur",
    "un",
    "une",
    "vous",
}


class LocalKnowledgeRetriever:
    """Retrieve information from the local private knowledge base."""

    def __init__(
        self,
        knowledge_directory: Path = DEFAULT_KNOWLEDGE_DIRECTORY,
    ) -> None:
        self._knowledge_directory = knowledge_directory

    def search(
        self,
        query: str,
        *,
        limit: int = 6,
    ) -> list[KnowledgeMatch]:
        """Search structured data first, then textual documentation."""

        if limit <= 0:
            return []

        clean_query = query.strip()

        if not clean_query:
            return []

        normalized_query = self._normalize_text(clean_query)

        #
        # 1. Exact business identifiers
        #
        exact_results = self._search_exact_identifier(
            query=clean_query,
        )

        if exact_results:
            return exact_results[:limit]

        #
        # 2. Structured business queries
        #
        structured_results = self._search_structured_query(
            query=clean_query,
            normalized_query=normalized_query,
        )

        if structured_results:
            return structured_results[:limit]

        #
        # 3. Fallback document / lexical search
        #
        return self._search_general(
            query=clean_query,
            limit=limit,
        )

    # =========================================================
    # EXACT IDENTIFIER LOOKUPS
    # =========================================================

    def _search_exact_identifier(
        self,
        *,
        query: str,
    ) -> list[KnowledgeMatch]:
        """Resolve exact IDs such as MP-2026-125."""

        normalized_query = self._normalize_text(query)

        patterns = (
            (
                r"\bmp-\d{4}-\d{3}\b",
                "marches.csv",
                "numero",
            ),
            (
                r"\bbc-\d{4}-\d{3}\b",
                "bons_commande.csv",
                "numero",
            ),
            (
                r"\birr-\d{4}-\d{3}\b",
                "projets_irrigation.csv",
                "projet_id",
            ),
            (
                r"\bfour-\d{3}\b",
                "fournisseurs.csv",
                "fournisseur_id",
            ),
        )

        for pattern, filename, identifier_column in patterns:
            match = re.search(
                pattern,
                normalized_query,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            identifier = match.group(0)

            path = self._knowledge_directory / filename

            if not path.exists():
                return []

            rows = self._read_csv(path)

            for row_index, row in enumerate(
                rows,
                start=1,
            ):
                current_identifier = self._normalize_text(
                    row.get(
                        identifier_column,
                        "",
                    )
                )

                if current_identifier != identifier:
                    continue

                content = self._format_row(row)

                return [
                    KnowledgeMatch(
                        source=filename,
                        content=content,
                        score=1.0,
                        chunk_index=row_index,
                        page=None,
                    )
                ]

            return []

        return []

    # =========================================================
    # STRUCTURED QUERY ROUTING
    # =========================================================

    def _search_structured_query(
        self,
        *,
        query: str,
        normalized_query: str,
    ) -> list[KnowledgeMatch]:
        """Route business questions to their structured dataset."""

        #
        # Bons de commande
        #
        if (
            "bon de commande" in normalized_query
            or "bons de commande" in normalized_query
        ):
            return self._query_csv_dataset(
                filename="bons_commande.csv",
                query=query,
                dataset_type="bons_commande",
            )

        #
        # Irrigation projects
        #
        if (
            "projet" in normalized_query
            and "irrigation" in normalized_query
        ):
            return self._query_csv_dataset(
                filename="projets_irrigation.csv",
                query=query,
                dataset_type="projets_irrigation",
            )

        #
        # Public markets
        #
        if (
            "marche" in normalized_query
            or "marches" in normalized_query
        ):
            return self._query_csv_dataset(
                filename="marches.csv",
                query=query,
                dataset_type="marches",
            )

        #
        # Suppliers
        #
        if (
            "fournisseur" in normalized_query
            or "fournisseurs" in normalized_query
        ):
            return self._query_csv_dataset(
                filename="fournisseurs.csv",
                query=query,
                dataset_type="fournisseurs",
            )

        #
        # Attributaire belongs primarily to markets
        #
        if "attributaire" in normalized_query:
            return self._query_csv_dataset(
                filename="marches.csv",
                query=query,
                dataset_type="marches",
            )

        return []

    def _query_csv_dataset(
        self,
        *,
        filename: str,
        query: str,
        dataset_type: str,
    ) -> list[KnowledgeMatch]:
        """Filter one CSV dataset using the user's intent."""

        path = self._knowledge_directory / filename

        if not path.exists():
            return []

        rows = self._read_csv(path)

        if not rows:
            return []

        normalized_query = self._normalize_text(query)

        filtered_rows = rows

        #
        # Filter by status
        #
        requested_status = self._detect_status(
            normalized_query
        )

        if requested_status is not None:
            status_filtered = [
                row
                for row in filtered_rows
                if self._normalize_text(
                    row.get(
                        "statut",
                        "",
                    )
                )
                == requested_status
            ]

            if status_filtered:
                filtered_rows = status_filtered

        #
        # Dataset-specific filtering
        #
        if dataset_type == "marches":
            filtered_rows = self._filter_markets(
                rows=filtered_rows,
                normalized_query=normalized_query,
            )

        elif dataset_type == "projets_irrigation":
            filtered_rows = self._filter_irrigation_projects(
                rows=filtered_rows,
                normalized_query=normalized_query,
            )

        elif dataset_type == "bons_commande":
            filtered_rows = self._filter_purchase_orders(
                rows=filtered_rows,
                normalized_query=normalized_query,
            )

        elif dataset_type == "fournisseurs":
            filtered_rows = self._filter_suppliers(
                rows=filtered_rows,
                normalized_query=normalized_query,
            )

        #
        # Rank remaining rows
        #
        ranked_rows = self._rank_rows(
            rows=filtered_rows,
            query=query,
        )

        if not ranked_rows:
            return []

        #
        # For broad list/count questions, aggregate results
        #
        if self._is_list_or_count_query(
            normalized_query
        ):
            return [
                self._build_aggregate_match(
                    filename=filename,
                    rows=ranked_rows,
                    dataset_type=dataset_type,
                )
            ]

        #
        # Otherwise return individual rows
        #
        matches: list[KnowledgeMatch] = []

        for row_index, (
            score,
            row,
        ) in enumerate(
            ranked_rows[:6],
            start=1,
        ):
            matches.append(
                KnowledgeMatch(
                    source=filename,
                    content=self._format_row(row),
                    score=min(
                        max(score, 0.50),
                        0.99,
                    ),
                    chunk_index=row_index,
                    page=None,
                )
            )

        return matches

    # =========================================================
    # MARKET FILTERS
    # =========================================================

    def _filter_markets(
        self,
        *,
        rows: list[dict[str, str]],
        normalized_query: str,
    ) -> list[dict[str, str]]:
        result = rows

        #
        # Category: irrigation
        #
        if "irrigation" in normalized_query:
            irrigation_rows = [
                row
                for row in result
                if (
                    "irrigation"
                    in self._normalize_text(
                        row.get(
                            "categorie",
                            "",
                        )
                    )
                    or
                    "irrigation"
                    in self._normalize_text(
                        row.get(
                            "objet",
                            "",
                        )
                    )
                )
            ]

            if irrigation_rows:
                result = irrigation_rows

        #
        # Informatique
        #
        if "informatique" in normalized_query:
            if "service informatique" in normalized_query:
                info_rows = [
                    row
                    for row in result
                    if (
                        "service informatique"
                        in self._normalize_text(
                            row.get(
                                "service_responsable",
                                "",
                            )
                        )
                    )
                ]
            else:
                info_rows = [
                    row
                    for row in result
                    if (
                        "informatique"
                        in self._normalize_text(
                            row.get(
                                "categorie",
                                "",
                            )
                        )
                        or
                        "informatique"
                        in self._normalize_text(
                            row.get(
                                "objet",
                                "",
                            )
                        )
                    )
                ]

            if info_rows:
                result = info_rows

        #
        # Known geographic zones
        #
        result = self._filter_by_known_zone(
            rows=result,
            normalized_query=normalized_query,
        )

        #
        # Service query
        #
        if "service " in normalized_query:
            result = self._filter_by_service(
                rows=result,
                normalized_query=normalized_query,
            )

        return result

    # =========================================================
    # IRRIGATION PROJECT FILTERS
    # =========================================================

    def _filter_irrigation_projects(
        self,
        *,
        rows: list[dict[str, str]],
        normalized_query: str,
    ) -> list[dict[str, str]]:
        result = self._filter_by_known_zone(
            rows=rows,
            normalized_query=normalized_query,
        )

        project_types = (
            "irrigation localisee",
            "rehabilitation de canal",
            "pompage",
            "modernisation reseau",
            "economie d'eau",
        )

        for project_type in project_types:
            if project_type not in normalized_query:
                continue

            selected = [
                row
                for row in result
                if project_type
                in self._normalize_text(
                    row.get(
                        "type_projet",
                        "",
                    )
                )
            ]

            if selected:
                result = selected

        return result

    # =========================================================
    # PURCHASE ORDER FILTERS
    # =========================================================

    def _filter_purchase_orders(
        self,
        *,
        rows: list[dict[str, str]],
        normalized_query: str,
    ) -> list[dict[str, str]]:
        result = rows

        if "informatique" in normalized_query:
            selected = [
                row
                for row in result
                if (
                    "informatique"
                    in self._normalize_text(
                        row.get(
                            "objet",
                            "",
                        )
                    )
                )
            ]

            if selected:
                result = selected

        result = self._filter_by_service(
            rows=result,
            normalized_query=normalized_query,
        )

        return result

    # =========================================================
    # SUPPLIER FILTERS
    # =========================================================

    def _filter_suppliers(
        self,
        *,
        rows: list[dict[str, str]],
        normalized_query: str,
    ) -> list[dict[str, str]]:
        result = rows

        result = self._filter_by_known_zone(
            rows=result,
            normalized_query=normalized_query,
        )

        categories = (
            "irrigation",
            "informatique",
            "maintenance",
            "logistique",
            "equipements agricoles",
        )

        for category in categories:
            if category not in normalized_query:
                continue

            selected = [
                row
                for row in result
                if category
                in self._normalize_text(
                    row.get(
                        "specialite",
                        "",
                    )
                )
            ]

            if selected:
                result = selected

        return result

    # =========================================================
    # GENERIC STRUCTURED FILTERS
    # =========================================================

    @staticmethod
    def _detect_status(
        normalized_query: str,
    ) -> str | None:
        statuses = {
            "en cours": "en cours",
            "attribue": "attribue",
            "attribues": "attribue",
            "cloture": "cloture",
            "clotures": "cloture",
            "annule": "annule",
            "annules": "annule",
            "acheve": "acheve",
            "acheves": "acheve",
            "en etude": "en etude",
            "livre": "livre",
            "reception partielle": "reception partielle",
        }

        for phrase, normalized_status in statuses.items():
            if phrase in normalized_query:
                return normalized_status

        return None

    def _filter_by_known_zone(
        self,
        *,
        rows: list[dict[str, str]],
        normalized_query: str,
    ) -> list[dict[str, str]]:
        zones = (
            "ouarzazate",
            "zagora",
            "tinghir",
            "skoura",
            "agdz",
            "boumalne-dades",
            "boumalne",
        )

        requested_zone = None

        for zone in zones:
            if zone in normalized_query:
                requested_zone = zone
                break

        if requested_zone is None:
            return rows

        selected = []

        for row in rows:
            row_zone = self._normalize_text(
                row.get(
                    "zone",
                    row.get(
                        "ville",
                        "",
                    ),
                )
            )

            if requested_zone in row_zone:
                selected.append(row)

        return selected or rows

    def _filter_by_service(
        self,
        *,
        rows: list[dict[str, str]],
        normalized_query: str,
    ) -> list[dict[str, str]]:
        services = (
            "service des marches",
            "service irrigation",
            "service equipements",
            "service informatique",
            "service etudes",
            "service logistique",
            "service maintenance",
            "service developpement agricole",
        )

        requested_service = None

        for service in services:
            if service in normalized_query:
                requested_service = service
                break

        if requested_service is None:
            return rows

        selected = [
            row
            for row in rows
            if requested_service
            in self._normalize_text(
                row.get(
                    "service_responsable",
                    "",
                )
            )
        ]

        return selected or rows

    # =========================================================
    # ROW RANKING
    # =========================================================

    def _rank_rows(
        self,
        *,
        rows: list[dict[str, str]],
        query: str,
    ) -> list[
        tuple[
            float,
            dict[str, str],
        ]
    ]:
        query_tokens = self._tokenize(query)

        ranked: list[
            tuple[
                float,
                dict[str, str],
            ]
        ] = []

        for row in rows:
            content = self._format_row(row)

            content_tokens = self._tokenize(
                content
            )

            common = (
                query_tokens
                & content_tokens
            )

            score = (
                len(common)
                / max(
                    len(query_tokens),
                    1,
                )
            )

            ranked.append(
                (
                    score,
                    row,
                )
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return ranked

    # =========================================================
    # AGGREGATION
    # =========================================================

    def _build_aggregate_match(
        self,
        *,
        filename: str,
        rows: list[
            tuple[
                float,
                dict[str, str],
            ]
        ],
        dataset_type: str,
    ) -> KnowledgeMatch:
        """Build one compact result for list/count queries."""

        total = len(rows)

        selected_rows = [
            row
            for _, row
            in rows[:10]
        ]

        lines = [
            f"Dataset: {filename}",
            f"Nombre de résultats correspondants: {total}",
            "",
        ]

        for index, row in enumerate(
            selected_rows,
            start=1,
        ):
            if dataset_type == "marches":
                lines.extend(
                    [
                        f"Résultat {index}:",
                        (
                            "Numéro: "
                            f"{row.get('numero', '')}"
                        ),
                        (
                            "Objet: "
                            f"{row.get('objet', '')}"
                        ),
                        (
                            "Catégorie: "
                            f"{row.get('categorie', '')}"
                        ),
                        (
                            "Zone: "
                            f"{row.get('zone', '')}"
                        ),
                        (
                            "Statut: "
                            f"{row.get('statut', '')}"
                        ),
                        (
                            "Budget estimé: "
                            f"{row.get('budget_estime_mad', '')} MAD"
                        ),
                        (
                            "Date limite: "
                            f"{row.get('date_limite', '')}"
                        ),
                        "",
                    ]
                )

            elif dataset_type == "projets_irrigation":
                lines.extend(
                    [
                        f"Résultat {index}:",
                        (
                            "Projet: "
                            f"{row.get('projet_id', '')}"
                        ),
                        (
                            "Type: "
                            f"{row.get('type_projet', '')}"
                        ),
                        (
                            "Zone: "
                            f"{row.get('zone', '')}"
                        ),
                        (
                            "Statut: "
                            f"{row.get('statut', '')}"
                        ),
                        (
                            "Avancement: "
                            f"{row.get('avancement_percent', '')}%"
                        ),
                        (
                            "Surface: "
                            f"{row.get('surface_ha', '')} ha"
                        ),
                        "",
                    ]
                )

            elif dataset_type == "bons_commande":
                lines.extend(
                    [
                        f"Résultat {index}:",
                        (
                            "Numéro: "
                            f"{row.get('numero', '')}"
                        ),
                        (
                            "Objet: "
                            f"{row.get('objet', '')}"
                        ),
                        (
                            "Statut: "
                            f"{row.get('statut', '')}"
                        ),
                        (
                            "Fournisseur: "
                            f"{row.get('fournisseur', '')}"
                        ),
                        (
                            "Montant: "
                            f"{row.get('montant_mad', '')} MAD"
                        ),
                        "",
                    ]
                )

            elif dataset_type == "fournisseurs":
                lines.extend(
                    [
                        f"Résultat {index}:",
                        (
                            "ID: "
                            f"{row.get('fournisseur_id', '')}"
                        ),
                        (
                            "Raison sociale: "
                            f"{row.get('raison_sociale', '')}"
                        ),
                        (
                            "Ville: "
                            f"{row.get('ville', '')}"
                        ),
                        (
                            "Spécialité: "
                            f"{row.get('specialite', '')}"
                        ),
                        "",
                    ]
                )

        if total > len(selected_rows):
            lines.append(
                
                    f"{total - len(selected_rows)} "
                    "autres résultats correspondent également "
                    "à la recherche."
                
            )

        return KnowledgeMatch(
            source=filename,
            content="\n".join(lines),
            score=1.0,
            chunk_index=None,
            page=None,
        )

    @staticmethod
    def _is_list_or_count_query(
        normalized_query: str,
    ) -> bool:
        list_terms = (
            "quels ",
            "quelles ",
            "liste",
            "lister",
            "affiche",
            "afficher",
            "combien",
            "nombre",
            "tous les",
            "toutes les",
            "en cours",
        )

        return any(
            term in normalized_query
            for term in list_terms
        )

    # =========================================================
    # GENERAL DOCUMENT RETRIEVAL
    # =========================================================

    def _search_general(
        self,
        *,
        query: str,
        limit: int,
    ) -> list[KnowledgeMatch]:
        query_tokens = self._tokenize(query)

        matches: list[KnowledgeMatch] = []

        for path in self._knowledge_files():
            if path.suffix.lower() == ".csv":
                matches.extend(
                    self._search_csv_general(
                        path=path,
                        query_tokens=query_tokens,
                    )
                )
            else:
                matches.extend(
                    self._search_document_general(
                        path=path,
                        query_tokens=query_tokens,
                    )
                )

        matches.sort(
            key=lambda match: match.score,
            reverse=True,
        )

        return matches[:limit]

    def _search_document_general(
        self,
        *,
        path: Path,
        query_tokens: set[str],
    ) -> list[KnowledgeMatch]:
        content = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        sections = self._split_document(
            content
        )

        matches: list[KnowledgeMatch] = []

        for chunk_index, section in enumerate(
            sections,
            start=1,
        ):
            section_tokens = self._tokenize(
                section
            )

            common = (
                query_tokens
                & section_tokens
            )

            if not common:
                continue

            score = (
                len(common)
                / max(
                    len(query_tokens),
                    1,
                )
            )

            score += self._general_source_bonus(
                path.name,
                query_tokens,
            )

            matches.append(
                KnowledgeMatch(
                    source=path.name,
                    content=section.strip(),
                    score=min(
                        score,
                        0.99,
                    ),
                    chunk_index=chunk_index,
                    page=self._page_for_chunk(
                        section
                    ),
                )
            )

        return matches

    def _search_csv_general(
        self,
        *,
        path: Path,
        query_tokens: set[str],
    ) -> list[KnowledgeMatch]:
        rows = self._read_csv(path)

        matches: list[KnowledgeMatch] = []

        for row_index, row in enumerate(
            rows,
            start=1,
        ):
            content = self._format_row(row)

            content_tokens = self._tokenize(
                content
            )

            common = (
                query_tokens
                & content_tokens
            )

            if not common:
                continue

            score = (
                len(common)
                / max(
                    len(query_tokens),
                    1,
                )
            )

            matches.append(
                KnowledgeMatch(
                    source=path.name,
                    content=content,
                    score=min(
                        score,
                        0.95,
                    ),
                    chunk_index=row_index,
                    page=None,
                )
            )

        return matches

    def _general_source_bonus(
        self,
        source_name: str,
        query_tokens: set[str],
    ) -> float:
        normalized_source = self._normalize_text(
            source_name
        )

        bonus = 0.0

        if (
            "ormvao" in query_tokens
            and normalized_source == "ormvao.md"
        ):
            bonus += 0.40

        platform_terms = {
            "kubernetes",
            "ollama",
            "vllm",
            "grafana",
            "prometheus",
            "rag",
            "benchmark",
            "devops",
            "docker",
            "plateforme",
        }

        if (
            query_tokens
            & platform_terms
            and normalized_source
            == "private_llm_platform.md"
        ):
            bonus += 0.40

        return bonus

    # =========================================================
    # FILE / TEXT UTILITIES
    # =========================================================

    def _knowledge_files(
        self,
    ) -> list[Path]:
        """Return searchable files."""

        if not self._knowledge_directory.exists():
            return []

        return sorted(
            path
            for path
            in self._knowledge_directory.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in SUPPORTED_EXTENSIONS
                and path.name
                not in IGNORED_FILENAMES
            )
        )

    @staticmethod
    def _read_csv(
        path: Path,
    ) -> list[dict[str, str]]:
        """Read a CSV database safely."""

        with path.open(
            "r",
            encoding="utf-8-sig",
            errors="replace",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            return [
                {
                    str(key).strip(): (
                        ""
                        if value is None
                        else str(value).strip()
                    )
                    for key, value
                    in row.items()
                }
                for row in reader
            ]

    @staticmethod
    def _format_row(
        row: dict[str, str],
    ) -> str:
        """Convert a structured row to LLM-friendly text."""

        lines = []

        for key, value in row.items():
            if not value:
                continue

            lines.append(
                f"{key}: {value}"
            )

        return "\n".join(lines)

    @staticmethod
    def _split_document(
        content: str,
    ) -> list[str]:
        """Keep Markdown headings with their content."""

        lines = content.splitlines()

        sections: list[str] = []
        current: list[str] = []

        for line in lines:
            stripped = line.strip()

            if (
                stripped.startswith("#")
                and current
            ):
                section = "\n".join(
                    current
                ).strip()

                if section:
                    sections.append(section)

                current = [line]
            else:
                current.append(line)

        if current:
            section = "\n".join(
                current
            ).strip()

            if section:
                sections.append(section)

        final_sections: list[str] = []

        for section in sections:
            if len(section) <= 1800:
                final_sections.append(
                    section
                )
            else:
                final_sections.extend(
                    LocalKnowledgeRetriever
                    ._split_large_section(
                        section
                    )
                )

        return final_sections

    @staticmethod
    def _split_large_section(
        section: str,
    ) -> list[str]:
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(
                r"\n\s*\n",
                section,
            )
            if paragraph.strip()
        ]

        chunks: list[str] = []
        current: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(
                paragraph
            )

            if (
                current
                and current_length
                + paragraph_length
                > 1800
            ):
                chunks.append(
                    "\n\n".join(
                        current
                    )
                )

                current = []
                current_length = 0

            current.append(
                paragraph
            )

            current_length += (
                paragraph_length
                + 2
            )

        if current:
            chunks.append(
                "\n\n".join(
                    current
                )
            )

        return chunks

    @staticmethod
    def _page_for_chunk(
        chunk: str,
    ) -> int | None:
        match = re.search(
            r"\bpage\s+(\d+)\b",
            chunk,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return int(
            match.group(1)
        )

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        normalized = unicodedata.normalize(
            "NFKD",
            text.lower(),
        )

        return "".join(
            character
            for character
            in normalized
            if not unicodedata.combining(
                character
            )
        )

    @classmethod
    def _tokenize(
        cls,
        text: str,
    ) -> set[str]:
        normalized_text = cls._normalize_text(
            text
        )

        raw_tokens = re.findall(
            r"\b[\w.-]+\b",
            normalized_text,
            flags=re.UNICODE,
        )

        tokens: set[str] = set()

        for token in raw_tokens:
            if (
                len(token) <= 2
                or token in STOP_WORDS
            ):
                continue

            tokens.add(
                token
            )

            if (
                len(token) > 4
                and token.endswith("s")
            ):
                tokens.add(
                    token[:-1]
                )

        return tokens