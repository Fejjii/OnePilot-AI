"""Localized template messages for workflow guardrails and general chat."""

from __future__ import annotations

from onepilot.core.constants import LanguageCode

WEAK_EVIDENCE: dict[LanguageCode, str] = {
    LanguageCode.EN: (
        "I couldn't find enough information in the knowledge base to answer that "
        "confidently. I've flagged this for a teammate to follow up."
    ),
    LanguageCode.DE: (
        "Ich konnte in der Wissensdatenbank nicht genug Informationen finden, um "
        "das sicher zu beantworten. Ich habe dies für ein Teammitglied zur Nachverfolgung markiert."
    ),
    LanguageCode.FR: (
        "Je n'ai pas trouvé suffisamment d'informations dans la base de connaissances "
        "pour répondre avec confiance. J'ai signalé cela à un collègue pour suivi."
    ),
    LanguageCode.ES: (
        "No encontré suficiente información en la base de conocimiento para responder "
        "con confianza. Lo he marcado para que un compañero le dé seguimiento."
    ),
}

OUT_OF_SCOPE: dict[LanguageCode, str] = {
    LanguageCode.EN: (
        "I'm built for business productivity (knowledge search, leads, email "
        "drafts, etc.) and can't help with that. Try rephrasing as a work task."
    ),
    LanguageCode.DE: (
        "Ich bin für geschäftliche Produktivität (Wissenssuche, Leads, E-Mails usw.) "
        "gebaut und kann dabei nicht helfen. Formulieren Sie es bitte als Arbeitsaufgabe um."
    ),
    LanguageCode.FR: (
        "Je suis conçu pour la productivité professionnelle (recherche documentaire, "
        "leads, e-mails, etc.) et je ne peux pas aider avec cela. Reformulez en tâche métier."
    ),
    LanguageCode.ES: (
        "Estoy diseñado para productividad empresarial (búsqueda de conocimiento, leads, "
        "correos, etc.) y no puedo ayudar con eso. Reformúlelo como una tarea de trabajo."
    ),
}

CLARIFICATION: dict[LanguageCode, str] = {
    LanguageCode.EN: (
        "Could you share a bit more detail? For example: what outcome you want, "
        "who it's for, and any deadline."
    ),
    LanguageCode.DE: (
        "Können Sie etwas mehr Details nennen? Zum Beispiel: gewünschtes Ergebnis, "
        "für wen es ist und ob es eine Frist gibt."
    ),
    LanguageCode.FR: (
        "Pouvez-vous préciser un peu ? Par exemple : le résultat souhaité, "
        "pour qui c'est, et une échéance éventuelle."
    ),
    LanguageCode.ES: (
        "¿Puede dar un poco más de detalle? Por ejemplo: el resultado deseado, "
        "para quién es y si hay una fecha límite."
    ),
}

RAG_WEAK_EVIDENCE: dict[LanguageCode, str] = {
    LanguageCode.EN: (
        "I don't have a confident answer based on the knowledge I have. "
        "I'm forwarding this to a human teammate."
    ),
    LanguageCode.DE: (
        "Ich habe keine sichere Antwort auf Basis des verfügbaren Wissens. "
        "Ich leite dies an einen menschlichen Kollegen weiter."
    ),
    LanguageCode.FR: (
        "Je n'ai pas de réponse fiable d'après les connaissances disponibles. "
        "Je transmets cela à un collègue humain."
    ),
    LanguageCode.ES: (
        "No tengo una respuesta segura según el conocimiento disponible. "
        "Lo reenvío a un compañero humano."
    ),
}

APPROVAL_FOOTNOTE: dict[LanguageCode, str] = {
    LanguageCode.EN: "\n\n*Pending approval before any external action is taken.*",
    LanguageCode.DE: "\n\n*Genehmigung ausstehend, bevor eine externe Aktion ausgeführt wird.*",
    LanguageCode.FR: "\n\n*Approbation en attente avant toute action externe.*",
    LanguageCode.ES: "\n\n*Aprobación pendiente antes de ejecutar cualquier acción externa.*",
}


def get_message(table: dict[LanguageCode, str], lang: LanguageCode | str) -> str:
    try:
        code = lang if isinstance(lang, LanguageCode) else LanguageCode(str(lang).lower())
    except ValueError:
        code = LanguageCode.EN
    return table.get(code, table[LanguageCode.EN])
