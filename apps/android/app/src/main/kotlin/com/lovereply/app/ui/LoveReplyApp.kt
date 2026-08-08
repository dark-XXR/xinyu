package com.lovereply.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.love_reply.generated.model.CommunicationGoal
import com.love_reply.generated.model.RelationshipStage
import com.lovereply.app.AppScreen
import com.lovereply.app.MainUiState
import com.lovereply.app.domain.EntitlementSummary
import com.lovereply.app.domain.GenerationPhase
import com.lovereply.app.domain.GenerationQuoteSummary
import com.lovereply.app.domain.GenerationResult
import com.lovereply.app.domain.ReplyCandidate

private data class LabeledValue<T>(val value: T, val label: String)

private val relationshipOptions = listOf(
    LabeledValue(RelationshipStage.MATCHING, "刚认识"),
    LabeledValue(RelationshipStage.DATING, "约会中"),
    LabeledValue(RelationshipStage.AMBIGUOUS, "暧昧期"),
    LabeledValue(RelationshipStage.IN_RELATIONSHIP, "恋爱中"),
    LabeledValue(RelationshipStage.CONFLICT, "有矛盾"),
    LabeledValue(RelationshipStage.NO_CONTACT, "断联中"),
    LabeledValue(RelationshipStage.OTHER, "其他"),
)

private val goalOptions = listOf(
    LabeledValue(CommunicationGoal.KEEP_CONVERSATION, "继续聊下去"),
    LabeledValue(CommunicationGoal.START_CONVERSATION, "开启话题"),
    LabeledValue(CommunicationGoal.ACCEPT_INVITATION, "接受邀请"),
    LabeledValue(CommunicationGoal.DECLINE_POLITELY, "礼貌拒绝"),
    LabeledValue(CommunicationGoal.INVITE_DATE, "发起约会"),
    LabeledValue(CommunicationGoal.APOLOGIZE, "认真道歉"),
    LabeledValue(CommunicationGoal.SET_BOUNDARY, "表达边界"),
    LabeledValue(CommunicationGoal.RESOLVE_CONFLICT, "缓和矛盾"),
    LabeledValue(CommunicationGoal.OTHER, "其他"),
)

private val styleOptions = listOf(
    "warm" to "温柔",
    "humorous" to "幽默",
    "steady" to "稳重",
    "concise" to "简洁",
)

@Composable
fun LoveReplyApp(
    state: MainUiState,
    onCountryCodeChange: (String) -> Unit,
    onPhoneChange: (String) -> Unit,
    onVerificationCodeChange: (String) -> Unit,
    onSendSms: () -> Unit,
    onLogin: () -> Unit,
    onMessageChange: (String) -> Unit,
    onRelationshipChange: (RelationshipStage) -> Unit,
    onGoalChange: (CommunicationGoal) -> Unit,
    onStyleToggle: (String) -> Unit,
    onAdditionalContextChange: (String) -> Unit,
    onRequestQuote: () -> Unit,
    onConfirmGeneration: () -> Unit,
    onRetry: () -> Unit,
    onEditDraft: () -> Unit,
    onDismissError: () -> Unit,
    onCopy: (String) -> Unit,
) {
    Scaffold(
        modifier = Modifier.fillMaxSize(),
        contentWindowInsets = WindowInsets.safeDrawing,
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        when (state.screen) {
            AppScreen.LOGIN -> LoginScreen(
                state = state,
                onCountryCodeChange = onCountryCodeChange,
                onPhoneChange = onPhoneChange,
                onVerificationCodeChange = onVerificationCodeChange,
                onSendSms = onSendSms,
                onLogin = onLogin,
                onDismissError = onDismissError,
                modifier = Modifier.padding(padding),
            )

            AppScreen.COMPOSER -> ComposerScreen(
                state = state,
                onMessageChange = onMessageChange,
                onRelationshipChange = onRelationshipChange,
                onGoalChange = onGoalChange,
                onStyleToggle = onStyleToggle,
                onAdditionalContextChange = onAdditionalContextChange,
                onRequestQuote = onRequestQuote,
                onConfirmGeneration = onConfirmGeneration,
                onDismissError = onDismissError,
                modifier = Modifier.padding(padding),
            )

            AppScreen.RESULT -> ResultScreen(
                state = state,
                onRetry = onRetry,
                onEditDraft = onEditDraft,
                onDismissError = onDismissError,
                onCopy = onCopy,
                modifier = Modifier.padding(padding),
            )
        }
    }
}

