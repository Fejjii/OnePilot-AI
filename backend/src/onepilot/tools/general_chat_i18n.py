"""Localized general-chat template responses."""

from __future__ import annotations

from onepilot.core.constants import LanguageCode

CAPABILITY_RESPONSE: dict[LanguageCode, str] = {
    LanguageCode.EN: """I can help you with:

**Knowledge & Search**
- Answer questions from your knowledge base with citations
- Search through documents and guides

**Email & Communication**
- Draft professional emails and replies
- Compose follow-up messages for leads

**Lead Management**
- Qualify and capture new leads
- Track customer inquiries
- Recommend next actions for prospects

**Workflows & Actions**
- Schedule meetings and appointments
- Update CRM records
- Summarize documents

**Visibility & Control**
- All actions are logged for audit
- Memory of conversation context
- Usage tracking and diagnostics
- Speech-to-text input support

You can ask me questions like:
- "What are our integration options?"
- "Draft a follow-up email for this lead"
- "Summarize this document"
- "What's our refund policy?"

How can I help you today?""",
    LanguageCode.DE: """Ich kann Ihnen helfen mit:

**Wissen & Suche**
- Fragen aus Ihrer Wissensdatenbank mit Quellenangaben beantworten
- Dokumente und Leitfäden durchsuchen

**E-Mail & Kommunikation**
- Professionelle E-Mails und Antworten entwerfen
- Follow-up-Nachrichten für Leads verfassen

**Lead-Management**
- Neue Leads qualifizieren und erfassen
- Kundenanfragen verfolgen
- Nächste Schritte für Interessenten empfehlen

**Workflows & Aktionen**
- Meetings und Termine planen
- CRM-Datensätze aktualisieren
- Dokumente zusammenfassen

**Transparenz & Kontrolle**
- Alle Aktionen werden protokolliert
- Gesprächskontext
- Nutzungsverfolgung und Diagnose
- Spracheingabe (Speech-to-Text)

Beispielfragen:
- „Welche Integrationen bieten wir?“
- „Entwirf eine Follow-up-E-Mail für diesen Lead“
- „Fasse dieses Dokument zusammen“

Wie kann ich Ihnen heute helfen?""",
    LanguageCode.FR: """Je peux vous aider avec :

**Connaissances & recherche**
- Répondre aux questions à partir de votre base de connaissances avec citations
- Parcourir documents et guides

**E-mail & communication**
- Rédiger des e-mails professionnels et des réponses
- Composer des relances pour les leads

**Gestion des leads**
- Qualifier et capturer de nouveaux leads
- Suivre les demandes clients
- Recommander les prochaines actions

**Workflows & actions**
- Planifier des réunions
- Mettre à jour le CRM
- Résumer des documents

**Visibilité & contrôle**
- Journalisation des actions
- Mémoire de conversation
- Suivi d'utilisation et diagnostics
- Saisie vocale (speech-to-text)

Exemples de questions :
- « Quelles sont nos options d'intégration ? »
- « Rédige un e-mail de relance pour ce lead »

Comment puis-je vous aider aujourd'hui ?""",
    LanguageCode.ES: """Puedo ayudarle con:

**Conocimiento y búsqueda**
- Responder preguntas desde su base de conocimiento con citas
- Buscar en documentos y guías

**Correo y comunicación**
- Redactar correos profesionales y respuestas
- Componer seguimientos para leads

**Gestión de leads**
- Calificar y capturar nuevos leads
- Seguir consultas de clientes
- Recomendar próximos pasos

**Flujos de trabajo y acciones**
- Programar reuniones
- Actualizar registros CRM
- Resumir documentos

**Visibilidad y control**
- Registro de auditoría de acciones
- Memoria de conversación
- Seguimiento de uso y diagnósticos
- Entrada por voz (speech-to-text)

Ejemplos:
- « ¿Qué opciones de integración tenemos? »
- « Redacta un correo de seguimiento para este lead »

¿En qué puedo ayudarle hoy?""",
}

OUT_OF_SCOPE_RESPONSE: dict[LanguageCode, str] = {
    LanguageCode.EN: (
        "I'm built for business productivity (knowledge search, leads, email "
        "drafts, workflows, etc.) and can't help with that. Try rephrasing as a work task, "
        "or let me know what business goal you're trying to achieve."
    ),
    LanguageCode.DE: (
        "Ich bin für geschäftliche Produktivität (Wissenssuche, Leads, E-Mails, "
        "Workflows usw.) gebaut und kann dabei nicht helfen. Formulieren Sie es als "
        "Arbeitsaufgabe oder nennen Sie Ihr geschäftliches Ziel."
    ),
    LanguageCode.FR: (
        "Je suis conçu pour la productivité professionnelle (recherche documentaire, "
        "leads, e-mails, workflows, etc.) et je ne peux pas aider avec cela. "
        "Reformulez en tâche métier ou indiquez votre objectif."
    ),
    LanguageCode.ES: (
        "Estoy diseñado para productividad empresarial (búsqueda de conocimiento, "
        "leads, correos, flujos de trabajo, etc.) y no puedo ayudar con eso. "
        "Reformúlelo como tarea de trabajo o indique su objetivo."
    ),
}


def get_capability(lang: str) -> str:
    try:
        code = LanguageCode(str(lang).lower())
    except ValueError:
        code = LanguageCode.EN
    return CAPABILITY_RESPONSE.get(code, CAPABILITY_RESPONSE[LanguageCode.EN])


def get_out_of_scope(lang: str) -> str:
    try:
        code = LanguageCode(str(lang).lower())
    except ValueError:
        code = LanguageCode.EN
    return OUT_OF_SCOPE_RESPONSE.get(code, OUT_OF_SCOPE_RESPONSE[LanguageCode.EN])
