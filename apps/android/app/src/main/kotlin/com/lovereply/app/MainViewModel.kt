package com.lovereply.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.love_reply.generated.model.CommunicationGoal
import com.love_reply.generated.model.RelationshipStage
import com.lovereply.app.data.LoveReplyRepository
import com.lovereply.app.domain.ApiFailure
import com.lovereply.app.domain.AppBootstrap
import com.lovereply.app.domain.ComposerDraft
import com.lovereply.app.domain.EntitlementSummary
import com.lovereply.app.domain.GenerationPhase
import com.lovereply.app.domain.GenerationQuoteSummary
import com.lovereply.app.domain.GenerationResult
import com.lovereply.app.domain.LoginChannel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class AppScreen {
    LOGIN,
    COMPOSER,
    RESULT,
}

data class LoginUiState(
    val selectedChannel: LoginChannel = LoginChannel.EMAIL,
    val email: String = "",
    val countryCode: String = "+86",
    val phoneNumber: String = "",
    val verificationCode: String = "",
    val challengeId: String? = null,
    val resendSeconds: Int = 0,
    val maskedDestination: String? = null,
    val channelPolicyLoading: Boolean = true,
    val emailAvailable: Boolean = true,
    val smsAvailable: Boolean = false,
    val channelPolicyVersion: Int? = null,
)

data class MainUiState(
    val screen: AppScreen = AppScreen.LOGIN,
    val login: LoginUiState = LoginUiState(),
    val bootstrap: AppBootstrap? = null,
    val draft: ComposerDraft = ComposerDraft(),
    val entitlement: EntitlementSummary? = null,
    val quote: GenerationQuoteSummary? = null,
    val generation: GenerationResult? = null,
    val busy: Boolean = false,
    val busyLabel: String? = null,
    val errorMessage: String? = null,
    val errorCode: String? = null,
)

