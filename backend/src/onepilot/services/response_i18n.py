"""Localized labels for generated user-facing assistant prose.

Used by email wrapping, web/RAG section headings, calendar status copy, and
deterministic fallback drafts. Source titles, URLs, names, and other literals
are not translated here — callers must pass them through unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from onepilot.core.constants import LanguageCode


def coerce_language(code: LanguageCode | str | None) -> LanguageCode:
    """Map a stored/response language value to a supported code."""
    if isinstance(code, LanguageCode):
        return code
    try:
        return LanguageCode(str(code or "en").lower())
    except ValueError:
        return LanguageCode.EN


@dataclass(frozen=True, slots=True)
class ResponseCopy:
    """User-facing generated labels for one response language."""

    summary_heading: str
    key_points_heading: str
    top_findings_heading: str
    sources_heading: str
    evidence_heading: str
    next_action_heading: str
    no_strong_points: str
    no_web_sources: str
    web_unconfigured_summary: str
    web_limited_summary: str
    web_related_summary: str
    web_unconfigured_next: str
    web_refine_next: str
    web_see_original_excerpt: str
    combined_research_for: str
    combined_with_internal: str
    combined_web_unconfigured: str
    combined_internal_limited: str
    internal_knowledge_label: str
    web_sources_label: str
    internal_first_prefix: str
    external_first_prefix: str
    internal_kb_weak_point: str
    internal_weak_block: str
    combined_next_both_weak: str
    combined_next_internal_weak: str
    combined_next_web_weak: str
    combined_next_align: str
    rag_next_action: str
    rag_empty_summary: str
    email_recipient_label: str
    email_subject_label: str
    email_approval_label: str
    email_approval_pending: str
    email_approval_not_required: str
    email_recipient_unspecified: str
    email_preview_only: str
    email_gmail_created: str
    email_default_subject: str
    email_subject_with_company: str
    email_subject_with_name: str
    email_greeting_named: str
    email_greeting_generic: str
    email_followup_company: str
    email_followup_generic: str
    email_mentioned: str
    email_next_step: str
    email_intro_call: str
    email_conversation: str
    email_signoff: str
    calendar_upcoming: str
    calendar_upcoming_window: str
    calendar_no_meetings_window: str
    calendar_no_meetings: str
    calendar_timezone_footer: str
    calendar_unavailable: str
    calendar_available_slots: str
    calendar_open_not_meetings: str
    calendar_open_tomorrow_afternoon: str
    calendar_open_window: str
    calendar_no_open_times: str
    calendar_that_time_open: str
    calendar_that_time_busy: str
    calendar_that_time_busy_short: str
    calendar_that_time_open_short: str
    calendar_available_meeting_times: str
    calendar_open_slots_not_meetings: str
    calendar_no_suggested: str
    calendar_suggested_next_week: str
    calendar_suggested_this_week: str
    calendar_date_tbc: str
    calendar_title_label: str
    calendar_when_label: str
    calendar_timezone_label: str
    calendar_approval_label: str
    calendar_next_action_label: str
    calendar_next_action: str
    calendar_created_after_approve: str
    calendar_attendees_label: str
    calendar_default_title: str
    compound_email_heading: str
    compound_calendar_heading: str
    compound_research_heading: str
    compound_email_preview_heading: str
    compound_meeting_heading: str
    empty_response: str


_EN = ResponseCopy(
    summary_heading="Summary",
    key_points_heading="Key points",
    top_findings_heading="Top findings",
    sources_heading="Sources",
    evidence_heading="Evidence or sources",
    next_action_heading="Suggested next action",
    no_strong_points="No strong points were extracted from the available sources.",
    no_web_sources="No external web sources were retrieved.",
    web_unconfigured_summary=(
        "External web search is not configured (SERPER_API_KEY is missing). "
        "Live web results are unavailable for this query."
    ),
    web_limited_summary=(
        "External web search was attempted but returned limited or mock results. "
        "Treat the evidence below as incomplete."
    ),
    web_related_summary="Retrieved web sources related to: {query}.",
    web_unconfigured_next=(
        "Configure SERPER_API_KEY to research '{query}' with live web results."
    ),
    web_refine_next="Refine the search query or try a more specific timeframe or topic.",
    web_see_original_excerpt="See the original excerpt under Sources.",
    combined_research_for="Combined research for: {query}.",
    combined_with_internal=(
        "External web search (Serper) was combined with internal company knowledge."
    ),
    combined_web_unconfigured=(
        "External web search is not configured; internal knowledge was used where available."
    ),
    combined_internal_limited=(
        "Internal knowledge base coverage was limited for this comparison."
    ),
    internal_knowledge_label="Internal knowledge",
    web_sources_label="Web sources",
    internal_first_prefix="Internal: {sentence}.",
    external_first_prefix="External: {title} — {finding}",
    internal_kb_weak_point="Internal KB did not provide confident coverage for this topic.",
    internal_weak_block=(
        "The knowledge base did not contain enough confident information for this comparison."
    ),
    combined_next_both_weak=(
        "Refresh internal service documentation and configure live web search "
        "to improve comparisons for '{query}'."
    ),
    combined_next_internal_weak=(
        "Refresh internal service documentation to strengthen the NovaEdge comparison."
    ),
    combined_next_web_weak=(
        "Configure SERPER_API_KEY to enrich market research for '{query}'."
    ),
    combined_next_align=(
        "Align external trend signals with NovaEdge offerings where they strengthen positioning."
    ),
    rag_next_action=(
        "Review the cited internal documents and confirm details with your team if needed."
    ),
    rag_empty_summary="The knowledge base contains relevant information on this topic.",
    email_recipient_label="Recipient",
    email_subject_label="Subject",
    email_approval_label="Approval status",
    email_approval_pending="pending",
    email_approval_not_required="not required",
    email_recipient_unspecified="Not specified",
    email_preview_only="Preview only — Gmail draft was not created.",
    email_gmail_created="Gmail draft created. Send remains disabled.",
    email_default_subject="Following up",
    email_subject_with_company="Following up with {company}",
    email_subject_with_name="Following up with {name}",
    email_greeting_named="Hi {name},",
    email_greeting_generic="Hello,",
    email_followup_company="I wanted to follow up with you at {company}.",
    email_followup_generic="I wanted to follow up as you requested.",
    email_mentioned="You mentioned {pain}.",
    email_next_step="Suggested next step: {action}",
    email_intro_call="If a short intro call would help, please share a time that works.",
    email_conversation="Please let me know if a short conversation would be helpful.",
    email_signoff="Best regards,\nThe OnePilot team",
    calendar_upcoming="Upcoming meetings",
    calendar_upcoming_window="Upcoming meetings {window}",
    calendar_no_meetings_window="No meetings are on the calendar {window}.",
    calendar_no_meetings="No meetings are on the calendar in that window.",
    calendar_timezone_footer="Times shown in {timezone}.",
    calendar_unavailable="I couldn't {action} right now. Please try again in a moment.",
    calendar_available_slots="Available time slots:",
    calendar_open_not_meetings="These are open times, not existing meetings.",
    calendar_open_tomorrow_afternoon="Open times tomorrow afternoon:",
    calendar_open_window="Open times {window}:",
    calendar_no_open_times="No open times in the requested window.",
    calendar_that_time_open="That time is open ({when}).",
    calendar_that_time_busy=(
        "That time is not open ({at_time}). It overlaps an existing meeting."
    ),
    calendar_that_time_busy_short="That time overlaps an existing meeting.",
    calendar_that_time_open_short="That time is open.",
    calendar_available_meeting_times="Available meeting times:",
    calendar_open_slots_not_meetings="These are open slots you can book, not existing meetings.",
    calendar_no_suggested="No open meeting times could be suggested for that window.",
    calendar_suggested_next_week="Suggested open times next week:",
    calendar_suggested_this_week="Suggested open times this week:",
    calendar_date_tbc="To be confirmed",
    calendar_title_label="Title",
    calendar_when_label="Date and time",
    calendar_timezone_label="Timezone",
    calendar_approval_label="Approval status",
    calendar_next_action_label="Next action",
    calendar_next_action="Review and approve to create this meeting.",
    calendar_created_after_approve="This meeting will be created only after you approve it.",
    calendar_attendees_label="Attendees",
    calendar_default_title="Meeting",
    compound_email_heading="Email draft",
    compound_calendar_heading="Calendar proposal",
    compound_research_heading="External market research",
    compound_email_preview_heading="Draft email preview",
    compound_meeting_heading="Meeting proposal",
    empty_response="I don't have a response for that yet.",
)

_DE = ResponseCopy(
    summary_heading="Zusammenfassung",
    key_points_heading="Kernpunkte",
    top_findings_heading="Wichtigste Erkenntnisse",
    sources_heading="Quellen",
    evidence_heading="Belege oder Quellen",
    next_action_heading="Vorgeschlagene nächste Aktion",
    no_strong_points="Aus den verfügbaren Quellen konnten keine starken Punkte extrahiert werden.",
    no_web_sources="Es wurden keine externen Webquellen abgerufen.",
    web_unconfigured_summary=(
        "Die externe Websuche ist nicht konfiguriert (SERPER_API_KEY fehlt). "
        "Live-Web-Ergebnisse sind für diese Anfrage nicht verfügbar."
    ),
    web_limited_summary=(
        "Die externe Websuche wurde versucht, lieferte aber begrenzte oder simulierte Ergebnisse. "
        "Die folgenden Belege sind unvollständig."
    ),
    web_related_summary="Abgerufene Webquellen zu: {query}.",
    web_unconfigured_next=(
        "Konfigurieren Sie SERPER_API_KEY, um '{query}' mit Live-Web-Ergebnissen zu recherchieren."
    ),
    web_refine_next="Verfeinern Sie die Suchanfrage oder wählen Sie einen engeren Zeitraum oder ein engeres Thema.",
    web_see_original_excerpt="Siehe den Originalauszug unter Quellen.",
    combined_research_for="Kombinierte Recherche für: {query}.",
    combined_with_internal=(
        "Externe Websuche (Serper) wurde mit internem Unternehmenswissen kombiniert."
    ),
    combined_web_unconfigured=(
        "Externe Websuche ist nicht konfiguriert; internes Wissen wurde soweit verfügbar genutzt."
    ),
    combined_internal_limited=(
        "Die Abdeckung der internen Wissensdatenbank war für diesen Vergleich begrenzt."
    ),
    internal_knowledge_label="Internes Wissen",
    web_sources_label="Webquellen",
    internal_first_prefix="Intern: {sentence}.",
    external_first_prefix="Extern: {title} — {finding}",
    internal_kb_weak_point="Die interne Wissensdatenbank bot zu diesem Thema keine sichere Abdeckung.",
    internal_weak_block=(
        "Die Wissensdatenbank enthielt für diesen Vergleich nicht genug belastbare Informationen."
    ),
    combined_next_both_weak=(
        "Aktualisieren Sie die interne Dokumentation und konfigurieren Sie die Live-Websuche, "
        "um Vergleiche für '{query}' zu verbessern."
    ),
    combined_next_internal_weak=(
        "Aktualisieren Sie die interne Dokumentation, um den NovaEdge-Vergleich zu stärken."
    ),
    combined_next_web_weak=(
        "Konfigurieren Sie SERPER_API_KEY, um die Marktrecherche für '{query}' zu ergänzen."
    ),
    combined_next_align=(
        "Stimmen Sie externe Trendsignale mit NovaEdge-Angeboten ab, wo sie die Positionierung stärken."
    ),
    rag_next_action=(
        "Prüfen Sie die zitierten internen Dokumente und bestätigen Sie Details bei Bedarf im Team."
    ),
    rag_empty_summary="Die Wissensdatenbank enthält relevante Informationen zu diesem Thema.",
    email_recipient_label="Empfänger",
    email_subject_label="Betreff",
    email_approval_label="Genehmigungsstatus",
    email_approval_pending="ausstehend",
    email_approval_not_required="nicht erforderlich",
    email_recipient_unspecified="Nicht angegeben",
    email_preview_only="Nur Vorschau — es wurde kein Gmail-Entwurf erstellt.",
    email_gmail_created="Gmail-Entwurf erstellt. Das Senden bleibt deaktiviert.",
    email_default_subject="Nachfrage",
    email_subject_with_company="Nachfrage bei {company}",
    email_subject_with_name="Nachfrage bei {name}",
    email_greeting_named="Hallo {name},",
    email_greeting_generic="Hallo,",
    email_followup_company="Ich wollte bei Ihnen bei {company} nachfassen.",
    email_followup_generic="Ich wollte wie gewünscht nachfassen.",
    email_mentioned="Sie haben {pain} erwähnt.",
    email_next_step="Vorgeschlagener nächster Schritt: {action}",
    email_intro_call="Wenn ein kurzes Kennenlerngespräch hilfreich wäre, teilen Sie uns gerne einen Termin mit.",
    email_conversation="Lassen Sie mich wissen, ob ein kurzes Gespräch hilfreich wäre.",
    email_signoff="Mit freundlichen Grüßen\nDas OnePilot-Team",
    calendar_upcoming="Anstehende Meetings",
    calendar_upcoming_window="Anstehende Meetings {window}",
    calendar_no_meetings_window="Im Kalender stehen {window} keine Meetings.",
    calendar_no_meetings="Im Kalender stehen in diesem Zeitraum keine Meetings.",
    calendar_timezone_footer="Zeiten angezeigt in {timezone}.",
    calendar_unavailable="Ich konnte {action} gerade nicht ausführen. Bitte versuchen Sie es in einem Moment erneut.",
    calendar_available_slots="Verfügbare Zeitfenster:",
    calendar_open_not_meetings="Das sind freie Zeiten, keine bestehenden Meetings.",
    calendar_open_tomorrow_afternoon="Freie Zeiten morgen Nachmittag:",
    calendar_open_window="Freie Zeiten {window}:",
    calendar_no_open_times="Keine freien Zeiten im angefragten Zeitraum.",
    calendar_that_time_open="Dieser Zeitpunkt ist frei ({when}).",
    calendar_that_time_busy=(
        "Dieser Zeitpunkt ist nicht frei ({at_time}). Er überschneidet sich mit einem bestehenden Meeting."
    ),
    calendar_that_time_busy_short="Dieser Zeitpunkt überschneidet sich mit einem bestehenden Meeting.",
    calendar_that_time_open_short="Dieser Zeitpunkt ist frei.",
    calendar_available_meeting_times="Verfügbare Meeting-Zeiten:",
    calendar_open_slots_not_meetings="Das sind buchbare freie Slots, keine bestehenden Meetings.",
    calendar_no_suggested="Für diesen Zeitraum konnten keine freien Meeting-Zeiten vorgeschlagen werden.",
    calendar_suggested_next_week="Vorgeschlagene freie Zeiten nächste Woche:",
    calendar_suggested_this_week="Vorgeschlagene freie Zeiten diese Woche:",
    calendar_date_tbc="Noch zu bestätigen",
    calendar_title_label="Titel",
    calendar_when_label="Datum und Uhrzeit",
    calendar_timezone_label="Zeitzone",
    calendar_approval_label="Genehmigungsstatus",
    calendar_next_action_label="Nächste Aktion",
    calendar_next_action="Prüfen und genehmigen, um dieses Meeting zu erstellen.",
    calendar_created_after_approve="Dieses Meeting wird erst nach Ihrer Genehmigung erstellt.",
    calendar_attendees_label="Teilnehmer",
    calendar_default_title="Meeting",
    compound_email_heading="E-Mail-Entwurf",
    compound_calendar_heading="Kalendervorschlag",
    compound_research_heading="Externe Marktrecherche",
    compound_email_preview_heading="E-Mail-Vorschau",
    compound_meeting_heading="Meetingvorschlag",
    empty_response="Ich habe dazu noch keine Antwort.",
)

_FR = ResponseCopy(
    summary_heading="Résumé",
    key_points_heading="Points clés",
    top_findings_heading="Principales conclusions",
    sources_heading="Sources",
    evidence_heading="Preuves ou sources",
    next_action_heading="Prochaine action suggérée",
    no_strong_points="Aucun point fort n'a pu être extrait des sources disponibles.",
    no_web_sources="Aucune source web externe n'a été récupérée.",
    web_unconfigured_summary=(
        "La recherche web externe n'est pas configurée (SERPER_API_KEY manquante). "
        "Les résultats web en direct sont indisponibles pour cette requête."
    ),
    web_limited_summary=(
        "La recherche web externe a été tentée mais a renvoyé des résultats limités ou simulés. "
        "Traitez les éléments ci-dessous comme incomplets."
    ),
    web_related_summary="Sources web récupérées pour : {query}.",
    web_unconfigured_next=(
        "Configurez SERPER_API_KEY pour rechercher « {query} » avec des résultats web en direct."
    ),
    web_refine_next="Affinez la requête ou précisez une période ou un sujet.",
    web_see_original_excerpt="Voir l'extrait original dans les Sources.",
    combined_research_for="Recherche combinée pour : {query}.",
    combined_with_internal=(
        "La recherche web externe (Serper) a été combinée aux connaissances internes de l'entreprise."
    ),
    combined_web_unconfigured=(
        "La recherche web externe n'est pas configurée ; les connaissances internes ont été utilisées si disponibles."
    ),
    combined_internal_limited=(
        "La couverture de la base de connaissances interne était limitée pour cette comparaison."
    ),
    internal_knowledge_label="Connaissances internes",
    web_sources_label="Sources web",
    internal_first_prefix="Interne : {sentence}.",
    external_first_prefix="Externe : {title} — {finding}",
    internal_kb_weak_point="La base interne n'a pas fourni de couverture fiable pour ce sujet.",
    internal_weak_block=(
        "La base de connaissances ne contenait pas assez d'informations fiables pour cette comparaison."
    ),
    combined_next_both_weak=(
        "Mettez à jour la documentation interne et configurez la recherche web en direct "
        "pour améliorer les comparaisons de « {query} »."
    ),
    combined_next_internal_weak=(
        "Mettez à jour la documentation interne pour renforcer la comparaison NovaEdge."
    ),
    combined_next_web_weak=(
        "Configurez SERPER_API_KEY pour enrichir la veille marché sur « {query} »."
    ),
    combined_next_align=(
        "Alignez les signaux de tendance externes avec les offres NovaEdge lorsqu'ils renforcent le positionnement."
    ),
    rag_next_action=(
        "Relisez les documents internes cités et confirmez les détails avec votre équipe si besoin."
    ),
    rag_empty_summary="La base de connaissances contient des informations pertinentes sur ce sujet.",
    email_recipient_label="Destinataire",
    email_subject_label="Objet",
    email_approval_label="Statut d'approbation",
    email_approval_pending="en attente",
    email_approval_not_required="non requise",
    email_recipient_unspecified="Non précisé",
    email_preview_only="Aperçu uniquement — le brouillon Gmail n'a pas été créé.",
    email_gmail_created="Brouillon Gmail créé. L'envoi reste désactivé.",
    email_default_subject="Suivi",
    email_subject_with_company="Suivi avec {company}",
    email_subject_with_name="Suivi avec {name}",
    email_greeting_named="Bonjour {name},",
    email_greeting_generic="Bonjour,",
    email_followup_company="Je souhaitais faire un suivi avec vous chez {company}.",
    email_followup_generic="Je souhaitais faire un suivi comme demandé.",
    email_mentioned="Vous avez mentionné {pain}.",
    email_next_step="Prochaine étape suggérée : {action}",
    email_intro_call="Si un court appel d'introduction serait utile, n'hésitez pas à proposer un créneau.",
    email_conversation="Dites-moi si une courte conversation serait utile.",
    email_signoff="Cordialement,\nL'équipe OnePilot",
    calendar_upcoming="Réunions à venir",
    calendar_upcoming_window="Réunions à venir {window}",
    calendar_no_meetings_window="Aucune réunion n'est au calendrier {window}.",
    calendar_no_meetings="Aucune réunion n'est au calendrier sur cette période.",
    calendar_timezone_footer="Horaires indiqués en {timezone}.",
    calendar_unavailable="Je n'ai pas pu {action} pour le moment. Réessayez dans un instant.",
    calendar_available_slots="Créneaux disponibles :",
    calendar_open_not_meetings="Ce sont des horaires libres, pas des réunions existantes.",
    calendar_open_tomorrow_afternoon="Horaires libres demain après-midi :",
    calendar_open_window="Horaires libres {window} :",
    calendar_no_open_times="Aucun horaire libre sur la période demandée.",
    calendar_that_time_open="Ce créneau est libre ({when}).",
    calendar_that_time_busy=(
        "Ce créneau n'est pas libre ({at_time}). Il chevauche une réunion existante."
    ),
    calendar_that_time_busy_short="Ce créneau chevauche une réunion existante.",
    calendar_that_time_open_short="Ce créneau est libre.",
    calendar_available_meeting_times="Horaires de réunion disponibles :",
    calendar_open_slots_not_meetings="Ce sont des créneaux réservables, pas des réunions existantes.",
    calendar_no_suggested="Aucun horaire de réunion n'a pu être proposé pour cette période.",
    calendar_suggested_next_week="Horaires libres proposés la semaine prochaine :",
    calendar_suggested_this_week="Horaires libres proposés cette semaine :",
    calendar_date_tbc="À confirmer",
    calendar_title_label="Titre",
    calendar_when_label="Date et heure",
    calendar_timezone_label="Fuseau horaire",
    calendar_approval_label="Statut d'approbation",
    calendar_next_action_label="Prochaine action",
    calendar_next_action="Relisez et approuvez pour créer cette réunion.",
    calendar_created_after_approve="Cette réunion ne sera créée qu'après votre approbation.",
    calendar_attendees_label="Participants",
    calendar_default_title="Réunion",
    compound_email_heading="Brouillon d'e-mail",
    compound_calendar_heading="Proposition de calendrier",
    compound_research_heading="Recherche marché externe",
    compound_email_preview_heading="Aperçu de l'e-mail",
    compound_meeting_heading="Proposition de réunion",
    empty_response="Je n'ai pas encore de réponse à cela.",
)

_ES = ResponseCopy(
    summary_heading="Resumen",
    key_points_heading="Puntos clave",
    top_findings_heading="Hallazgos principales",
    sources_heading="Fuentes",
    evidence_heading="Evidencia o fuentes",
    next_action_heading="Siguiente acción sugerida",
    no_strong_points="No se extrajeron puntos sólidos de las fuentes disponibles.",
    no_web_sources="No se recuperaron fuentes web externas.",
    web_unconfigured_summary=(
        "La búsqueda web externa no está configurada (falta SERPER_API_KEY). "
        "No hay resultados web en vivo para esta consulta."
    ),
    web_limited_summary=(
        "Se intentó la búsqueda web externa, pero devolvió resultados limitados o simulados. "
        "Trate la evidencia siguiente como incompleta."
    ),
    web_related_summary="Fuentes web recuperadas relacionadas con: {query}.",
    web_unconfigured_next=(
        "Configure SERPER_API_KEY para investigar '{query}' con resultados web en vivo."
    ),
    web_refine_next="Refine la consulta o pruebe un periodo o tema más específico.",
    web_see_original_excerpt="Véase el extracto original en Fuentes.",
    combined_research_for="Investigación combinada para: {query}.",
    combined_with_internal=(
        "La búsqueda web externa (Serper) se combinó con el conocimiento interno de la empresa."
    ),
    combined_web_unconfigured=(
        "La búsqueda web externa no está configurada; se usó el conocimiento interno cuando estaba disponible."
    ),
    combined_internal_limited=(
        "La cobertura de la base de conocimiento interna fue limitada para esta comparación."
    ),
    internal_knowledge_label="Conocimiento interno",
    web_sources_label="Fuentes web",
    internal_first_prefix="Interno: {sentence}.",
    external_first_prefix="Externo: {title} — {finding}",
    internal_kb_weak_point="La base interna no ofreció cobertura fiable sobre este tema.",
    internal_weak_block=(
        "La base de conocimiento no contenía información suficientemente fiable para esta comparación."
    ),
    combined_next_both_weak=(
        "Actualice la documentación interna y configure la búsqueda web en vivo "
        "para mejorar las comparaciones de '{query}'."
    ),
    combined_next_internal_weak=(
        "Actualice la documentación interna para reforzar la comparación de NovaEdge."
    ),
    combined_next_web_weak=(
        "Configure SERPER_API_KEY para enriquecer la investigación de mercado de '{query}'."
    ),
    combined_next_align=(
        "Alinee las señales de tendencia externas con las ofertas de NovaEdge cuando refuercen el posicionamiento."
    ),
    rag_next_action=(
        "Revise los documentos internos citados y confirme los detalles con su equipo si hace falta."
    ),
    rag_empty_summary="La base de conocimiento contiene información relevante sobre este tema.",
    email_recipient_label="Destinatario",
    email_subject_label="Asunto",
    email_approval_label="Estado de aprobación",
    email_approval_pending="pendiente",
    email_approval_not_required="no requerida",
    email_recipient_unspecified="No especificado",
    email_preview_only="Solo vista previa: no se creó el borrador de Gmail.",
    email_gmail_created="Borrador de Gmail creado. El envío sigue desactivado.",
    email_default_subject="Seguimiento",
    email_subject_with_company="Seguimiento con {company}",
    email_subject_with_name="Seguimiento con {name}",
    email_greeting_named="Hola {name},",
    email_greeting_generic="Hola,",
    email_followup_company="Quería hacer un seguimiento con usted en {company}.",
    email_followup_generic="Quería hacer un seguimiento como solicitó.",
    email_mentioned="Mencionó {pain}.",
    email_next_step="Siguiente paso sugerido: {action}",
    email_intro_call="Si una breve llamada de presentación sería útil, comparta un horario que le convenga.",
    email_conversation="Dígame si una breve conversación sería útil.",
    email_signoff="Un cordial saludo,\nEl equipo de OnePilot",
    calendar_upcoming="Próximas reuniones",
    calendar_upcoming_window="Próximas reuniones {window}",
    calendar_no_meetings_window="No hay reuniones en el calendario {window}.",
    calendar_no_meetings="No hay reuniones en el calendario en esa ventana.",
    calendar_timezone_footer="Horarios mostrados en {timezone}.",
    calendar_unavailable="No pude {action} ahora mismo. Inténtelo de nuevo en un momento.",
    calendar_available_slots="Huecos disponibles:",
    calendar_open_not_meetings="Son horarios libres, no reuniones existentes.",
    calendar_open_tomorrow_afternoon="Horarios libres mañana por la tarde:",
    calendar_open_window="Horarios libres {window}:",
    calendar_no_open_times="No hay horarios libres en la ventana solicitada.",
    calendar_that_time_open="Ese horario está libre ({when}).",
    calendar_that_time_busy=(
        "Ese horario no está libre ({at_time}). Se solapa con una reunión existente."
    ),
    calendar_that_time_busy_short="Ese horario se solapa con una reunión existente.",
    calendar_that_time_open_short="Ese horario está libre.",
    calendar_available_meeting_times="Horarios de reunión disponibles:",
    calendar_open_slots_not_meetings="Son huecos reservables, no reuniones existentes.",
    calendar_no_suggested="No se pudieron sugerir horarios de reunión para esa ventana.",
    calendar_suggested_next_week="Horarios libres sugeridos la próxima semana:",
    calendar_suggested_this_week="Horarios libres sugeridos esta semana:",
    calendar_date_tbc="Por confirmar",
    calendar_title_label="Título",
    calendar_when_label="Fecha y hora",
    calendar_timezone_label="Zona horaria",
    calendar_approval_label="Estado de aprobación",
    calendar_next_action_label="Siguiente acción",
    calendar_next_action="Revise y apruebe para crear esta reunión.",
    calendar_created_after_approve="Esta reunión se creará solo después de que la apruebe.",
    calendar_attendees_label="Asistentes",
    calendar_default_title="Reunión",
    compound_email_heading="Borrador de correo",
    compound_calendar_heading="Propuesta de calendario",
    compound_research_heading="Investigación de mercado externa",
    compound_email_preview_heading="Vista previa del correo",
    compound_meeting_heading="Propuesta de reunión",
    empty_response="Todavía no tengo una respuesta para eso.",
)

_BY_LANG: dict[LanguageCode, ResponseCopy] = {
    LanguageCode.EN: _EN,
    LanguageCode.DE: _DE,
    LanguageCode.FR: _FR,
    LanguageCode.ES: _ES,
}


def response_copy(code: LanguageCode | str | None) -> ResponseCopy:
    """Return localized generated-prose labels for ``code``."""
    return _BY_LANG[coerce_language(code)]