@Composable
private fun LoginScreen(
    state: MainUiState,
    onCountryCodeChange: (String) -> Unit,
    onPhoneChange: (String) -> Unit,
    onVerificationCodeChange: (String) -> Unit,
    onSendSms: () -> Unit,
    onLogin: () -> Unit,
    onDismissError: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .imePadding()
            .padding(horizontal = 24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "会回",
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            text = "先登录，再把难回的话交给我",
            modifier = Modifier.padding(top = 8.dp, bottom = 32.dp),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        state.errorMessage?.let {
            ErrorBanner(it, onDismissError, Modifier.padding(bottom = 16.dp))
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(
                value = state.login.countryCode,
                onValueChange = onCountryCodeChange,
                modifier = Modifier.width(92.dp),
                label = { Text("区号") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            )
            OutlinedTextField(
                value = state.login.phoneNumber,
                onValueChange = onPhoneChange,
                modifier = Modifier
                    .weight(1f)
                    .testTag("phone_input"),
                label = { Text("手机号") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            )
        }

        Spacer(Modifier.height(12.dp))
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = state.login.verificationCode,
                onValueChange = onVerificationCodeChange,
                modifier = Modifier
                    .weight(1f)
                    .testTag("code_input"),
                label = { Text("验证码") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            )
            OutlinedButton(
                onClick = onSendSms,
                enabled = !state.busy && state.login.resendSeconds == 0,
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 14.dp),
            ) {
                Text(
                    if (state.login.resendSeconds > 0) "${state.login.resendSeconds}s" else "获取验证码",
                    maxLines = 1,
                )
            }
        }

        Button(
            onClick = onLogin,
            enabled = !state.busy,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 20.dp)
                .height(52.dp)
                .testTag("login_button"),
            shape = RoundedCornerShape(8.dp),
        ) {
            BusyButtonContent(state.busy, state.busyLabel ?: "登录")
        }

        Row(
            modifier = Modifier.padding(top = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Default.Lock,
                contentDescription = null,
                modifier = Modifier.size(16.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = "验证码仅用于账户登录",
                modifier = Modifier.padding(start = 6.dp),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ComposerScreen(
    state: MainUiState,
    onMessageChange: (String) -> Unit,
    onRelationshipChange: (RelationshipStage) -> Unit,
    onGoalChange: (CommunicationGoal) -> Unit,
    onStyleToggle: (String) -> Unit,
    onAdditionalContextChange: (String) -> Unit,
    onRequestQuote: () -> Unit,
    onConfirmGeneration: () -> Unit,
    onDismissError: () -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .imePadding(),
        contentPadding = PaddingValues(bottom = 28.dp),
    ) {
        item {
            Column(Modifier.padding(horizontal = 20.dp, vertical = 18.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Bottom,
                ) {
                    Column {
                        Text(
                            text = "帮我回",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "输入上下文，生成三种不同策略",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    state.entitlement?.let { EntitlementLabel(it) }
                }

                state.errorMessage?.let {
                    ErrorBanner(it, onDismissError, Modifier.padding(top = 16.dp))
                }

                OutlinedTextField(
                    value = state.draft.message,
                    onValueChange = onMessageChange,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(172.dp)
                        .padding(top = 20.dp)
                        .testTag("message_input"),
                    label = { Text("对方说了什么") },
                    placeholder = { Text("例如：对方：周末有空吗？") },
                    supportingText = { Text("${state.draft.message.length}/3000") },
                )
            }
        }

        item { HorizontalDivider() }

        item {
            Column(
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(
                    text = "这段关系",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                SelectionMenu(
                    label = "关系阶段",
                    selected = relationshipOptions.first { it.value == state.draft.relationshipStage }.label,
                    options = relationshipOptions,
                    onSelect = { onRelationshipChange(it.value) },
                )
                SelectionMenu(
                    label = "这次想达到",
                    selected = goalOptions.first { it.value == state.draft.communicationGoal }.label,
                    options = goalOptions,
                    onSelect = { onGoalChange(it.value) },
                )

                Text(
                    text = "回复风格",
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    styleOptions.forEach { (id, label) ->
                        FilterChip(
                            selected = id in state.draft.styleIds,
                            onClick = { onStyleToggle(id) },
                            label = { Text(label) },
                            leadingIcon = if (id in state.draft.styleIds) {
                                {
                                    Icon(
                                        Icons.Default.CheckCircle,
                                        contentDescription = null,
                                        modifier = Modifier.size(16.dp),
                                    )
                                }
                            } else null,
                        )
                    }
                }

                OutlinedTextField(
                    value = state.draft.additionalContext,
                    onValueChange = onAdditionalContextChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("补充背景（可选）") },
                    placeholder = { Text("例如：希望自然一点，不要太主动") },
                    minLines = 2,
                    maxLines = 4,
                    supportingText = { Text("${state.draft.additionalContext.length}/500") },
                )
            }
        }

        item {
            state.quote?.let {
                QuoteConfirmation(
                    quote = it,
                    busy = state.busy,
                    busyLabel = state.busyLabel,
                    onConfirm = onConfirmGeneration,
                    modifier = Modifier.padding(horizontal = 20.dp),
                )
            } ?: Button(
                onClick = onRequestQuote,
                enabled = !state.busy && state.draft.message.isNotBlank(),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
                    .height(52.dp)
                    .testTag("quote_button"),
                shape = RoundedCornerShape(8.dp),
            ) {
                BusyButtonContent(state.busy, state.busyLabel ?: "查看用量并生成")
            }
        }
    }
}

@Composable
private fun QuoteConfirmation(
    quote: GenerationQuoteSummary,
    busy: Boolean,
    busyLabel: String?,
    onConfirm: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.primaryContainer,
        shape = RoundedCornerShape(8.dp),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("本次预计用量", style = MaterialTheme.typography.labelLarge)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 4.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = "${quote.estimatedEnergy} 能量",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = "报价有效至 ${quote.expiresAtLabel}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Button(
                    onClick = onConfirm,
                    enabled = !busy,
                    modifier = Modifier.testTag("generate_button"),
                    shape = RoundedCornerShape(8.dp),
                ) {
                    BusyButtonContent(busy, busyLabel ?: "确认生成")
                }
            }
        }
    }
}

@Composable
private fun ResultScreen(
    state: MainUiState,
    onRetry: () -> Unit,
    onEditDraft: () -> Unit,
    onDismissError: () -> Unit,
    onCopy: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val result = state.generation
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 32.dp),
    ) {
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onEditDraft) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回编辑")
                }
                Column(Modifier.weight(1f)) {
                    Text(
                        text = "回复建议",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = result?.statusLabel?.toReadableStatus() ?: "正在创建",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                result?.chargedEnergy?.let {
                    Text(
                        text = "已用 $it 能量",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        if (state.busy || result?.phase == GenerationPhase.WORKING) {
            item {
                LinearProgressIndicator(
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("generation_progress"),
                )
                Text(
                    text = state.busyLabel ?: "正在生成",
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
        }

        state.errorMessage?.let { message ->
            item {
                ErrorBanner(
                    message = message,
                    onDismiss = onDismissError,
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
                )
            }
        }

        if (result?.phase == GenerationPhase.FAILED || result?.phase == GenerationPhase.CANCELLED) {
            item {
                Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
                    Button(
                        onClick = onRetry,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                            .testTag("retry_button"),
                        shape = RoundedCornerShape(8.dp),
                    ) {
                        Text("保留原文重新报价")
                    }
                    TextButton(
                        onClick = onEditDraft,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("返回修改")
                    }
                }
            }
        }

        result?.analysis?.let { analysis ->
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
                ) {
                    Column(Modifier.padding(horizontal = 20.dp, vertical = 18.dp)) {
                        Text("对话分析", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        AnalysisLine("可能意图", analysis.possibleIntent)
                        AnalysisLine("情绪", analysis.emotion)
                        Text(
                            text = analysis.uncertaintyNote,
                            modifier = Modifier.padding(top = 10.dp),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        analysis.riskTips.forEach { tip ->
                            Text(
                                text = "• $tip",
                                modifier = Modifier.padding(top = 6.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.secondary,
                            )
                        }
                    }
                }
            }
        }

        if (!result?.candidates.isNullOrEmpty()) {
            item {
                Text(
                    text = "三种回复策略",
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
            }
            items(result!!.candidates, key = ReplyCandidate::id) { candidate ->
                CandidateCard(
                    candidate = candidate,
                    onCopy = onCopy,
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
                )
            }
        }
    }
}

@Composable
private fun CandidateCard(
    candidate: ReplyCandidate,
    onCopy: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .testTag("candidate_${candidate.strategy}"),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = CardDefaults.outlinedCardBorder(),
    ) {
        Column(Modifier.padding(start = 16.dp, top = 14.dp, end = 8.dp, bottom = 14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = candidate.strategy.toStrategyLabel(),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = candidate.styleId.toStyleLabel(),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                IconButton(onClick = { onCopy(candidate.text) }) {
                    Icon(Icons.Default.ContentCopy, contentDescription = "复制回复")
                }
            }
            Text(
                text = candidate.text,
                modifier = Modifier.padding(top = 10.dp, end = 8.dp),
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}

@Composable
private fun ErrorBanner(
    message: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.errorContainer,
        shape = RoundedCornerShape(8.dp),
    ) {
        Row(
            modifier = Modifier.padding(start = 14.dp, top = 8.dp, bottom = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = message,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onErrorContainer,
            )
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, contentDescription = "关闭提示")
            }
        }
    }
}

@Composable
private fun <T> SelectionMenu(
    label: String,
    selected: String,
    options: List<LabeledValue<T>>,
    onSelect: (LabeledValue<T>) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { expanded = true },
            shape = RoundedCornerShape(8.dp),
            border = CardDefaults.outlinedCardBorder(),
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = selected,
                        style = MaterialTheme.typography.bodyLarge,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Icon(Icons.Default.ExpandMore, contentDescription = "展开选项")
            }
        }
        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
            modifier = Modifier.fillMaxWidth(0.88f),
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.label) },
                    onClick = {
                        expanded = false
                        onSelect(option)
                    },
                )
            }
        }
    }
}