class MainViewModel(
    private val repository: LoveReplyRepository,
) : ViewModel() {
    private val mutableState = MutableStateFlow(
        MainUiState(screen = if (repository.hasSession()) AppScreen.COMPOSER else AppScreen.LOGIN),
    )
    val state: StateFlow<MainUiState> = mutableState.asStateFlow()

    private var countdownJob: Job? = null
    private var pollingJob: Job? = null

    init {
        loadBootstrap()
        if (repository.hasSession()) {
            refreshEntitlements()
        } else {
            loadAuthChannels()
        }
    }

    fun selectLoginChannel(channel: LoginChannel) {
        val login = state.value.login
        if (channel == login.selectedChannel) return
        if (channel == LoginChannel.SMS && !login.smsAvailable) return
        if (channel == LoginChannel.EMAIL && !login.emailAvailable) return
        countdownJob?.cancel()
        updateLogin {
            copy(
                selectedChannel = channel,
                verificationCode = "",
                challengeId = null,
                resendSeconds = 0,
                maskedDestination = null,
            )
        }
    }

    fun updateEmail(value: String) = updateLogin {
        copy(email = value.trim().take(254), challengeId = null, maskedDestination = null)
    }

    fun updateCountryCode(value: String) = updateLogin {
        copy(countryCode = value.filter { it == '+' || it.isDigit() }.take(4))
    }

    fun updatePhone(value: String) = updateLogin {
        copy(phoneNumber = value.filter(Char::isDigit).take(15), challengeId = null)
    }

    fun updateVerificationCode(value: String) = updateLogin {
        copy(verificationCode = value.filter(Char::isDigit).take(8))
    }

    fun sendVerificationCode() {
        val login = state.value.login
        when (login.selectedChannel) {
            LoginChannel.EMAIL -> if (!login.email.isValidEmail()) {
                setError("请输入正确的邮箱地址", "INVALID_EMAIL")
                return
            }
            LoginChannel.SMS -> if (login.phoneNumber.length !in 6..15) {
                setError("请输入正确的手机号", "INVALID_PHONE")
                return
            }
        }
        launchAction("正在发送验证码") {
            val challenge = when (login.selectedChannel) {
                LoginChannel.EMAIL -> repository.sendEmail(login.email)
                LoginChannel.SMS -> repository.sendSms(login.countryCode, login.phoneNumber)
            }
            mutableState.value = state.value.copy(
                login = state.value.login.copy(
                    challengeId = challenge.id,
                    resendSeconds = challenge.resendAfterSeconds,
                    maskedDestination = challenge.maskedDestination,
                ),
                errorMessage = null,
                errorCode = null,
            )
            startCountdown()
        }
    }

    fun login() {
        val login = state.value.login
        val challengeId = login.challengeId
        if (challengeId == null) {
            setError("请先获取验证码", "CHALLENGE_REQUIRED")
            return
        }
        if (login.verificationCode.length !in 4..8) {
            setError("请输入验证码", "INVALID_CODE")
            return
        }
        launchAction("正在登录") {
            when (login.selectedChannel) {
                LoginChannel.EMAIL -> repository.loginWithEmail(challengeId, login.verificationCode)
                LoginChannel.SMS -> repository.loginWithSms(challengeId, login.verificationCode)
            }
            mutableState.value = state.value.copy(
                screen = AppScreen.COMPOSER,
                busy = false,
                busyLabel = null,
                errorMessage = null,
                errorCode = null,
            )
            refreshEntitlements()
        }
    }

    fun updateMessage(value: String) = updateDraft { copy(message = value.take(3000)) }

    fun updateRelationshipStage(value: RelationshipStage) = updateDraft {
        copy(relationshipStage = value)
    }

    fun updateCommunicationGoal(value: CommunicationGoal) = updateDraft {
        copy(communicationGoal = value)
    }

    fun toggleStyle(styleId: String) = updateDraft {
        val next = if (styleId in styleIds) styleIds - styleId else styleIds + styleId
        copy(styleIds = next.ifEmpty { setOf(styleId) })
    }

    fun updateAdditionalContext(value: String) = updateDraft {
        copy(additionalContext = value.take(500))
    }

    fun requestQuote() {
        val draft = state.value.draft
        if (draft.message.isBlank()) {
            setError("请先粘贴或输入对方说的话", "INPUT_REQUIRED")
            return
        }
        launchAction("正在计算本次用量") {
            val quote = repository.quote(draft)
            mutableState.value = state.value.copy(
                quote = quote,
                busy = false,
                busyLabel = null,
                errorMessage = null,
                errorCode = null,
            )
        }
    }

    fun confirmGeneration() {
        val current = state.value
        val quote = current.quote ?: return
        launchAction("正在创建回复") {
            val generation = repository.create(current.draft, quote)
            mutableState.value = state.value.copy(
                screen = AppScreen.RESULT,
                generation = generation,
                busy = generation.phase == GenerationPhase.WORKING,
                busyLabel = generation.statusLabel.toStatusLabel(),
                errorMessage = null,
                errorCode = null,
            )
            if (generation.phase == GenerationPhase.WORKING) {
                startPolling(generation.id)
            } else {
                handleTerminalGeneration(generation)
            }
        }
    }

    fun retryGeneration() {
        pollingJob?.cancel()
        mutableState.value = state.value.copy(
            screen = AppScreen.COMPOSER,
            quote = null,
            generation = null,
            busy = false,
            busyLabel = null,
            errorMessage = null,
            errorCode = null,
        )
        requestQuote()
    }

    fun editDraft() {
        pollingJob?.cancel()
        mutableState.value = state.value.copy(
            screen = AppScreen.COMPOSER,
            quote = null,
            generation = null,
            busy = false,
            busyLabel = null,
            errorMessage = null,
            errorCode = null,
        )
    }

    fun clearError() {
        mutableState.value = state.value.copy(errorMessage = null, errorCode = null)
    }

    private fun startPolling(generationId: String) {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            repeat(MAX_POLL_ATTEMPTS) {
                delay(POLL_INTERVAL_MILLIS)
                try {
                    val generation = repository.getGeneration(generationId)
                    mutableState.value = state.value.copy(
                        generation = generation,
                        busy = generation.phase == GenerationPhase.WORKING,
                        busyLabel = generation.statusLabel.toStatusLabel(),
                    )
                    if (generation.phase != GenerationPhase.WORKING) {
                        handleTerminalGeneration(generation)
                        return@launch
                    }
                } catch (error: ApiFailure) {
                    if (!error.retryable) {
                        showFailure(error)
                        return@launch
                    }
                }
            }
            setError("生成仍在处理中，可稍后重试查询", "POLL_TIMEOUT")
            mutableState.value = state.value.copy(busy = false, busyLabel = null)
        }
    }

    private fun handleTerminalGeneration(generation: GenerationResult) {
        mutableState.value = state.value.copy(
            generation = generation,
            busy = false,
            busyLabel = null,
            errorMessage = when (generation.phase) {
                GenerationPhase.FAILED -> generation.failureCode.toFailureMessage()
                GenerationPhase.CANCELLED -> "本次生成已取消，额度不会被扣除"
                else -> null
            },
            errorCode = generation.failureCode,
        )
        refreshEntitlements()
    }

    private fun refreshEntitlements() {
        viewModelScope.launch {
            try {
                val entitlement = repository.getEntitlements()
                val allowedStyles = entitlement.allowedStyleIds
                val selectedStyles = state.value.draft.styleIds.intersect(allowedStyles)
                val firstAllowedStyle = state.value.bootstrap?.styles
                    ?.firstOrNull { it.id in allowedStyles }
                    ?.id
                    ?: allowedStyles.firstOrNull()
                mutableState.value = state.value.copy(
                    entitlement = entitlement,
                    draft = state.value.draft.copy(
                        styleIds = selectedStyles.ifEmpty {
                            firstAllowedStyle?.let(::setOf).orEmpty()
                        },
                    ),
                )
            } catch (error: ApiFailure) {
                if (error.code in SESSION_ERROR_CODES) {
                    repository.clearSession()
                    mutableState.value = MainUiState(
                        screen = AppScreen.LOGIN,
                        errorMessage = error.message,
                        errorCode = error.code,
                    )
                }
            }
        }
    }

    private fun loadBootstrap() {
        viewModelScope.launch {
            try {
                val bootstrap = repository.getBootstrap() ?: return@launch
                mutableState.value = state.value.copy(
                    bootstrap = bootstrap,
                    draft = state.value.draft.copy(
                        styleIds = state.value.draft.styleIds.ifEmpty { bootstrap.defaultStyleIds }
                    ),
                )
            } catch (_: ApiFailure) {
                // Login remains usable while the public bootstrap endpoint recovers.
            }
        }
    }

    private fun loadAuthChannels() {
        viewModelScope.launch {
            try {
                val policy = repository.getAuthChannels()
                val emailAvailable = LoginChannel.EMAIL in policy.availableChannels
                val smsAvailable = LoginChannel.SMS in policy.availableChannels
                val selectedChannel = if (emailAvailable || !smsAvailable) {
                    LoginChannel.EMAIL
                } else {
                    LoginChannel.SMS
                }
                mutableState.value = state.value.copy(
                    login = state.value.login.copy(
                        selectedChannel = selectedChannel,
                        channelPolicyLoading = false,
                        emailAvailable = emailAvailable,
                        smsAvailable = smsAvailable,
                        channelPolicyVersion = policy.policyVersion,
                    ),
                )
            } catch (_: ApiFailure) {
                mutableState.value = state.value.copy(
                    login = state.value.login.copy(channelPolicyLoading = false),
                )
            }
        }
    }

    private fun launchAction(label: String, action: suspend () -> Unit) {
        if (state.value.busy) return
        mutableState.value = state.value.copy(
            busy = true,
            busyLabel = label,
            errorMessage = null,
            errorCode = null,
        )
        viewModelScope.launch {
            try {
                action()
            } catch (error: ApiFailure) {
                showFailure(error)
            } catch (_: Exception) {
                setError("出现未预期的问题，请稍后重试", "UNEXPECTED_ERROR")
            } finally {
                if (state.value.screen != AppScreen.RESULT || state.value.generation == null) {
                    mutableState.value = state.value.copy(busy = false, busyLabel = null)
                }
            }
        }
    }

    private fun showFailure(error: ApiFailure) {
        if (error.code in SESSION_ERROR_CODES) {
            repository.clearSession()
            mutableState.value = MainUiState(
                screen = AppScreen.LOGIN,
                errorMessage = error.message,
                errorCode = error.code,
            )
        } else {
            setError(error.message, error.code)
        }
    }

    private fun setError(message: String, code: String) {
        mutableState.value = state.value.copy(
            busy = false,
            busyLabel = null,
            errorMessage = message,
            errorCode = code,
        )
    }

    private fun updateLogin(transform: LoginUiState.() -> LoginUiState) {
        mutableState.value = state.value.copy(
            login = state.value.login.transform(),
            errorMessage = null,
            errorCode = null,
        )
    }

    private fun updateDraft(transform: ComposerDraft.() -> ComposerDraft) {
        mutableState.value = state.value.copy(
            draft = state.value.draft.transform(),
            quote = null,
            errorMessage = null,
            errorCode = null,
        )
    }

    private fun startCountdown() {
        countdownJob?.cancel()
        countdownJob = viewModelScope.launch {
            while (state.value.login.resendSeconds > 0) {
                delay(1000)
                updateLogin { copy(resendSeconds = (resendSeconds - 1).coerceAtLeast(0)) }
            }
        }
    }

    companion object {
        private const val MAX_POLL_ATTEMPTS = 80
        private const val POLL_INTERVAL_MILLIS = 1_500L
        private val SESSION_ERROR_CODES = setOf(
            "SESSION_EXPIRED",
            "SESSION_REQUIRED",
            "TOKEN_EXPIRED",
        )

        fun factory(repository: LoveReplyRepository): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    MainViewModel(repository) as T
            }
    }
}

private fun String.toStatusLabel(): String = when (this) {
    "CREATED", "QUOTA_RESERVED" -> "已锁定额度，准备生成"
    "PARSING" -> "正在整理上下文"
    "ANALYZING" -> "正在分析语气和意图"
    "GENERATING" -> "正在生成三种回复"
    "FILTERING" -> "正在进行安全检查"
    else -> "正在处理"
}

private fun String?.toFailureMessage(): String = when (this) {
    "MODEL_PROVIDER_UNAVAILABLE" -> "生成服务暂时不可用，本次额度已释放"
    "GENERATION_TIMEOUT" -> "生成超时，本次额度已释放"
    "CONTENT_BLOCKED" -> "内容未通过安全检查，本次额度已释放"
    else -> "本次生成未完成，额度不会被扣除"
}

private fun String.isValidEmail(): Boolean =
    length in 3..254 && EMAIL_PATTERN.matches(this)

private val EMAIL_PATTERN = Regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")
