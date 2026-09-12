"""Semantic trigger classification."""

from __future__ import annotations


class SemanticTrigger:
    """Classifies user input to determine if handshake should run."""

    @staticmethod
    def should_run_handshake(user_input: str) -> bool:
        """
        Detect if user input is technical/contextual.

        Returns True if handshake should run automatically.
        """
        if not user_input:
            return False

        input_lower = user_input.lower()

        technical_keywords = [
            "estou conectado",
            "connected",
            "status",
            "health",
            "handshake",
            "verificar",
            "validate",
            "codigo",
            "code",
            "arquivo",
            "file",
            "implementar",
            "implement",
            "arquitetura",
            "architecture",
            "estrutura",
            "structure",
            "projeto",
            "project",
            ".providence",
            "governance",
            "mandates",
            "guidelines",
            "spec",
            "fase",
            "phase",
            "wizard",
            ".vscode",
            ".cursor",
            ".github",
        ]

        casual_keywords = [
            "oi",
            "ola",
            "hello world",
            "hi there",
            "obrigado",
            "thanks for",
            "muito legal",
            "pretty cool",
            "que legal",
            "muito nice",
            "como voce esta",
            "how are you",
            "qual seu nome",
            "your name",
            "qual e seu nome",
            "piada",
            "joke",
            "meme",
            "funny",
        ]

        for casual_kw in casual_keywords:
            if (
                casual_kw in input_lower
                and not any(
                    tech_kw in input_lower
                    for tech_kw in [
                        ".providence",
                        ".vscode",
                        ".cursor",
                        "-architecture",
                        "-project",
                    ]
                )
                and (
                    len(casual_kw.split()) > 1
                    or casual_kw
                    in [
                        " oi ",
                        " ola ",
                        " hi ",
                        "obrigado",
                    ]
                )
            ):
                return False

        return any(kw in input_lower for kw in technical_keywords)
