package com.lovereply.app.domain

import com.love_reply.generated.model.CommunicationGoal
import com.love_reply.generated.model.RelationshipStage

data class SmsChallenge(
    val id: String,
    val resendAfterSeconds: Int,
)

data class EntitlementSummary(
    val textRemaining: Int,
    val energyAvailable: Int,
    val allowedModelIds: Set<String>,
    val allowedStyleIds: Set<String>,
)

data class ComposerDraft(
    val message: String = "",
    val relationshipStage: RelationshipStage = RelationshipStage.DATING,
    val communicationGoal: CommunicationGoal = CommunicationGoal.KEEP_CONVERSATION,
    val styleIds: Set<String> = setOf("warm"),
    val additionalContext: String = "",
)

data class GenerationQuoteSummary(
    val id: String,
    val selectedModelId: String,
    val estimatedEnergy: Int,
    val expiresAtLabel: String,
)

data class ReplyAnalysis(
    val possibleIntent: String,
    val emotion: String,
    val uncertaintyNote: String,
    val riskTips: List<String>,
)

data class ReplyCandidate(
    val id: String,
    val strategy: String,
    val styleId: String,
    val text: String,
)

enum class GenerationPhase {
    WORKING,
    SUCCEEDED,
    FAILED,
    CANCELLED,
}

data class GenerationResult(
    val id: String,
    val phase: GenerationPhase,
    val statusLabel: String,
    val analysis: ReplyAnalysis? = null,
    val candidates: List<ReplyCandidate> = emptyList(),
    val chargedEnergy: Int? = null,
    val failureCode: String? = null,
)

class ApiFailure(
    val code: String,
    override val message: String,
    val retryable: Boolean,
) : Exception(message)
