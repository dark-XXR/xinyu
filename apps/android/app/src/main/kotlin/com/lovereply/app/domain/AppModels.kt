package com.lovereply.app.domain

import com.love_reply.generated.model.CommunicationGoal
import com.love_reply.generated.model.RelationshipStage

enum class LoginChannel {
    EMAIL,
    SMS,
}

data class LoginChannelPolicy(
    val availableChannels: Set<LoginChannel>,
    val policyVersion: Int,
)

data class LoginChallenge(
    val id: String,
    val resendAfterSeconds: Int,
    val maskedDestination: String? = null,
)

data class AppBootstrap(
    val configVersion: Int,
    val styles: List<ReplyStyleOption>,
    val defaultStyleIds: Set<String>,
)

data class ReplyStyleOption(
    val id: String,
    val label: String,
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
    val styleIds: Set<String> = emptySet(),
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