@Composable
private fun EntitlementLabel(entitlement: EntitlementSummary) {
    Column(horizontalAlignment = Alignment.End) {
        Text(
            text = "剩余 ${entitlement.textRemaining} 次",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = "${entitlement.energyAvailable} 能量",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun AnalysisLine(label: String, value: String) {
    Row(Modifier.padding(top = 12.dp)) {
        Text(
            text = label,
            modifier = Modifier.width(72.dp),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(text = value, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun BusyButtonContent(busy: Boolean, label: String) {
    if (busy) {
        CircularProgressIndicator(
            modifier = Modifier.size(18.dp),
            strokeWidth = 2.dp,
            color = MaterialTheme.colorScheme.onPrimary,
        )
        Spacer(Modifier.width(8.dp))
    }
    Text(label, maxLines = 1, overflow = TextOverflow.Ellipsis)
}

private fun String.toStrategyLabel(): String = when (this) {
    "SAFE" -> "稳妥回应"
    "PUSH_PULL" -> "留有张力"
    "DIRECT" -> "直接表达"
    else -> this
}

private fun String.toStyleLabel(): String = styleOptions.firstOrNull { it.first == this }?.second ?: this

private fun String.toReadableStatus(): String = when (this) {
    "SUCCEEDED" -> "已生成并通过安全检查"
    "FAILED" -> "生成未完成"
    "CANCELLED" -> "已取消"
    "ANALYZING" -> "正在分析"
    "GENERATING" -> "正在生成"
    "FILTERING" -> "正在安全检查"
    else -> "处理中"
}
